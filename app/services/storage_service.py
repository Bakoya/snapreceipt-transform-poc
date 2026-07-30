import boto3
from app.config import settings


def _s3_client():
    return boto3.client("s3", region_name=settings.aws_region)


def upload_receipt_image(image_bytes: bytes, key: str) -> str:
    _s3_client().put_object(
        Bucket=settings.s3_bucket_receipts,
        Key=key,
        Body=image_bytes,
        ContentType="image/jpeg",
    )
    return f"s3://{settings.s3_bucket_receipts}/{key}"


def get_presigned_upload_url(key: str, expires: int = 300) -> str:
    return _s3_client().generate_presigned_url(
        "put_object",
        Params={
            "Bucket": settings.s3_bucket_receipts,
            "Key": key,
            "ContentType": "image/jpeg",
        },
        ExpiresIn=expires,
    )


def get_presigned_url(key: str, expires: int = 3600) -> str:
    return _s3_client().generate_presigned_url(
        "get_object",
        Params={"Bucket": settings.s3_bucket_receipts, "Key": key},
        ExpiresIn=expires,
    )


def get_image_bytes(key: str) -> bytes:
    resp = _s3_client().get_object(Bucket=settings.s3_bucket_receipts, Key=key)
    return resp["Body"].read()
