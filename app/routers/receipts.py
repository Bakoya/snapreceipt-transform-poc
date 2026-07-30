import uuid
from fastapi import APIRouter, HTTPException, Depends, UploadFile, File
from pydantic import BaseModel

from app.auth import verify_api_key
from app.services import db_service, textract_service, storage_service

router = APIRouter(prefix="/receipts", tags=["receipts"])


# --- Upload Flow: works for ALL file sizes ---

@router.post("/upload-url")
def get_upload_url(user=Depends(verify_api_key)):
    """Step 1: Get a presigned URL to upload your receipt image."""
    if not db_service.can_scan(user):
        raise HTTPException(
            status_code=429,
            detail=f"Free plan limit reached ({user.get('scans_this_month', 0)} scans this month). Upgrade to Pro for unlimited scans.",
        )

    image_key = f"{user['user_id']}/{uuid.uuid4()}.jpg"
    upload_url = storage_service.get_presigned_upload_url(image_key)

    return {
        "upload_url": upload_url,
        "image_key": image_key,
        "method": "PUT",
        "headers": {"Content-Type": "image/jpeg"},
    }


class ProcessRequest(BaseModel):
    image_key: str


@router.post("/process")
def process_receipt(payload: ProcessRequest, user=Depends(verify_api_key)):
    """Step 2: After uploading the image, call this to extract receipt data."""
    if not payload.image_key.startswith(f"{user['user_id']}/"):
        raise HTTPException(status_code=403, detail="Not your image")

    try:
        image_bytes = storage_service.get_image_bytes(payload.image_key)
    except Exception:
        raise HTTPException(status_code=404, detail="Image not found in S3. Upload it first using the presigned URL from /receipts/upload-url.")

    receipt_data = textract_service.extract_receipt(image_bytes)
    receipt_data["category"] = textract_service.categorize_receipt(receipt_data["store_name"])

    if receipt_data["currency"] == "USD":
        store_currency = textract_service.detect_currency_from_store(receipt_data["store_name"])
        if store_currency:
            receipt_data["currency"] = store_currency

    saved = db_service.save_receipt(user["user_id"], receipt_data, payload.image_key)
    db_service.increment_scan_count(user["user_id"])

    saved["total"] = float(saved["total"])
    saved["image_url"] = storage_service.get_presigned_url(payload.image_key)
    return saved


# --- Quick upload (small files only, convenience endpoint) ---

@router.post("")
async def upload_receipt_direct(file: UploadFile = File(...), user=Depends(verify_api_key)):
    """Quick upload for small files (< 4MB). For larger files, use /receipts/upload-url + /receipts/process."""
    if not db_service.can_scan(user):
        raise HTTPException(
            status_code=429,
            detail=f"Free plan limit reached ({user.get('scans_this_month', 0)} scans this month). Upgrade to Pro for unlimited scans.",
        )

    image_bytes = await file.read()
    if len(image_bytes) > 10 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="Image too large (max 10MB)")

    receipt_data = textract_service.extract_receipt(image_bytes)
    receipt_data["category"] = textract_service.categorize_receipt(receipt_data["store_name"])

    if receipt_data["currency"] == "USD":
        store_currency = textract_service.detect_currency_from_store(receipt_data["store_name"])
        if store_currency:
            receipt_data["currency"] = store_currency

    image_key = f"{user['user_id']}/{uuid.uuid4()}.jpg"
    storage_service.upload_receipt_image(image_bytes, image_key)

    saved = db_service.save_receipt(user["user_id"], receipt_data, image_key)
    db_service.increment_scan_count(user["user_id"])

    saved["total"] = float(saved["total"])
    saved["image_url"] = storage_service.get_presigned_url(image_key)
    return saved


# --- List / Get / Delete ---

@router.get("")
def list_receipts(limit: int = 50, user=Depends(verify_api_key)):
    receipts = db_service.list_receipts(user["user_id"], limit=limit)
    for r in receipts:
        r["image_url"] = storage_service.get_presigned_url(r["image_key"])
    return receipts


@router.get("/{receipt_id}")
def get_receipt(receipt_id: str, user=Depends(verify_api_key)):
    receipt = db_service.get_receipt(receipt_id, user["user_id"])
    if not receipt:
        raise HTTPException(status_code=404, detail="Receipt not found")
    receipt["image_url"] = storage_service.get_presigned_url(receipt["image_key"])
    return receipt


@router.delete("/{receipt_id}")
def delete_receipt(receipt_id: str, user=Depends(verify_api_key)):
    receipt = db_service.get_receipt(receipt_id, user["user_id"])
    if not receipt:
        raise HTTPException(status_code=404, detail="Receipt not found")
    db_service.delete_receipt(receipt_id)
    return {"message": "Receipt deleted"}
