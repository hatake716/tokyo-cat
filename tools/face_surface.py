"""Detailed CC BY 4.0 feline face adapted from Fripouille / Bicolor Cat.

Source attribution and modifications: tools/assets/cat-face/README.md.
The head uses the existing game rig; the source animation is not retargeted.
"""

import io
from pathlib import Path
import numpy as np
from PIL import Image

ASSETS = Path(__file__).parent / "assets/cat-face"


def srgb_linear(c):
    return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)


def image_bytes(a):
    out = io.BytesIO()
    Image.fromarray(np.uint8(np.clip(a, 0, 1) * 255)).save(out, format="PNG")
    return out.getvalue()


def coat_texture(breed):
    original = (
        np.asarray(
            Image.open(ASSETS / "detailed-albedo.png").convert("RGB"), dtype=float
        )
        / 255
    )
    r, g, blue = np.moveaxis(original, -1, 0)
    # Recolour ginger pigment; retain white muzzle, nose leather and inner ear.
    pigment = np.clip((g - blue - 0.004) * 42, 0, 1) * np.clip(
        (r - g - 0.008) * 40, 0, 1
    )
    target = np.array([int(breed["color"][i : i + 2], 16) for i in [1, 3, 5]]) / 255
    if breed["id"] in ["ragdoll", "ragamuffin"]:
        target *= 0.72
    lum = original @ np.array([0.3, 0.55, 0.15])
    colored = np.clip(target[None, None, :] * (lum / 0.54)[:, :, None], 0, 1)
    rgb = original * (1 - pigment[:, :, None]) + colored * pigment[:, :, None]
    return rgb, original


def sample_rgb(tex, uv):
    h, w = tex.shape[:2]
    x = np.clip(uv[:, 0] * (w - 1), 0, w - 1)
    y = np.clip(uv[:, 1] * (h - 1), 0, h - 1)
    a = x.astype(int)
    c = y.astype(int)
    dx = (x - a)[:, None]
    dy = (y - c)[:, None]
    return (tex[c, a] * (1 - dx) + tex[c, np.minimum(a + 1, w - 1)] * dx) * (1 - dy) + (
        tex[np.minimum(c + 1, h - 1), a] * (1 - dx)
        + tex[np.minimum(c + 1, h - 1), np.minimum(a + 1, w - 1)] * dx
    ) * dy


def normal_texture():
    return (ASSETS / "source-normal.png").read_bytes()


def adapt(p, b, delta=False):
    # Blender Z-up, -Y forward -> glTF Y-up, +X forward. Centre at the skull.
    offset = np.zeros(3) if delta else np.array([0, -0.240, 0.302])
    p = p - offset
    result = np.column_stack([-p[:, 1] * 1.12, p[:, 2] * 1.02, p[:, 0] * 1.04])
    roundness = 1.09 if b["id"] in ["british", "scottish", "minuet"] else 1
    result[:, 2] *= roundness
    result[:, 0] *= 0.94 if roundness > 1 else 1
    return result


def normals_for(p, faces):
    n = np.zeros_like(p)
    raw = np.cross(p[faces[:, 1]] - p[faces[:, 0]], p[faces[:, 2]] - p[faces[:, 0]])
    for k in range(3):
        np.add.at(n, faces[:, k], raw)
    n /= np.maximum(np.linalg.norm(n, axis=1, keepdims=True), 1e-9)
    return n


