import base64
import os
import re
import subprocess
import tempfile
from pathlib import Path
from typing import List

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import HTMLResponse
from openai import OpenAI

# ---------- Configuration ----------
MODEL = os.getenv("LM_STUDIO_MODEL", "qwen/qwen3-vl-4b")
LM_STUDIO_URL = os.getenv("LM_STUDIO_BASE_URL", "http://localhost:1234/v1")
LM_STUDIO_API_KEY = os.getenv("LM_STUDIO_API_KEY", "lm-studio")
FPS = float(os.getenv("FRAME_FPS", "2.0"))
MAX_FRAMES = int(os.getenv("MAX_FRAMES", "12"))
SCALE = os.getenv("FRAME_SCALE", "448:-1")
ALLOWED_EVENTS = ["shot", "save", "goalkick", "corner", "freekick"]

app = FastAPI(title="Football Clip Event Predictor", version="0.1.0")


# ---------- Helper ----------
def _encode_image(image_path: str) -> str:
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode("utf-8")


# ---------- Frame extraction with scaling and limit ----------
def extract_frames(video_path: str, output_dir: str, fps: float = FPS, max_frames: int = MAX_FRAMES) -> List[str]:
    """
    Extract frames at a fixed fps, then subsample down to max_frames.

    Subsampling is weighted toward the END of the clip. Event outcomes
    (a save being made, the ball crossing the line, a kick connecting)
    almost always resolve in the final frames, so naive uniform striding
    can skip right over the frame that actually disambiguates the event.
    """
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    for old_file in Path(output_dir).glob("*.jpg"):
        old_file.unlink()

    command = [
        "ffmpeg", "-y", "-i", video_path,
        "-vf", f"fps={fps},scale={SCALE}",
        str(Path(output_dir) / "frame_%03d.jpg"),
    ]
    result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"ffmpeg failed: {result.stderr.strip() or result.stdout.strip()}")

    frame_paths = sorted(Path(output_dir).glob("*.jpg"))
    if not frame_paths:
        raise RuntimeError("No frames were extracted")

    if len(frame_paths) > max_frames:
        frame_paths = _select_weighted_frames(frame_paths, max_frames)

    return [str(path) for path in frame_paths]


