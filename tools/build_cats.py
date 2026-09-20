#!/usr/bin/env python3
"""Authored body and groom with a CC BY 4.0 adapted face, metres, +X forward, +Y up.
No frames or textures from the reference video are embedded.
Analytical geometry is deliberately labelled authored, not photogrammetry.
Requires numpy, Pillow, scipy and scikit-image. Emits self-contained GLB with joint hierarchies + clips.
"""

import json, math, struct, io, hashlib
from pathlib import Path
import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "app/src/main/assets/game/models"
OUT.mkdir(exist_ok=True)
BREEDS = json.loads((OUT.parent / "catalog.json").read_text())["breeds"]


class GLB:
    def __init__(self):
        self.binary = bytearray()
        self.j = {
            "asset": {
                "version": "2.0",
                "generator": "TOKYO-CAT authored cat generator 0.1",
            },
            "scene": 0,
            "scenes": [{"nodes": [0]}],
            "nodes": [{"name": "cat", "children": []}],
            "meshes": [],
            "materials": [],
            "bufferViews": [],
            "accessors": [],
            "textures": [],
            "images": [],
            "samplers": [
                {"magFilter": 9729, "minFilter": 9987, "wrapS": 10497, "wrapT": 10497}
            ],
            "animations": [],
        }

    def blob(self, b):
        while len(self.binary) % 4:
            self.binary.append(0)
        v = len(self.j["bufferViews"])
        self.j["bufferViews"].append(
            {"buffer": 0, "byteOffset": len(self.binary), "byteLength": len(b)}
        )
        self.binary += b
        return v

    def acc(self, a, kind, component=5126):
        a = np.asarray(
            a,
            dtype=(
                np.float32
                if component == 5126
                else (np.uint16 if component == 5123 else np.uint32)
            ),
        )
        i = len(self.j["accessors"])
        d = {
            "bufferView": self.blob(a.tobytes()),
            "componentType": component,
            "count": len(a),
            "type": kind,
        }
        if kind == "VEC3":
            d.update(min=a.min(axis=0).tolist(), max=a.max(axis=0).tolist())
        if kind == "SCALAR":
            d.update(min=[float(a.min())], max=[float(a.max())])
        self.j["accessors"].append(d)
        return i

    def material(self, name, rgb, rough=0.85, texture=None):
        p = {
            "baseColorFactor": [*rgb, 1],
            "metallicFactor": 0,
            "roughnessFactor": rough,
        }
        if texture is not None:
            im = len(self.j["images"])
            self.j["images"].append(
                {"bufferView": self.blob(texture), "mimeType": "image/png"}
            )
            tex = len(self.j["textures"])
            self.j["textures"].append({"source": im, "sampler": 0})
            p["baseColorTexture"] = {"index": tex}
        i = len(self.j["materials"])
        self.j["materials"].append(
            {"name": name, "pbrMetallicRoughness": p, "doubleSided": True}
        )
        return i

    def mesh(self, pos, norm, uv, indices, mat):
        mesh = {
            "primitives": [
                {
                    "attributes": {
                        "POSITION": self.acc(pos, "VEC3"),
                        "NORMAL": self.acc(norm, "VEC3"),
                        "TEXCOORD_0": self.acc(uv, "VEC2"),
                    },
                    "indices": self.acc(indices, "SCALAR", 5125),
                    "material": mat,
                }
            ]
        }
        i = len(self.j["meshes"])
        self.j["meshes"].append(mesh)
        return i

    def node(self, name, mesh=None, pos=(0, 0, 0), scale=None, parent=0, rotation=None):
        i = len(self.j["nodes"])
        n = {"name": name, "translation": list(pos)}
        if mesh is not None:
            n["mesh"] = mesh
        if scale:
            n["scale"] = list(scale)
        if rotation:
            n["rotation"] = rotation
        self.j["nodes"].append(n)
        self.j["nodes"][parent].setdefault("children", []).append(i)
        return i

    def write(self, path):
        while len(self.binary) % 4:
            self.binary.append(0)
        self.j["buffers"] = [{"byteLength": len(self.binary)}]
        raw = json.dumps(self.j, separators=(",", ":")).encode()
        raw += b" " * ((-len(raw)) % 4)
        out = (
            struct.pack("<4sII", b"glTF", 2, 28 + len(raw) + len(self.binary))
            + struct.pack("<I4s", len(raw), b"JSON")
            + raw
            + struct.pack("<I4s", len(self.binary), b"BIN\0")
            + self.binary
        )
        path.write_bytes(out)


