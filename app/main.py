from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
from app.config import Settings
from app.downloader import YoutubeDownloader
# from app.queue.sqs_client import SqsClient
from app.s3_client import S3client
from contextlib import asynccontextmanager
import logging
from app.api.routes import router as match_router


logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

settings = Settings()

@asynccontextmanager
async def lifespan(app: FastAPI):
    s3_client = S3client(
        aws_access_key=settings.aws_access_key,
        aws_secret_key=settings.aws_secret_key,
        aws_region=settings.aws_region,
        aws_bucket=settings.aws_bucket
    )

    # sqs_client = SqsClient(
    #     aws_access_key=settings.aws_access_key,
    #     aws_region=settings.aws_region,
    #     aws_secret_key=settings.aws_secret_key,
    #     aws_queue_url=settings.aws_queue_url
    # )

    mongodb_client = AsyncIOMotorClient(settings.database_connection_string)
    mongodb = mongodb_client[settings.database_name]
    
    app.state.mongodb_client = mongodb_client
    app.state.mongodb = mongodb
    app.state.s3_client = s3_client
    app.state.logger = logger
    app.state.youtube_downloader = YoutubeDownloader()
    # app.state.sqs_client = sqs_client
    
    yield
    
    mongodb_client.close()

app = FastAPI(
    title="Afriskaut Match Uploader",
    description='Afriskaut Match Uploader API',
    version="1.0",
    lifespan=lifespan
)

origins = [
    "http://localhost",
    "http://localhost:3000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(match_router, prefix="/api")

@app.get("/")
async def root():
    return {"message": "Hello World"}
