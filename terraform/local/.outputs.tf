output "blob_endpoint" {
  description = "Azurite Blob endpoint to use in the connection string"
  value       = "http://127.0.0.1:${var.blob_port}/devstoreaccount1"
}

output "container_name" {
  value = docker_container.azurite.name
}