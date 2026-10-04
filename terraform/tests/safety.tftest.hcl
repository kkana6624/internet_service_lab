# Mock provider: no OCI credentials, API access, resources or charges.
mock_provider "oci" {}

variables {
  region              = "ap-tokyo-1"
  compartment_ocid    = "ocid1.compartment.oc1..testfixture"
  availability_domain = "TEST:AP-TOKYO-1-AD-1"
  image_ocid          = "ocid1.image.oc1.ap-tokyo-1.testfixture"
  ssh_public_key_path = "tests/fixtures/ssh.pub"
  admin_cidr          = "203.0.113.8/32"
}

run "private_default" {
  command = plan
  assert {
    condition     = !var.public_web && oci_core_network_security_group_security_rule.web.source == var.admin_cidr
    error_message = "Default Web access must remain restricted to the management CIDR."
  }
  assert {
    condition     = length(module.vm) == 2 && length(oci_core_security_list.empty.ingress_security_rules) == 0
    error_message = "Use two VMs and a Security List without additive ingress permissions."
  }
}

run "public_web_preserves_ssh_restriction" {
  command = plan
  variables { public_web = true }
  assert {
    condition     = oci_core_network_security_group_security_rule.web.source == "0.0.0.0/0" && alltrue([for rule in oci_core_network_security_group_security_rule.ssh : rule.source == var.admin_cidr])
    error_message = "Publication may open Web only; SSH must stay restricted."
  }
}

run "reject_world_management" {
  command = plan
  variables { admin_cidr = "0.0.0.0/0" }
  expect_failures = [var.admin_cidr]
}

run "reject_broad_management" {
  command = plan
  variables { admin_cidr = "203.0.0.0/16" }
  expect_failures = [var.admin_cidr]
}

run "reject_ipv6_management" {
  command = plan
  variables { admin_cidr = "2001:db8::/32" }
  expect_failures = [var.admin_cidr]
}
