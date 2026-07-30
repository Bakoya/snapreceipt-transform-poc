import os
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    aws_region: str = os.environ.get("AWS_REGION", "eu-west-1")
    dynamodb_table_users: str = "receipts-users"
    dynamodb_table_receipts: str = "receipts-data"
    s3_bucket_receipts: str = "receipts-uploads"
    free_scans_per_month: int = 20

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()
