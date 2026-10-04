#!/usr/bin/env python3
"""Save non-secret OCI inventory context BEFORE destroying Terraform outputs."""
import json,pathlib,subprocess,os
root=pathlib.Path(__file__).resolve().parents[1]
r=subprocess.run([os.environ.get('TF','terraform'),'-chdir='+str(root/'terraform'),'output','-json'],capture_output=True,text=True,check=True)
outputs=json.loads(r.stdout)
context={k:outputs[k]['value'] for k in ['region','oci_profile','compartment_ocid','availability_domain','vms']}
dest=root/'.private/cleanup-context.json';dest.parent.mkdir(mode=0o700,exist_ok=True);dest.write_text(json.dumps(context,indent=2)+'\n');dest.chmod(0o600)
print('Saved .private/cleanup-context.json (contains infrastructure identifiers; keep private)')
