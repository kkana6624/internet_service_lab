#!/usr/bin/env bash
set -euo pipefail
ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
TF=${TF:-terraform}
export TF_IN_AUTOMATION=1
umask 077
out() { "$TF" -chdir="$ROOT/terraform" output -json "$1"; }
value() { out "$1" | python3 -c 'import json,sys;print(json.load(sys.stdin))'; }
ip() { out vms | python3 -c 'import json,sys;print(json.load(sys.stdin)[sys.argv[1]][sys.argv[2]])' "$1" "${2:-public_ip}"; }
: "${SSH_KEY:=$HOME/.ssh/internet-service-lab}"
SSH=(ssh -i "$SSH_KEY" -o BatchMode=yes -o ConnectTimeout=10 -o ServerAliveInterval=10 -o ServerAliveCountMax=2 -o StrictHostKeyChecking=yes)
remote() { local role=$1; shift; "${SSH[@]}" "opc@$(ip "$role")" "$@"; }
remote_bounded() { local seconds=$1 role=$2; shift 2; timeout -k 2 "${seconds}s" "${SSH[@]}" "opc@$(ip "$role")" "$@"; }
session() {
 local profile
 if profile=$(value oci_profile 2>/dev/null); then :; else
  profile=${OCI_PROFILE:?Set OCI_PROFILE when partial State has no outputs}
 fi
 oci session validate --profile "$profile" --auth security_token
}
