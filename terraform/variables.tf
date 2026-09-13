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



variable "image_tag" {
  type        = string
  description = "Image tag to deploy"
  default     = "3c6124a"
}


variable "azure_storage_container" {
  type        = string
  description = "Blob container for attachments and exports"
  default     = "attachments"
}