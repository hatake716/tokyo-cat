#!/usr/bin/env python3
"""Package the built developer APK and cat models with adapted-face attribution."""

import hashlib
import json
import shutil
import re
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VERSION = re.search(
    r'versionName = "([^"]+)"', (ROOT / "app/build.gradle.kts").read_text()
).group(1)
OUT = ROOT / "artifacts" / VERSION
OUT.mkdir(parents=True, exist_ok=True)
apk = OUT / f"TOKYO-CAT-{VERSION}.apk"
shutil.copy2(ROOT / "app/build/outputs/apk/debug/app-debug.apk", apk)
with zipfile.ZipFile(apk) as archive:
    files = archive.namelist()
    assert (
        len(
            [
                n
                for n in files
                if n.startswith("assets/game/models/") and n.endswith(".glb")
            ]
        )
        == 10
    )
    assert not any(n.endswith((".mp4", ".mp3", ".webm")) for n in files)
    catalog = json.loads(archive.read("assets/game/catalog.json"))
    assert len(catalog["regions"]) == 5 and len(catalog["places"]) == 15
    for model in json.loads(archive.read("assets/game/models/manifest.json")):
        assert (
            hashlib.sha256(
                archive.read("assets/game/models/" + model["file"])
            ).hexdigest()
            == model["sha256"]
        )
    for runtime in [
        "game.mjs",
        "cat-motion.mjs",
        "fur-light.mjs",
        "i18n.mjs",
        "index.html",
    ]:
        assert (
            archive.read("assets/game/" + runtime)
            == (ROOT / "app/src/main/assets/game" / runtime).read_bytes()
        )
    code = archive.read("assets/game/game.mjs")
    assert b"forwardAxis: C.Axis.X" in code
    assert b"useBrowserRecommendedResolution = false" in code
    assert b"guillaume bolis" in archive.read("assets/game/models/ATTRIBUTION.md")
    assert b"Creative Commons" in archive.read(
        "assets/game/models/LICENSE-CC-BY-4.0.txt"
    )

with zipfile.ZipFile(
    OUT / f"TOKYO-CAT-cat-models-{VERSION}.zip", "w", zipfile.ZIP_DEFLATED
) as archive:
    for path in sorted((ROOT / "app/src/main/assets/game/models").iterdir()):
        archive.write(path, path.name)
    archive.write(ROOT / "docs/CAT_MODELS.md", "README.md")
    archive.write(ROOT / "docs/FUR.md", "FUR.md")
    archive.write(ROOT / "docs/FACE.md", "FACE.md")
    archive.write(
        ROOT / "docs/sources/cat-video-reference.json",
        "sources/cat-video-reference.json",
    )
    for path in sorted((ROOT / "docs/sources/cat-reference").iterdir()):
        archive.write(path, "sources/cat-reference/" + path.name)
    for path in sorted((ROOT / "docs/sources/cat-face").iterdir()):
        archive.write(path, "sources/cat-face/" + path.name)
    archive.writestr(
        "breeds.json",
        json.dumps(catalog["breeds"], ensure_ascii=False, indent=2) + "\n",
    )

manifest = {
    p.name: {
        "bytes": p.stat().st_size,
        "sha256": hashlib.sha256(p.read_bytes()).hexdigest(),
    }
    for p in sorted(OUT.iterdir())
    if p.suffix in [".apk", ".zip"]
}
(OUT / "SHA256SUMS.txt").write_text(
    "".join(f"{v['sha256']}  {k}\n" for k, v in manifest.items())
)
(ROOT / "docs/verification/artifacts.json").write_text(
    json.dumps(manifest, indent=2) + "\n"
)
print(json.dumps(manifest, indent=2))
