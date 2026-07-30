provider "aws" {
  region  = var.region
  profile = var.aws_profile
}

terraform {
  required_version = ">= 1.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = ">= 5.0"
    }
  }
}

variable "region" {
  default = "eu-west-1"
}

variable "project" {
  default = "atx-receipts"
}

variable "aws_profile" {
  default = "personal-sapc01"
}

# --- DynamoDB Tables ---

resource "aws_dynamodb_table" "users" {
  name         = "${var.project}-users"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "user_id"

  attribute {
    name = "user_id"
    type = "S"
  }

  tags = { Project = var.project }
}

resource "aws_dynamodb_table" "receipts" {
  name         = "${var.project}-data"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "receipt_id"

  attribute {
    name = "receipt_id"
    type = "S"
  }

  tags = { Project = var.project }
}

# --- S3 Bucket for Receipt Images ---

resource "aws_s3_bucket" "uploads" {
  bucket = "${var.project}-uploads-${data.aws_caller_identity.current.account_id}"
  tags   = { Project = var.project }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "uploads" {
  bucket = aws_s3_bucket.uploads.bucket
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_public_access_block" "uploads" {
  bucket                  = aws_s3_bucket.uploads.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_cors_configuration" "uploads" {
  bucket = aws_s3_bucket.uploads.id

  cors_rule {
    allowed_headers = ["*"]
    allowed_methods = ["GET", "PUT", "POST"]
    allowed_origins = ["*"]
    max_age_seconds = 3600
  }
}

data "aws_caller_identity" "current" {}

# --- IAM Role ---

resource "aws_iam_role" "lambda" {
  name = "${var.project}-lambda-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "lambda.amazonaws.com" }
      Action    = "sts:AssumeRole"
    }]
  })
}

resource "aws_iam_role_policy" "lambda" {
  role = aws_iam_role.lambda.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect   = "Allow"
        Action   = ["dynamodb:GetItem", "dynamodb:PutItem", "dynamodb:DeleteItem", "dynamodb:Scan", "dynamodb:Query", "dynamodb:UpdateItem"]
        Resource = [aws_dynamodb_table.users.arn, aws_dynamodb_table.receipts.arn]
      },
      {
        Effect   = "Allow"
        Action   = ["s3:PutObject", "s3:GetObject", "s3:DeleteObject"]
        Resource = "${aws_s3_bucket.uploads.arn}/*"
      },
      {
        Effect   = "Allow"
        Action   = ["textract:AnalyzeExpense"]
        Resource = "*"
      },
      {
        Effect   = "Allow"
        Action   = ["logs:CreateLogGroup", "logs:CreateLogStream", "logs:PutLogEvents"]
        Resource = "arn:aws:logs:*:*:*"
      }
    ]
  })
}

# --- Lambda ---

resource "aws_lambda_function" "api" {
  function_name    = "${var.project}-api"
  role             = aws_iam_role.lambda.arn
  handler          = "app.main.handler"
  runtime          = "python3.12"
  timeout          = 60
  memory_size      = 512
  filename         = "../deployment.zip"
  source_code_hash = filebase64sha256("../deployment.zip")

  environment {
    variables = {
      DYNAMODB_TABLE_USERS    = aws_dynamodb_table.users.name
      DYNAMODB_TABLE_RECEIPTS = aws_dynamodb_table.receipts.name
      S3_BUCKET_RECEIPTS      = aws_s3_bucket.uploads.bucket
      FREE_SCANS_PER_MONTH    = "20"
    }
  }

  tags = { Project = var.project }
}

# --- API Gateway ---

resource "aws_apigatewayv2_api" "this" {
  name          = "${var.project}-api"
  protocol_type = "HTTP"
}

resource "aws_apigatewayv2_integration" "lambda" {
  api_id                 = aws_apigatewayv2_api.this.id
  integration_type       = "AWS_PROXY"
  integration_uri        = aws_lambda_function.api.invoke_arn
  payload_format_version = "2.0"
}

resource "aws_apigatewayv2_route" "default" {
  api_id    = aws_apigatewayv2_api.this.id
  route_key = "$default"
  target    = "integrations/${aws_apigatewayv2_integration.lambda.id}"
}

resource "aws_apigatewayv2_stage" "default" {
  api_id      = aws_apigatewayv2_api.this.id
  name        = "$default"
  auto_deploy = true
}

resource "aws_lambda_permission" "apigw" {
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.api.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.this.execution_arn}/*/*"
}

# --- Outputs ---

output "api_url" {
  value = aws_apigatewayv2_api.this.api_endpoint
}

output "uploads_bucket" {
  value = aws_s3_bucket.uploads.bucket
}
