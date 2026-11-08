variable "subscription_id" {
  description = "Azure subscription ID"
  type        = string
}

variable "location" {
  description = "Azure region"
  type        = string
  default     = "southafricanorth"
}

variable "resource_group_name" {
  type    = string
  default = "rg-islandride-tf"
}

variable "storage_prefix" {
  description = "Start of the storage account name (lowercase letters/numbers only)"
  type        = string
  default     = "islandride"
}

variable "layers" {
  description = "Medallion containers to create"
  type        = list(string)
  default     = ["bronze", "silver", "gold"]
}

variable "tags" {
  type = map(string)
  default = {
    project    = "islandride"
    managed_by = "terraform"
  }
}