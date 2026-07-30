from pydantic import BaseModel
from typing import Optional


class UserCreate(BaseModel):
    email: str
    name: str


class UserResponse(BaseModel):
    user_id: str
    email: str
    name: str
    api_key: str
    plan: str
    scans_this_month: int
    created_at: str


class ReceiptItem(BaseModel):
    name: str
    quantity: float = 1
    price: float


class ReceiptResponse(BaseModel):
    receipt_id: str
    user_id: str
    store_name: str
    date: str
    total: float
    currency: str
    category: str
    items: list[ReceiptItem]
    image_url: str
    created_at: str


class SpendingSummary(BaseModel):
    period: str
    total: float
    currency: str
    by_category: dict[str, float]
    by_store: dict[str, float]
    receipt_count: int


class MonthlyTrend(BaseModel):
    month: str
    total: float
    currency: str
