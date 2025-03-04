variable "maas_url" {
  type    = string
  default = "https://maas.lab.linuxcontainers.org/MAAS"
}

variable "maas_key" {
  type = string
}

variable "maas_machines" {
  type    = set(string)
  default = ["asuras", "entak", "velona"]
}
