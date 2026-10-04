#!/usr/bin/env bash
source "$(dirname "$0")/common.sh"
case "${1:-plan}" in
 plan)
  python3 "$ROOT/scripts/save-context.py"
  "$ROOT/scripts/stop-public.sh"
  if ! "$ROOT/scripts/collect-evidence.sh" 06; then echo "Evidence collection incomplete; manifest records failures. Retain available artifacts before destroy." >&2; fi
  echo 'Retreat evidence/backups per operations.md before invoking cleanup.sh destroy.'
  session
  "$TF" -chdir="$ROOT/terraform" plan -destroy -var=public_web=false -out=destroy.tfplan
  ;;
 destroy)
  session
  [[ -f $ROOT/terraform/destroy.tfplan ]] || { echo 'Run cleanup.sh plan first' >&2; exit 1; }
  "$TF" -chdir="$ROOT/terraform" show "$ROOT/terraform/destroy.tfplan"
  # Explicit typed acknowledgement of data loss; no automatic cloud destruction.
  read -r -p 'Backup/evidence saved? Type DESTROY: ' answer
  [[ $answer == DESTROY ]] || exit 1
  "$TF" -chdir="$ROOT/terraform" apply destroy.tfplan
  "$TF" -chdir="$ROOT/terraform" state list
  python3 "$ROOT/scripts/residuals.py"
  echo 'Inspect inventory per docs/operations.md; an empty State alone is insufficient.'
  ;;
 partial-plan)
  session
  echo 'Partial build: no SSH/readiness dependency; preserve available logs/backups yourself. Initial bootstrap is private.'
  "$TF" -chdir="$ROOT/terraform" plan -destroy -var=public_web=false -out=destroy.tfplan
  echo 'Prepare .private/cleanup-context.json from tfvars for residual inventory, then cleanup.sh destroy.'
  ;;
 *) exit 2;; esac
