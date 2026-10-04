#!/usr/bin/env bash
source "$(dirname "$0")/common.sh"
role=${1:-all}; case "$role" in service|monitoring) roles=("$role");; all) roles=(service monitoring);; *) exit 2;; esac
folder="$ROOT/.private/backups/$(date -u +%Y%m%dT%H%M%SZ)"
mkdir -p "$folder"
for role in "${roles[@]}"; do
 mkdir -p "$folder/$role"
 stage=$(remote "$role" 'sudo cat /var/lib/lab/stage')
 [[ $stage =~ ^[2-5]$ ]] || { echo 'Backup requires deployed stage >=2' >&2; exit 1; }
 if [[ $role == service ]]; then names=(nginx wordpress db); volumes=(db wordpress); else
  ((stage>=3)) || { echo 'Monitoring is not deployed yet' >&2; exit 1; }
  names=(grafana prometheus blackbox); volumes=(prometheus grafana)
 fi
 units=(); for name in "${names[@]}"; do units+=("lab-container@$name"); done
 restart() { remote "$role" "sudo systemctl start ${units[*]}"; }
 trap restart EXIT
 remote "$role" "sudo systemctl stop ${units[*]}"
 for volume in "${volumes[@]}"; do
  remote "$role" "sudo podman volume export lab-$volume" > "$folder/$role/$volume.tar"
 done
 remote "$role" 'sudo tar --exclude=anomaly-delay -C /var/lib/lab -czf - .' > "$folder/$role/secrets.tar.gz"
 cp "$ROOT/images.lock.json" "$folder/$role/"
 printf '%s\n' "$stage" > "$folder/$role/stage.txt"
 restart
 trap - EXIT
 "$ROOT/scripts/wait-ready.sh" "$role" "$stage"
 python3 - "$folder/$role" <<'PY'
import sys,pathlib,hashlib,json,datetime
p=pathlib.Path(sys.argv[1]);m={'status':'measured','utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'method':'cold Podman volume export; containers stopped','files':{f.name:hashlib.sha256(f.read_bytes()).hexdigest() for f in p.iterdir() if f.is_file()}}
(p/'manifest.json').write_text(json.dumps(m,indent=2)+'\n')
PY
done
printf 'Private backup (contains secrets): %s\n' "$folder"
