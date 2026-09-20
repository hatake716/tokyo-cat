// Build-time exporter: samples exactly the functions used during gameplay.
import {
  catPose,
  gaitDistance,
} from "../app/src/main/assets/game/cat-motion.mjs";
import fs from "node:fs";
const breeds = JSON.parse(
  fs.readFileSync(
    new URL("../app/src/main/assets/game/catalog.json", import.meta.url),
  ),
).breeds;
const result = {};
for (const b of breeds) {
  result[b.id] = [];
  for (const [name, speed, sit, greeting, duration] of [
    ["Idle", 0, 0, 0, 5.7],
    ["Walk", 1.0, 0, 0, 0],
    ["Trot", 2.6, 0, 0, 0],
    ["Greet", 0, 0, 1, 5.7],
    ["Sit", 0, 1, 0, 5.7],
  ]) {
    const period = duration || gaitDistance(speed, b.legs) / speed;
    const frames = Array.from({ length: 61 }, (_, i) => {
      const t = (i / 60) * period;
      return {
        time: t,
        pose: catPose({
          time: t,
          cycle: duration ? 0 : i / 60,
          speed,
          legScale: b.legs,
          sit,
          greeting,
        }),
      };
    });
    result[b.id].push({ name, frames });
  }
}
process.stdout.write(JSON.stringify(result));
