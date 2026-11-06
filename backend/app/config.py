from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "MedImage Studio API"
    database_url: str = "postgresql+asyncpg://medimage:medimage@localhost:5432/medimage"
    redis_url: str = "redis://localhost:6379/0"
    jwt_secret: str = "change_me"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 24

    orthanc_url: str = "http://localhost:8042"
    orthanc_user: str = "orthanc"
    orthanc_password: str = "orthanc"

    s3_endpoint_url: str = "http://localhost:9000"
    s3_access_key: str = "miniokey"
    s3_secret_key: str = "miniosecret"
    s3_bucket: str = "medimage-storage"
    s3_region: str = "us-east-1"

    cors_origins: str = "http://localhost:5173"
    upload_max_bytes: int = 5 * 1024**3  # 5GB

    local_fallback_storage: str = "/data/storage"

    demo_data_label: str = "demo_synthetic"


settings = Settings()
