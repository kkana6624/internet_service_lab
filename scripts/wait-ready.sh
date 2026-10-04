#!/usr/bin/env bash
source "$(dirname "$0")/common.sh"
role=${1:?role}; stage=${2:?stage}; timeout=${READY_TIMEOUT:-900}
[[ $timeout =~ ^[1-9][0-9]*$ ]] || exit 2
deadline=$((SECONDS+timeout))
case "$role" in service|monitoring) ;; *) exit 2;; esac
case "$stage" in 1|2|3|4|5) ;; *) exit 2;; esac
check='sudo test -f /var/lib/cloud/instance/boot-finished && ! sudo test -s /var/lib/cloud/instance/error.log && sudo systemctl is-active --quiet lab-firewall'
if ((stage>=2)); then
 check+=' && sudo systemctl is-active --quiet lab-container@node'
 if [[ $role == service ]]; then
  check+=' && sudo timeout 10 podman exec lab-db healthcheck.sh --connect --innodb_initialized && curl --max-time 5 -fsS -o /dev/null http://127.0.0.1/healthz && curl --max-time 5 -fsS -o /dev/null http://127.0.0.1:8080/'
 elif ((stage>=3)); then
  check+=' && curl --max-time 5 -fsS -o /dev/null http://127.0.0.1:9090/-/ready && curl --max-time 5 -fsS -o /dev/null http://127.0.0.1:3000/api/health && curl --max-time 5 -fsS -o /dev/null http://127.0.0.1:9115/'
 fi
fi
while ((SECONDS<deadline)); do
 remaining=$((deadline-SECONDS)); attempt_timeout=$remaining
 ((attempt_timeout<=30)) || attempt_timeout=30
 if remote_bounded "$attempt_timeout" "$role" "$check"; then echo "$role ready"; exit 0; fi
 remaining=$((deadline-SECONDS)); ((remaining>0)) || break
 if ((remaining>5)); then sleep 5; else sleep "$remaining"; fi
done
remote_bounded 20 "$role" 'sudo cloud-init status --long; sudo systemctl --failed; sudo podman ps -a; sudo journalctl -n 80 -u lab-firewall -u lab-container@nginx -u lab-container@prometheus --no-pager' >&2 || true
echo "Readiness timeout: $role" >&2
exit 1
