from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):

    # S3 configs
    aws_access_key: str
    aws_secret_key: str
    aws_region: str
    aws_bucket: str
    sqs_queue_url: str

    # mongo configs
    database_connection_string: str
    database_name: str

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

