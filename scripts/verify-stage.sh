#!/usr/bin/env bash
source "$(dirname "$0")/common.sh"
stage=${1:?stage}
for role in service monitoring; do
 "$ROOT/scripts/wait-ready.sh" "$role" "$stage"
 remote "$role" 'sudo nft list table inet lab_guard && sudo firewall-cmd --list-all && sudo ss -lntp && sudo podman ps --format "{{.Names}} {{.Ports}}"'
done
if ((stage>=2)); then curl --max-time 15 -fsS "http://$(ip service)/healthz"; fi
if ((stage>=3)); then
 remote_bounded 15 monitoring "set -o pipefail; curl --max-time 10 -fsS 'http://127.0.0.1:9115/probe?module=http_2xx&target=http://$(ip service private_ip)/' | grep '^probe_success 1'"
 targets_ready=false
 deadline=$((SECONDS+90))
 while ((SECONDS<deadline)); do
  remaining=$((deadline-SECONDS)); attempt_timeout=$remaining
  ((attempt_timeout<=15)) || attempt_timeout=15
  if remote_bounded "$attempt_timeout" monitoring "curl --max-time 10 -fsS 'http://127.0.0.1:9090/api/v1/targets'" | python3 "$ROOT/scripts/check-targets.py"; then targets_ready=true; break; fi
  remaining=$((deadline-SECONDS)); ((remaining>0)) || break
  if ((remaining>5)); then sleep 5; else sleep "$remaining"; fi
 done
 [[ $targets_ready == true ]] || { echo 'Prometheus targets failed to become healthy within 90 seconds.' >&2; exit 1; }
fi
printf '%s\n' 'Separate-source denial checks, reboot, persistence and destroy still require docs/verification.md.'
