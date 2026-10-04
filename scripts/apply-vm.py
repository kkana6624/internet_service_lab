#!/usr/bin/env python3
"""Run as root on the VM; repo is deployed to /opt/internet-service-lab."""
import argparse, json, subprocess, pathlib, secrets, os, ipaddress
p=argparse.ArgumentParser(); p.add_argument('role',choices=['service','monitoring']);p.add_argument('stage',type=int,choices=range(1,6));p.add_argument('service_ip');p.add_argument('monitor_ip');p.add_argument('admin_cidr');p.add_argument('public',choices=['true','false']);p.add_argument('--firewall-only',action='store_true');p.add_argument('--service-public-host');a=p.parse_args()
for ip in [a.service_ip,a.monitor_ip]: ipaddress.IPv4Address(ip)
if a.service_public_host: ipaddress.IPv4Address(a.service_public_host)
net=ipaddress.IPv4Network(a.admin_cidr,strict=False)
if net.prefixlen<24: raise SystemExit('admin CIDR too broad')
base=pathlib.Path(__file__).resolve().parents[1]; cfg=pathlib.Path('/etc/lab');cfg.mkdir(mode=0o700,exist_ok=True);(cfg/'units').mkdir(exist_ok=True)
data=pathlib.Path('/var/lib/lab');data.mkdir(mode=0o700,exist_ok=True)
images=json.loads((base/'images.lock.json').read_text())
def run(*args):
    timeout = 900 if args[:2] == ('podman','pull') else 120
    subprocess.run(args,check=True,timeout=timeout)
def save(path,s,mode=0o600):
    path=pathlib.Path(path);path.parent.mkdir(parents=True,exist_ok=True);path.write_text(s);path.chmod(mode)
def secret(name,uid=0):
    f=data/name
    if not f.exists(): save(f,secrets.token_hex(32))
    os.chown(f,uid,uid);f.chmod(0o400)
    return str(f)
# Keep firewalld/SELinux active; nft prerouting protects published ports BEFORE DNAT.
# Established egress replies are allowed; management/source rules cover only new TCP.
allowweb='0.0.0.0/0' if a.public=='true' else str(net)
private=a.service_ip if a.role=='service' else a.monitor_ip
rules=f"""table inet lab_guard {{
 chain ingress {{
  type filter hook prerouting priority -150; policy accept;
  iifname "lo" accept
  ct state established,related accept
  ip daddr {private} ip saddr {net} tcp dport 22 accept
  ip daddr {private} tcp dport 22 drop
  ip daddr {private} ip saddr {a.monitor_ip} tcp dport 9100 accept
  ip daddr {private} tcp dport 9100 drop
  ip daddr {private} tcp dport {{3000,3306,8080,9090,9115}} drop
"""
if a.role=='service': rules+=f"  ip daddr {private} ip saddr {a.monitor_ip} tcp dport 80 accept\n  ip daddr {private} ip saddr {allowweb} tcp dport 80 accept\n  ip daddr {private} tcp dport 80 drop\n  ip daddr {private} ip saddr {a.monitor_ip} tcp dport 8081 accept\n  ip daddr {private} tcp dport 8081 drop\n"
else: rules+=f"  ip daddr {private} tcp dport {{80,8081}} drop\n"
rules+=' }\n}\n';save(cfg/'guard.nft',rules)
# Replacement is one nft transaction; do not flush OCI/Podman/firewalld rules.
save('/usr/local/libexec/lab-firewall', '#!/bin/bash\nset -euo pipefail\nif nft list table inet lab_guard >/dev/null 2>&1; then { echo "delete table inet lab_guard"; cat /etc/lab/guard.nft; } | nft -f -; else nft -f /etc/lab/guard.nft; fi\n',0o755)
save('/etc/systemd/system/lab-firewall.service','[Unit]\nAfter=firewalld.service\nRequires=firewalld.service\nBefore=lab-container@nginx.service\n[Service]\nType=oneshot\nExecStart=/usr/local/libexec/lab-firewall\nExecReload=/usr/local/libexec/lab-firewall\nRemainAfterExit=yes\n[Install]\nWantedBy=multi-user.target\n')
run('systemctl','enable','--now','firewalld')
for port in ([80,8081,9100] if a.role=='service' else [9100]):
    run('firewall-cmd','--permanent','--add-port='+str(port)+'/tcp')
run('firewall-cmd','--reload')
run('systemctl','daemon-reload');run('systemctl','enable','lab-firewall');run('systemctl','reload-or-restart','lab-firewall')
# firewalld reload can remove rootful Podman network rules; restore after guard.
if a.stage>=2: run('podman','network','reload','--all')
if a.firewall_only: raise SystemExit(0)
if a.stage==1:
    save(data/'stage','1\n')
    raise SystemExit(0)
save('/usr/local/libexec/lab-container',(base/'scripts/container-runner.py').read_text(),0o755)
save('/etc/systemd/system/lab-container@.service',(base/'service/lab-container@.service').read_text(),0o644)
def container(name,image,args,extra=''):
    ref=images[image]['image'];run('podman','pull',ref)
    save(cfg/'units'/f'{name}.json',json.dumps(args+[ref]+extra.split()))
    save(cfg/'units'/f'{name}.env','LAB_MANAGED=1\n')
    run('systemctl','daemon-reload');run('systemctl','enable',f'lab-container@{name}');run('systemctl','restart',f'lab-container@{name}')