def sphere(g, mat, nu=24, nv=16):
    p = []
    n = []
    uv = []
    ix = []
    for j in range(nv + 1):
        phi = math.pi * j / nv
        for i in range(nu + 1):
            theta = 2 * math.pi * i / nu
            v = [
                math.sin(phi) * math.cos(theta),
                math.cos(phi),
                math.sin(phi) * math.sin(theta),
            ]
            p.append(v)
            n.append(v)
            uv.append([i / nu, j / nv])
    for j in range(nv):
        for i in range(nu):
            a = j * (nu + 1) + i
            ix.extend([a, a + 1, a + nu + 1, a + 1, a + nu + 2, a + nu + 1])
    return g.mesh(p, n, uv, ix, mat)


def coat(b):
    rng = np.random.default_rng(20260920)
    w, h = 512, 256
    u, v = np.meshgrid(np.linspace(0, 1, w), np.linspace(0, 1, h))
    rgb = np.array([int(b["color"][i : i + 2], 16) for i in [1, 3, 5]]) / 255
    noise = rng.normal(0, 0.032, (h, w))
    hair = 0.035 * np.sin(u * 2100 + np.sin(v * 35) * 3)
    stripe = np.maximum(0, np.cos(u * math.pi * 22 + np.sin(v * 19) * 1.7)) ** 10
    factor = 1 + noise + hair
    if b["id"] in ["mixed", "american", "siberian", "norwegian"]:
        factor -= stripe * 0.42
    if b["id"] in ["ragdoll", "minuet", "ragamuffin"]:
        factor += 0.13 * np.cos(v * 4)
    col = np.clip(factor[:, :, None] * rgb[None, None, :], 0, 1)
    if b["id"] == "mixed":
        patch = np.sin(u * 15) * np.cos(v * 9) > 0.48
        col[patch] *= 0.42
    im = Image.fromarray(np.uint8(col * 255))
    buf = io.BytesIO()
    im.save(buf, format="PNG")
    return buf.getvalue()


def tube_mesh(g, curves, mat, sides=5):
    pos = []
    norm = []
    uv = []
    indices = []
    for points, radius in curves:
        points = np.asarray(points)
        base = len(pos)
        for j, point in enumerate(points):
            tangent = points[min(j + 1, len(points) - 1)] - points[max(0, j - 1)]
            tangent /= np.linalg.norm(tangent)
            a = np.cross(tangent, [0, 1, 0])
            if np.linalg.norm(a) < 0.01:
                a = np.cross(tangent, [1, 0, 0])
            a /= np.linalg.norm(a)
            bb = np.cross(tangent, a)
            for k in range(sides):
                n = a * math.cos(k * math.tau / sides) + bb * math.sin(
                    k * math.tau / sides
                )
                pos.append(point + n * radius * (1 - 0.88 * j / (len(points) - 1)))
                norm.append(n)
                uv.append([k / sides, j / (len(points) - 1)])
        for j in range(len(points) - 1):
            for k in range(sides):
                a = base + j * sides + k
                bb = base + j * sides + (k + 1) % sides
                c = a + sides
                d = bb + sides
                indices.extend([a, bb, c, bb, d, c])
    return g.mesh(pos, norm, uv, indices, mat)


