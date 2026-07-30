# SnapReceipt — Receipt Tracker 📸

> Snap a photo of any receipt. AI extracts the data, categorizes your spending, and shows you where your money goes.
> Built with FastAPI + Amazon Textract. Runs on AWS Free Tier.

## Features

- **AI receipt scanning** — Amazon Textract extracts store, date, items, total
- **Auto-categorization** — Groceries, restaurants, transport, shopping, etc.
- **Spending analytics** — Monthly summaries, category breakdowns, 6-month trends
- **Freemium model** — 20 free scans/month, $3/month for unlimited
- **REST API** — upload receipts and query spending programmatically

## API Endpoints

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/signup` | No | Create account, get API key |
| POST | `/receipts` | Yes | Upload receipt image (multipart) |
| GET | `/receipts` | Yes | List all receipts |
| GET | `/receipts/{id}` | Yes | Get single receipt |
| DELETE | `/receipts/{id}` | Yes | Delete receipt |
| GET | `/spending/summary` | Yes | Monthly spending by category/store |
| GET | `/spending/trends` | Yes | 6-month spending trends |
| GET | `/health` | No | Health check |

## Architecture

```
User uploads image → API Gateway → Lambda (FastAPI)
                                      ├── Amazon Textract (OCR)
                                      ├── S3 (image storage)
                                      └── DynamoDB (receipt data)
```

## Deploy

```bash
chmod +x scripts/package.sh
./scripts/package.sh
cd infra && terraform init && terraform apply
```

## Cost

- **Textract:** ~$0.01 per receipt scan (AnalyzeExpense)
- **Everything else:** AWS Free Tier ($0)
- **At 1000 scans/month:** ~$10/month total AWS cost

## Status

🟡 Scaffolded — ready to deploy when you're ready to launch.

## License

MIT
