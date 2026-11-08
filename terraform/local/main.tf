terraform {
  required_version = ">= 1.6"

  required_providers {
    docker = {
      source  = "kreuzwerker/docker"
      version = "~> 3.0"
    }
  }
}

# Docker Desktop on Windows listens on this named pipe
provider "docker" {
  host = "npipe:////./pipe/docker_engine"
}

resource "docker_image" "azurite" {
  name         = "mcr.microsoft.com/azure-storage/azurite:latest"
  keep_locally = true
}

resource "docker_volume" "azurite_data" {
  name = "islandride_tf_azurite_data"
}

resource "docker_container" "azurite" {
  name    = var.container_name
  image   = docker_image.azurite.image_id
  command = ["azurite-blob", "--blobHost", "0.0.0.0", "--loose", "--skipApiVersionCheck"]
  restart = "unless-stopped"

  ports {
    internal = 10000
    external = var.blob_port
  }

  volumes {
    volume_name    = docker_volume.azurite_data.name
    container_path = "/data"
  }
}