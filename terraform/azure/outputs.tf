output "resource_group" {
  value = azurerm_resource_group.islandride.name
}

output "storage_account_name" {
  value = azurerm_storage_account.lake.name
}

output "dfs_endpoint" {
  value = azurerm_storage_account.lake.primary_dfs_endpoint
}

output "containers" {
  value = [for c in azurerm_storage_container.layers : c.name]
}

output "connection_string" {
  value     = azurerm_storage_account.lake.primary_connection_string
  sensitive = true
}