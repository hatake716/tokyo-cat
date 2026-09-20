export const EARTH = 6378137;
export const clamp = (n, a, b) => Math.max(a, Math.min(b, n));
export function distance(a, b) {
  const rad = Math.PI / 180,
    p1 = a.lat * rad,
    p2 = b.lat * rad,
    dp = (b.lat - a.lat) * rad,
    dl = (b.lon - a.lon) * rad;
  return (
    2 *
    EARTH *
    Math.atan2(
      Math.sqrt(
        Math.sin(dp / 2) ** 2 +
          Math.cos(p1) * Math.cos(p2) * Math.sin(dl / 2) ** 2,
      ),
      Math.sqrt(
        Math.max(
          0,
          1 -
            (Math.sin(dp / 2) ** 2 +
              Math.cos(p1) * Math.cos(p2) * Math.sin(dl / 2) ** 2),
        ),
      ),
    )
  );
}
export function offset(p, east, north) {
  return {
    ...p,
    lat: p.lat + ((north / EARTH) * 180) / Math.PI,
    lon:
      p.lon +
      ((east / (EARTH * Math.cos((p.lat * Math.PI) / 180))) * 180) / Math.PI,
  };
}
export function angleDelta(a, b) {
  return Math.atan2(Math.sin(b - a), Math.cos(b - a));
}
export function advance(p, input, heading, dt, running, region) {
  const magnitude = Math.min(1, Math.hypot(input.x, input.y));
  if (magnitude < 0.08) return { ...p, speed: 0 };
  const yaw = heading + Math.atan2(input.x, -input.y),
    speed = (running ? 3.4 : 1.25) * magnitude;
  const n = offset(
    p,
    Math.sin(yaw) * speed * clamp(dt, 0, 0.05),
    Math.cos(yaw) * speed * clamp(dt, 0, 0.05),
  );
  if (distance(n, region) > region.radius) return { ...p, speed: 0 };
  return {
    ...n,
    heading: p.heading + angleDelta(p.heading, yaw) * Math.min(1, dt * 12),
    speed,
  };
}
export function nearbyPlaces(p, places, area) {
  return places
    .filter((x) => x.area === area)
    .map((x) => ({ ...x, distance: distance(p, x) }))
    .sort((a, b) => a.distance - b.distance);
}
export function discoveries(p, places, area, visited) {
  return nearbyPlaces(p, places, area).filter(
    (x) => x.distance <= x.radius && !visited[x.id],
  );
}
export function canGreet(p, npc) {
  return distance(p, npc) <= 3.0;
}
export function validSave(raw, catalog) {
  let s;
  try {
    s = JSON.parse(raw || "{}");
  } catch {
    s = {};
  }
  if (!s || typeof s !== "object" || Array.isArray(s)) s = {};
  const region =
    catalog.regions.find((r) => r.id === s.area) || catalog.regions[0];
  const breed = catalog.breeds.some((b) => b.id === s.breed)
    ? s.breed
    : "mixed";
  const visited = Object.fromEntries(
    Object.entries(s.visited || {}).filter(
      ([k, v]) =>
        catalog.places.some((p) => p.id === k) && Number.isFinite(v) && v > 0,
    ),
  );
  const friends = Array.isArray(s.friends)
    ? [...new Set(s.friends.filter((x) => /^\w+-\d+$/.test(x)))].slice(0, 200)
    : [];
  const position =
    s.position &&
    Number.isFinite(s.position.lat) &&
    Number.isFinite(s.position.lon) &&
    distance(s.position, region) <= region.radius
      ? {
          lon: s.position.lon,
          lat: s.position.lat,
          heading: Number.isFinite(s.position.heading) ? s.position.heading : 0,
        }
      : {
          lon: region.lon,
          lat: region.lat,
          heading: (region.heading * Math.PI) / 180,
        };
  return {
    version: 1,
    lang: s.lang === "en" ? "en" : "ja",
    area: region.id,
    breed,
    visited,
    friends,
    position,
    quality: s.quality === "high" ? "high" : "balanced",
    tutorial: s.tutorial === true,
  };
}

// Authored locomotion, not motion capture. Foot stance/swing and two-link IK.
// cycle is advanced by travelled metres, so stopping does not keep cycling feet.
export function gaitPose(cycle, speed, legScale = 1) {
  const trot = speed > 1.7,
    duty = trot ? 0.5 : 0.66;
  const phases = trot
    ? { front_left: 0, rear_right: 0, front_right: 0.5, rear_left: 0.5 }
    : { rear_left: 0, front_left: 0.25, rear_right: 0.5, front_right: 0.75 };
  const stride = (trot ? 0.16 : 0.115) * Math.min(1, speed / 0.8) * legScale;
  const result = {};
  for (const [name, phase] of Object.entries(phases)) {
    const u = (((cycle + phase) % 1) + 1) % 1;
    const stance = u < duty;
    const swing = (u - duty) / (1 - duty);
    const x = stance ? stride * (0.5 - u / duty) : stride * (-0.5 + swing);
    const lift = stance
      ? 0
      : Math.sin(swing * Math.PI) *
        (trot ? 0.065 : 0.042) *
        legScale *
        Math.min(1, speed / 0.6);
    const a = 0.13 * legScale,
      b = 0.15 * legScale;
    const y = -(a + b - 0.01 * legScale * Math.min(1, speed / 0.8)) + lift;
    const r = Math.min(a + b - 0.0001, Math.hypot(x, y));
    const alpha = Math.acos(
      clamp((a * a + r * r - b * b) / (2 * a * r), -1, 1),
    );
    const beta =
      Math.PI - Math.acos(clamp((a * a + b * b - r * r) / (2 * a * b), -1, 1));
    const sign = name.startsWith("front") ? -1 : 1;
    const hip = Math.atan2(x, -y) - sign * alpha;
    result[name] = {
      hip,
      knee: sign * beta,
      ankle: -hip - sign * beta,
      stance,
      lift,
    };
  }
  return result;
}
