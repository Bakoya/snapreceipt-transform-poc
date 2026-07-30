from datetime import datetime
from fastapi import APIRouter, Depends

from app.auth import verify_api_key
from app.models.schemas import SpendingSummary, MonthlyTrend
from app.services import db_service

router = APIRouter(prefix="/spending", tags=["spending"])


@router.get("/summary", response_model=SpendingSummary)
def get_spending_summary(year: int = None, month: int = None, user=Depends(verify_api_key)):
    now = datetime.utcnow()
    year = year or now.year
    month = month or now.month
    return db_service.get_spending_summary(user["user_id"], year, month)


@router.get("/trends")
def get_spending_trends(months: int = 6, user=Depends(verify_api_key)):
    now = datetime.utcnow()
    trends = []
    for i in range(months):
        m = now.month - i
        y = now.year
        if m <= 0:
            m += 12
            y -= 1
        summary = db_service.get_spending_summary(user["user_id"], y, m)
        trends.append({
            "month": f"{y}-{m:02d}",
            "total": summary["total"],
            "currency": "USD",
        })
    return sorted(trends, key=lambda x: x["month"])
