#!/usr/bin/env python3
"""Validate actual packaged skin, joint indices, buffers and provenance, no GL required."""

import json, struct, hashlib, os
from pathlib import Path
import numpy as np

root = Path(__file__).resolve().parents[1] / "app/src/main/assets/game/models"
face_reference = np.load(Path(__file__).parent / "assets/cat-face/face-base.npz")
for info in json.loads((root / "manifest.json").read_text()):
    if (
        os.environ.get("TOKYO_CAT_VERIFY_BREED")
        and info["id"] != os.environ["TOKYO_CAT_VERIFY_BREED"]
    ):
        continue
    data = (root / info["file"]).read_bytes()
    assert hashlib.sha256(data).hexdigest() == info["sha256"]
    assert data[:4] == b"glTF"
    assert struct.unpack_from("<I", data, 8)[0] == len(data)
    n = struct.unpack_from("<I", data, 12)[0]
    j = json.loads(data[20 : 20 + n])
    binary = data[28 + n :]

    def accessor(i):
        a = j["accessors"][i]
        v = j["bufferViews"][a["bufferView"]]
        width = {"SCALAR": 1, "VEC2": 2, "VEC3": 3, "VEC4": 4, "MAT4": 16}[a["type"]]
        dtype = {5126: "<f4", 5125: "<u4", 5123: "<u2"}[a["componentType"]]
        offset = v.get("byteOffset", 0) + a.get("byteOffset", 0)
        arr = np.frombuffer(
            binary, dtype=dtype, count=a["count"] * width, offset=offset
        ).reshape(-1, width)
        assert np.isfinite(arr).all()
        assert offset + arr.nbytes <= len(binary)
        return arr

    for i in range(len(j["accessors"])):
        accessor(i)
    skin = j["skins"][0]
    assert len(skin["joints"]) == 26
    assert accessor(skin["inverseBindMatrices"]).shape[0] == len(skin["joints"])
    assert all(
        any(j["nodes"][i]["name"] == leg + "_paw" for i in skin["joints"])
        for leg in ["front_left", "front_right", "rear_left", "rear_right"]
    ), "Paws need deforming joints for foot IK"
    for i, node in enumerate(j["nodes"]):
        if node["name"] in ["fur_guard", "fur_undercoat"]:
            assert (
                node.get("skin") == 0
            ), "Fur must deform with the same skin as the body"
    groom = j["extras"].get("fur")
    assert groom and len(groom["layers"]) == 2, "Two-layer groom is required"
    assert {n["name"] for n in j["nodes"]} >= {"fur_guard", "fur_undercoat"}
    for layer in groom["layers"]:
        assert layer["clumps"] > 1500
        assert layer["regions"]["face"] > 40 and layer["regions"]["tail"] > 40
        assert layer["regions"]["chest"] > 40
        assert 0 < layer["lengthRangeMetres"][0] < layer["lengthRangeMetres"][1] < 0.08
    furmat = next(m for m in j["materials"] if m["name"] == "groomed_soft_fur")
    assert furmat["alphaMode"] == "BLEND", "Subpixel strands need soft alpha edges"
    mesh = next(
        m for m in j["meshes"] if m.get("name") == "continuous_anatomical_skin"
    )["primitives"][0]
    attrs = mesh["attributes"]
    weights = accessor(attrs["WEIGHTS_0"])
    joints = accessor(attrs["JOINTS_0"])
    assert np.allclose(weights.sum(axis=1), 1, atol=1e-5)
    assert joints.max() < len(skin["joints"])
    assert accessor(mesh["indices"]).max() < len(weights)
    normals = accessor(attrs["NORMAL"])
    assert np.allclose(np.linalg.norm(normals, axis=1), 1, atol=0.01)
    positions = accessor(attrs["POSITION"])
    triangles = accessor(mesh["indices"]).reshape(-1, 3)
    face_normals = np.cross(
        positions[triangles[:, 1]] - positions[triangles[:, 0]],
        positions[triangles[:, 2]] - positions[triangles[:, 0]],
    )
    areas = np.linalg.norm(face_normals, axis=1)
    dots = np.einsum("ij,ij->i", face_normals, normals[triangles].mean(axis=1))
    assert np.all(
        dots[areas > 1e-10] > 0
    ), "Surface winding must agree with outward normals"
    assert "TEXCOORD_0" in attrs
    material = j["materials"][mesh["material"]]
    assert "normalTexture" in material
    for m in j["meshes"]:
        for primitive in m["primitives"]:
            at = primitive["attributes"]
            if "WEIGHTS_0" in at:
                assert np.allclose(accessor(at["WEIGHTS_0"]).sum(axis=1), 1, atol=1e-5)
                assert accessor(at["JOINTS_0"]).max() < len(skin["joints"])
                pos = accessor(at["POSITION"])
                face = accessor(primitive["indices"]).reshape(-1, 3)
                assert face.max() < len(pos)
                if m.get("name", "").startswith("groomed_fur_"):
                    norm = accessor(at["NORMAL"])
                    assert np.allclose(np.linalg.norm(norm, axis=1), 1, atol=0.01)
                    fn = np.cross(
                        pos[face[:, 1]] - pos[face[:, 0]],
                        pos[face[:, 2]] - pos[face[:, 0]],
                    )
                    assert np.all(
                        np.einsum("ij,ij->i", fn, norm[face].mean(axis=1)) > 0
                    ), "Fur winding must face away from skin"

    assert [a["name"] for a in j["animations"]] == [
        "Blink",
        "Idle",
        "Walk",
        "Trot",
        "Greet",
        "Sit",
    ]
    assert j["extras"]["face"]["license"] == "CC-BY-4.0"
    for part in ["sculpted_face", "sculpted_eyes"]:
        node = next(n for n in j["nodes"] if n["name"] == part)
        assert node["skin"] == 0
        primitive = j["meshes"][node["mesh"]]["primitives"][0]
        assert len(primitive["targets"]) == 1
        at = primitive["attributes"]
        delta = accessor(primitive["targets"][0]["POSITION"])
        assert delta.shape == accessor(at["POSITION"]).shape
        assert np.max(np.abs(delta)) > (0.004 if part == "sculpted_face" else 0.002)
        assert np.allclose(np.linalg.norm(accessor(at["NORMAL"]), axis=1), 1, atol=0.01)
        # Cross products alone would allow a consistently inverted surface to
        # pass. Compare with the source artist's outward normals as well.
        source_part = "face" if part == "sculpted_face" else "eyes"
        ref = face_reference[source_part + "_normal"]
        expected = np.column_stack([-ref[:, 1], ref[:, 2], ref[:, 0]])
        unbent = face_reference[source_part + "_position"][:, 2] < 0.326
        alignment = np.sum(accessor(at["NORMAL"]) * expected, axis=1)
        assert (
            np.quantile(alignment[unbent], 0.01) > 0.90
        ), "Face normals must point outward after coordinate conversion"
        mat = j["materials"][primitive["material"]]
        assert "baseColorTexture" in mat["pbrMetallicRoughness"]
        if part == "sculpted_face":
            assert "normalTexture" in mat
    # Validate the exported joint transforms, not only the runtime equations.
    parents = {c: i for i, n in enumerate(j["nodes"]) for c in n.get("children", [])}

    def trs(p):
        x, y, z, w = p.get("rotation", [0, 0, 0, 1])
        m = np.eye(4)
        m[:3, :3] = np.array(
            [
                [1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)],
                [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
                [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)],
            ]
        ) @ np.diag(p.get("scale", [1, 1, 1]))
        m[:3, 3] = p.get("translation", [0, 0, 0])
        return m

    paws = [
        i
        for i, n in enumerate(j["nodes"])
        if n["name"]
        in ["front_left_paw", "front_right_paw", "rear_left_paw", "rear_right_paw"]
    ]
    for clip in j["animations"]:
        if clip["name"] == "Blink":
            assert len(clip["channels"]) == 2
            assert {
                j["nodes"][ch["target"]["node"]]["name"] for ch in clip["channels"]
            } == {"sculpted_face", "sculpted_eyes"}
            for ch in clip["channels"]:
                assert ch["target"]["path"] == "weights"
                sampler = clip["samplers"][ch["sampler"]]
                times, values = accessor(sampler["input"]), accessor(sampler["output"])
                assert len(times) == len(values) == 61
                assert np.all(np.diff(times[:, 0]) > 0)
                assert np.isclose(times[-1, 0], 5.7)
                assert values.min() >= 0 and 0.95 <= values.max() <= 1
                assert values[0, 0] == values[-1, 0] == 0
            # A standalone facial clip does not pose the bind-state feet.
            continue
        channels = []
        for ch in clip["channels"]:
            sm = clip["samplers"][ch["sampler"]]
            values = accessor(sm["output"])
            assert np.allclose(values[0], values[-1]), "Clip must loop continuously"
            channels.append((ch["target"]["node"], ch["target"]["path"], values))
        for frame in range(61):
            poses = [dict(n) for n in j["nodes"]]
            for node, path, values in channels:
                poses[node][path] = values[frame]
            worlds = {}

            def world(i):
                if i not in worlds:
                    worlds[i] = (
                        world(parents[i]) if i in parents else np.eye(4)
                    ) @ trs(poses[i])
                return worlds[i]

            heights = [world(i)[1, 3] for i in paws]
            assert min(heights) > -0.0001, (clip["name"], frame, heights)
            if clip["name"] in ["Idle", "Sit", "Greet"]:
                assert max(abs(v) for v in heights) < 0.0001, (clip["name"], heights)
            else:
                assert max(heights) < 0.08
    assert all("uri" not in image for image in j["images"])
    assert j["extras"]["reference"] == "https://www.youtube.com/watch?v=Jxv0e1VXSR0"
    print(
        f"PASS {info['id']}: {len(weights)} vertices, {len(skin['joints'])} joints, two-layer groom and soft alpha, grounded paw anchors, looping clips, valid weights/buffers/SHA256"
    )
