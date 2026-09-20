#!/usr/bin/env python3
"""Package the already-built developer APK and authored cat models; verify contents."""
import hashlib
import json
import shutil
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'artifacts/0.1.0-dev'
OUT.mkdir(parents=True, exist_ok=True)
apk = OUT / 'TOKYO-CAT-0.1.0-dev.apk'
shutil.copy2(ROOT / 'app/build/outputs/apk/debug/app-debug.apk', apk)
with zipfile.ZipFile(apk) as archive:
    files = archive.namelist()
    assert len([n for n in files if n.startswith('assets/game/models/') and n.endswith('.glb')]) == 10
    assert not any(n.endswith(('.mp4', '.mp3', '.webm')) for n in files)
    catalog = json.loads(archive.read('assets/game/catalog.json'))
    assert len(catalog['regions']) == 5 and len(catalog['places']) == 15
    for model in json.loads(archive.read('assets/game/models/manifest.json')):
        assert hashlib.sha256(archive.read('assets/game/models/' + model['file'])).hexdigest() == model['sha256']
    code = archive.read('assets/game/game.mjs')
    assert b'forwardAxis: C.Axis.X' in code
    assert b'useBrowserRecommendedResolution = false' in code

with zipfile.ZipFile(OUT / 'TOKYO-CAT-cat-models-0.1.0-dev.zip', 'w', zipfile.ZIP_DEFLATED) as archive:
    for path in sorted((ROOT / 'app/src/main/assets/game/models').iterdir()):
        archive.write(path, path.name)
    archive.write(ROOT / 'docs/CAT_MODELS.md', 'README.md')
    archive.write(ROOT / 'docs/sources/cat-video-reference.json', 'sources/cat-video-reference.json')
    archive.writestr('breeds.json', json.dumps(catalog['breeds'], ensure_ascii=False, indent=2) + '\n')

manifest = {
    p.name: {'bytes': p.stat().st_size, 'sha256': hashlib.sha256(p.read_bytes()).hexdigest()}
    for p in sorted(OUT.iterdir()) if p.suffix in ['.apk', '.zip']
}
(OUT / 'SHA256SUMS.txt').write_text(''.join(f"{v['sha256']}  {k}\n" for k, v in manifest.items()))
(ROOT / 'docs/verification/artifacts.json').write_text(json.dumps(manifest, indent=2) + '\n')
print(json.dumps(manifest, indent=2))
