#!/usr/bin/env bash
source "$(dirname "$0")/common.sh"
# Contain first without waiting for Terraform; established public flows are stopped by nginx restart.
stage=$(remote_bounded 30 service 'sudo cat /var/lib/lab/stage 2>/dev/null || echo 0')
[[ $stage =~ ^[0-5]$ ]] || exit 1
if ((stage>=2)); then remote_bounded 60 service 'sudo systemctl stop lab-container@nginx'; fi
# An expired OCI token must not prevent SSH containment. Failure keeps nginx stopped.
session
"$TF" -chdir="$ROOT/terraform" plan -var=public_web=false -out=stop.tfplan
"$TF" -chdir="$ROOT/terraform" apply stop.tfplan
# Narrow OS guard using the current stage, retaining stage-05 protection.
if ((stage>=1)); then remote service "sudo python3 /opt/internet-service-lab/scripts/apply-vm.py service '$stage' '$(ip service private_ip)' '$(ip monitoring private_ip)' '$(value admin_cidr)' false --firewall-only"; fi
if ((stage>=2)); then
 remote service 'sudo systemctl start lab-container@nginx'
 "$ROOT/scripts/wait-ready.sh" service "$stage"
fi
