#!/usr/bin/env bash
source "$(dirname "$0")/common.sh"
"$ROOT/scripts/preflight.sh"
: "${OCI_PROFILE:=internet-service-lab}"
oci session validate --profile "$OCI_PROFILE" --auth security_token
"$TF" -chdir="$ROOT/terraform" init -lockfile=readonly
"$TF" -chdir="$ROOT/terraform" fmt -check -recursive
"$TF" -chdir="$ROOT/terraform" validate
"$TF" -chdir="$ROOT/terraform" plan -var=public_web=false -out=initial.tfplan
"$TF" -chdir="$ROOT/terraform" apply initial.tfplan
printf '%s\n' 'Confirm both SSH host key fingerprints using OCI console, then docs/bootstrap.md known_hosts procedure.' 'Next: ./scripts/deploy-stage.sh 1'
