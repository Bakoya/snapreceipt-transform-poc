variable "artifact_bucket_name" {}
variable "build_image" {}
variable "pipelines_repository" {}
variable "region" {}
variable "cust_name" {}
variable "env" {}
variable "project" {}
variable "repository" {}
variable "owner" {}
variable "deploy_role" {}
variable "devops_account_id" {}
variable "connection_arn" {
  description = "CodeStar connection ARN for GitHub"
}
variable "github_org" {
  description = "GitHub organization or username"
}
variable "privileged_mode" {
  type        = bool
  description = "Whether to enable running the Docker daemon inside a Docker container"
  default     = false
}