def _select_weighted_frames(frame_paths: List[Path], max_frames: int) -> List[Path]:
    """
    Keep evenly-spaced coverage of the whole clip (context: setup, run-up,
    positioning) but guarantee the last few frames are always included
    (outcome: save, goal, block, ball leaving frame).
    """
    n = len(frame_paths)
    tail_count = min(3, max_frames // 3 or 1)  # reserve slots for the ending
    head_count = max_frames - tail_count

    head_idx = sorted(set(int(round(i * (n - 1) / max(head_count - 1, 1))) for i in range(head_count)))
    tail_idx = list(range(n - tail_count, n))

    keep_idx = sorted(set(head_idx) | set(tail_idx))
    return [frame_paths[i] for i in keep_idx]


# ---------- Build payload with detailed prompt ----------
def build_content_payload(frame_paths: List[str]) -> List[dict]:
    prompt = (
        "You are a football (soccer) event classifier. You are shown a sequence of "
        f"{len(frame_paths)} frames, in chronological order (frame 1 = earliest, "
        "frame N = latest), sampled from a short video clip.\n\n"
        "Identify the football event(s) happening in the clip. A clip often contains "
        "TWO chronological events (a setup/restart or strike, followed by its "
        "outcome) — report BOTH when that's the case, rather than collapsing them "
        "into one. Only report a single event if just one is actually present.\n\n"
        "Possible events and their visual clues:\n"
        "- shot: a player strikes the ball toward the goal.\n"
        "- save: the goalkeeper (or a defender on the line) blocks, catches, parries, "
        "or otherwise stops a shot that was headed toward goal.\n"
        "- goalkick: a stationary restart taken by the goalkeeper from inside their "
        "own six-yard box, after play had stopped.\n"
        "- freekick: a stationary restart following a foul, typically with a defensive "
        "wall of players standing close together between the ball and the goal.\n"
        "- corner: a restart taken from the corner arc at the very edge of the pitch "
        "(where the sideline meets the goal line), played into the penalty area. "
        "Do not confuse this with the D-shaped arc in front of the penalty box, or "
        "with general open play near the box.\n\n"
        "Common two-event sequences: a shot followed by a save; a corner/freekick/"
        "goalkick followed by a shot; a corner/freekick followed by a save. Judge "
        "each event by what actually happens across the frames, in chronological "
        "order (frame 1 -> frame N).\n\n"
        "Output format: for each event you identify (one or two, in the order they "
        "occur), output a block of exactly these two lines:\n"
        "EVENT: <event>\n"
        "REASON: <one sentence, citing what you see in the frames that supports it>\n"
        "where <event> is one of: shot, save, goalkick, freekick, corner.\n"
        "If there are two events, output the two blocks back to back, in "
        "chronological order, with nothing else before, between, or after them. "
        "If there is only one event, output only one block."
    )
    payload = [{"type": "text", "text": prompt}]
    for i, frame_path in enumerate(frame_paths, start=1):
        payload.append({"type": "text", "text": f"Frame {i}:"})
        payload.append({
            "type": "image_url",
            "image_url": {"url": f"data:image/jpeg;base64,{_encode_image(frame_path)}"}
        })
    return payload


# ---------- Parse response ----------
_EVENT_ALIASES = {
    "goalkick": ["goal kick", "goal-kick"],
    "freekick": ["free kick", "free-kick"],
    "corner": ["corner kick", "corner-kick"],
}


def _normalize_event(raw_event: str) -> str:
    text = raw_event.lower().strip()
    for event in ALLOWED_EVENTS:
        if re.search(rf"\b{re.escape(event)}\b", text):
            return event
    for event, values in _EVENT_ALIASES.items():
        for value in values:
            if value in text:
                return event
    return "unknown"


def parse_events_from_response(response_text: str) -> List[dict]:
    """
    Extract one or two (event, reason) pairs from the model's structured
    output. Expected shape, repeated once or twice, in order:
        EVENT: <event>
        REASON: <sentence>
    Falls back to a best-effort single-event scan if the model didn't
    follow the format.
    """
    blocks = re.findall(
        r"event:\s*([a-z\- ]+?)\s*\n\s*reason:\s*(.+?)(?=\n\s*event:|\Z)",
        response_text,
        flags=re.IGNORECASE | re.DOTALL,
    )

    events: List[dict] = []
    for raw_event, raw_reason in blocks:
        events.append({
            "event": _normalize_event(raw_event),
            "reason": raw_reason.strip().splitlines()[0].strip(),
        })

    if events:
        return events

    # Fallback: no structured blocks found, scan the whole text for any
    # known event keyword so we still return something usable.
    normalized = response_text.lower()
    for event in ALLOWED_EVENTS:
        if re.search(rf"\b{re.escape(event)}\b", normalized):
            return [{"event": event, "reason": response_text.strip()}]

    return [{"event": "unknown", "reason": response_text.strip()}]


# ---------- Core prediction ----------
def predict_event_from_video(video_path: str) -> dict:
    try:
        with tempfile.TemporaryDirectory(prefix="football-frames-", dir="/tmp") as frame_dir:
            frame_paths = extract_frames(video_path, frame_dir)
            payload = build_content_payload(frame_paths)

            client = OpenAI(base_url=LM_STUDIO_URL, api_key=LM_STUDIO_API_KEY)
            response = client.chat.completions.create(
                model=MODEL,
                messages=[{"role": "user", "content": payload}],
                temperature=0.0,
                max_tokens=300,  # room for up to two EVENT/REASON blocks
            )
            raw_response = response.choices[0].message.content.strip()
            events = parse_events_from_response(raw_response)
            return {
                "events": events,  # list of {"event": ..., "reason": ...}, chronological order
                "raw_response": raw_response,
            }
    except Exception as exc:
        raise RuntimeError(f"Prediction failed: {exc}") from exc


# ---------- FastAPI endpoints ----------
@app.get("/", response_class=HTMLResponse)
def index() -> str:
    index_path = Path(__file__).parent / "index.html"
    with open(index_path, "r", encoding="utf-8") as f:
        return f.read()


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.post("/predict")
async def predict(file: UploadFile = File(...)) -> dict:
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file uploaded")

    allowed_extensions = {".mp4", ".mov", ".avi", ".mkv", ".webm"}
    if Path(file.filename).suffix.lower() not in allowed_extensions:
        raise HTTPException(status_code=400, detail="Please upload a video file")

    with tempfile.NamedTemporaryFile(suffix=Path(file.filename).suffix or ".mp4", delete=False) as temp_file:
        contents = await file.read()
        temp_file.write(contents)
        temp_path = temp_file.name

    try:
        result = predict_event_from_video(temp_path)
        return result
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    finally:
        if os.path.exists(temp_path):
            os.unlink(temp_path)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("qwen_test:app", host="0.0.0.0", port=8000, reload=True)