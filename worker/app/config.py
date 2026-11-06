import os

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql://medimage:medimage@localhost:5432/medimage"
    redis_url: str = "redis://localhost:6379/0"

    s3_endpoint_url: str = "http://localhost:9000"
    s3_access_key: str = "miniokey"
    s3_secret_key: str = "miniosecret"
    s3_bucket: str = "medimage-storage"
    s3_region: str = "us-east-1"

    model_weights_dir: str = "/data/models"


settings = Settings()
