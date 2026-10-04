variable "region" {
  type = string
}
variable "compartment_ocid" {
  type = string
}
variable "availability_domain" {
  type = string
}
variable "image_ocid" {
  type = string
}
variable "ssh_public_key_path" {
  type = string
}
variable "oci_profile" {
  type    = string
  default = "internet-service-lab"
}
variable "vcn_cidr" {
  type    = string
  default = "10.20.0.0/16"
}
variable "subnet_cidr" {
  type    = string
  default = "10.20.1.0/24"
}
variable "shape" {
  type    = string
  default = "VM.Standard.E4.Flex"
}
variable "ocpus" {
  type    = number
  default = 1
}
variable "memory_gbs" {
  type    = number
  default = 8
}
variable "boot_volume_gbs" {
  type    = number
  default = 50
}
variable "public_web" {
  type    = bool
  default = false
}
variable "admin_cidr" {
  type = string
  validation {
    condition     = can(cidrnetmask(var.admin_cidr)) && can(regex("/(2[4-9]|3[0-2])$", var.admin_cidr))
    error_message = "admin_cidr must be an IPv4 CIDR /24 through /32; world access is forbidden."
  }
}
