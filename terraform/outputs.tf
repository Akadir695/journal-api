output "resource_group_name" {
  value = azurerm_resource_group.main.name
}

output "storage_account_name" {
  value = azurerm_storage_account.journal.name
}

output "storage_connection_string" {
  value     = azurerm_storage_account.journal.primary_connection_string
  sensitive = true
}
output "api_url" {
  description = "Public URL of the API"
  value       = "https://${azurerm_container_app.api.ingress[0].fqdn}"
}
output "ci_client_id" {
  description = "Client ID of the GitHub Actions identity"
  value       = azuread_application.ci.client_id
}

output "tenant_id" {
  description = "Entra tenant the identity belongs to"
  value       = data.azurerm_client_config.current.tenant_id
}

output "subscription_id" {
  description = "Subscription the pipeline deploys into"
  value       = data.azurerm_client_config.current.subscription_id
}