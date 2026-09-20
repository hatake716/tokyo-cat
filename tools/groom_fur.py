"""Deterministic, area-sampled, skinned two-layer fur with a hand-authored groom.

Curved ribbons carry an original alpha atlas of individual tapered strands.
The alpha atlas is authored; facial root colours sample the credited adapted texture.
Individual strands are not physically simulated.
"""

import io
import numpy as np
from PIL import Image, ImageDraw

LONGHAIR = {"ragdoll", "minuet", "siberian", "norwegian", "ragamuffin"}


def strand_atlas():
    """Four non-periodic clumps, each 128x256, supersampled for fine wisps."""
    rng = np.random.default_rng(12390)
    ss = 3
    tile = 128
    height = 256
    alpha = Image.new("L", (tile * 4 * ss, height * ss))
    draw = ImageDraw.Draw(alpha)
    for variant in range(4):
        for hair in range(52):
            start = rng.uniform(0.03, 0.97)
            end = np.clip(start + rng.normal(0, 0.095), 0.025, 0.975)
            length = rng.uniform(0.62, 1) if hair < 31 else rng.uniform(0.30, 0.76)
            bend = rng.normal(0, 0.040)
            opacity = int(rng.uniform(155, 255))
            points = []
            for t in np.linspace(0, 1, 29):
                x = start * (1 - t) + end * t + bend * np.sin(t * np.pi)
                points.append(
                    ((variant * tile + x * tile) * ss, t * length * height * ss)
                )
            for k in range(len(points) - 1):
                t = k / (len(points) - 1)
                width = max(1, int((1.35 * (1 - t) + 0.28) * ss))
                draw.line(
                    [points[k], points[k + 1]],
                    fill=int(opacity * (1 - 0.33 * t)),
                    width=width,
                )
    alpha = alpha.resize((tile * 4, height), Image.Resampling.LANCZOS)
    rgb = Image.new("RGBA", alpha.size, (255, 255, 255, 0))
    rgb.putalpha(alpha)
    result = io.BytesIO()
    rgb.save(result, format="PNG")
    return result.getvalue()


def groom(points, normals, breed, head):
    """Per-region flow and length; eyes/nose stay clear of long coat."""
    x, y, z = points.T
    long = breed["id"] in LONGHAIR
    hip = 0.267 * breed["legs"] + 0.002
    relative = points - head
    is_head = (x > 0.19) & (y > hip + 0.066)
    tail = x < -0.275
    leg = (y < hip - 0.065) & ~tail
    chest = (x > 0.12) & (x < 0.23) & (y > hip - 0.025) & ~is_head
    cheek = is_head & (np.abs(relative[:, 2]) > 0.032) & (relative[:, 1] < 0.025)
    belly = (y < hip) & (x > -0.17) & (x < 0.12) & ~leg
    length = np.full(len(points), 0.028 if long else 0.011)
    length[tail] = (0.048 if long else 0.019) * np.clip(
        (x[tail] + 0.60) / 0.12, 0.20, 1
    )
    length[leg] = 0.012 if long else 0.006
    length[chest] = 0.040 if long else 0.015
    length[belly] = 0.033 if long else 0.011
    length[is_head] = 0.008 if long else 0.006
    length[cheek] = 0.014 if long else 0.007
    muzzle = is_head & (relative[:, 0] > 0.035) & (relative[:, 1] < 0.005)
    length[muzzle] = 0.0035
    ear = is_head & (relative[:, 1] > 0.032)
    length[ear] = 0.0035
    # Groom along the body, down the bib, out over the cheeks, towards tail tip.
    direction = np.tile([-1.0, -0.12, 0.0], (len(points), 1))
    direction[chest] = np.column_stack(
        [np.full(chest.sum(), -0.23), np.full(chest.sum(), -1.0), z[chest] * 4]
    )
    direction[leg] = [0.05, -1, 0]
    direction[belly] = [-0.65, -0.65, 0]
    direction[is_head] = relative[is_head] * [0.25, 0.55, 1.8]
    direction[is_head, 0] -= 0.018
    direction[cheek] = np.column_stack(
        [
            np.full(cheek.sum(), -0.10),
            np.full(cheek.sum(), -0.55),
            np.sign(z[cheek]) * 0.75,
        ]
    )
    direction -= normals * np.sum(direction * normals, axis=1)[:, None]
    length_dir = np.linalg.norm(direction, axis=1)
    alternate = np.cross(normals, [0, 0, 1.0])
    direction[length_dir < 0.01] = alternate[length_dir < 0.01]
    direction /= np.maximum(np.linalg.norm(direction, axis=1, keepdims=True), 1e-7)
    # Keep the eye aperture, nose leather and lip line unobstructed.
    bare = np.zeros(len(points), dtype=bool)
    for sign in [-1, 1]:
        eye = head + np.array([0.030, 0.007, sign * 0.027])
        bare |= np.sum(((points - eye) / [0.015, 0.012, 0.014]) ** 2, axis=1) < 1
    bare |= (
        is_head
        & (relative[:, 0] > 0.055)
        & (np.abs(relative[:, 2]) < 0.024)
        & (relative[:, 1] < 0.006)
    )
    length[bare] = 0
    # Do not grow fur through the ground at the paw bind pose.
    length[y < 0.045] = 0.003
    return (
        direction,
        length,
        {
            "face": is_head,
            "cheek": cheek,
            "chest": chest,
            "tail": tail,
            "legs": leg,
            "belly": belly,
        },
    )


