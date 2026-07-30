"""
Receipt OCR using Amazon Textract AnalyzeExpense API.
Extracts store name, date, items, totals from receipt images.
"""
import boto3
import re
from datetime import datetime

from app.config import settings


def _get_textract_client():
    return boto3.client("textract", region_name=settings.aws_region)


def extract_receipt(image_bytes: bytes) -> dict:
    textract = _get_textract_client()

    resp = textract.analyze_expense(
        Document={"Bytes": image_bytes}
    )

    result = {
        "store_name": "Unknown Store",
        "date": datetime.utcnow().strftime("%Y-%m-%d"),
        "total": 0.0,
        "currency": "USD",
        "items": [],
        "raw_text": "",
    }

    all_text = ""
    candidate_totals = []

    for doc in resp.get("ExpenseDocuments", []):
        for field in doc.get("SummaryFields", []):
            field_type = field.get("Type", {}).get("Text", "")
            value = field.get("ValueDetection", {}).get("Text", "")
            all_text += f" {value}"

            if field_type == "VENDOR_NAME" and value:
                result["store_name"] = value.strip()
            elif field_type == "INVOICE_RECEIPT_DATE" and value:
                result["date"] = _parse_date(value)
            elif field_type == "TOTAL" and value:
                amt = _parse_amount(value)
                if amt > 0:
                    candidate_totals.append(("TOTAL", amt))
            elif field_type == "SUBTOTAL" and value:
                amt = _parse_amount(value)
                if amt > 0:
                    candidate_totals.append(("SUBTOTAL", amt))
            elif field_type == "AMOUNT_DUE" and value:
                amt = _parse_amount(value)
                if amt > 0:
                    candidate_totals.append(("AMOUNT_DUE", amt))

        for group in doc.get("LineItemGroups", []):
            for line in group.get("LineItems", []):
                item = {"name": "", "quantity": 1, "price": 0.0}
                for field in line.get("LineItemExpenseFields", []):
                    field_type = field.get("Type", {}).get("Text", "")
                    value = field.get("ValueDetection", {}).get("Text", "")

                    if field_type == "ITEM" and value:
                        item["name"] = value.strip()
                    elif field_type == "PRICE" and value:
                        item["price"] = _parse_amount(value)
                    elif field_type == "QUANTITY" and value:
                        try:
                            item["quantity"] = float(re.sub(r"[^\d.]", "", value))
                        except ValueError:
                            item["quantity"] = 1

                if item["name"]:
                    result["items"].append(item)

    # Pick the best total
    result["total"] = _pick_best_total(candidate_totals, result["items"])

    # Detect currency from text, then from store name
    result["currency"] = _detect_currency(all_text)

    return result


def _pick_best_total(candidate_totals: list, items: list) -> float:
    if not candidate_totals and not items:
        return 0.0

    items_sum = round(sum(i["price"] for i in items), 2) if items else 0.0

    if not candidate_totals:
        return items_sum

    # If only one candidate, use it
    if len(candidate_totals) == 1:
        return candidate_totals[0][1]

    # If items exist, pick the candidate closest to the items sum
    # This avoids picking phone numbers or reference numbers as totals
    if items_sum > 0:
        best = min(candidate_totals, key=lambda t: abs(t[1] - items_sum))
        return best[1]

    # Prefer TOTAL over SUBTOTAL over AMOUNT_DUE
    priority = {"TOTAL": 0, "AMOUNT_DUE": 1, "SUBTOTAL": 2}
    candidate_totals.sort(key=lambda t: priority.get(t[0], 3))

    # If multiple TOTALs, pick the smallest reasonable one
    # (the largest is often a running total or reference number)
    totals_only = [t[1] for t in candidate_totals if t[0] == "TOTAL"]
    if len(totals_only) > 1:
        return min(totals_only)

    return candidate_totals[0][1]


def _parse_amount(text: str) -> float:
    cleaned = re.sub(r"[^\d.,]", "", text)
    cleaned = cleaned.replace(",", ".")
    if cleaned.count(".") > 1:
        cleaned = cleaned.replace(".", "", cleaned.count(".") - 1)
    try:
        return round(float(cleaned), 2)
    except ValueError:
        return 0.0


