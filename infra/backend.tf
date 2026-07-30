terraform {
  backend "s3" {
    encrypt        = true
    bucket         = "ladoumi-terraform-remote-state"
    dynamodb_table = "ladoumi-terraform-locks"
    region         = "eu-west-1"
    key            = "snapreceipt-transform-poc/terraform.tfstate"
    kms_key_id     = "arn:aws:kms:eu-west-1:363475792261:key/b3499b6c-52a8-42ad-bedf-4be96e5d4fc0"
  }
}
