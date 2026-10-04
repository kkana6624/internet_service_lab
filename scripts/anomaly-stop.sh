#!/usr/bin/env bash
source "$(dirname "$0")/common.sh"
case "${1:-delay}" in
 delay) remote service 'sudo rm -f /var/lib/lab/anomaly-delay; sudo systemctl start lab-container@nginx' ;;
 stop) remote service 'sudo systemctl start lab-container@nginx' ;;
 *) echo 'Use delay or stop' >&2; exit 2;;
esac
