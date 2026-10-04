terraform {
  required_providers {
    oci = { source = "oracle/oci" }
  }
}
resource "oci_core_instance" "this" {
  compartment_id      = var.compartment_ocid
  availability_domain = var.availability_domain
  display_name        = "lab-${var.role}"
  shape               = var.shape
  shape_config {
    ocpus         = var.ocpus
    memory_in_gbs = var.memory_gbs
  }
  create_vnic_details {
    subnet_id        = var.subnet_id
    nsg_ids          = [var.nsg_id]
    assign_public_ip = true
  }
  source_details {
    source_type             = "image"
    source_id               = var.image_ocid
    boot_volume_size_in_gbs = var.boot_volume_gbs
  }
  preserve_boot_volume = false
  metadata = {
    ssh_authorized_keys = var.ssh_public_key
    user_data           = base64encode(file("${path.module}/cloud-init.yaml"))
  }
}
output "public_ip" { value = oci_core_instance.this.public_ip }
output "private_ip" { value = oci_core_instance.this.private_ip }
output "id" { value = oci_core_instance.this.id }
