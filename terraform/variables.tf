variable "project" {
  type        = string
  description = "Project name, used in resource names"
}

variable "environment" {
  type        = string
  description = "Environment name, e.g. dev or prod"
}

variable "location" {
  type        = string
  description = "Azure region for all resources"
  default     = "uksouth"
}

variable "postgres_admin_username" {
  type        = string
  description = "Admin username for the Postgres server"
  default     = "journaladmin"
}

variable "postgres_admin_password" {
  type        = string
  description = "Admin password for the Postgres server"
  sensitive   = true
}
variable "github_username" {
  type        = string
  description = "GitHub username for pulling from GHCR"
  default     = "Akadir695"
}

variable "ghcr_token" {
  type        = string
  description = "GitHub PAT with read:packages"
  sensitive   = true
}

variable "jwt_secret" {
  type        = string
  description = "Secret used to sign JWTs"
  sensitive   = true
}

variable "image_tag" {
  type        = string
  description = "Image tag to deploy"
  default     = "daba3d4"
}

variable "resend_api_key" {
  type        = string
  description = "Resend API key for sending email"
  sensitive   = true
}