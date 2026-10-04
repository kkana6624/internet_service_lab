module "vm" {
  for_each            = { service = oci_core_network_security_group.service.id, monitoring = oci_core_network_security_group.monitoring.id }
  source              = "./modules/vm"
  role                = each.key
  compartment_ocid    = var.compartment_ocid
  availability_domain = var.availability_domain
  subnet_id           = oci_core_subnet.lab.id
  nsg_id              = each.value
  image_ocid          = var.image_ocid
  shape               = var.shape
  ocpus               = var.ocpus
  memory_gbs          = var.memory_gbs
  boot_volume_gbs     = var.boot_volume_gbs
  ssh_public_key      = file(pathexpand(var.ssh_public_key_path))
}
