#!/usr/bin/env python3
"""Read-only live verification of pinned city manifests and authoritative terrain."""
import json,urllib.request,hashlib,datetime
from pathlib import Path
root=Path(__file__).resolve().parents[1]
cat=json.loads((root/'app/src/main/assets/game/catalog.json').read_text())
urls={r['ward']:r['tiles'] for r in cat['regions']}
urls['terrain']='https://tile.plateauview.mlit.go.jp/terrain/layer.json'
results=[]
for id,url in urls.items():
 with urllib.request.urlopen(url,timeout=30) as response:
  data=response.read();j=json.loads(data)
  assert ('root' in j if id!='terrain' else 'tiles' in j)
  results.append(dict(id=id,url=url,http=response.status,bytes=len(data),sha256=hashlib.sha256(data).hexdigest()))
 print(id,'OK',len(data),'bytes')
(root/'docs/verification/live-sources.json').write_text(json.dumps({'checked_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'results':results},indent=2)+'\n')
