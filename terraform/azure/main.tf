terraform {
  required_version = ">= 1.6"

  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 4.0"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.6"
    }
  }
}

provider "azurerm" {
  features {}
  subscription_id = var.subscription_id
}

resource "random_string" "suffix" {
  length  = 6
  upper   = false
  special = false
}

resource "azurerm_resource_group" "islandride" {
  name     = var.resource_group_name
  location = var.location
  tags     = var.tags
}

resource "azurerm_storage_account" "lake" {
  name                            = "${var.storage_prefix}${random_string.suffix.result}"
  resource_group_name             = azurerm_resource_group.islandride.name
  location                        = azurerm_resource_group.islandride.location
  account_kind                    = "StorageV2"
  account_tier                    = "Standard"
  account_replication_type        = "LRS"
  is_hns_enabled                  = true
  min_tls_version                 = "TLS1_2"
  allow_nested_items_to_be_public = false
  tags                            = var.tags
}

resource "azurerm_storage_container" "layers" {
  for_each              = toset(var.layers)
  name                  = each.value
  storage_account_id    = azurerm_storage_account.lake.id
  container_access_type = "private"
}

resource "azurerm_storage_management_policy" "lifecycle" {
  storage_account_id = azurerm_storage_account.lake.id

  rule {
    name    = "bronze-trips-tiering"
    enabled = true

    filters {
      prefix_match = ["bronze/trips/"]
      blob_types   = ["blockBlob"]
    }

    actions {
      base_blob {
        tier_to_cool_after_days_since_modification_greater_than = 30
        delete_after_days_since_modification_greater_than       = 365
      }
    }
  }
}