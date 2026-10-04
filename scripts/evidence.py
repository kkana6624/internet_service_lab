#!/usr/bin/env python3
"""Capture only real commands; unavailable stage components are explicitly unacquired."""
import subprocess, datetime, json, os, pathlib, sys, hashlib
root = pathlib.Path(__file__).resolve().parents[1]
dest = pathlib.Path(os.environ['EVIDENCE_DIR'])
stage = int(sys.argv[1])
def capture(label, command):
    try:
        r = subprocess.run(command, cwd=root, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, timeout=240)
    except subprocess.TimeoutExpired as error:
        output = error.stdout or ''
        if isinstance(output, bytes): output = output.decode(errors='replace')
        r = subprocess.CompletedProcess(command, 124, output + '\nEvidence command timed out after 240 seconds.\n')
    (dest / (label + '.txt')).write_text(r.stdout)
    return {'artifact': label + '.txt', 'utc': datetime.datetime.now(datetime.timezone.utc).isoformat(), 'cwd': 'repository root', 'command': command, 'exit_code': r.returncode, 'status': 'measured' if r.returncode == 0 else 'failed', 'processing': 'none; raw private; review required'}
def shell(role, command):
    return ['bash', '-c', 'source scripts/common.sh; remote_bounded 120 "$1" "$2"', 'evidence', role, 'set -e; ' + command]
commit = subprocess.run(['git', 'rev-parse', 'HEAD'], capture_output=True, text=True)
tag = subprocess.run(['git', 'describe', '--tags', '--exact-match'], capture_output=True, text=True)
tree = subprocess.run(['git', 'status', '--porcelain'], cwd=root, capture_output=True, text=True)
manifest = {'stage': f'{stage:02d}', 'timezone': 'UTC', 'commit': commit.stdout.strip() if commit.returncode == 0 else 'uncommitted', 'tag': tag.stdout.strip() if tag.returncode == 0 else 'no-stage-tag', 'conditions': {'internal': 'monitor VM -> service Private IP:8081/experiment', 'external': 'management PC -> service Public IP:80/', 'measurement': '10 requests, 2s interval, curl timeout5s, User-Agent lab-controlled-measure; observations are separate paths'}, 'entries': [], 'screenshots': 'not-acquired'}
manifest['working_tree_has_changes'] = bool(tree.stdout.strip()) if tree.returncode == 0 else None
manifest['source_sha256'] = {str(f.relative_to(root)): hashlib.sha256(f.read_bytes()).hexdigest() for pattern in ['scripts/*.sh','scripts/*.py','service/**/*','monitoring/**/*','terraform/**/*.tf','terraform/**/*.yaml','stages/config/*.json','images.lock.json','terraform/.terraform.lock.hcl'] for f in sorted(root.glob(pattern)) if f.is_file()}
manifest['source_scope'] = 'local repository only; VM deployment source hashes recorded separately'
level = stage
if stage == 6:
    r = subprocess.run(shell('service', 'sudo cat /var/lib/lab/stage'), cwd=root, capture_output=True, text=True)
    level = int(r.stdout.strip()) if r.returncode == 0 and r.stdout.strip() in ['1','2','3','4','5'] else 0
    manifest['deployed_stage_at_cleanup'] = level
commands = [('versions', [os.environ.get('TF', 'terraform'), 'version']), ('images', ['cat', 'images.lock.json']), ('outputs', [os.environ.get('TF','terraform'), '-chdir=terraform', 'output', '-json'])]
for role in ['service', 'monitoring']:
    commands.append((role+'-deployed-source', shell(role, "sudo python3 -c 'import pathlib,hashlib,json; p=pathlib.Path(\"/opt/internet-service-lab\"); print(json.dumps({str(f.relative_to(p)):hashlib.sha256(f.read_bytes()).hexdigest() for f in sorted(p.rglob(\"*\")) if f.is_file()}))'")))
    commands += [(role+'-runtime', shell(role, 'sudo podman ps -a; sudo systemctl --failed; sudo ss -lntp')), (role+'-guard', shell(role, 'sudo nft list table inet lab_guard; sudo firewall-cmd --list-all')), (role+'-versions', shell(role, 'cat /etc/os-release; rpm -q podman nftables firewalld; sudo cloud-init status --long'))]
    if role == 'service' and level >= 2:
        commands.append(('service-access-log', shell(role, 'sudo journalctl -u lab-container@nginx -n 500 --no-pager; sudo podman logs --tail 500 lab-nginx')))
        commands.append(('service-image-versions', shell(role, '''sudo podman exec lab-nginx nginx -v && sudo podman exec lab-db mariadb --version && sudo podman exec lab-wordpress php -r 'include "/usr/src/wordpress/wp-includes/version.php"; echo $wp_version, PHP_EOL;' ''')))
    elif role == 'monitoring' and level >= 3:
        commands.append(('monitoring-logs', shell(role, 'sudo journalctl -u lab-container@prometheus -n 500 --no-pager; sudo podman logs --tail 100 lab-prometheus')))
        commands.append(('targets', shell(role, 'curl -fsS http://127.0.0.1:9090/api/v1/targets')))
        commands.append(('alerts', shell(role, 'curl -fsS http://127.0.0.1:9090/api/v1/alerts')))
        commands.append(('monitoring-image-versions', shell(role, 'sudo podman exec lab-prometheus prometheus --version && sudo podman exec lab-blackbox blackbox_exporter --version && curl -fsS http://127.0.0.1:3000/api/health')))
    else:
        manifest['entries'].append({'artifact': role+'-workload-logs', 'status':'not-acquired', 'reason':'workload not deployed at this stage', 'command':None, 'exit_code':None, 'processing':'none'})
if level >= 3: commands.append(('internal', ['scripts/measure.sh','internal','10']))
else: manifest['entries'].append({'artifact':'internal','status':'not-acquired','reason':'monitoring stage not deployed','command':None,'exit_code':None,'processing':'none'})
if level >= 2: commands.append(('external', ['scripts/measure.sh','external','10']))
else: manifest['entries'].append({'artifact':'external','status':'not-acquired','reason':'Web stage not deployed','command':None,'exit_code':None,'processing':'none'})
for label, command in commands:
    manifest['entries'].append(capture(label,command))
(dest/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
sys.exit(1 if any(e['status']=='failed' for e in manifest['entries']) else 0)
