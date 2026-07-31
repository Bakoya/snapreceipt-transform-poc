# SnapReceipt API — Docker Guide

## Overview

This document describes how to build and run the **SnapReceipt API** Docker image standalone, outside the automated pipeline.

The application is a FastAPI service that uses:
- **Amazon DynamoDB** — user accounts and receipt data storage
- **Amazon S3** — receipt image storage
- **Amazon Textract** — OCR receipt processing

AWS credentials must be available at runtime (via IAM role, instance profile, or environment variables).

---

## Build

```bash
# From the root of the extracted source archive:
docker build -t snapreceipt-api .
```

---

## Run

```bash
docker run -p 8000:8000 \
  -e AWS_REGION=eu-west-1 \
  -e DYNAMODB_TABLE_USERS=receipts-users \
  -e DYNAMODB_TABLE_RECEIPTS=receipts-data \
  -e S3_BUCKET_RECEIPTS=receipts-uploads \
  -e FREE_SCANS_PER_MONTH=20 \
  -e AWS_ACCESS_KEY_ID=<your-access-key-id> \
  -e AWS_SECRET_ACCESS_KEY=<your-secret-access-key> \
  snapreceipt-api
```

> **Note:** For production deployments, use [ECS Secrets Manager integration](https://docs.aws.amazon.com/AmazonECS/latest/developerguide/secrets-envvar-secrets-manager.html) or [EKS Secrets Manager / KMS encryption](https://docs.aws.amazon.com/eks/latest/userguide/security-k8s.html) to handle AWS credentials and other sensitive environment variables securely. Do **not** pass credentials as plain environment variables in production.

---

## Environment Variables

| Variable | Default | Required | Description |
|---|---|---|---|
| `AWS_REGION` | `eu-west-1` | No | AWS region for DynamoDB, S3, and Textract |
| `DYNAMODB_TABLE_USERS` | `receipts-users` | No | DynamoDB table for user accounts |
| `DYNAMODB_TABLE_RECEIPTS` | `receipts-data` | No | DynamoDB table for receipt records |
| `S3_BUCKET_RECEIPTS` | `receipts-uploads` | No | S3 bucket for receipt images |
| `FREE_SCANS_PER_MONTH` | `20` | No | Free tier monthly scan limit |
| `AWS_ACCESS_KEY_ID` | — | Yes* | AWS access key (or use IAM role) |
| `AWS_SECRET_ACCESS_KEY` | — | Yes* | AWS secret key (or use IAM role) |

*Required unless running on an EC2/ECS instance with an attached IAM role.

---

## Ports

| Port | Protocol | Description |
|---|---|---|
| `8000` | HTTP | FastAPI REST API served by Uvicorn |

---

## Health Check

```bash
curl http://localhost:8000/health
# Expected: {"status": "ok"}
```

---

## API Endpoints

| Method | Path | Auth | Description |
|---|---|---|---|
| `POST` | `/signup` | No | Create account, get API key |
| `POST` | `/receipts` | Yes | Upload receipt image (multipart) |
| `GET` | `/receipts` | Yes | List all receipts |
| `GET` | `/receipts/{id}` | Yes | Get single receipt |
| `DELETE` | `/receipts/{id}` | Yes | Delete receipt |
| `GET` | `/spending/summary` | Yes | Monthly spending by category/store |
| `GET` | `/spending/trends` | Yes | 6-month spending trends |
| `GET` | `/health` | No | Health check |

Authenticated endpoints require the `X-API-Key` header with the API key returned from `/signup`.

---

## Interactive API Docs

Once running, visit:
- **Swagger UI:** http://localhost:8000/docs
- **ReDoc:** http://localhost:8000/redoc
