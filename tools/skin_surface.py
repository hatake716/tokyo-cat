"""Smoothly union anatomical volumes, then bind continuous skin to articulated joints."""

import math, io
from PIL import Image
import numpy as np
from skimage.measure import marching_cubes


def build(g, b, fur_mesh, cream_mesh):
    nodes = g.j["nodes"]
    parent = {child: i for i, n in enumerate(nodes) for child in n.get("children", [])}

    def translation(i):
        t = np.array(nodes[i].get("translation", [0, 0, 0]), dtype=np.float32)
        return t + translation(parent[i]) if i in parent else t

    joint_names = {
        "cat",
        "torso",
        "haunch",
        "shoulders",
        "neck",
        "chest",
        "head",
        "front_left",
        "front_right",
        "rear_left",
        "rear_right",
        "tail0",
        "tail1",
        "tail2",
        "tail3",
        "tail4",
        "front_left_knee",
        "front_right_knee",
        "rear_left_knee",
        "rear_right_knee",
    }
    joint_names.update(
        {
            leg + "_paw"
            for leg in ["front_left", "front_right", "rear_left", "rear_right"]
        }
    )
    joints = [i for i, n in enumerate(nodes) if n["name"] in joint_names]
    ji = {n: i for i, n in enumerate(joints)}

    def bone(i):
        while i not in ji:
            i = parent[i]
        return ji[i]

    shapes = []
    for i, n in enumerate(nodes):
        if n.get("mesh") in [fur_mesh, cream_mesh]:
            shapes.append(
                (
                    translation(i),
                    np.array(n["scale"], dtype=np.float32),
                    bone(i),
                    n["mesh"] == cream_mesh,
                )
            )
            del n["mesh"]
    step = 0.0045
    lo = (
        np.floor((np.min([c - r for c, r, _, _ in shapes], axis=0) - 0.02) / step)
        * step
    )
    hi = np.max([c + r for c, r, _, _ in shapes], axis=0) + 0.02
    axes = [np.arange(a, z + step, step, dtype=np.float32) for a, z in zip(lo, hi)]
    xyz = np.stack(np.meshgrid(*axes, indexing="ij"), -1)
    field = np.full(xyz.shape[:-1], 10, dtype=np.float32)

    def sdf(points, c, r):
        p = (points - c) / r
        k0 = np.linalg.norm(p, axis=-1)
        k1 = np.linalg.norm(p / r, axis=-1)
        return k0 * (k0 - 1) / np.maximum(k1, 0.00001)

    k = 0.011
    for c, r, j, w in shapes:
        d = sdf(xyz, c, r)
        h = np.maximum(k - np.abs(field - d), 0) / k
        field = np.minimum(field, d) - h * h * k * 0.25
    # Small concave eye sockets seat the cornea within the face rather than on it.
    head_pos = translation(next(i for i, n in enumerate(nodes) if n["name"] == "head"))
    for side in [-1, 1]:
        socket = head_pos + np.array([0.040, 0.008, side * 0.035], dtype=np.float32)
        field = np.maximum(
            field, -sdf(xyz, socket, np.array([0.020, 0.013, 0.018], dtype=np.float32))
        )
    verts, faces, normals, _ = marching_cubes(
        field, 0, spacing=(step, step, step), gradient_direction="ascent"
    )
    verts += lo
    normals = -normals
    faces = faces[:, [0, 2, 1]]
    influences = np.zeros((len(verts), len(joints)), dtype=np.float32)
    white = np.zeros(len(verts), dtype=np.float32)
    for c, r, j, w in shapes:
        weight = np.exp(-np.clip(sdf(verts, c, r), -0.015, 1) / 0.009)
        influences[:, j] += weight
        if w:
            white += weight
    order = np.argsort(influences, axis=1)[:, -4:]
    weights = np.take_along_axis(influences, order, axis=1)
    weights /= weights.sum(axis=1, keepdims=True)
    white = np.clip(white / np.maximum(influences.sum(axis=1), 1e-12), 0, 1)
    rgb = np.array([int(b["color"][i : i + 2], 16) for i in [1, 3, 5]]) / 255
    x, y, z = verts.T
    hip = 0.267 * b["legs"] + 0.002
    factor = np.ones(len(verts))
    tabby = b["id"] in ["mixed", "american", "siberian", "norwegian"]
    if tabby:
        # Broken side stripes, cheek stripes and rings below knees / along the tail.
        side = (
            np.maximum(0, np.cos(x * 108 + np.sin(y * 33) * 1.7 + np.cos(z * 28) * 0.8))
            ** 9
        )
        legstripe = np.maximum(0, np.cos(y * 180 + x * 10)) ** 10
        tailstripe = np.maximum(0, np.cos(x * 115)) ** 9
        mask = np.where(
            y < hip - 0.08, legstripe, np.where(x < -0.29, tailstripe, side)
        )
        headmask = (x > 0.245) & (y > hip + 0.09)
        mask[headmask] = (
            np.maximum(0, np.cos(z[headmask] * 300 + x[headmask] * 65)) ** 8
        )
        factor -= mask * 0.45
    col = np.clip(factor[:, None] * rgb, 0, 1)
    if tabby:
        back = np.clip((y - hip - 0.028) * 7, 0, 0.22) * (x < 0.15)
        col *= 1 - back[:, None]
        bib = np.clip((hip + 0.015 - y) * 5, 0, 0.40) * (x > 0.12)
        col = col * (1 - bib[:, None]) + np.array([0.70, 0.68, 0.59]) * bib[:, None]
    if b["id"] in ["ragdoll", "ragamuffin"]:
        face = np.clip((x - 0.242) * 20, 0, 0.85) * np.clip(
            (y - hip - 0.045) * 20, 0, 1
        )
        points = np.maximum.reduce(
            [face, np.clip((0.07 - y) * 7, 0, 0.6), np.clip((-x - 0.25) * 3, 0, 0.65)]
        )
        col *= 1 - points[:, None] * 0.68
        # Pale inverted V and bib; pigments, not a source photograph.
        blaze = (np.abs(z) < np.maximum(0, (hip + 0.15 - y) * 0.30)) & (x > 0.26)
        col[blaze] = col[blaze] * 0.25 + np.array([0.89, 0.87, 0.81]) * 0.75
    under = np.clip((hip + 0.015 - y) * 2, 0, 0.12)
    col = np.clip(col + under[:, None], 0, 1)
    col = col * (1 - white[:, None]) + np.array([0.83, 0.81, 0.75]) * white[:, None]
    # Material color factors are linear; convert authored sRGB coat samples.
    linear = np.where(col <= 0.04045, col / 12.92, ((col + 0.055) / 1.055) ** 2.4)
    # Fine authored fibre albedo and tangent-space normal texture.
    rng = np.random.default_rng(740)
    w = 256
    h = 256
    grain = rng.random((h, w))
    grain = (
        grain
        + np.roll(grain, 1, axis=1)
        + np.roll(grain, 2, axis=1)
        + np.roll(grain, 3, axis=1)
    ) / 4
    color = np.repeat((0.86 + 0.14 * grain)[:, :, None], 3, axis=2)
    buf = io.BytesIO()
    Image.fromarray(np.uint8(color * 255)).save(buf, format="PNG")
    material = g.material("continuous_coat", [1, 1, 1], 0.94, buf.getvalue())
    dy, dx = np.gradient(grain)
    normal = np.dstack([-dx * 0.9, -dy * 0.9, np.ones_like(grain)])
    normal /= np.linalg.norm(normal, axis=2, keepdims=True)
    buf = io.BytesIO()
    Image.fromarray(np.uint8((normal * 0.5 + 0.5) * 255)).save(buf, format="PNG")
    im = len(g.j["images"])
    g.j["images"].append(
        {"bufferView": g.blob(buf.getvalue()), "mimeType": "image/png"}
    )
    tex = len(g.j["textures"])
    g.j["textures"].append({"source": im, "sampler": 0})
    g.j["materials"][material]["normalTexture"] = {"index": tex, "scale": 0.45}
    # Seam is on the underside; use local cylindrical coordinates, fine repeating detail.
    uv = np.column_stack([x * 7, np.arctan2(z, y - hip) / (2 * math.pi) * 6])
    attrs = {
        "POSITION": g.acc(verts, "VEC3"),
        "NORMAL": g.acc(normals, "VEC3"),
        "TEXCOORD_0": g.acc(uv, "VEC2"),
        "COLOR_0": g.acc(linear, "VEC3"),
        "JOINTS_0": g.acc(order, "VEC4", 5123),
        "WEIGHTS_0": g.acc(weights, "VEC4"),
    }
    mesh = len(g.j["meshes"])
    g.j["meshes"].append(
        {
            "name": "continuous_anatomical_skin",
            "primitives": [
                {
                    "attributes": attrs,
                    "indices": g.acc(faces.reshape(-1), "SCALAR", 5125),
                    "material": material,
                }
            ],
        }
    )
    inv = []
    for i in joints:
        m = np.eye(4, dtype=np.float32)
        scale = np.array(nodes[i].get("scale", [1, 1, 1]))
        m[:3, :3] = np.diag(1 / scale)
        m[:3, 3] = -translation(i) / scale
        inv.append(m.T.reshape(16))
    g.j["skins"] = [
        {
            "name": "quadruped_rig",
            "inverseBindMatrices": g.acc(inv, "MAT4"),
            "skeleton": 0,
            "joints": joints,
        }
    ]
    node = g.node("continuous_skin", mesh)
    nodes[node]["skin"] = 0
    g.j.setdefault("extras", {})["surface"] = {
        "method": "smooth implicit union, marching cubes, weighted skin",
        "vertices": len(verts),
        "triangles": len(faces),
        "joints": len(joints),
    }

    from groom_fur import build as build_fur

    build_fur(g, b, verts, faces, normals, linear, order, weights, head_pos)
