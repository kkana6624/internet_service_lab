#!/usr/bin/env bash
source "$(dirname "$0")/common.sh"
case "${1:-delay}" in
 delay) remote service 'sudo touch /var/lib/lab/anomaly-delay' ;;
 stop) remote service 'sudo systemctl stop lab-container@nginx' ;;
 *) echo 'Use delay or stop' >&2; exit 2;;
esac
