#!/usr/bin/env bash
set -euo pipefail
TF=${TF:-terraform}
for tool in "$TF" oci ssh tar python3 curl timeout; do command -v "$tool" >/dev/null || { echo "Missing: $tool" >&2; exit 1; }; done
"$TF" version
oci --version
python3 --version
printf '%s\n' 'Check docs/bootstrap.md: token, compartment policy, OL9 x86_64 image, capacity and costs.'
