resource "oci_core_network_security_group" "service" {
  compartment_id = var.compartment_ocid
  vcn_id         = oci_core_vcn.lab.id
  display_name   = "lab-service"
}
resource "oci_core_network_security_group" "monitoring" {
  compartment_id = var.compartment_ocid
  vcn_id         = oci_core_vcn.lab.id
  display_name   = "lab-monitoring"
}
resource "oci_core_network_security_group_security_rule" "ssh" {
  for_each                  = { service = oci_core_network_security_group.service.id, monitoring = oci_core_network_security_group.monitoring.id }
  network_security_group_id = each.value
  direction                 = "INGRESS"
  protocol                  = "6"
  source                    = var.admin_cidr
  source_type               = "CIDR_BLOCK"
  tcp_options {
    destination_port_range {
      min = 22
      max = 22
    }
  }
}
resource "oci_core_network_security_group_security_rule" "egress" {
  for_each                  = { service = oci_core_network_security_group.service.id, monitoring = oci_core_network_security_group.monitoring.id }
  network_security_group_id = each.value
  direction                 = "EGRESS"
  protocol                  = "all"
  destination               = "0.0.0.0/0"
  destination_type          = "CIDR_BLOCK"
}
resource "oci_core_network_security_group_security_rule" "web" {
  network_security_group_id = oci_core_network_security_group.service.id
  direction                 = "INGRESS"
  protocol                  = "6"
  source                    = var.public_web ? "0.0.0.0/0" : var.admin_cidr
  source_type               = "CIDR_BLOCK"
  tcp_options {
    destination_port_range {
      min = 80
      max = 80
    }
  }
}
resource "oci_core_network_security_group_security_rule" "probe" {
  for_each                  = { http = 80, node = 9100, experiment = 8081 }
  network_security_group_id = oci_core_network_security_group.service.id
  direction                 = "INGRESS"
  protocol                  = "6"
  source                    = oci_core_network_security_group.monitoring.id
  source_type               = "NETWORK_SECURITY_GROUP"
  tcp_options {
    destination_port_range {
      min = each.value
      max = each.value
    }
  }
}