def build(g, breed, verts, faces, normals, linear, joint_indices, weights, head):
    rng = np.random.default_rng(308)
    long = breed["id"] in LONGHAIR
    tex = strand_atlas()
    mat = g.material("groomed_soft_fur", [1, 1, 1], 0.97, tex)
    g.j["materials"][mat].update(alphaMode="BLEND")
    # Supported by glTF viewers with sheen; Cesium uses a small grazing-angle
    # light contribution in the app's custom shader instead (see fur-light.mjs).
    g.j["materials"][mat]["extensions"] = {
        "KHR_materials_sheen": {
            "sheenColorFactor": [0.16, 0.15, 0.13],
            "sheenRoughnessFactor": 0.85,
        }
    }
    g.j.setdefault("extensionsUsed", []).append("KHR_materials_sheen")
    a, b, c = verts[faces[:, 0]], verts[faces[:, 1]], verts[faces[:, 2]]
    area = np.linalg.norm(np.cross(b - a, c - a), axis=1) * 0.5
    centers = (a + b + c) / 3
    # Face, bib and tail receive more roots per square metre than the trunk.
    _, _, regions = groom(centers, normals[faces].mean(axis=1), breed, head)
    importance = np.ones(len(faces))
    importance[regions["face"]] = 4.0
    importance[regions["chest"]] = 1.7
    importance[regions["tail"]] = 2.4
    prob = area * importance
    prob /= prob.sum()
    meta = {
        "method": "area-sampled curved skinned ribbons, two coat layers",
        "atlasStrandsPerClump": 52,
        "layers": [],
    }
    for label, count, length_scale in [
        ("undercoat", 3800 if long else 2400, 0.52),
        ("guard", 5200 if long else 3200, 1.0),
    ]:
        choice = rng.choice(len(faces), count, p=prob)
        tri = faces[choice]
        uvw = rng.random((count, 2))
        root = np.sqrt(uvw[:, 0])
        bary = np.column_stack([1 - root, root * (1 - uvw[:, 1]), root * uvw[:, 1]])
        roots = np.einsum("ij,ijk->ik", bary, verts[tri])
        nn = np.einsum("ij,ijk->ik", bary, normals[tri])
        nn /= np.linalg.norm(nn, axis=1, keepdims=True)
        colors = np.einsum("ij,ijk->ik", bary, linear[tri])
        flow, length, regions = groom(roots, nn, breed, head)
        length *= length_scale * rng.uniform(0.72, 1.25, count)
        # Root joint blends are barycentric across the surface triangle, avoiding
        # clumps tearing away from a moving cheek, shoulder, hock or tail.
        dense = np.zeros((count, len(g.j["skins"][0]["joints"])), dtype=np.float32)
        for v in range(3):
            for k in range(4):
                np.add.at(
                    dense,
                    (np.arange(count), joint_indices[tri[:, v], k]),
                    weights[tri[:, v], k] * bary[:, v],
                )
        order = np.argsort(dense, axis=1)[:, -4:]
        weight = np.take_along_axis(dense, order, axis=1)
        weight /= weight.sum(axis=1, keepdims=True)
        pp = []
        normal = []
        uv = []
        cc = []
        jj = []
        ww = []
        indices = []
        kept = np.flatnonzero(length > 0.001)
        for idx in kept:
            n = nn[idx]
            f = flow[idx]
            tangent = np.cross(n, f)
            tangent /= max(np.linalg.norm(tangent), 1e-7)
            yaw = rng.uniform(-0.42, 0.42)
            f = f * np.cos(yaw) + tangent * np.sin(yaw)
            side = np.cross(n, f)
            le = length[idx]
            width = np.clip(le * 0.52, 0.0025, 0.020) * rng.uniform(0.75, 1.2)
            # Broad soft undercoat; longer guard hair curves with the groom.
            lift = 0.65 if label == "undercoat" else 0.50
            variant = int(rng.integers(4))
            base = len(pp)
            tone = rng.uniform(0.96, 1.05)
            for row, t in enumerate([0.0, 0.33, 0.67, 1.0]):
                center = (
                    roots[idx]
                    - n * 0.001
                    + le
                    * (
                        n * lift * np.sin(t * np.pi * 0.5)
                        + f * (0.78 * t + 0.08 * t * t)
                    )
                )
                center[1] -= le * 0.10 * t * t
                taper = 1 - 0.57 * t
                for direction in [-1, 1]:
                    pp.append(center + side * width * 0.5 * taper * direction)
                    # Smooth normals follow the coat, not the sharp card edges.
                    normal.append(n)
                    uv.append(
                        [(variant + (0.018 if direction < 0 else 0.982)) / 4, t * 0.995]
                    )
                    cc.append(np.clip(colors[idx] * tone * (0.91 + 0.16 * t), 0, 1))
                    jj.append(order[idx])
                    ww.append(weight[idx])
            for k in range(3):
                q = base + k * 2
                indices.extend([q, q + 2, q + 1, q + 1, q + 2, q + 3])
        attrs = {
            "POSITION": g.acc(pp, "VEC3"),
            "NORMAL": g.acc(normal, "VEC3"),
            "TEXCOORD_0": g.acc(uv, "VEC2"),
            "COLOR_0": g.acc(cc, "VEC3"),
            "JOINTS_0": g.acc(jj, "VEC4", 5123),
            "WEIGHTS_0": g.acc(ww, "VEC4"),
        }
        mesh = len(g.j["meshes"])
        g.j["meshes"].append(
            {
                "name": "groomed_fur_" + label,
                "primitives": [
                    {
                        "attributes": attrs,
                        "indices": g.acc(indices, "SCALAR", 5125),
                        "material": mat,
                    }
                ],
            }
        )
        node = g.node("fur_" + label, mesh)
        g.j["nodes"][node]["skin"] = 0
        meta["layers"].append(
            {
                "name": label,
                "clumps": len(kept),
                "vertices": len(pp),
                "triangles": len(indices) // 3,
                "lengthRangeMetres": [
                    float(length[kept].min()),
                    float(length[kept].max()),
                ],
                "regions": {
                    name: int(mask[kept].sum()) for name, mask in regions.items()
                },
            }
        )
    g.j.setdefault("extras", {})["fur"] = meta
