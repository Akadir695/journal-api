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