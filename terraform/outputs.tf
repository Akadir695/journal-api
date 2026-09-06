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