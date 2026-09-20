import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import {
  distance,
  offset,
  advance,
  validSave,
  discoveries,
  canGreet,
  angleDelta,
} from "../app/src/main/assets/game/core.mjs";
import { words } from "../app/src/main/assets/game/i18n.mjs";
const catalog = JSON.parse(
  fs.readFileSync(
    new URL("../app/src/main/assets/game/catalog.json", import.meta.url),
  ),
);
const region = catalog.regions[0];
test("five requested districts are present", () =>
  assert.deepEqual(
    catalog.regions.map((x) => x.id),
    ["marunouchi", "shinjuku", "shibuya", "asakusa", "akihabara"],
  ));
test("each district has three bilingual sourced landmarks within playable radius", () => {
  for (const r of catalog.regions) {
    const pp = catalog.places.filter((x) => x.area === r.id);
    assert.equal(pp.length, 3);
    for (const p of pp) {
      assert.ok(distance(p, r) < r.radius);
      assert.ok(p.description.ja.length > 40);
      assert.ok(p.description.en.length > 60);
      assert.ok(p.source.startsWith("https://"));
      assert.ok(p.radius >= 20 && p.radius <= 100);
    }
  }
});
test("ten unique breeds, actual GLBs and provenance", () => {
  assert.equal(new Set(catalog.breeds.map((x) => x.id)).size, 10);
  for (const b of catalog.breeds) {
    const buf = fs.readFileSync(
      new URL("../app/src/main/assets/game/" + b.model, import.meta.url),
    );
    assert.equal(buf.toString("ascii", 0, 4), "glTF");
    assert.equal(buf.readUInt32LE(8), buf.length);
    const j = JSON.parse(
      buf.subarray(20, 20 + buf.readUInt32LE(12)).toString(),
    );
    assert.equal(j.asset.version, "2.0");
    assert.ok(j.nodes.some((n) => n.name === "front_left_knee"));
    assert.ok(j.nodes.some((n) => n.name === "tail2"));
    assert.deepEqual(
      j.animations.map((x) => x.name),
      ["Blink", "Idle", "Walk", "Trot", "Greet", "Sit"],
    );
    assert.ok(j.extras.provenance.includes("CC BY 4.0"));
    assert.equal(j.extras.face.license, "CC-BY-4.0");
    assert.ok(j.extras.face.source.includes("guillaume bolis"));
    for (const a of j.accessors)
      if (a.type === "VEC3") assert.ok(a.min.every(Number.isFinite));
  }
});
test("localization keys match", () =>
  assert.deepEqual(Object.keys(words.ja).sort(), Object.keys(words.en).sort()));
test("one meter geographic displacement stays in meters", () =>
  assert.ok(Math.abs(distance(region, offset(region, 1, 0)) - 1) < 0.001));
test("north and east are independent", () => {
  assert.equal(offset(region, 0, 1).lon, region.lon);
  assert.equal(offset(region, 1, 0).lat, region.lat);
});
test("Tokyo-Shibuya distance is plausible", () => {
  const d = distance(catalog.regions[0], catalog.regions[2]);
  assert.ok(d > 5500 && d < 7500);
});
test("walk and run actually differ", () => {
  const p = { ...region, heading: 0 };
  const w = advance(p, { x: 0, y: -1 }, 0, 0.05, false, region);
  const r = advance(p, { x: 0, y: -1 }, 0, 0.05, true, region);
  assert.ok(distance(p, r) > distance(p, w) * 2.5);
});
test("diagonal input cannot exceed speed limit", () => {
  const p = { ...region, heading: 0 };
  assert.ok(
    distance(p, advance(p, { x: 1, y: -1 }, 0, 0.05, false, region)) < 0.063,
  );
});
test("camera heading controls travel direction", () => {
  const p = { ...region, heading: 0 };
  const q = advance(p, { x: 0, y: -1 }, Math.PI / 2, 0.05, false, region);
  assert.ok(q.lon > p.lon);
  assert.ok(Math.abs(q.lat - p.lat) < 1e-9);
});
test("release stops motion", () => {
  const p = { ...region, heading: 0 };
  const q = advance(p, { x: 0, y: 0 }, 0, 0.05, true, region);
  assert.equal(distance(p, q), 0);
  assert.equal(q.speed, 0);
});
test("stalled frames do not teleport", () => {
  const p = { ...region, heading: 0 };
  assert.ok(
    distance(p, advance(p, { x: 0, y: -1 }, 0, 20, true, region)) < 0.18,
  );
});
test("region boundary prevents walking outside loaded area", () => {
  const p = { ...offset(region, 0, region.radius - 0.01), heading: 0 };
  assert.equal(advance(p, { x: 0, y: -1 }, 0, 0.05, true, region).speed, 0);
});
test("angle wrap uses short turn", () =>
  assert.ok(
    Math.abs(angleDelta(Math.PI - 0.01, -Math.PI + 0.01) - 0.02) < 1e-9,
  ));
