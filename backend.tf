
provider "aws" {
  region = var.region
  assume_role {
    role_arn = "arn:aws:iam::${var.devops_account_id}:role/${var.deploy_role}"
  }
}

terraform {
  required_providers {
    aws = ">= 4.32.0"
  }
  backend "s3" {
    encrypt        = true
    bucket         = "ladoumi-terraform-remote-state"
    dynamodb_table = "ladoumi-terraform-locks"
    region         = "eu-west-1"
    key            = "snapreceipt-transform-poc/terraform.tfstate"
    kms_key_id     = "arn:aws:kms:eu-west-1:363475792261:key/b3499b6c-52a8-42ad-bedf-4be96e5d4fc0"
  }
}

data "terraform_remote_state" "cust_name_cicd" {
  backend = "s3"

  config = {
    bucket = "ladoumi-terraform-remote-state"
    key    = "ladoumi-cicd-pre-reqs/terraform.tfstate"
    region = "eu-west-1"
  }
}
