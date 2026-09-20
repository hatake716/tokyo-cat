import json, struct, numpy as np
from pathlib import Path
from scipy.spatial.transform import Rotation

p = Path("private-assets/free-reference/fox-animations.glb")
raw = p.read_bytes()
n = struct.unpack_from("<I", raw, 12)[0]
j = json.loads(raw[20 : 20 + n])
binary = raw[28 + n :]


def acc(i):
    a = j["accessors"][i]
    v = j["bufferViews"][a["bufferView"]]
    return np.frombuffer(
        binary,
        dtype="<f4",
        count=a["count"] * {"SCALAR": 1, "VEC3": 3, "VEC4": 4}[a["type"]],
        offset=v.get("byteOffset", 0) + a.get("byteOffset", 0),
    ).reshape(a["count"], -1)


parents = {c: i for i, x in enumerate(j["nodes"]) for c in x.get("children", [])}
feet = [12, 18, 35, 42]
result = {}
for clip in j["animations"]:
    if clip["name"] not in ["Walk", "Run", "Sit"]:
        continue
    frames = []
    for t in np.linspace(0, max(acc(s["input"])[-1, 0] for s in clip["samplers"]), 61):
        poses = [
            {
                k: node.get(k, default)
                for k, default in [
                    ("translation", [0, 0, 0]),
                    ("rotation", [0, 0, 0, 1]),
                    ("scale", [1, 1, 1]),
                ]
            }
            for node in j["nodes"]
        ]
        for ch in clip["channels"]:
            sm = clip["samplers"][ch["sampler"]]
            times = acc(sm["input"])[:, 0]
            values = acc(sm["output"])
            v = [np.interp(t, times, values[:, k]) for k in range(values.shape[1])]
            poses[ch["target"]["node"]][ch["target"]["path"]] = v
        worlds = {}

        def world(i):
            if i in worlds:
                return worlds[i]
            p = poses[i]
            m = np.eye(4)
            m[:3, :3] = Rotation.from_quat(p["rotation"]).as_matrix() @ np.diag(
                p["scale"]
            )
            m[:3, 3] = p["translation"]
            worlds[i] = world(parents[i]) @ m if i in parents else m
            return worlds[i]

        frames.append(
            {
                "time": round(float(t), 4),
                "feet": [world(i)[:3, 3].round(5).tolist() for i in feet],
                "head": world(8)[:3, 3].round(5).tolist(),
                "hips": world(47)[:3, 3].round(5).tolist(),
            }
        )
    result[clip["name"]] = frames
Path("docs/sources/cat-reference/cc0-motion-samples.json").write_text(
    json.dumps(
        {
            "source": "https://github.com/Mesh2Motion/mesh2motion-app/blob/3ce7f9d97d25e608b4779ce797da343775ded62b/static/animations/fox-animations.glb",
            "license": "CC0-1.0",
            "description": "Forward-kinematics samples for observation only. Fox animation is not feline mocap. Foot order front L/R, rear L/R. Original source axes.",
            "clips": result,
        },
        indent=2,
    )
    + "\n"
)
for name, frames in result.items():
    a = np.array([f["feet"] for f in frames])
    print(
        name,
        "ranges",
        np.ptp(a, axis=0).round(3).tolist(),
        "peak height frame",
        np.argmax(a[:, :, 1], axis=0).tolist(),
    )
