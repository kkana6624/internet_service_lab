#!/usr/bin/python3
import json, os, sys
with open('/etc/lab/units/'+sys.argv[1]+'.json') as f:
    args=json.load(f)
os.execv('/usr/bin/podman',['podman','run','--rm','--name','lab-'+sys.argv[1],
    '--log-driver=k8s-file','--log-opt=max-size=10mb']+args)
