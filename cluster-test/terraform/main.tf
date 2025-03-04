provider "maas" {
  api_version = "2.0"
  api_key     = var.maas_key
  api_url     = var.maas_url
}

resource "maas_instance" "server" {
  for_each = var.maas_machines

  allocate_params {
    hostname = each.value
  }

  deploy_params {
    distro_series = "noble"
  }
}

output "addresses" {
  value = { for k, v in maas_instance.server : k => v.ip_addresses }
}