def volume(name):
    run('podman','volume','create','--ignore','lab-'+name)
container('node','node',['--network=host','--pid=host','--security-opt=label=disable','--read-only','-v','/:/host:ro,rslave'],f'--path.rootfs=/host --web.listen-address={private}:9100')
if a.role=='service':
    if subprocess.run(['podman','network','exists','lab-db']).returncode: run('podman','network','create','lab-db')
    for v in ['db','wordpress']: volume(v)
    dbpw=secret('db-password');rootpw=secret('db-root-password',999)
    # Entrypoints/runtime read _FILE as their container UID, not always root.
    dbcopy=data/'db-container-password';wpcopy=data/'wp-container-password'
    for target,uid in [(dbcopy,999),(wpcopy,33)]:
        save(target,pathlib.Path(dbpw).read_text(),0o400);os.chown(target,uid,uid)
    container('db','mariadb',['--network=lab-db','--network-alias=db','-v','lab-db:/var/lib/mysql','-v',str(dbcopy)+':/run/secrets/db:ro,Z','-v',rootpw+':/run/secrets/root:ro,Z','-e','MARIADB_ROOT_PASSWORD_FILE=/run/secrets/root','-e','MARIADB_PASSWORD_FILE=/run/secrets/db','-e','MARIADB_DATABASE=wordpress','-e','MARIADB_USER=wordpress'])
    container('wordpress','wordpress',['--network=lab-db','-p','127.0.0.1:8080:80','-v','lab-wordpress:/var/www/html','-v',str(wpcopy)+':/run/secrets/db:ro,Z','-e','WORDPRESS_DB_HOST=db','-e','WORDPRESS_DB_NAME=wordpress','-e','WORDPRESS_DB_USER=wordpress','-e','WORDPRESS_DB_PASSWORD_FILE=/run/secrets/db'])
    nginx=(base/'service/nginx/nginx.conf').read_text()
    if a.stage>=5: nginx=nginx.replace('# PROTECTED_RULES',f'allow {net}; deny all; limit_req zone=login burst=3 nodelay;')
    save(cfg/'nginx.conf',nginx,0o644)
    container('nginx','nginx',['--network=host','-v',str(cfg/'nginx.conf')+':/etc/nginx/nginx.conf:ro,Z'])
    save('/etc/systemd/system/lab-experiment.service',f'[Unit]\nAfter=network-online.target lab-firewall.service\nRequires=lab-firewall.service\n[Service]\nExecStart=/usr/bin/python3 {base}/service/experiment.py {private}\nRestart=always\n[Install]\nWantedBy=multi-user.target\n',0o644)
    run('systemctl','daemon-reload');run('systemctl','enable','--now','lab-experiment')
elif a.stage>=3:
    for v in ['prometheus','grafana']: volume(v)
    content=(base/'monitoring/prometheus/prometheus.yml').read_text().replace('SERVICE_IP',a.service_ip).replace('MONITOR_IP',a.monitor_ip)
    save(cfg/'prometheus.yml',content,0o644)
    save(cfg/'blackbox.yml',(base/'monitoring/blackbox.yml').read_text().replace('SERVICE_PUBLIC_HOST',a.service_public_host or a.service_ip),0o644)
    container('blackbox','blackbox',['--network=host','-v',str(cfg/'blackbox.yml')+':/etc/blackbox.yml:ro,Z'],'--config.file=/etc/blackbox.yml --web.listen-address=127.0.0.1:9115')
    container('prometheus','prometheus',['--network=host','-v',str(cfg/'prometheus.yml')+':/etc/prometheus/prometheus.yml:ro,Z','-v',str(base/'monitoring/prometheus/alerts.yml')+':/etc/prometheus/alerts.yml:ro,Z','-v','lab-prometheus:/prometheus:U'],'--config.file=/etc/prometheus/prometheus.yml --web.listen-address=127.0.0.1:9090 --storage.tsdb.path=/prometheus --storage.tsdb.retention.time=7d --storage.tsdb.retention.size=2GB')
    gpw=secret('grafana-password',472)
    container('grafana','grafana',['--network=host','-v','lab-grafana:/var/lib/grafana:U','-v',gpw+':/run/secrets/admin:ro,Z','-v',str(base/'monitoring/grafana/provisioning')+':/etc/grafana/provisioning:ro,Z','-v',str(base/'monitoring/grafana/dashboards')+':/etc/grafana/dashboards:ro,Z','-e','GF_SECURITY_ADMIN_PASSWORD__FILE=/run/secrets/admin','-e','GF_SERVER_HTTP_ADDR=127.0.0.1','-e','GF_USERS_ALLOW_SIGN_UP=false','-e','GF_AUTH_ANONYMOUS_ENABLED=false'])
save(data/'stage',str(a.stage)+'\n')
