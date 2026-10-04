#!/usr/bin/env bash
source "$(dirname "$0")/common.sh"
stage=${1:?stage label}; [[ $stage =~ ^[0-9]{2}$ ]] || exit 2
folder="$ROOT/.private/evidence/$(date -u +%Y%m%dT%H%M%SZ)-step$stage"
mkdir -p "$folder"
export EVIDENCE_DIR="$folder"
python3 "$ROOT/scripts/evidence.py" "$stage"
printf 'Raw evidence (private): %s\nReview/redact using docs/evidence/README.md before copying into docs/evidence.\n' "$folder"
