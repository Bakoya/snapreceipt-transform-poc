from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from mangum import Mangum

from app.auth import verify_api_key
from app.config import settings
from app.routers import signup, receipts, spending

app = FastAPI(
    title="Receipt Tracker",
    description="Snap a receipt, track your spending. Powered by Amazon Textract.",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(signup.router)
app.include_router(receipts.router)
app.include_router(spending.router)


@app.get("/health", tags=["system"])
def health():
    return {"status": "ok"}


@app.get("/me", tags=["user"])
def get_me(user=Depends(verify_api_key)):
    scans = int(user.get("scans_this_month", 0))
    plan = user.get("plan", "free")
    limit = 0 if plan == "pro" else settings.free_scans_per_month
    return {
        "user_id": user["user_id"],
        "name": user.get("name", ""),
        "email": user.get("email", ""),
        "plan": plan,
        "scans_this_month": scans,
        "scans_limit": limit,
        "scans_remaining": max(0, limit - scans) if plan != "pro" else -1,
    }


handler = Mangum(app)
