#!/usr/bin/env bash
source "$(dirname "$0")/common.sh"
stage=${1:?Usage: deploy-stage.sh 1..5}; case "$stage" in 1|2|3|4|5) ;; *) exit 2;; esac
session
public=$(python3 - "$ROOT/stages/config/$(printf '%02d' "$stage").json" <<'PY_CONFIG'
import json,sys
print(str(json.load(open(sys.argv[1]))['public_web']).lower())
PY_CONFIG
)
[[ $public == true || $public == false ]] || exit 2
if [[ $public == true ]]; then
 # Query the actual database through the running WordPress PHP runtime; never trust a marker file.
 # wp-load may exit with status 0 on installer redirect/DB error. Require an
 # exact success marker as well as exit 0; WP_INSTALLING suppresses redirect.
 installed=$(remote service "sudo podman exec lab-wordpress php -r 'define(\"WP_INSTALLING\", true); require \"/var/www/html/wp-load.php\"; if (is_blog_installed()) { echo \"LAB_INSTALLED\"; } else { exit(1); }'")
 [[ $installed == LAB_INSTALLED ]] || { echo 'WordPress installation could not be verified; refusing public access.' >&2; exit 1; }
fi
for role in service monitoring; do
 previous=$(remote "$role" 'sudo cat /var/lib/lab/stage 2>/dev/null || echo 0')
 [[ $previous =~ ^[0-5]$ ]] || exit 1
 ((stage>=previous)) || { echo 'Backward transition refused; use stop-public.sh for containment.' >&2; exit 1; }
 # Wait cloud-init independently; do not assume Terraform completion implies OS readiness.
 remote_bounded 930 "$role" 'sudo timeout 900 cloud-init status --wait'
 tar -C "$ROOT" --exclude=.git --exclude=.terraform --exclude=.private --exclude='*.tfvars' --exclude='*.tfstate*' --exclude='*.tfplan' -czf - scripts service monitoring images.lock.json |
 remote_bounded 120 "$role" 'sudo mkdir -p /opt/internet-service-lab && sudo tar -xzf - -C /opt/internet-service-lab'
 remote_bounded 1850 "$role" "sudo timeout -k 30 1800 python3 /opt/internet-service-lab/scripts/apply-vm.py '$role' '$stage' '$(ip service private_ip)' '$(ip monitoring private_ip)' '$(value admin_cidr)' '$public' --service-public-host '$(ip service)'"
 "$ROOT/scripts/wait-ready.sh" "$role" "$stage"
done
# Configure VM first, then open NSG only after readiness and installation gate.
"$TF" -chdir="$ROOT/terraform" plan -var="public_web=$public" -out=stage.tfplan
"$TF" -chdir="$ROOT/terraform" apply stage.tfplan
"$ROOT/scripts/verify-stage.sh" "$stage"
