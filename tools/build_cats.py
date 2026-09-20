#!/usr/bin/env python3
"""Original anatomical development meshes, metres, +X forward, +Y up.
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


def ear_surface(u, v, sign, fold):
    width = 0.025 * (1 - v) ** 0.85 + 0.0015
    return np.array(
        [
            -0.014
            + 0.016 * (1 - u * u) * (1 - v)
            + (v * v * 0.030 if fold else -0.008 * v),
            0.030 + (0.021 if fold else 0.043) * v,
            sign * (0.044 + v * 0.014 + u * width),
        ]
    )


def ear_fuzz(g, mat, sign, fold, long):
    """Small soft tufts on the pinna and rim, following the animated ear node."""
    rng = np.random.default_rng(476 + sign)
    points, normals, uv, faces = [], [], [], []
    for k in range(240):
        u = rng.uniform(-1, 1)
        if k < 100:
            u = rng.choice([-1, 1]) * rng.uniform(0.82, 1)
        v = rng.uniform(0.05, 0.97)
        root = ear_surface(u, v, sign, fold)
        root[0] += 0.002
        direction = np.array([0.28, 0.7, sign * u * 0.8])
        direction /= np.linalg.norm(direction)
        side = np.cross([1, 0, 0], direction)
        side /= np.linalg.norm(side)
        length = rng.uniform(0.004, 0.009) * (1 if long else 0.7)
        width = length * 0.55
        variant = k % 4
        base = len(points)
        for t in [0, 0.5, 1]:
            center = root + direction * length * t
            center[0] += 0.0015 * np.sin(t * np.pi)
            for edge in [-1, 1]:
                points.append(center + side * width * 0.5 * edge * (1 - 0.6 * t))
                normals.append([1, 0, 0])
                uv.append([(variant + (0.02 if edge < 0 else 0.98)) / 4, t * 0.995])
        for row in range(2):
            i = base + 2 * row
            faces.extend([i, i + 2, i + 1, i + 1, i + 2, i + 3])
    return g.mesh(points, normals, uv, faces, mat)


def ear_mesh(g, mat, sign, fold=False, inner=False):
    # Curved shell with a rolled rim and actual thickness; +X faces forward.
    p = []
    uv = []
    faces = []
    rings = 10
    cols = 14
    for row in range(rings):
        v = row / (rings - 1)
        for col in range(cols):
            u = col / (cols - 1) * 2 - 1
            point = ear_surface(
                u * 0.68 if inner else u, 0.12 + v * 0.74 if inner else v, sign, fold
            )
            if inner:
                point[0] += 0.0015
            p.append(point)
            uv.append([(u + 1) / 2, v])
    for row in range(rings - 1):
        for col in range(cols - 1):
            a = row * cols + col
            faces.extend([[a, a + cols, a + 1], [a + 1, a + cols, a + cols + 1]])
    p = np.array(p)
    faces = np.array(faces)
    norm = np.zeros_like(p)
    for face in faces:
        n = np.cross(p[face[1]] - p[face[0]], p[face[2]] - p[face[0]])
        if n[0] < 0:
            n = -n
        norm[face] += n
    norm /= np.maximum(np.linalg.norm(norm, axis=1, keepdims=True), 1e-12)
    if not inner:
        count = len(p)
        back = p.copy()
        back[:, 0] -= 0.008 * (1 - np.asarray(uv)[:, 1]) + 0.001
        p = np.concatenate([p, back])
        norm = np.concatenate([norm, -norm])
        uv = uv + uv
        rear = faces[:, [0, 2, 1]] + count
        faces = np.concatenate([faces, rear])
    return g.mesh(p, norm, uv, faces.reshape(-1), mat)


def eye_mesh(g, sign, mat, rx=0.015, ry=0.0105, depth=0.0035):
    pos = []
    norm = []
    uv = []
    ix = []
    normal = np.array([0.79, 0, sign * 0.61])
    tangent = np.array([-0.61, 0, sign * 0.79])
    for row in range(8):
        r = row / 7
        for k in range(33):
            a = k / 32 * math.tau
            v = (
                tangent * math.cos(a) * rx * r
                + np.array(
                    [0, math.sin(a) * ry * r * (0.80 + 0.20 * abs(math.cos(a))), 0]
                )
                + normal * depth * (1 - r * r)
            )
            pos.append(v)
            norm.append(normal)
            uv.append([0.5 + 0.5 * r * math.cos(a), 0.5 + 0.5 * r * math.sin(a)])
    for row in range(7):
        for k in range(32):
            a = row * 33 + k
            ix.extend([a, a + 1, a + 33, a + 1, a + 34, a + 33])
    return g.mesh(pos, norm, uv, ix, mat)


def iris_texture(blue):
    u, v = np.meshgrid(np.linspace(-1, 1, 256), np.linspace(-1, 1, 256))
    r = np.hypot(u, v)
    a = np.arctan2(v, u)
    base = np.array([0.24, 0.49, 0.66] if blue else [0.57, 0.60, 0.27])
    radial = 0.11 * np.sin(a * 83 + np.sin(r * 38)) + 0.05 * np.sin(a * 147)
    color = base[None, None, :] * (0.88 + radial[:, :, None])
    color *= np.clip((1 - r) * 6, 0.22, 1)[:, :, None]
    color[r < 0.22] *= 0.60
    out = io.BytesIO()
    Image.fromarray(np.uint8(np.clip(color, 0, 1) * 255)).save(out, format="PNG")
    return out.getvalue()


def make(b, motion):
    g = GLB()
    g.j["asset"]["generator"] = "TOKYO-CAT authored cat generator 0.3"
    fur = g.material("authored_coat", [1, 1, 1], texture=coat(b))
    cream = g.material("chin", [0.83, 0.81, 0.74])
    pink = g.material("ear_inner", [0.40, 0.24, 0.23])
    nosemat = g.material("nose_leather", [0.19, 0.085, 0.075], 0.65)
    dark = g.material("pupil_and_lid", [0.009, 0.013, 0.012], 0.28)
    iris = g.material(
        "radial_iris", [1, 1, 1], 0.16, iris_texture(b["id"] == "ragdoll")
    )
    glint = g.material("corneal_catchlight", [0.94, 0.98, 1], 0.09)
    whisker = g.material("whisker", [0.48, 0.47, 0.42])
    sp = {m: sphere(g, m) for m in [fur, cream, dark, glint]}
    earfur = g.material(
        "ear_back_fur",
        [int(b["color"][i : i + 2], 16) / 255 * 0.48 for i in [1, 3, 5]],
        0.98,
    )
    from groom_fur import strand_atlas

    earcoat = g.material(
        "ear_soft_fur",
        [int(b["color"][i : i + 2], 16) / 255 * 0.60 for i in [1, 3, 5]],
        0.97,
        strand_atlas(),
    )
    g.j["materials"][earcoat]["alphaMode"] = "BLEND"
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
    roundness = 1.13 if b["id"] in ["british", "scottish", "minuet"] else 1
    g.node(
        "cranium",
        sp[fur],
        (-0.006, 0, 0),
        (0.061, 0.052 * roundness, 0.061 * roundness),
        head,
    )
    g.node(
        "cheeks", sp[fur], (0.022, -0.020, 0), (0.039, 0.035, 0.057 * roundness), head
    )
    g.node("bridge", sp[fur], (0.042, -0.003, 0), (0.029, 0.029, 0.025), head)
    for side, z in [("left", -1), ("right", 1)]:
        g.node(
            "muzzle", sp[cream], (0.054, -0.026, z * 0.016), (0.023, 0.018, 0.020), head
        )
        eye = g.node("eye_" + side, None, (0.040, 0.008, z * 0.035), parent=head)
        g.node("eyelid_edge", eye_mesh(g, z, dark, 0.0157, 0.0112, 0.0035), parent=eye)
        g.node("iris", eye_mesh(g, z, iris), pos=(0.001, 0, z * 0.001), parent=eye)
        g.node(
            "pupil",
            eye_mesh(g, z, dark, 0.0052, 0.0083, 0.001),
            pos=(0.0039, 0, z * 0.003),
            parent=eye,
        )
        g.node(
            "eye_light",
            sp[glint],
            (0.0045, 0.0032, z * 0.0036),
            (0.0016, 0.0018, 0.0014),
            eye,
        )
        ear = g.node("ear_" + side, parent=head)
        g.node("ear_shell", ear_mesh(g, earfur, z, b["fold"]), parent=ear)
        g.node("ear_concha", ear_mesh(g, pink, z, b["fold"], True), parent=ear)
        g.node("ear_fuzz_" + side, ear_fuzz(g, earcoat, z, b["fold"], long), parent=ear)
        # Rolled outer ear rim prevents a paper-thin triangular silhouette.
        rim = []
        for direction in [-1, 1]:
            rim.append(
                (
                    [
                        ear_surface(direction, v, z, b["fold"])
                        for v in np.linspace(0, 1, 14)
                    ],
                    0.0016,
                )
            )
        g.node("ear_rim", tube_mesh(g, rim, earfur), parent=ear)
        whiskers = []
        for k in range(7):
            start = np.array(
                [0.067, -0.022 + (k % 3) * 0.003, z * (0.022 + (k % 2) * 0.003)]
            )
            end = np.array(
                [
                    0.035 - k * 0.004,
                    -0.025 + (k - 3) * 0.009,
                    z * (0.095 + (k % 3) * 0.007),
                ]
            )
            pts = [
                start * (1 - t)
                + end * t
                + np.array([0.016 * math.sin(t * math.pi), -0.007 * t * t, 0])
                for t in np.linspace(0, 1, 9)
            ]
            whiskers.append((pts, 0.00030))
        for k in range(3):
            start = np.array([0.014, 0.035, z * 0.034])
            end = np.array([0.001, 0.067 + k * 0.004, z * (0.075 + k * 0.003)])
            whiskers.append(
                (
                    [
                        start * (1 - t)
                        + end * t
                        + np.array([0.009 * math.sin(t * math.pi), 0, 0])
                        for t in np.linspace(0, 1, 7)
                    ],
                    0.00023,
                )
            )
        g.node("whiskers", tube_mesh(g, whiskers, whisker), parent=head)
    nose = g.mesh(
        [
            [0.075, -0.014, -0.009],
            [0.075, -0.014, 0.009],
            [0.078, -0.024, 0],
            [0.068, -0.017, 0],
        ],
        [[1, 0, 0]] * 4,
        [[0, 0], [1, 0], [0.5, 1], [0.5, 0.5]],
        [0, 1, 2, 0, 3, 1, 0, 2, 3, 1, 3, 2],
        nosemat,
    )
    g.node("nose", nose, parent=head)
    mouth = [
        ([[0.074, -0.023, 0], [0.073, -0.032, 0], [0.066, -0.035, -0.013]], 0.0006),
        ([[0.073, -0.032, 0], [0.066, -0.035, 0.013]], 0.0006),
    ]
    g.node("mouth", tube_mesh(g, mouth, dark), parent=head)
    g.node("chin", sp[cream], (0.050, -0.042, 0), (0.023, 0.012, 0.026), head)
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
        "provenance": "Original authored development model; reference-informed, not a scan or CGTrader asset",
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
