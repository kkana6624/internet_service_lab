import urllib.request,json
from pathlib import Path
images={'nginx':('library/nginx','stable'),'wordpress':('library/wordpress','php8.3-apache'),'mariadb':('library/mariadb','lts'),'prometheus':('prom/prometheus','latest'),'grafana':('grafana/grafana','latest'),'blackbox':('prom/blackbox-exporter','latest'),'node':('prom/node-exporter','latest')}
out={}
for name,(repo,tag) in images.items():
 token=json.load(urllib.request.urlopen('https://auth.docker.io/token?service=registry.docker.io&scope=repository:'+repo+':pull'))['token']
 req=urllib.request.Request('https://registry-1.docker.io/v2/'+repo+'/manifests/'+tag,headers={'Authorization':'Bearer '+token,'Accept':'application/vnd.oci.image.index.v1+json, application/vnd.docker.distribution.manifest.list.v2+json'})
 with urllib.request.urlopen(req) as r:
  data=json.load(r); digest=r.headers['Docker-Content-Digest']
 out[name]={'image':'docker.io/'+repo+'@'+digest,'tag':tag,'platforms':[m['platform'] for m in data.get('manifests',[])]}
 child=next((m['digest'] for m in data.get('manifests',[]) if m['platform'].get('architecture')=='amd64' and m['platform'].get('os')=='linux'),digest)
 req=urllib.request.Request('https://registry-1.docker.io/v2/'+repo+'/manifests/'+child,headers={'Authorization':'Bearer '+token,'Accept':'application/vnd.oci.image.manifest.v1+json, application/vnd.docker.distribution.manifest.v2+json'})
 manifest=json.load(urllib.request.urlopen(req))
 req=urllib.request.Request('https://registry-1.docker.io/v2/'+repo+'/blobs/'+manifest['config']['digest'],headers={'Authorization':'Bearer '+token})
 config=json.load(urllib.request.urlopen(req))
 out[name]['metadata']={k:config.get('config',{}).get(k) for k in ['Env','Labels']}
 print(name,tag,digest)
Path('images.lock.json').write_text(json.dumps(out,indent=2)+'\n')
