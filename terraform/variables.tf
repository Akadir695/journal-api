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