import test from "node:test";
import assert from "node:assert/strict";
import {
  gaitPose,
  gaitDistance,
  hipHeight,
  catPose,
} from "../app/src/main/assets/game/cat-motion.mjs";
const close = (a, b, eps = 1e-7) =>
  assert.ok(Math.abs(a - b) < eps, `${a} vs ${b}`);
test("stance feet cancel travelled distance at steady speed, all leg lengths", () => {
  for (const speed of [0.4, 1, 1.7, 2, 3.4])
    for (const scale of [0.67, 1, 1.15]) {
      const d = 0.0001,
        step = d / gaitDistance(speed, scale);
      for (let cycle = 0; cycle < 1; cycle += 0.02) {
        const a = gaitPose(cycle, speed, scale),
          b = gaitPose(cycle + step, speed, scale);
        for (const name of Object.keys(a))
          if (a[name].stance && b[name].stance) close(a[name].x, b[name].x + d);
      }
    }
});
test("forward kinematics reaches commanded pad height without leg overextension", () => {
  for (const scale of [0.67, 1, 1.15])
    for (const speed of [0, 0.4, 1.25, 1.7, 2, 3.4])
      for (let cycle = 0; cycle < 1; cycle += 0.01)
        for (const v of Object.values(gaitPose(cycle, speed, scale))) {
          const x =
            0.13 * scale * Math.sin(v.hip) +
            0.15 * scale * Math.sin(v.hip + v.knee);
          const y =
            -0.13 * scale * Math.cos(v.hip) -
            0.15 * scale * Math.cos(v.hip + v.knee);
          close(x, v.x);
          close(y + hipHeight(scale, speed), v.lift);
          assert.ok(v.lift >= 0);
          close(v.hip + v.knee + v.ankle, 0);
        }
});
test("toe off and touchdown preserve position and horizontal velocity", () => {
  for (const speed of [1, 3]) {
    const duty = speed === 1 ? 0.66 : 0.52,
      e = 1e-6;
    for (const at of [duty, 1]) {
      const a = gaitPose(at - e, speed).front_left,
        b = gaitPose(at, speed).front_left,
        c = gaitPose(at + e, speed).front_left;
      close(a.x, c.x, 2e-6);
      close((b.x - a.x) / e, (c.x - b.x) / e, 1e-4);
      close(a.lift, c.lift, 1e-8);
    }
  }
});
test("breed stride length changes cadence without stretching paw travel", () => {
  close(gaitDistance(1, 0.67) / gaitDistance(1, 1), 0.67);
});
test("eyes blink, breathing and ears animate independently from locomotion", () => {
  const open = catPose({ time: 1 }),
    closed = catPose({ time: 0.11 });
  assert.ok(open.eye_left.scale[1] > 0.99);
  assert.ok(closed.eye_left.scale[1] < 0.1);
  assert.notDeepEqual(open.torso.scale, closed.torso.scale);
  assert.notDeepEqual(open.ear_left.rotation, closed.ear_left.rotation);
  for (const pose of [open, closed, catPose({ sit: 1, greeting: 1, speed: 3 })])
    for (const t of Object.values(pose))
      assert.ok(
        [...t.rotation, ...t.translation, ...t.scale].every(Number.isFinite),
      );
});
test("seated transition keeps rear paw anchors on the floor for every breed scale", () => {
  for (const scale of [0.67, 1, 1.15])
    for (const sit of [0, 0.25, 0.5, 0.75, 1]) {
      const p = catPose({ legScale: scale, sit, time: 1 }),
        h = p.rear_left.rotation[2],
        k = p.rear_left_knee.rotation[2];
      const y =
        hipHeight(scale) +
        p.rear_left.translation[1] -
        0.13 * scale * Math.cos(h) -
        0.15 * scale * Math.cos(h + k);
      close(y, 0);
      close(h + k + p.rear_left_paw.rotation[2], 0);
    }
});
