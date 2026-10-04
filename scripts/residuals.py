#!/usr/bin/env python3
"""Read-only OCI inventory after destroy; does NOT delete manually bootstrapped resources."""
import pathlib,json,subprocess,datetime,sys
root=pathlib.Path(__file__).resolve().parents[1]
context_path=root/'.private/cleanup-context.json'
if not context_path.exists(): raise SystemExit('Missing context. Run scripts/save-context.py before destroy, or prepare context per docs/operations.md.')
c=json.loads(context_path.read_text());d=root/'.private/residuals'/datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%SZ');d.mkdir(parents=True,mode=0o700)
common=['--profile',c['oci_profile'],'--auth','security_token','--region',c['region'],'--compartment-id',c['compartment_ocid'],'--all']
commands={'instances':['compute','instance','list'],'boot-volumes':['bv','boot-volume','list','--availability-domain',c['availability_domain']],'block-volumes':['bv','volume','list'],'boot-backups':['bv','boot-volume-backup','list'],'block-backups':['bv','backup','list'],'reserved-ips':['network','public-ip','list','--scope','REGION'],'vcns':['network','vcn','list']}
entries=[]
for label,cmd in commands.items():
 full=['oci']+cmd+common;r=subprocess.run(full,capture_output=True,text=True)
 (d/(label+'.json')).write_text(r.stdout);(d/(label+'.stderr')).write_text(r.stderr)
 entries.append({'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'command':full,'artifact':label+'.json','exit_code':r.returncode,'status':'measured' if r.returncode==0 else 'failed','processing':'none; private infrastructure inventory'})
(d/'manifest.json').write_text(json.dumps({'entries':entries,'instruction':'Inspect lifecycle states: TERMINATED instances may remain visible; confirm no active resources/boot volumes/backups/reserved IPs. Manual IAM/compartment/DNS and local files remain outside this inventory.'},indent=2)+'\n')
print(d)
raise SystemExit(1 if any(e['exit_code'] for e in entries) else 0)
