#!/usr/bin/env bash
source "$(dirname "$0")/common.sh"
role=${1:?service or monitoring}; folder=${2:?backup role directory}
case "$role" in service) names=(nginx wordpress db); volumes=(db wordpress);; monitoring) names=(grafana prometheus blackbox);volumes=(prometheus grafana);; *) exit 2;; esac
python3 - "$folder" <<'PY'
import sys,pathlib,json,hashlib
p=pathlib.Path(sys.argv[1]);m=json.loads((p/'manifest.json').read_text())
for name,digest in m['files'].items():
 if pathlib.Path(name).name!=name: raise SystemExit('Invalid backup file name')
 if hashlib.sha256((p/name).read_bytes()).hexdigest()!=digest: raise SystemExit('Backup checksum mismatch: '+name)
PY
stage=$(cat "$folder/stage.txt"); [[ $stage =~ ^[2-5]$ ]] || exit 2
python3 - "$ROOT/images.lock.json" "$folder/images.lock.json" <<'PY_IMAGES'
import json,sys
current,backup=[{k:v['image'] for k,v in json.load(open(p)).items()} for p in sys.argv[1:]]
if current!=backup: raise SystemExit('Restore with the same pinned image digests first.')
PY_IMAGES
read -r -p "Replace $role volumes and secrets from $folder? Type RESTORE: " answer
[[ $answer == RESTORE ]] || exit 1
if [[ $role == service ]]; then "$ROOT/scripts/stop-public.sh"; fi
units=(); for name in "${names[@]}"; do units+=("lab-container@$name"); done
current_stage=$(remote "$role" 'sudo cat /var/lib/lab/stage')
[[ $current_stage =~ ^[1-5]$ ]] || exit 2
if ((current_stage>stage)); then stage=$current_stage; fi
remote "$role" "sudo systemctl stop ${units[*]}"
# On failure leave services stopped for diagnosis; do not restart with partial data.
for volume in "${volumes[@]}"; do
 remote "$role" "sudo podman volume rm lab-$volume && sudo podman volume create lab-$volume"
 remote "$role" "sudo podman volume import lab-$volume -" < "$folder/$volume.tar"
done
remote "$role" 'sudo tar -xzf - -C /var/lib/lab' < "$folder/secrets.tar.gz"
remote "$role" "sudo python3 /opt/internet-service-lab/scripts/apply-vm.py '$role' '$stage' '$(ip service private_ip)' '$(ip monitoring private_ip)' '$(value admin_cidr)' false --service-public-host '$(ip service)'"
"$ROOT/scripts/wait-ready.sh" "$role" "$stage"
echo "Restore completed privately at stage $stage. Verify content/database before separately authorizing public deployment."
