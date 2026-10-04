output "vms" { value = { for role, vm in module.vm : role => { public_ip = vm.public_ip, private_ip = vm.private_ip, id = vm.id } } }
output "admin_cidr" { value = var.admin_cidr }
output "region" { value = var.region }
output "oci_profile" { value = var.oci_profile }
output "compartment_ocid" { value = var.compartment_ocid }
output "public_web" { value = var.public_web }
output "availability_domain" { value = var.availability_domain }