def build(g, b, head, head_joint, ear_joints):
    data = np.load(ASSETS / "face-base.npz")
    detail, original = coat_texture(b)
    coat = g.material("sculpted_face_coat", [1, 1, 1], 0.93, image_bytes(detail))
    im = len(g.j["images"])
    g.j["images"].append(
        {"bufferView": g.blob(normal_texture()), "mimeType": "image/png"}
    )
    tex = len(g.j["textures"])
    g.j["textures"].append({"source": im, "sampler": 0})
    g.j["materials"][coat]["normalTexture"] = {"index": tex, "scale": 0.36}
    eye_rgb = (
        np.asarray(Image.open(ASSETS / "source-albedo.png").convert("RGB"), dtype=float)
        / 255
    )
    if b["id"] == "ragdoll":
        lum = eye_rgb @ np.array([0.25, 0.60, 0.15])
        eye_rgb = np.stack([lum * 0.68, lum * 0.89, lum * 1.06], axis=-1)
    eye = g.material("corneal_iris", [1, 1, 1], 0.10, image_bytes(eye_rgb))
    g.j["materials"][eye]["extensions"] = {"KHR_materials_ior": {"ior": 1.38}}
    g.j.setdefault("extensionsUsed", []).append("KHR_materials_ior")
    samples = None
    blink_nodes = []
    for part, material in [("face", coat), ("eyes", eye)]:
        local = adapt(data[part + "_position"], b)
        blink = adapt(data[part + "_blink"], b, True)
        # The axis conversion reflects handedness: reverse winding so normals
        # and fur point OUT of the face. Double-sided materials can otherwise
        # hide the error while corneal reflections and the groom stay inverted.
        faces = data[part + "_triangles"][:, [0, 2, 1]]
        uv = data[part + "_uv"]
        if b["fold"]:
            height = np.clip((local[:, 1] - 0.032) / 0.035, 0, 1)
            local[:, 0] += height**2 * 0.030
            local[:, 1] -= height**2 * 0.028
        # Recalculate smooth normals after axis/breed/ear-shape adaptations.
        normals = normals_for(local, faces)
        pos = local + head
        joints = np.full((len(pos), 4), head_joint, dtype=np.uint16)
        weights = np.zeros((len(pos), 4))
        weights[:, 0] = 1
        if part == "face":
            for sign, joint in zip([-1, 1], ear_joints):
                influence = np.clip((local[:, 1] - 0.025) / 0.030, 0, 1) * (
                    local[:, 2] * sign > 0.018
                )
                joints[:, 1] = np.where(influence > 0, joint, joints[:, 1])
                weights[:, 1] += influence
                weights[:, 0] -= influence
        colors = np.ones((len(pos), 3))
        attrs = {
            "POSITION": g.acc(pos, "VEC3"),
            "NORMAL": g.acc(normals, "VEC3"),
            "TEXCOORD_0": g.acc(uv, "VEC2"),
            "COLOR_0": g.acc(colors, "VEC3"),
            "JOINTS_0": g.acc(joints, "VEC4", 5123),
            "WEIGHTS_0": g.acc(weights, "VEC4"),
        }
        # Artist's eyelid deformation, with a real closed-lid surface.
        targets = [
            {
                "POSITION": g.acc(blink, "VEC3"),
                "NORMAL": g.acc(normals_for(local + blink, faces) - normals, "VEC3"),
            }
        ]
        mesh = len(g.j["meshes"])
        g.j["meshes"].append(
            {
                "name": "sculpted_" + part,
                "weights": [0],
                "primitives": [
                    {
                        "attributes": attrs,
                        "indices": g.acc(faces.reshape(-1), "SCALAR", 5125),
                        "material": material,
                        "targets": targets,
                    }
                ],
            }
        )
        node = g.node("sculpted_" + part, mesh)
        g.j["nodes"][node]["skin"] = 0
        blink_nodes.append(node)
        if part == "face":
            # Avoid growing coat on the wet nose, eyelid margins and ear cavity.
            sampled = srgb_linear(sample_rgb(detail, uv))
            samples = (pos, faces, normals, sampled, joints, weights)
    # 61 samples to match the existing clip verification and delivery contract.
    times = np.linspace(0, 5.7, 61)
    closing = np.clip((times - 3.23) / 0.14, 0, 1)
    opening = np.clip((3.70 - times) / 0.18, 0, 1)
    value = (closing**2 * (3 - 2 * closing)) * (opening**2 * (3 - 2 * opening))
    value[0] = value[-1] = 0
    g.j["animations"].append(
        {
            "name": "Blink",
            "samplers": [
                {
                    "input": g.acc(times, "SCALAR"),
                    "output": g.acc(value, "SCALAR"),
                    "interpolation": "LINEAR",
                }
            ],
            "channels": [
                {"sampler": 0, "target": {"node": n, "path": "weights"}}
                for n in blink_nodes
            ],
        }
    )
    g.j.setdefault("extras", {})["face"] = {
        "source": "Bicolor Cat by kenchoo, after Fripouille by guillaume bolis",
        "license": "CC-BY-4.0",
        "url": "https://sketchfab.com/3d-models/bicolor-cat-e623a618ca344a8393d7ba4d63ec23cf",
        "changes": "head extraction, subdivision, recolouring, rig adaptation, layered groom, cornea and morph blinking",
        "vertices": len(data["face_position"]),
        "blink": "source target_0, shared eyelid and eyeball deformation",
    }
    return samples
