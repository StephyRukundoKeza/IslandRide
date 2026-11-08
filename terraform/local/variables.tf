variable "container_name" {
  description = "Name of the Azurite container"
  type        = string
  default     = "islandride-azurite-tf"
}

variable "blob_port" {
  description = "Port on your PC for Azurite's Blob storage"
  type        = number
  default     = 10000
}