def make(b, motion):
    g = GLB()
    g.j["asset"]["generator"] = "TOKYO-CAT cat generator 0.4 / CC BY facial adaptation"
    fur = g.material("authored_coat", [1, 1, 1], texture=coat(b))
    cream = g.material("chin", [0.83, 0.81, 0.74])
    whisker = g.material("whisker", [0.62, 0.60, 0.55], 0.97)
    sp = {m: sphere(g, m) for m in [fur, cream]}
    bulk = b["body"]
    leg = b["legs"]
    y = 0.267 * leg + 0.002
    long = b["id"] in ["ragdoll", "minuet", "siberian", "norwegian", "ragamuffin"]
    fluff = 1.10 if long else 1
    g.node(
        "torso", sp[fur], (-0.023, y + 0.018, 0), (0.218, 0.082 * bulk, 0.074 * bulk)
    )
    g.node(
        "haunch", sp[fur], (-0.177, y + 0.013, 0), (0.085, 0.098 * bulk, 0.076 * bulk)
    )
    g.node("shoulders", sp[fur], (0.132, y + 0.030, 0), (0.075, 0.086, 0.071))
    g.node(
        "chest", sp[fur], (0.178, y + 0.028, 0), (0.048, 0.064 * fluff, 0.058 * fluff)
    )
    g.node(
        "neck", sp[fur], (0.201, y + 0.062, 0), (0.046, 0.059 * fluff, 0.052 * fluff)
    )
    head = g.node("head", None, (0.236, y + 0.098, 0))
    for side, sign in [("left", -1), ("right", 1)]:
        g.node("eye_" + side, parent=head)
        g.node("ear_" + side, parent=head)
        whiskers = []
        for k in range(12):
            start = np.array(
                [0.058, -0.030 + (k % 4) * 0.003, sign * (0.021 + (k // 4) * 0.003)]
            )
            end = np.array(
                [
                    0.026 - (k // 4) * 0.004,
                    -0.022 + (k - 6) * 0.004,
                    sign * (0.083 + (k % 4) * 0.008),
                ]
            )
            pts = [
                start * (1 - t)
                + end * t
                + np.array([0.015 * math.sin(t * math.pi), -0.004 * t * t, 0])
                for t in np.linspace(0, 1, 13)
            ]
            whiskers.append((pts, 0.00018))
        for k in range(3):
            start = np.array([0.020, 0.022, sign * 0.031])
            end = np.array([0.008, 0.050 + k * 0.004, sign * (0.072 + k * 0.004)])
            whiskers.append(
                ([start * (1 - t) + end * t for t in np.linspace(0, 1, 9)], 0.00014)
            )
        g.node(
            "whiskers_" + side, tube_mesh(g, whiskers, whisker, sides=6), parent=head
        )
    for prefix, x in [("front", 0.158), ("rear", -0.174)]:
        for side, z in [("left", -0.055), ("right", 0.055)]:
            name = prefix + "_" + side
            hip = g.node(name, None, (x, y, z))
            a = 0.13 * leg
            bb = 0.15 * leg
            g.node(
                name + "_upper",
                sp[fur],
                (-0.005, -a / 2, 0),
                (
                    0.028 if prefix == "front" else 0.049,
                    a * 0.67,
                    0.027 if prefix == "front" else 0.039,
                ),
                hip,
            )
            knee = g.node(name + "_knee", None, (0, -a, 0), parent=hip)
            g.node(
                name + "_shin",
                sp[fur],
                (0.002, -bb / 2, 0),
                (0.0165, bb * 0.58, 0.019),
                knee,
            )
            paw = g.node(name + "_paw", None, (0, -bb, 0), parent=knee)
            g.node(
                name + "_pad", sp[fur], (0.016, 0.018, 0), (0.032, 0.021, 0.026), paw
            )
            for toe in [-1, 0, 1]:
                g.node(
                    "toe",
                    sp[fur],
                    (0.034, 0.013, toe * 0.013),
                    (0.014, 0.015, 0.009),
                    paw,
                )
    tail = g.node("tail0", None, (-0.248, y + 0.042, 0))
    for i in range(5):
        if i:
            tail = g.node("tail" + str(i), None, (-0.063, 0, 0), parent=tail)
        radius = (0.018 - i * 0.0026) * fluff
        g.node("tail_fur", sp[fur], (-0.034, 0, 0), (0.048, radius, radius), tail)
    from skin_surface import build

    build(g, b, sp[fur], sp[cream])
    u, v = np.meshgrid(np.linspace(-1, 1, 128), np.linspace(-1, 1, 128))
    alpha = np.clip(1 - u * u - v * v, 0, 1) ** 3 * 0.22
    rgba = np.zeros((128, 128, 4), dtype=np.uint8)
    rgba[:, :, :3] = 20
    rgba[:, :, 3] = np.uint8(alpha * 255)
    buf = io.BytesIO()
    Image.fromarray(rgba).save(buf, format="PNG")
    shadowmat = g.material("soft_contact_shading", [1, 1, 1], texture=buf.getvalue())
    g.j["materials"][shadowmat].update(
        alphaMode="BLEND", extensions={"KHR_materials_unlit": {}}
    )
    g.j.setdefault("extensionsUsed", []).append("KHR_materials_unlit")
    shadow = g.mesh(
        [
            [-0.46, 0.002, -0.18],
            [0.34, 0.002, -0.18],
            [0.34, 0.002, 0.18],
            [-0.46, 0.002, 0.18],
        ],
        [[0, 1, 0]] * 4,
        [[0, 0], [1, 0], [1, 1], [0, 1]],
        [0, 2, 1, 0, 3, 2],
        shadowmat,
    )
    g.node("contact_shading", shadow)
    from scipy.spatial.transform import Rotation

    byname = {n["name"]: i for i, n in enumerate(g.j["nodes"])}
    for clip in motion[b["id"]]:
        samplers = []
        channels = []
        frames = clip["frames"]
        timeacc = g.acc([f["time"] for f in frames], "SCALAR")
        for name in frames[0]["pose"]:
            node = byname[name]
            rest = g.j["nodes"][node]
            for path, kind in [
                ("rotation", "VEC4"),
                ("translation", "VEC3"),
                ("scale", "VEC3"),
            ]:
                values = []
                for f in frames:
                    v = f["pose"][name][path]
                    if path == "rotation":
                        v = (
                            Rotation.from_rotvec([0, v[1], 0])
                            * Rotation.from_rotvec([0, 0, v[2]])
                        ).as_quat()
                    elif path == "translation":
                        v = np.array(rest.get(path, [0, 0, 0])) + v
                    else:
                        v = np.array(rest.get(path, [1, 1, 1])) * v
                    values.append(v)
                values[-1] = values[0]  # continuous looping exported clips
                samplers.append(
                    {
                        "input": timeacc,
                        "output": g.acc(values, kind),
                        "interpolation": "LINEAR",
                    }
                )
                channels.append(
                    {
                        "sampler": len(samplers) - 1,
                        "target": {"node": node, "path": path},
                    }
                )
        g.j["animations"].append(
            {"name": clip["name"], "samplers": samplers, "channels": channels}
        )
    g.j["extras"] = {
        **g.j.get("extras", {}),
        "provenance": "Authored body, rig and groom with CC BY 4.0 face adapted from Fripouille / Bicolor Cat; not a scan",
        "reference": "https://www.youtube.com/watch?v=Jxv0e1VXSR0",
        "additionalReferences": [
            "https://www.nga.gov/artworks/220472-plate-number-720-cat-galloping",
            "https://github.com/Mesh2Motion/mesh2motion-app",
            "https://commons.wikimedia.org/wiki/File:Felis_catus-cat_on_snow.jpg",
        ],
        "unit": "metre",
        "forward": "+X",
        "quality": "development; authored approximations, not photoreal or motion capture",
        "motionSource": "cat-motion.mjs; shared runtime and clip poses",
    }
    f = OUT / (b["id"] + ".glb")
    g.write(f)
    return {
        "id": b["id"],
        "file": f.name,
        "sha256": hashlib.sha256(f.read_bytes()).hexdigest(),
        "bytes": f.stat().st_size,
        "nodes": len(g.j["nodes"]),
        "triangles": sum(
            sum(g.j["accessors"][p["indices"]]["count"] // 3 for p in m["primitives"])
            for m in g.j["meshes"]
        ),
    }


if __name__ == "__main__":
    import os, subprocess

    node = os.environ.get("TOKYO_CAT_NODE", "node")
    motion = json.loads(
        subprocess.check_output([node, str(ROOT / "tools/export_cat_motion.mjs")])
    )
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--breed", choices=[b["id"] for b in BREEDS])
    args = parser.parse_args()
    previous = (
        {m["id"]: m for m in json.loads((OUT / "manifest.json").read_text())}
        if (OUT / "manifest.json").exists()
        else {}
    )
    for b in BREEDS:
        if args.breed is None or b["id"] == args.breed:
            previous[b["id"]] = make(b, motion)
    manifest = [previous[b["id"]] for b in BREEDS if b["id"] in previous]
    (OUT / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(json.dumps(manifest, indent=2))
