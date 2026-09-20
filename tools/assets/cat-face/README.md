# Facial mesh and texture assets

The face is a derivative of **Bicolor Cat** by **kenchoo**, itself rebuilt from **3d modelling my cat: Fripouille** by **guillaume bolis**. Both artists publish their works under **Creative Commons Attribution 4.0 International**.

- Bicolor Cat: https://sketchfab.com/3d-models/bicolor-cat-e623a618ca344a8393d7ba4d63ec23cf
- Fripouille: https://sketchfab.com/3d-models/3d-modelling-my-cat-fripouille-0ab14bf98e754f8d90fe1bf1c84ca66c
- License: https://creativecommons.org/licenses/by/4.0/
- GLB distribution mirror: https://github.com/code4fukui/vr-cats/blob/main/bicolor_cat.glb

The mirror repository's MIT software license does not replace the model's CC BY 4.0 license. The source GLB embeds the artist, source URL and CC BY 4.0 license. Public source API responses were checked on 2026-09-21; their relevant metadata and hashes are recorded in `docs/sources/cat-face/source.json`.

## Files and changes

- `face-base.npz`: head and eyes extracted from the original mesh, Catmull-Clark subdivision level 2, original UVs and target_0 shape deformation retained. The original body, skeleton and locomotion animation are not included.
- `source-albedo.png`, `source-normal.png`: source images extracted from the original GLB, retained for reproducibility.
- `detailed-albedo.png`: AI-assisted refinement of the source atlas, generated with the built-in imagegen tool. Same UV island arrangement; finer fur, iris, muzzle and nose details. This is a generated material texture, not a photograph or a screenshot of the game. The exact prompt is in `docs/sources/cat-face/texture-prompt.txt`.
- `tools/face_surface.py`: adapts the cached mesh to the game's coordinate system and breeds, recolours ginger pigment, binds the head and ears to the game rig and exports a Blink morph animation.

These source and adapted art assets are provided under **CC BY 4.0**. Credit both artists, link the license and indicate changes when reusing them. No endorsement by the source artists is implied. The game's own code and other assets are governed separately.

To reproduce extraction, download the source GLB with the recorded SHA-256 and run:

```sh
blender -b --python tools/extract_face.py -- path/to/bicolor-cat.glb
python3 tools/build_cats.py
```

The cached NPZ allows ordinary model generation without Blender. Extraction was performed with Blender 5.1.1.