test("discovery happens only inside radius and in selected area", () => {
  const place = catalog.places[0];
  assert.equal(
    discoveries(place, catalog.places, place.area, {}).filter(
      (p) => p.id === place.id,
    ).length,
    1,
  );
  assert.equal(
    discoveries(offset(place, place.radius + 1, 0), [place], place.area, {})
      .length,
    0,
  );
  assert.equal(discoveries(place, [place], "asakusa", {}).length, 0);
});
test("discovery is not duplicated", () => {
  const p = catalog.places[0];
  assert.equal(discoveries(p, [p], p.area, { [p.id]: 1 }).length, 0);
});
test("greeting enforces three meter range", () => {
  assert.ok(canGreet(region, offset(region, 2.99, 0)));
  assert.ok(!canGreet(region, offset(region, 3.01, 0)));
});
test("corrupt save falls back safely", () => {
  for (const raw of [
    "broken",
    "null",
    "[]",
    "1",
    '{"position":{"lat":9999,"lon":-999}}',
  ])
    assert.equal(validSave(raw, catalog).area, "marunouchi");
});
test("unknown identifiers cannot pollute progress", () => {
  const s = validSave(
    JSON.stringify({
      area: "x",
      breed: "x",
      visited: { unknown: 12, "tokyo-station": 12, omoide: -1 },
      friends: ["asakusa-1", "asakusa-1", "invalid"],
    }),
    catalog,
  );
  assert.equal(s.breed, "mixed");
  assert.deepEqual(Object.keys(s.visited), ["tokyo-station"]);
  assert.equal(s.friends.length, 1);
});
test("valid progress survives round trip", () => {
  const s = validSave(
    JSON.stringify({
      lang: "en",
      area: "shibuya",
      breed: "ragdoll",
      visited: { hachiko: 1770000 },
      friends: ["shibuya-1"],
      tutorial: true,
    }),
    catalog,
  );
  assert.deepEqual(validSave(JSON.stringify(s), catalog), s);
});
const { gaitPose } = await import("../app/src/main/assets/game/core.mjs");
test("stopping plants all four feet regardless of cycle", () => {
  for (const cycle of [0, 0.3, 0.7, 0.93]) {
    for (const pose of Object.values(gaitPose(cycle, 0))) {
      assert.equal(pose.lift, 0);
      assert.equal(pose.x, 0);
      assert.ok(pose.stance);
    }
  }
});
test("stance feet stay on ground and swing feet lift", () => {
  const stance = gaitPose(0, 1.2).front_left,
    swing = gaitPose(0.83, 1.2).front_left;
  assert.equal(stance.lift, 0);
  assert.ok(swing.lift > 0.03);
});
test("four limbs receive finite hip knee and ankle rotations", () => {
  for (const speed of [0, 0.4, 1.25, 3.4])
    for (const scale of [0.67, 1, 1.15])
      for (const u of [0, 0.2, 0.5, 0.85])
        for (const v of Object.values(gaitPose(u, speed, scale))) {
          assert.ok([v.hip, v.knee, v.ankle].every(Number.isFinite));
          assert.ok(Math.abs(v.hip + v.knee + v.ankle) < 1e-8);
        }
});
test("trotting diagonal pairs match", () => {
  const g = gaitPose(0.2, 3.4);
  assert.deepEqual(g.front_left.stance, g.rear_right.stance);
  assert.equal(g.front_left.lift, g.rear_right.lift);
});
