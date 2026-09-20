"""Blender preprocessing for the CC BY 4.0 Fripouille / Bicolor Cat face.

Usage: blender -b --python tools/extract_face.py -- path/to/bicolor-cat.glb
The output contains a cropped subdivided head, eyes, UVs and blink deltas.
Body, source rig, source animation and reference photos are not copied.
"""

import sys
from pathlib import Path
import bpy
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "tools/assets/cat-face"
OUT.mkdir(parents=True, exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=sys.argv[sys.argv.index("--") + 1])
result = {}
for obj in list(bpy.data.objects):
    if obj.type != "MESH" or not obj.data.shape_keys:
        continue
    obj.data.shape_keys.animation_data_clear()
    for key in obj.data.shape_keys.key_blocks:
        key.value = 0
    for mod in obj.modifiers:
        if mod.type == "ARMATURE":
            mod.show_viewport = False
            mod.show_render = False
    sub = obj.modifiers.new("Face subdivision", "SUBSURF")
    sub.levels = 2
    sub.render_levels = 2
    part = "face" if len(obj.data.vertices) > 500 else "eyes"
    bpy.context.view_layer.update()

    def arrays():
        evaluated = obj.evaluated_get(bpy.context.evaluated_depsgraph_get())
        mesh = evaluated.to_mesh()
        mesh.calc_loop_triangles()
        matrix = obj.matrix_world
        pp = np.array([matrix @ v.co for v in mesh.vertices], dtype=np.float32)
        normal_matrix = matrix.to_3x3().inverted().transposed()
        nn = np.array(
            [normal_matrix @ v.normal for v in mesh.vertices], dtype=np.float32
        )
        nn /= np.maximum(np.linalg.norm(nn, axis=1, keepdims=True), 1e-9)
        tris = np.array([t.vertices[:] for t in mesh.loop_triangles], dtype=np.int32)
        uv = np.array(
            [
                [mesh.uv_layers.active.data[i].uv[:] for i in t.loops]
                for t in mesh.loop_triangles
            ],
            dtype=np.float32,
        )
        evaluated.to_mesh_clear()
        return pp, nn, tris, uv

    pos, normal, tris, uv = arrays()
    keep = ((pos[:, 1] < -0.163) & (pos[:, 2] > 0.248))[tris].all(axis=1)
    tris = tris[keep]
    uv = uv[keep]
    uv[:, :, 1] = 1 - uv[:, :, 1]
    # Preserve UV seams while sharing the original subdivided topology elsewhere.
    mapping = {}
    indices = []
    source = []
    tex = []
    for tri, coords in zip(tris, uv):
        face = []
        for v, t in zip(tri, coords):
            key = (int(v), round(float(t[0]), 7), round(float(t[1]), 7))
            if key not in mapping:
                mapping[key] = len(source)
                source.append(v)
                tex.append(t)
            face.append(mapping[key])
        indices.append(face)
    source = np.array(source)
    result[part + "_position"] = pos[source]
    result[part + "_normal"] = normal[source]
    result[part + "_uv"] = np.array(tex, dtype=np.float32)
    result[part + "_triangles"] = np.array(indices, dtype=np.int32)
    obj.data.shape_keys.key_blocks[1].value = 1
    bpy.context.view_layer.update()
    closed, closed_normal, _, _ = arrays()
    result[part + "_blink"] = closed[source] - pos[source]
    result[part + "_blink_normal"] = closed_normal[source] - normal[source]
    obj.data.shape_keys.key_blocks[1].value = 0
    print(
        part,
        len(source),
        len(indices),
        "blink max",
        np.max(np.abs(result[part + "_blink"])),
    )
np.savez_compressed(OUT / "face-base.npz", **result)
