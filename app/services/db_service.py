import secrets
import uuid
from decimal import Decimal

import boto3
from datetime import datetime, timezone
from boto3.dynamodb.conditions import Key, Attr

from app.config import settings

dynamodb = boto3.resource("dynamodb", region_name=settings.aws_region)


def _users_table():
    return dynamodb.Table(settings.dynamodb_table_users)


def _receipts_table():
    return dynamodb.Table(settings.dynamodb_table_receipts)


# --- Users ---

def create_user(email: str, name: str) -> dict:
    user_id = str(uuid.uuid4())[:8]
    api_key = f"rt_{secrets.token_urlsafe(32)}"
    item = {
        "user_id": user_id,
        "email": email,
        "name": name,
        "api_key": api_key,
        "plan": "free",
        "scans_this_month": 0,
        "scan_month": datetime.now(timezone.utc).strftime("%Y-%m"),
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    _users_table().put_item(Item=item)
    return item


def get_user_by_api_key(api_key: str) -> dict | None:
    resp = _users_table().scan(FilterExpression=Attr("api_key").eq(api_key))
    items = resp.get("Items", [])
    return items[0] if items else None


def get_user_by_email(email: str) -> dict | None:
    resp = _users_table().scan(FilterExpression=Attr("email").eq(email))
    items = resp.get("Items", [])
    return items[0] if items else None


def increment_scan_count(user_id: str) -> int:
    current_month = datetime.now(timezone.utc).strftime("%Y-%m")
    table = _users_table()

    user = table.get_item(Key={"user_id": user_id}).get("Item", {})
    if user.get("scan_month") != current_month:
        table.update_item(
            Key={"user_id": user_id},
            UpdateExpression="SET scans_this_month = :zero, scan_month = :month",
            ExpressionAttributeValues={":zero": 0, ":month": current_month},
        )

    resp = table.update_item(
        Key={"user_id": user_id},
        UpdateExpression="SET scans_this_month = scans_this_month + :inc",
        ExpressionAttributeValues={":inc": 1},
        ReturnValues="UPDATED_NEW",
    )
    return int(resp["Attributes"]["scans_this_month"])


def can_scan(user: dict) -> bool:
    current_month = datetime.now(timezone.utc).strftime("%Y-%m")
    if user.get("plan") == "pro":
        return True
    if user.get("scan_month") != current_month:
        return True
    return int(user.get("scans_this_month", 0)) < settings.free_scans_per_month


# --- Receipts ---

def save_receipt(user_id: str, receipt_data: dict, image_key: str) -> dict:
    receipt_id = str(uuid.uuid4())[:12]
    # Convert float values in items to Decimal for DynamoDB
    items_for_db = []
    for item in receipt_data.get("items", []):
        items_for_db.append({
            "name": item["name"],
            "quantity": Decimal(str(item.get("quantity", 1))),
            "price": Decimal(str(item.get("price", 0))),
        })
    record = {
        "receipt_id": receipt_id,
        "user_id": user_id,
        "store_name": receipt_data["store_name"],
        "date": receipt_data["date"],
        "total": Decimal(str(receipt_data["total"])),
        "currency": receipt_data.get("currency", "USD"),
        "category": receipt_data.get("category", "Other"),
        "items": items_for_db,
        "image_key": image_key,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    _receipts_table().put_item(Item=record)
    # Return with floats for JSON serialization
    record["total"] = float(record["total"])
    for item in record["items"]:
        item["quantity"] = float(item["quantity"])
        item["price"] = float(item["price"])
    return record


def list_receipts(user_id: str, limit: int = 500) -> list:
    items = []
    scan_kwargs = {"FilterExpression": Attr("user_id").eq(user_id)}

    while True:
        resp = _receipts_table().scan(**scan_kwargs)
        items.extend(resp.get("Items", []))
        if "LastEvaluatedKey" not in resp or len(items) >= limit:
            break
        scan_kwargs["ExclusiveStartKey"] = resp["LastEvaluatedKey"]

    for item in items:
        item["total"] = float(item["total"])
        for li in item.get("items", []):
            li["quantity"] = float(li.get("quantity", 1))
            li["price"] = float(li.get("price", 0))
    return sorted(items, key=lambda x: x["date"], reverse=True)[:limit]


def get_receipt(receipt_id: str, user_id: str) -> dict | None:
    resp = _receipts_table().get_item(Key={"receipt_id": receipt_id})
    item = resp.get("Item")
    if item and item.get("user_id") == user_id:
        item["total"] = float(item["total"])
        for li in item.get("items", []):
            li["quantity"] = float(li.get("quantity", 1))
            li["price"] = float(li.get("price", 0))
        return item
    return None


def delete_receipt(receipt_id: str):
    _receipts_table().delete_item(Key={"receipt_id": receipt_id})


def get_spending_summary(user_id: str, year: int, month: int) -> dict:
    receipts = list_receipts(user_id, limit=500)
    prefix = f"{year}-{month:02d}"

    filtered = [r for r in receipts if r["date"].startswith(prefix)]

    by_category = {}
    by_store = {}
    by_currency = {}
    total = 0.0

    for r in filtered:
        amt = float(r["total"])
        total += amt
        cat = r.get("category", "Other")
        store = r.get("store_name", "Unknown")
        cur = r.get("currency", "USD")
        by_category[cat] = round(by_category.get(cat, 0) + amt, 2)
        by_store[store] = round(by_store.get(store, 0) + amt, 2)
        by_currency[cur] = round(by_currency.get(cur, 0) + amt, 2)

    by_category = dict(sorted(by_category.items(), key=lambda x: x[1], reverse=True))
    by_store = dict(sorted(by_store.items(), key=lambda x: x[1], reverse=True))

    # Use the most common currency from the receipts
    currency = max(by_currency, key=by_currency.get) if by_currency else "USD"

    return {
        "period": prefix,
        "total": round(total, 2),
        "currency": currency,
        "by_category": by_category,
        "by_store": by_store,
        "by_currency": by_currency,
        "receipt_count": len(filtered),
    }
