// Authored feline approximation in metres; not motion capture.
// Reference observations and limits: docs/CAT_MODELS.md.
const clamp = (x, a, b) => Math.max(a, Math.min(b, x));
const mix = (a, b, t) => a + (b - a) * t;
const smooth = (x) => {
  x = clamp(x, 0, 1);
  return x * x * (3 - 2 * x);
};
const tau = Math.PI * 2;
export const hipHeight = (scale = 1, speed = 0) =>
  (0.267 - 0.043 * smooth(speed / 0.35)) * scale + 0.002;
export function gaitDistance(speed, legScale = 1) {
  return mix(0.42, 0.55, smooth((speed - 1.5) / 0.8)) * legScale;
}
export function gaitPose(cycle, speed, legScale = 1) {
  const trot = smooth((speed - 1.5) / 0.8);
  const duty = mix(0.66, 0.52, trot);
  const amount = smooth(speed / 0.35);
  const phases = {
    front_left: 0,
    rear_left: mix(0.75, 0.5, trot),
    front_right: 0.5,
    rear_right: mix(0.25, 0, trot),
  };
  // dx/dcycle = -distance: a stance foot cancels forward travel exactly at
  // steady speed. The previous short stride caused visible skating.
  const stride = gaitDistance(speed, legScale) * duty;
  const result = {};
  for (const [name, phase] of Object.entries(phases)) {
    const u = (((cycle + phase) % 1) + 1) % 1;
    const stance = u < duty || amount === 0;
    const swing = clamp((u - duty) / (1 - duty), 0, 1);
    // Hermite swing preserves backward velocity at toe-off and landing.
    const h = swing * swing * (3 - 2 * swing);
    const tangent = -gaitDistance(speed, legScale) * (1 - duty);
    const x =
      amount === 0
        ? 0
        : amount *
          (u < duty
            ? stride / 2 - gaitDistance(speed, legScale) * u
            : -stride / 2 +
              stride * h +
              tangent * (2 * swing ** 3 - 3 * swing ** 2 + swing));
    const lift = stance
      ? 0
      : Math.sin(Math.PI * swing) ** 2 *
        mix(0.038, 0.06, trot) *
        legScale *
        amount;
    const y = -hipHeight(legScale, speed) + lift;
    result[name] = {
      ...solveLeg(x, y, legScale, name.startsWith("front") ? 1 : -1),
      stance,
      lift,
      x,
      y,
    };
  }
  return result;
}
function solveLeg(x, y, scale, sign) {
  const a = 0.13 * scale,
    b = 0.15 * scale,
    r = Math.min(a + b - 0.00001, Math.hypot(x, y));
  const alpha = Math.acos(clamp((a * a + r * r - b * b) / (2 * a * r), -1, 1));
  const beta =
    Math.PI - Math.acos(clamp((a * a + b * b - r * r) / (2 * a * b), -1, 1));
  const hip = Math.atan2(x, -y) - sign * alpha;
  return { hip, knee: sign * beta, ankle: -hip - sign * beta };
}
// One pose definition is shared by the game and the GLB animation exporter.
export function catPose({
  cycle = 0,
  speed = 0,
  legScale = 1,
  time = 0,
  phase = 0,
  sit = 0,
  greeting = 0,
} = {}) {
  const nodes = {},
    seated = clamp(sit, 0, 1),
    moving = smooth(speed / 0.35);
  const put = (
    name,
    z = 0,
    translation = [0, 0, 0],
    y = 0,
    scale = [1, 1, 1],
  ) => (nodes[name] = { rotation: [0, y, z], translation, scale });
  for (const [name, v] of Object.entries(gaitPose(cycle, speed, legScale))) {
    const rear = name.startsWith("rear");
    // Solve rear limbs against the floor throughout the seated transition.
    const seat = rear
      ? solveLeg(
          mix(v.x, 0.06 * legScale, seated),
          v.y + 0.09 * legScale * seated,
          legScale,
          -1,
        )
      : v;
    put(name, seat.hip, [
      rear ? 0.018 * seated : 0,
      rear ? -0.09 * legScale * seated : 0,
      0,
    ]);
    put(name + "_knee", seat.knee);
    put(name + "_paw", seat.ankle);
  }
  const breath = Math.sin(time * 1.8 + phase) * 0.002;
  const strideWave = Math.sin(cycle * tau) * moving * (1 - seated);
  put(
    "torso",
    0.23 * seated,
    [0.01 * seated, -0.037 * legScale * seated + breath, 0],
    0,
    [1, 1 + breath * 2, 1 + breath * 1.5],
  );
  put("haunch", 0, [0, -0.085 * legScale * seated, 0]);
  put("shoulders", strideWave * 0.018, [
    -0.008 * seated,
    breath + Math.cos(cycle * tau * 2) * moving * 0.002,
    0,
  ]);
  put("neck", 0.05 * seated, [-0.02 * seated, breath, 0]);
  put("chest", 0.08 * seated, [-0.012 * seated, breath, 0]);
  put(
    "head",
    greeting
      ? -0.1 + Math.sin(time * 3) * 0.018
      : Math.sin(time * 0.7 + phase) * 0.013 - moving * 0.045,
    [-0.023 * seated, breath - moving * 0.005, 0],
    Math.sin(time * 0.35 + phase) * 0.045 * (1 - moving),
  );
  const blinkPhase = (((time + phase * 2) % 5.7) + 5.7) % 5.7;
  const blink =
    blinkPhase < 0.22 ? Math.sin((Math.PI * blinkPhase) / 0.22) ** 2 : 0;
  for (const [side, sign] of [
    ["left", -1],
    ["right", 1],
  ]) {
    put("eye_" + side, 0, [0, 0, 0], 0, [
      1,
      Math.max(0.08, 1 - blink * 0.94),
      1,
    ]);
    put(
      "ear_" + side,
      Math.sin(time * 0.9 + phase + sign) * 0.035,
      [0, 0, 0],
      Math.sin(time * 0.6 + phase + sign) * 0.065,
    );
  }
  for (let i = 0; i < 5; i++) {
    const wave = Math.sin(time * 1.3 + phase - i * 0.65);
    put(
      "tail" + i,
      (-0.05 - wave * 0.045) * (1 - seated) - (greeting ? 0.18 : 0),
      i === 0 ? [0.02 * seated, -0.08 * legScale * seated, 0] : [0, 0, 0],
      wave * (0.08 + i * 0.015) + seated * 0.2,
    );
  }
  const crouch = hipHeight(legScale, speed) - hipHeight(legScale);
  for (const name of [
    "torso",
    "haunch",
    "shoulders",
    "chest",
    "neck",
    "head",
    "front_left",
    "front_right",
    "rear_left",
    "rear_right",
    "tail0",
  ])
    nodes[name].translation[1] += crouch;
  return nodes;
}
