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
  # Only read when Terraform first creates the container apps. After that CI
  # owns the image, so this is the starting image for a rebuilt environment.
  default = "905d834fb593605c0621d77d0e24b914471bc46b"
}


variable "azure_storage_container" {
  type        = string
  description = "Blob container for attachments and exports"
  default     = "attachments"
}

variable "alert_email" {
  type        = string
  description = "Address that receives alert notifications"
}