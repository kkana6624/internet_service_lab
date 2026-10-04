#!/usr/bin/env bash
source "$(dirname "$0")/common.sh"
# Same URL, agent, count, interval, timeout before/during/after. Public IP is a separate path.
mode=${1:?internal or external}; count=${2:-10}
case "$mode" in internal|external) ;; *) exit 2;; esac
[[ $count =~ ^[1-9][0-9]*$ ]] && ((count<=100)) || exit 2
failed=0
for ((i=0;i<count;i++)); do
 date -u +%FT%TZ
 code=0
 case "$mode" in
 internal) remote_bounded 15 monitoring "curl --max-time 5 -sS -o /dev/null -A lab-controlled-measure -w '%{http_code} %{time_total}\\n' 'http://$(ip service private_ip):8081/experiment'" || code=$? ;;
 external) curl --max-time 5 -sS -o /dev/null -A lab-controlled-measure -w '%{http_code} %{time_total}\n' "http://$(ip service)/" || code=$? ;;
 esac
 printf 'sample=%s exit_code=%s\n' "$((i+1))" "$code"
 if ((code!=0)); then failed=1; fi
 if ((i+1<count)); then sleep 2; fi
done
exit "$failed"