def _parse_date(text: str) -> str:
    formats = [
        "%m/%d/%Y", "%d/%m/%Y", "%Y-%m-%d", "%m-%d-%Y",
        "%d-%m-%Y", "%m/%d/%y", "%d/%m/%y", "%d.%m.%Y",
        "%d %b %Y", "%d %B %Y", "%b %d, %Y", "%B %d, %Y",
    ]
    for fmt in formats:
        try:
            return datetime.strptime(text.strip(), fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    return datetime.utcnow().strftime("%Y-%m-%d")


CATEGORY_KEYWORDS = {
    "Groceries": [
        "grocery", "supermarket", "market", "food",
        "walmart", "tesco", "aldi", "lidl", "carrefour", "kroger",
        "sainsbury", "asda", "morrisons", "waitrose", "co-op", "coop",
        "spar", "iceland", "m&s food", "marks & spencer",
        "whole foods", "trader joe", "costco", "penny", "rewe", "edeka",
        "intermarche", "leclerc", "monoprix", "casino",
    ],
    "Restaurant": [
        "restaurant", "cafe", "coffee", "pizza", "burger",
        "mcdonald", "starbucks", "subway", "kfc", "nando",
        "greggs", "pret", "costa", "domino", "deliveroo", "uber eats",
        "just eat", "grubhub", "doordash", "chipotle", "wendy",
    ],
    "Transport": [
        "gas", "fuel", "petrol", "diesel", "shell", "bp", "esso", "texaco",
        "uber", "lyft", "taxi", "parking", "tfl", "oyster",
        "train", "rail", "bus", "metro",
        "airline", "airways", "air france", "british airways", "easyjet",
        "ryanair", "wizz air", "vueling", "klm", "lufthansa", "emirates",
        "flight", "boarding",
    ],
    "Shopping": [
        "amazon", "target", "mall", "store", "shop", "clothing", "fashion",
        "primark", "zara", "h&m", "next", "argos", "john lewis",
        "ikea", "decathlon", "sports direct",
    ],
    "Health": [
        "pharmacy", "drug", "cvs", "walgreens", "medical", "doctor", "hospital",
        "boots", "superdrug", "chemist", "dental", "optician",
        "clinic", "surgery", "health", "gp ",
    ],
    "Entertainment": [
        "cinema", "movie", "theater", "theatre", "netflix", "spotify", "game",
        "odeon", "vue", "cineworld", "pub", "bar", "club",
    ],
    "Utilities": [
        "electric", "water", "internet", "phone", "mobile", "telecom",
        "vodafone", "ee", "three", "o2", "bt", "sky", "virgin media",
    ],
}


def categorize_receipt(store_name: str) -> str:
    lower = store_name.lower()
    for category, keywords in CATEGORY_KEYWORDS.items():
        if any(kw in lower for kw in keywords):
            return category
    return "Other"


CURRENCY_SYMBOLS = {
    "£": "GBP",
    "€": "EUR",
    "$": "USD",
    "¥": "JPY",
    "₹": "INR",
    "₩": "KRW",
    "R$": "BRL",
    "CHF": "CHF",
    "kr": "SEK",
    "zł": "PLN",
    "Kč": "CZK",
}

CURRENCY_WORDS = {
    "GBP": "GBP", "gbp": "GBP", "pound": "GBP", "sterling": "GBP",
    "EUR": "EUR", "eur": "EUR", "euro": "EUR",
    "USD": "USD", "usd": "USD", "dollar": "USD",
    "JPY": "JPY", "yen": "JPY",
    "INR": "INR", "rupee": "INR",
    "CAD": "CAD", "AUD": "AUD",
}

STORE_CURRENCY = {
    "GBP": [
        "sainsbury", "tesco", "asda", "morrisons", "waitrose", "co-op", "coop",
        "spar", "iceland", "m&s", "marks & spencer", "aldi uk", "lidl uk",
        "greggs", "boots", "superdrug", "primark", "argos", "john lewis",
        "nando", "pret", "costa", "london", "british",
    ],
    "EUR": [
        "carrefour", "leclerc", "intermarche", "monoprix", "casino",
        "rewe", "edeka", "penny", "auchan", "air france",
    ],
}


def _detect_currency(text: str) -> str:
    for symbol, currency in CURRENCY_SYMBOLS.items():
        if symbol in text:
            return currency

    lower = text.lower()
    for word, currency in CURRENCY_WORDS.items():
        if word in lower:
            return currency

    return "USD"


def detect_currency_from_store(store_name: str) -> str | None:
    lower = store_name.lower()
    for currency, stores in STORE_CURRENCY.items():
        if any(s in lower for s in stores):
            return currency
    return None
