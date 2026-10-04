resource "oci_core_vcn" "lab" {
  compartment_id = var.compartment_ocid
  cidr_block     = var.vcn_cidr
  display_name   = "internet-service-lab"
  dns_label      = "lab"
}
resource "oci_core_internet_gateway" "lab" {
  compartment_id = var.compartment_ocid
  vcn_id         = oci_core_vcn.lab.id
  display_name   = "lab-igw"
  enabled        = true
}
resource "oci_core_route_table" "lab" {
  compartment_id = var.compartment_ocid
  vcn_id         = oci_core_vcn.lab.id
  route_rules {
    destination       = "0.0.0.0/0"
    destination_type  = "CIDR_BLOCK"
    network_entity_id = oci_core_internet_gateway.lab.id
  }
}
# No default Security List ingress: NSG grants cannot be bypassed here.
resource "oci_core_security_list" "empty" {
  compartment_id = var.compartment_ocid
  vcn_id         = oci_core_vcn.lab.id
  display_name   = "lab-no-ingress"
}
resource "oci_core_subnet" "lab" {
  compartment_id    = var.compartment_ocid
  vcn_id            = oci_core_vcn.lab.id
  cidr_block        = var.subnet_cidr
  route_table_id    = oci_core_route_table.lab.id
  security_list_ids = [oci_core_security_list.empty.id]
  dns_label         = "public"
}
