import { catPose, gaitDistance } from "./cat-motion.mjs";
import {
  clamp,
  distance,
  offset,
  advance,
  angleDelta,
  nearbyPlaces,
  discoveries,
  canGreet,
  validSave,
} from "./core.mjs";
import { words } from "./i18n.mjs";
import { photos, addPhoto, removePhoto } from "./storage.mjs";
const $ = (id) => document.getElementById(id),
  C = window.Cesium;
const catalog = await fetch("catalog.json").then((r) => r.json());
let state = validSave(localStorage.getItem("tokyo-cat-save"), catalog);
let region = catalog.regions.find((r) => r.id === state.area),
  p = { ...state.position, height: region.height, speed: 0 };
let mode = "home",
  modal = null,
  viewer,
  terrain,
  tileset,
  cat,
  npcs = [],
  markers = [],
  loadId = 0,
  catId = 0,
  terrainReady = false,
  tilesReady = false,
  modelsReady = false;
let input = { x: 0, y: 0 },
  running = false,
  firstPerson = false,
  yaw = p.heading,
  pitch = -0.24,
  photoRange = 3.5,
  seated = false,
  time = 0,
  last = 0,
  hudTick = 0,
  saveTick = 0,
  target = null,
  toastTimer;
let cityStats = { tilesLoaded: 0, tilesFailed: 0, terrain: false },
  lastError = "",
  paused = false,
  photoBusy = false;
const t = (k) => words[state.lang][k] || k,
  local = (x) => x?.[state.lang] || x?.en || "",
  esc = (s) =>
    String(s).replace(
      /[&<>"']/g,
      (c) =>
        ({
          "&": "&amp;",
          "<": "&lt;",
          ">": "&gt;",
          '"': "&quot;",
          "'": "&#39;",
        })[c],
    );
const fmt = (n) =>
  new Date(n).toLocaleString(state.lang === "ja" ? "ja-JP" : "en-US", {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
function save() {
  try {
    state.position = { lon: p.lon, lat: p.lat, heading: p.heading };
    localStorage.setItem("tokyo-cat-save", JSON.stringify(state));
  } catch (e) {
    toast(t("storageError"));
  }
}
function toast(s) {
  clearTimeout(toastTimer);
  $("toast").textContent = s;
  $("toast").hidden = false;
  toastTimer = setTimeout(() => ($("toast").hidden = true), 3200);
}
function status(key, error = false) {
  lastError = error ? key : "";
  $("load-status").classList.toggle("error", error);
  $("load-status").querySelector("span").textContent = t(key);
  $("retry").hidden = !error;
}
function renderText() {
  document.documentElement.lang = state.lang;
  const ids = {
    intro: "intro",
    "brand-tagline": "brandTagline",
    "map-credit": "mapCredit",
    start: "start",
    "choose-cat": "choose",
    "network-note": "network",
    "district-title": "districts",
    "build-badge": "dev",
    "open-map": "map",
    "open-album": "album",
    "home-button": "home",
    camera: "camera",
    greet: "greet",
    "move-hint": "move",
    "gesture-hint": "look",
    "zoom-label": "zoom",
    shutter: "shutter",
    "exit-camera": "done",
  };
  for (const [id, key] of Object.entries(ids)) $(id).textContent = t(key);
  $("language").textContent = state.lang === "ja" ? "EN" : "日本語";
  $("run").textContent = running ? t("walk") : t("run");
  $("perspective").textContent = firstPerson ? t("follow") : t("catEye");
  $("pose").textContent = seated ? t("stand") : t("sit");
  $("home-album").innerHTML =
    esc(t("album")) +
    " <span>" +
    Object.keys(state.visited).length +
    " / " +
    catalog.places.length +
    "  ↗</span>";
  $("districts").innerHTML = catalog.regions
    .map(
      (r) =>
        `<button class="district ${r.id === state.area ? "active" : ""}" data-area="${r.id}"><span class="number">0${r.index}</span><div><strong>${esc(local(r.name))}</strong><small>${esc(state.lang === "ja" ? r.name.en.toUpperCase() : r.tagline.en)}</small></div><span class="arrow">↗</span></button>`,
    )
    .join("");
  for (const b of $("districts").querySelectorAll("button"))
    b.onclick = () => travel(b.dataset.area);
  updateHud();
}
function setMode(next) {
  mode = next;
  input = { x: 0, y: 0 };
  $("stick").style.transform = "";
  $("home").hidden = mode !== "home";
  $("hud").hidden = mode !== "play";
  $("camera-ui").hidden = mode !== "photo";
  document.body.classList.toggle("playing", mode !== "home");
  document.body.classList.toggle("photographing", mode === "photo");
  for (const e of markers) e.show = mode === "play";
  if (cat) cat.show = mode !== "home" && !firstPerson;
  for (const n of npcs) if (n.model) n.model.show = mode !== "home";
  $("photo-name").textContent = local(region.name);
}
function openModal(title, html, type) {
  input = { x: 0, y: 0 };
  $("stick").style.transform = "";
  modal = type;
  $("modal-title").textContent = title;
  $("modal-content").innerHTML = html;
  $("modal").hidden = false;
}
function closeModal() {
  modal = null;
  $("modal").hidden = true;
}
function start() {
  setMode("play");
  yaw = p.heading;
  pitch = -0.24;
  if (!state.tutorial) {
    openModal(
      t("tutorialTitle"),
      `<p>${esc(t("tutorial"))}</p><p class="notice">${esc(t("catNote"))}</p><button class="primary" id="tutorial-ok">${esc(t("understood"))}</button>`,
      "tutorial",
    );
    $("tutorial-ok").onclick = () => {
      state.tutorial = true;
      save();
      closeModal();
    };
  }
}
async function travel(id) {
  if (id === state.area && tileset) return;
  state.area = id;
  region = catalog.regions.find((r) => r.id === id);
  p = {
    lon: region.lon,
    lat: region.lat,
    height: region.height,
    heading: (region.heading * Math.PI) / 180,
    speed: 0,
  };
  yaw = p.heading;
  pitch = -0.24;
  target = null;
  save();
  renderText();
  await loadDistrict();
}
function resetStart() {
  p = {
    lon: region.lon,
    lat: region.lat,
    height: region.height,
    heading: (region.heading * Math.PI) / 180,
    speed: 0,
  };
  yaw = p.heading;
  pitch = -0.24;
  save();
}
function updateHud() {
  if (!region) return;
  $("area-code").textContent = "TOKYO / 0" + region.index;
  $("area-name").textContent = local(region.name);
  const count = catalog.places.filter(
    (x) => x.area === state.area && state.visited[x.id],
  ).length;
  $("progress").textContent =
    `${t("places")}  ${count} / 3  ·  ${t("friends")} ${state.friends.length}`;
  let near = nearbyPlaces(p, catalog.places, state.area);
  let objective =
    near.find((x) => x.id === target) ||
    near.find((x) => !state.visited[x.id]) ||
    near[0];
  $("destination").innerHTML = objective
    ? `${esc(local(objective.name))}<small>${Math.round(objective.distance)} m  ${state.visited[objective.id] ? "✓" : ""}</small>`
    : "";
  let friend = npcs.find((n) => canGreet(p, n));
  $("greet").disabled = !friend;
  $("greet").textContent = friend ? "♡ " + t("greet") : t("greet");
}
function updateReady() {
  const ready = terrainReady && tilesReady && modelsReady;
  if (ready) status("ready");
  $("start").disabled = !ready;
  if (!ready && lastError === "") status("loading");
}
async function setup() {
  try {
    C.Ion.defaultAccessToken = "";
    C.RequestScheduler.maximumRequestsPerServer = 8;
    viewer = new C.Viewer("world", {
      baseLayer: false,
      animation: false,
      timeline: false,
      geocoder: false,
      homeButton: false,
      baseLayerPicker: false,
      sceneModePicker: false,
      navigationHelpButton: false,
      fullscreenButton: false,
      selectionIndicator: false,
      infoBox: false,
      shouldAnimate: true,
      shadows: false,
      contextOptions: { webgl: { alpha: false, preserveDrawingBuffer: true } },
      msaaSamples: 1,
    });
    viewer.useBrowserRecommendedResolution = false;
    viewer.resolutionScale = state.quality === "high" ? 1 : 0.75;
    viewer.targetFrameRate = 30;
    viewer.scene.screenSpaceCameraController.enableInputs = false;
    viewer.scene.globe.depthTestAgainstTerrain = true;
    viewer.scene.globe.maximumScreenSpaceError = 2;
    viewer.scene.fog.density = 0.00013;
    viewer.scene.backgroundColor = C.Color.fromCssColorString("#8faebb");
    viewer.scene.skyAtmosphere.show = true;
    viewer.scene.globe.enableLighting = false;
    viewer.scene.light = new C.SunLight({ intensity: 2 });
    viewer.scene.highDynamicRange = false;
    viewer.scene.postProcessStages.fxaa.enabled = true;
    viewer.clock.currentTime = C.JulianDate.fromIso8601("2026-05-15T05:00:00Z");
    viewer.clock.shouldAnimate = false;
    viewer.imageryLayers.addImageryProvider(
      new C.UrlTemplateImageryProvider({
        url: "https://cyberjapandata.gsi.go.jp/xyz/seamlessphoto/{z}/{x}/{y}.jpg",
        minimumLevel: 2,
        maximumLevel: 18,
        rectangle: C.Rectangle.fromDegrees(122, 20, 154, 46),
        credit: "国土地理院 / GSI",
      }),
    );
    viewer.scene.renderError.addEventListener((s, e) => {
      console.error(e);
      status("failed", true);
    });
    await loadTerrain();
    await loadDistrict();
    viewer.scene.preRender.addEventListener(frame);
  } catch (e) {
    console.error(e);
    status("failed", true);
  }
}
async function loadTerrain() {
  terrainReady = false;
  try {
    terrain = await C.CesiumTerrainProvider.fromUrl(
      "https://tile.plateauview.mlit.go.jp/terrain/",
      { requestVertexNormals: true },
    );
    viewer.terrainProvider = terrain;
    terrain.errorEvent.addEventListener((e) => {
      console.warn("terrain", e.message);
    });
    cityStats.terrain = true;
    terrainReady = true;
  } catch (e) {
    console.error(e);
    status("terrainError", true);
  }
}
async function sampleGround(position) {
  if (!terrain) return region.height;
  try {
    const samples = await C.sampleTerrainMostDetailed(terrain, [
      C.Cartographic.fromDegrees(position.lon, position.lat),
    ]);
    return Number.isFinite(samples[0].height)
      ? samples[0].height
      : region.height;
  } catch {
    return region.height;
  }
}
async function loadDistrict() {
  const ticket = ++loadId;
  status("loading");
  tilesReady = false;
  modelsReady = false;
  cityStats.tilesLoaded = 0;
  cityStats.tilesFailed = 0;
  updateReady();
  if (tileset) {
    viewer.scene.primitives.remove(tileset);
    tileset = null;
  }
  for (const n of npcs) if (n.model) viewer.scene.primitives.remove(n.model);
  npcs = [];
  for (const m of markers) viewer.entities.remove(m);
  markers = [];
  const initialHeight = await sampleGround(p);
  if (ticket !== loadId) return;
  p.height = initialHeight;
  updateCamera();
  try {
    const tiles = await C.Cesium3DTileset.fromUrl(region.tiles, {
      maximumScreenSpaceError: state.quality === "high" ? 4 : 12,
      cacheBytes: 160 * 1024 * 1024,
      environmentMapOptions: { enabled: false },
      maximumCacheOverflowBytes: 64 * 1024 * 1024,
      skipLevelOfDetail: true,
      dynamicScreenSpaceError: true,
    });
    if (ticket !== loadId) {
      tiles.destroy();
      return;
    }
    tileset = viewer.scene.primitives.add(tiles);
    tiles.tileLoad.addEventListener(() => {
      cityStats.tilesLoaded++;
      if (ticket === loadId) {
        tilesReady = true;
        updateReady();
      }
    });
    tiles.tileFailed.addEventListener((e) => {
      cityStats.tilesFailed++;
      console.warn("tile failed", e.message);
      if (!tilesReady) status("failed", true);
    });
    tiles.allTilesLoaded.addEventListener(() => {
      if (ticket === loadId) {
        tilesReady = true;
        updateReady();
      }
    });
    for (const spot of catalog.places.filter((s) => s.area === state.area)) {
      const h = await sampleGround(spot);
      if (ticket !== loadId) return;
      markers.push(
        viewer.entities.add({
          position: C.Cartesian3.fromDegrees(spot.lon, spot.lat, h + 3),
          point: {
            pixelSize: 7,
            color: C.Color.fromCssColorString("#d9efaa"),
            outlineColor: C.Color.fromCssColorString("#244530"),
            outlineWidth: 2,
          },
          label: {
            text: local(spot.name),
            font: "12px sans-serif",
            fillColor: C.Color.WHITE,
            outlineColor: C.Color.BLACK,
            outlineWidth: 3,
            style: C.LabelStyle.FILL_AND_OUTLINE,
            pixelOffset: new C.Cartesian2(0, -15),
            distanceDisplayCondition: new C.DistanceDisplayCondition(0, 260),
          },
          show: mode === "play",
        }),
      );
    }
    await loadPlayer();
    if (ticket !== loadId) return;
    await loadNpcs(ticket);
    modelsReady = !!cat;
    updateReady();
  } catch (e) {
    console.error(e);
    status("failed", true);
  }
}
function matrixAt(pos) {
  return C.Transforms.headingPitchRollToFixedFrame(
    C.Cartesian3.fromDegrees(pos.lon, pos.lat, pos.height),
    new C.HeadingPitchRoll((pos.heading || 0) - Math.PI / 2, 0, 0),
  );
}
async function makeCat(breed, pos) {
  const m = await C.Model.fromGltfAsync({
    url: breed.model,
    modelMatrix: matrixAt(pos),
    upAxis: C.Axis.Y,
    forwardAxis: C.Axis.X,
    scale: 1,
    minimumPixelSize: 0,
    maximumScale: 1,
    allowPicking: false,
    environmentMapOptions: { enabled: false },
    shadows: C.ShadowMode.DISABLED,
  });
  m._breed = breed;
  viewer.scene.primitives.add(m);
  return m;
}
async function loadPlayer() {
  const id = ++catId;
  if (cat) {
    viewer.scene.primitives.remove(cat);
    cat = null;
  }
  try {
    let model = await makeCat(
      catalog.breeds.find((b) => b.id === state.breed),
      p,
    );
    if (id !== catId) {
      viewer.scene.primitives.remove(model);
      return;
    }
    cat = model;
    cat.show = mode !== "home" && !firstPerson;
  } catch (e) {
    console.error(e);
    status("modelError", true);
  }
}
async function loadNpcs(ticket) {
  const names = [
    "Mugi",
    "Luna",
    "Sora",
    "Momo",
    "Kai",
    "Hana",
    "Kinako",
    "Leo",
    "Rin",
    "Haru",
    "Yuki",
    "Koko",
  ];
  for (let i = 0; i < 12; i++) {
    if (ticket !== loadId) return;
    let angle = i * 2.399,
      rad = i === 0 ? 2.0 : 9 + ((i * 13) % 65);
    let pos = offset(region, Math.sin(angle) * rad, Math.cos(angle) * rad);
    pos.height = await sampleGround(pos);
    pos.heading = angle;
    const n = {
      ...pos,
      id: region.id + "-" + i,
      name: names[i],
      home: { ...pos },
      phase: i * 1.4,
      timer: 2 + i * 0.3,
      speed: 0,
      model: null,
      greeting: 0,
    };
    try {
      n.model = await makeCat(
        catalog.breeds[(i + 3) % catalog.breeds.length],
        n,
      );
      if (ticket !== loadId) {
        viewer.scene.primitives.remove(n.model);
        return;
      }
      n.model.show = mode !== "home";
      npcs.push(n);
    } catch (e) {
      console.warn(e);
    }
  }
}
function collided(from, to, exclude) {
  if (!tilesReady) return true;
  const a = C.Cartesian3.fromDegrees(from.lon, from.lat, from.height + 0.24),
    b = C.Cartesian3.fromDegrees(
      to.lon,
      to.lat,
      (to.height ?? from.height) + 0.24,
    );
  const delta = C.Cartesian3.subtract(b, a, new C.Cartesian3());
  const length = C.Cartesian3.magnitude(delta);
  if (length < 0.0001) return false;
  try {
    const ray = new C.Ray(a, C.Cartesian3.normalize(delta, delta));
    const hit = viewer.scene.pickFromRay(ray, [
      cat,
      ...npcs.map((n) => n.model),
      ...markers,
      ...(exclude || []),
    ]);
    return (
      hit &&
      hit.position &&
      C.Cartesian3.distance(a, hit.position) < length + 0.22
    );
  } catch {
    return false;
  }
}
function ground(pos) {
  const h = viewer.scene.globe.getHeight(
    C.Cartographic.fromDegrees(pos.lon, pos.lat),
  );
  return Number.isFinite(h) ? h : pos.height;
}
function applyCatPose(model, name, pose) {
  const node = model.getNode(name);
  if (!node) return;
  if (!node._catRest)
    node._catRest = {
      position: C.Matrix4.getTranslation(node.matrix, new C.Cartesian3()),
      scale: C.Matrix4.getScale(node.matrix, new C.Cartesian3()),
    };
  const rest = node._catRest;
  const position = C.Cartesian3.add(
    rest.position,
    new C.Cartesian3(...pose.translation),
    new C.Cartesian3(),
  );
  const pitch = C.Quaternion.fromAxisAngle(
    C.Cartesian3.UNIT_Z,
    pose.rotation[2],
  );
  const yaw = C.Quaternion.fromAxisAngle(C.Cartesian3.UNIT_Y, pose.rotation[1]);
  const rotation = C.Quaternion.multiply(yaw, pitch, new C.Quaternion());
  const scale = C.Cartesian3.multiplyComponents(
    rest.scale,
    new C.Cartesian3(...pose.scale),
    new C.Cartesian3(),
  );
  node.matrix = C.Matrix4.fromTranslationQuaternionRotationScale(
    position,
    rotation,
    scale,
    new C.Matrix4(),
  );
}
function animate(model, pos, dt, phase = 0, greeting = 0, locomotion = true) {
  if (!model || !model.ready) return;
  model.modelMatrix = matrixAt(pos);
  const speed = locomotion ? pos.speed : 0;
  const breed = model._breed || catalog.breeds[1];
  model._walkSpeed =
    (model._walkSpeed || 0) +
    (speed - (model._walkSpeed || 0)) * Math.min(1, dt * 12);
  // Advance by actual travel, including breed leg length, not smoothed speed.
  model._cycle =
    (model._cycle ?? phase) +
    (speed * dt) / gaitDistance(model._walkSpeed, breed.legs);
  model._sit =
    (model._sit || 0) +
    ((model === cat && seated ? 1 : 0) - (model._sit || 0)) *
      Math.min(1, dt * 5);
  const pose = catPose({
    cycle: model._cycle,
    speed: model._walkSpeed,
    legScale: breed.legs,
    time,
    phase,
    sit: model._sit,
    greeting,
  });
  for (const [name, transform] of Object.entries(pose))
    applyCatPose(model, name, transform);
}

function frame(scene, clock) {
  const now = performance.now() / 1000,
    dt = last ? clamp(now - last, 0, 0.05) : 0;
  last = now;
  time += dt;
  const exploring =
    !modal && !paused && mode === "play" && terrainReady && tilesReady;
  if (exploring) {
    const next = advance(p, input, yaw, dt, running, region);
    if (!collided(p, next) && !npcs.some((n) => distance(next, n) < 0.95))
      p = { ...next, height: p.height };
    else p.speed = 0;
    const h = ground(p);
    if (Math.abs(h - p.height) < 4)
      p.height += (h - p.height) * Math.min(1, dt * 8);
    for (const n of npcs) {
      n.timer -= dt;
      n.greeting = Math.max(0, n.greeting - dt);
      if (n.greeting > 0) {
        n.speed = 0;
        n.heading +=
          angleDelta(
            n.heading,
            Math.atan2(
              (p.lon - n.lon) * Math.cos((p.lat * Math.PI) / 180),
              p.lat - n.lat,
            ),
          ) * Math.min(1, dt * 4);
      } else if (n.timer < 0) {
        n.timer = 4 + (Math.sin(n.phase + time) + 1) * 3;
        n.speed = n.speed ? 0 : 0.45;
        n.heading += Math.sin(time + n.phase) * 2;
      }
      if (n.speed) {
        let q = offset(
          n,
          Math.sin(n.heading) * n.speed * dt,
          Math.cos(n.heading) * n.speed * dt,
        );
        if (
          distance(q, n.home) > 12 ||
          distance(q, p) < 0.9 ||
          npcs.some((other) => other !== n && distance(q, other) < 0.8) ||
          collided(n, q)
        ) {
          n.heading += Math.PI * 0.6;
          n.speed = 0;
          n.timer = 1;
        } else {
          n.lon = q.lon;
          n.lat = q.lat;
          n.height = ground(n);
        }
      }
    }
    hudTick += dt;
    saveTick += dt;
    if (hudTick > 0.4) {
      hudTick = 0;
      for (const spot of discoveries(
        p,
        catalog.places,
        state.area,
        state.visited,
      )) {
        state.visited[spot.id] = Date.now();
        save();
        toast("✧ " + local(spot.name) + " — " + t("discovered"));
        renderText();
      }
      updateHud();
    }
    if (saveTick > 3) {
      saveTick = 0;
      save();
    }
  } else p.speed = 0;
  animate(cat, p, dt, 0, seated ? 1 : 0);
  for (const n of npcs) animate(n.model, n, dt, n.phase, n.greeting, exploring);
  updateCamera();
}
function updateCamera() {
  if (!viewer) return;
  const center = C.Cartesian3.fromDegrees(
    p.lon,
    p.lat,
    p.height + (firstPerson && mode === "play" ? 0.3 : 0.26),
  );
  if (mode === "home") {
    const r = 260,
      heading = (region.heading * Math.PI) / 180 + Math.sin(time * 0.04) * 0.16;
    viewer.camera.lookAt(
      C.Cartesian3.fromDegrees(region.lon, region.lat, p.height),
      new C.HeadingPitchRange(heading, -0.45, r),
    );
    return;
  }
  if (firstPerson && mode === "play") {
    viewer.camera.lookAtTransform(C.Matrix4.IDENTITY);
    viewer.camera.setView({
      destination: center,
      orientation: { heading: yaw, pitch: clamp(pitch, -0.7, 0.4), roll: 0 },
    });
    if (cat) cat.show = false;
    return;
  }
  if (cat) cat.show = true;
  const range = mode === "photo" ? photoRange : 4.2;
  viewer.camera.lookAt(
    center,
    new C.HeadingPitchRange(yaw, clamp(pitch, -1.1, 0.1), range),
  );
}
function greet() {
  const n = npcs.find((n) => canGreet(p, n));
  if (!n) {
    toast(t("greetHint"));
    return;
  }
  n.greeting = 4;
  n.speed = 0;
  const first = !state.friends.includes(n.id);
  if (first) state.friends.push(n.id);
  save();
  toast("♡ " + n.name + " · " + t(first ? "friend" : "friendAgain"));
  updateHud();
}
function showCats() {
  openModal(
    t("choose"),
    `<p class="notice">${esc(t("catNote"))}</p><div class="grid">${catalog.breeds.map((b) => `<button class="card ${b.id === state.breed ? "selected" : ""}" data-breed="${b.id}"><div class="swatch"><span class="breed-icon" style="background:${b.color}"><b>••</b></span></div><strong>${esc(local(b.name))}</strong><small>${esc(b.id === state.breed ? t("selected") : b.name.en)}</small></button>`).join("")}</div><p class="small">${esc(t("breedNote"))}</p><a href="${catalog.breedSource}">${esc(t("source"))}</a>`,
    "cats",
  );
  for (const b of $("modal-content").querySelectorAll("[data-breed]"))
    b.onclick = async () => {
      state.breed = b.dataset.breed;
      save();
      await loadPlayer();
      showCats();
    };
}
function mapSvg() {
  const spots = catalog.places.filter((x) => x.area === state.area),
    all = [region, ...spots, p];
  const minx = Math.min(...all.map((x) => x.lon)) - 0.0006,
    maxx = Math.max(...all.map((x) => x.lon)) + 0.0006,
    miny = Math.min(...all.map((x) => x.lat)) - 0.0006,
    maxy = Math.max(...all.map((x) => x.lat)) + 0.0006;
  const xy = (x) => [
    30 + ((x.lon - minx) / (maxx - minx)) * 540,
    240 - ((x.lat - miny) / (maxy - miny)) * 200,
  ];
  return `<svg class="map-svg" viewBox="0 0 600 280" role="img" aria-label="${esc(t("places"))}"><defs><pattern id="grid" width="30" height="30" patternUnits="userSpaceOnUse"><path d="M30 0H0V30" fill="none" stroke="#c5d1bc"/></pattern></defs><rect width="600" height="280" fill="url(#grid)"/><text x="20" y="25" fill="#507141" font-size="12">N ↑ · ${esc(local(region.name))}</text>${spots
    .map((s, i) => {
      const [x, y] = xy(s);
      return `<circle cx="${x}" cy="${y}" r="9" fill="${state.visited[s.id] ? "#547343" : "#b6ba9e"}"/><text x="${x + 15}" y="${y + 4}" fill="#21362b" font-size="11">${esc(local(s.name))}</text>`;
    })
    .join(
      "",
    )}<circle cx="${xy(p)[0]}" cy="${xy(p)[1]}" r="7" fill="#dc8649" stroke="white" stroke-width="3"/></svg>`;
}
function showMap() {
  openModal(
    t("map"),
    `<div class="tabs">${catalog.regions.map((r) => `<button data-region="${r.id}" class="${r.id === state.area ? "selected" : ""}">${esc(local(r.name))}</button>`).join("")}</div>${mapSvg()}<p>${esc(t("travelHint"))}</p>${nearbyPlaces(
      p,
      catalog.places,
      state.area,
    )
      .map(
        (s) =>
          `<div class="row"><div><strong>${state.visited[s.id] ? "✓" : "◇"} ${esc(local(s.name))}</strong><small>${Math.round(s.distance)} m · ${esc(t(state.visited[s.id] ? "visit" : "unvisited"))}</small></div><button data-place="${s.id}">↗</button></div>`,
      )
      .join("")}`,
    "map",
  );
  for (const b of $("modal-content").querySelectorAll("[data-region]"))
    b.onclick = async () => {
      closeModal();
      await travel(b.dataset.region);
      showMap();
    };
  for (const b of $("modal-content").querySelectorAll("[data-place]"))
    b.onclick = () => showPlace(b.dataset.place);
}
function showPlace(id) {
  const s = catalog.places.find((x) => x.id === id);
  openModal(
    local(s.name),
    `<span class="stamp">${esc(t(state.visited[id] ? "visit" : "unvisited"))}${state.visited[id] ? " · " + fmt(state.visited[id]) : ""}</span><p class="place-description">${esc(local(s.description))}</p><p><a href="${s.source}">${esc(t("source"))}</a></p><button class="primary" id="set-target">${esc(s.area === state.area ? t("navigate") : t("toArea"))}</button>`,
    "place",
  );
  $("set-target").onclick = async () => {
    if (s.area !== state.area) await travel(s.area);
    target = id;
    closeModal();
    start();
    toast(t("targetSet"));
  };
}
async function showAlbum(tab = "places") {
  let data = [];
  try {
    data = await photos();
  } catch {
    toast(t("saveError"));
  }
  const tabs = `<div class="tabs">${["places", "photos", "friends"].map((x) => `<button data-tab="${x}" class="${tab === x ? "selected" : ""}">${esc(t(x))} · ${x === "places" ? Object.keys(state.visited).length : x === "photos" ? data.length : state.friends.length}</button>`).join("")}</div>`;
  let body = "";
  if (tab === "places") {
    body =
      catalog.places
        .filter((x) => state.visited[x.id])
        .map(
          (s) =>
            `<div class="row"><div><strong>✧ ${esc(local(s.name))}</strong><small>${fmt(state.visited[s.id])}</small></div><button data-place="${s.id}">↗</button></div>`,
        )
        .join("") ||
      `<div class="empty"><span>◇</span>${esc(t("noPlaces"))}</div>`;
  } else if (tab === "photos") {
    body = data.length
      ? `<div class="grid photo-grid">${data.map((x) => `<button class="card photo-card" data-photo="${x.id}"><img src="${x.image}" alt="${esc(local(catalog.regions.find((r) => r.id === x.area).name))}"><div><strong>${esc(local(catalog.regions.find((r) => r.id === x.area).name))}</strong><small>${fmt(x.time)}</small></div></button>`).join("")}</div>`
      : `<div class="empty"><span>▣</span>${esc(t("noPhotos"))}<p>${esc(t("photoHint"))}</p></div>`;
  } else {
    body =
      state.friends
        .map((id) => {
          const [area, num] = id.split("-");
          const name =
            [
              "Mugi",
              "Luna",
              "Sora",
              "Momo",
              "Kai",
              "Hana",
              "Kinako",
              "Leo",
              "Rin",
              "Haru",
              "Yuki",
              "Koko",
            ][Number(num)] || "Cat";
          return `<div class="row"><strong>♡ ${name}</strong><small>${esc(local(catalog.regions.find((r) => r.id === area)?.name))}</small></div>`;
        })
        .join("") ||
      `<div class="empty"><span>♡</span>${esc(t("friendEmpty"))}</div>`;
  }
  openModal(t("album"), tabs + body, "album");
  for (const b of $("modal-content").querySelectorAll("[data-tab]"))
    b.onclick = () => showAlbum(b.dataset.tab);
  for (const b of $("modal-content").querySelectorAll("[data-place]"))
    b.onclick = () => showPlace(b.dataset.place);
  for (const b of $("modal-content").querySelectorAll("[data-photo]"))
    b.onclick = () => showPhoto(data.find((x) => x.id === b.dataset.photo));
}
function showPhoto(photo) {
  openModal(
    local(catalog.regions.find((r) => r.id === photo.area).name),
    `<img class="photo-full" src="${photo.image}" alt="TOKYO-CAT"><div class="row"><small>${fmt(photo.time)}</small><div><button id="export-photo" class="primary">${esc(t("export"))}</button> <button class="danger" id="delete-photo">${esc(t("delete"))}</button></div></div>`,
    "photo",
  );
  $("export-photo").onclick = () => {
    if (window.TokyoCatAndroid) {
      window.TokyoCatAndroid.exportPhoto(photo.id, photo.image.split(",")[1]);
      $("export-photo").disabled = true;
    } else {
      const a = document.createElement("a");
      a.href = photo.image;
      a.download = "TOKYO-CAT-" + photo.id + ".jpg";
      a.click();
    }
  };
  $("delete-photo").onclick = () => {
    openModal(
      t("confirmDelete"),
      `<button id="delete-yes" class="danger">${esc(t("delete"))}</button> <button id="delete-no">${esc(t("cancel"))}</button>`,
      "delete",
    );
    $("delete-no").onclick = () => showPhoto(photo);
    $("delete-yes").onclick = async () => {
      try {
        await removePhoto(photo.id);
        toast(t("deleted"));
        showAlbum("photos");
      } catch {
        toast(t("saveError"));
      }
    };
  };
}
window.onPhotoExport = (id, ok) => {
  toast(t(ok ? "exported" : "exportError"));
  if ($("export-photo")) $("export-photo").disabled = false;
};
function enterCamera() {
  firstPerson = false;
  pitch = -0.2;
  seated = false;
  setMode("photo");
  renderText();
}
async function capture() {
  if (photoBusy || !tilesReady) return;
  photoBusy = true;
  $("shutter").disabled = true;
  try {
    await new Promise((resolve) => {
      const off = viewer.scene.postRender.addEventListener(() => {
        off();
        resolve();
      });
      viewer.scene.requestRender();
    });
    const src = viewer.canvas,
      canvas = document.createElement("canvas");
    const scale = Math.min(1, 1920 / src.width);
    canvas.width = Math.round(src.width * scale);
    canvas.height = Math.round(src.height * scale);
    const ctx = canvas.getContext("2d");
    ctx.drawImage(src, 0, 0, canvas.width, canvas.height);
    const h = Math.max(30, canvas.height * 0.05);
    ctx.fillStyle = "#112b27cc";
    ctx.fillRect(0, canvas.height - h, canvas.width, h);
    ctx.fillStyle = "#ecf2dd";
    ctx.font = Math.round(h * 0.34) + "px sans-serif";
    ctx.fillText(
      "TOKYO-CAT  /  " +
        local(region.name) +
        "  ·  PLATEAU / Mapterhorn / 国土地理院 (GSI)",
      18,
      canvas.height - h * 0.38,
    );
    await addPhoto({
      id: crypto.randomUUID(),
      time: Date.now(),
      area: state.area,
      breed: state.breed,
      lon: p.lon,
      lat: p.lat,
      image: canvas.toDataURL("image/jpeg", 0.91),
    });
    toast(t("saved"));
  } catch (e) {
    console.error(e);
    toast(t("saveError"));
  } finally {
    photoBusy = false;
    $("shutter").disabled = false;
  }
}
function showSettings() {
  openModal(
    t("settings"),
    `<div class="row"><div><strong>${esc(t("language"))}</strong></div><button id="settings-language">${state.lang === "ja" ? "English" : "日本語"}</button></div><div class="row"><strong>${esc(t("quality"))}</strong><button id="quality">${esc(t(state.quality))}</button></div><div class="row"><strong>${esc(t("choose"))}</strong><button id="settings-cats">↗</button></div><p>${esc(t("tutorial"))}</p><div class="row"><button id="reset-view">${esc(t("resetView"))}</button><button id="return-start">${esc(t("returnStart"))}</button></div><button id="settings-about">${esc(t("about"))}</button>`,
    "settings",
  );
  $("settings-language").onclick = () => {
    toggleLanguage();
    showSettings();
  };
  $("quality").onclick = () => {
    state.quality = state.quality === "balanced" ? "high" : "balanced";
    viewer.resolutionScale = state.quality === "high" ? 1 : 0.75;
    if (tileset)
      tileset.maximumScreenSpaceError = state.quality === "high" ? 4 : 12;
    save();
    showSettings();
  };
  $("settings-cats").onclick = showCats;
  $("reset-view").onclick = () => {
    yaw = p.heading;
    pitch = -0.24;
    closeModal();
  };
  $("return-start").onclick = () => {
    resetStart();
    closeModal();
  };
  $("settings-about").onclick = showCredits;
}
function showCredits() {
  openModal(
    t("about"),
    `<p class="notice">${esc(t("catNote"))}</p><p>${esc(t("dataNote"))}</p><p>${esc(t("tourNote"))}</p><p>3D: <a href="https://www.mlit.go.jp/plateau/">Project PLATEAU</a> / <a href="https://www.mlit.go.jp/plateau/site-policy/">${state.lang === "ja" ? "利用規約" : "Data policy"}</a> / <a href="https://3dview.tokyo-digitaltwin.metro.tokyo.lg.jp/">Tokyo Digital Twin</a></p><p>${state.lang === "ja" ? "使用データ：東京都（千代田区・新宿区・渋谷区）／台東区、2025年度建築物モデル。ゲーム画面として合成・表示を加工。" : "Data: Tokyo Metropolitan Government (Chiyoda, Shinjuku, Shibuya) and Taito City, FY2025 buildings. Composited and styled for gameplay."}</p><p>Terrain: PLATEAU | Mapterhorn | 国土地理院<br><a href="https://docs.plateauview.mlit.go.jp/datasets/terrain/">PLATEAU Terrain</a></p><p>Imagery: <a href="https://maps.gsi.go.jp/development/ichiran.html">国土地理院 / GSI</a></p><p>Renderer: CesiumJS 1.127.0 — Apache-2.0<br><a href="https://github.com/CesiumGS/cesium/blob/1.127/LICENSE.md">Cesium license</a></p><p>${esc(t("breedNote"))}<br><a href="${catalog.breedSource}">Anicom 2026</a></p><p>${state.lang === "ja" ? "猫モデル制作の参考指定動画（映像自体は同梱していません）" : "User-designated cat reference (video not included)"}<br><a href="https://www.youtube.com/watch?v=Jxv0e1VXSR0">ネコの生態【サクっと解説】</a></p><p>${state.lang === "ja" ? "猫の形と動きの参考（素材自体は同梱していません）" : "Cat anatomy and motion references (reference media not bundled)"}<br><a href="https://www.nga.gov/artworks/220472-plate-number-720-cat-galloping">Eadweard Muybridge / NGA — Public domain</a><br><a href="https://commons.wikimedia.org/wiki/File:Felis_catus-cat_on_snow.jpg">Von.grzanka — CC BY-SA 3.0</a><br><a href="https://github.com/Mesh2Motion/mesh2motion-app">Mesh2Motion — CC0 art and animations</a></p><p>TOKYO-CAT 0.2.0 · Development build</p>`,
    "credits",
  );
}
function toggleLanguage() {
  state.lang = state.lang === "ja" ? "en" : "ja";
  save();
  renderText();
  for (let i = 0; i < markers.length; i++)
    markers[i].label.text = local(
      catalog.places.filter((s) => s.area === state.area)[i].name,
    );
  if (lastError) status(lastError, true);
  else updateReady();
}
$("language").onclick = toggleLanguage;
$("start").onclick = start;
$("choose-cat").onclick = showCats;
$("settings").onclick = showSettings;
$("close-modal").onclick = closeModal;
$("modal").querySelector(".scrim").onclick = closeModal;
$("home-album").onclick = () => showAlbum();
$("open-album").onclick = () => showAlbum();
$("open-map").onclick = showMap;
$("home-button").onclick = () => {
  save();
  setMode("home");
};
$("greet").onclick = greet;
$("run").onclick = () => {
  running = !running;
  $("run").classList.toggle("active", running);
  renderText();
};
$("perspective").onclick = () => {
  firstPerson = !firstPerson;
  renderText();
};
$("camera").onclick = enterCamera;
$("exit-camera").onclick = () => {
  seated = false;
  setMode("play");
  renderText();
};
$("shutter").onclick = capture;
$("pose").onclick = () => {
  seated = !seated;
  renderText();
};
$("photo-distance").oninput = (e) => (photoRange = Number(e.target.value));
$("about-data").onclick = showCredits;
$("retry").onclick = async () => {
  if (!viewer) {
    await setup();
    return;
  }
  if (!terrainReady) await loadTerrain();
  await loadDistrict();
};
let stickId = null,
  lookId = null,
  lookX = 0,
  lookY = 0;
function stick(e) {
  const r = $("joystick").getBoundingClientRect(),
    dx = (e.clientX - r.left - r.width / 2) / (r.width * 0.38),
    dy = (e.clientY - r.top - r.height / 2) / (r.height * 0.38),
    mag = Math.max(1, Math.hypot(dx, dy));
  input = { x: dx / mag, y: dy / mag };
  $("stick").style.transform =
    `translate(${input.x * r.width * 0.3}px,${input.y * r.height * 0.3}px)`;
}
$("joystick").onpointerdown = (e) => {
  stickId = e.pointerId;
  $("joystick").setPointerCapture(e.pointerId);
  stick(e);
};
$("joystick").onpointermove = (e) => {
  if (e.pointerId === stickId) stick(e);
};
function releaseStick(e) {
  if (e.pointerId === stickId) {
    stickId = null;
    input = { x: 0, y: 0 };
    $("stick").style.transform = "";
  }
}
$("joystick").onpointerup = releaseStick;
$("joystick").onpointercancel = releaseStick;
$("world").addEventListener("pointerdown", (e) => {
  if (mode === "home" || modal) return;
  lookId = e.pointerId;
  lookX = e.clientX;
  lookY = e.clientY;
  $("world").setPointerCapture(lookId);
});
$("world").addEventListener("pointermove", (e) => {
  if (e.pointerId !== lookId) return;
  yaw -= (e.clientX - lookX) * 0.006;
  pitch = clamp(pitch + (e.clientY - lookY) * 0.004, -1.1, 0.12);
  lookX = e.clientX;
  lookY = e.clientY;
});
for (const type of ["pointerup", "pointercancel"])
  $("world").addEventListener(type, () => (lookId = null));
const keys = new Set();
document.addEventListener("keydown", (e) => {
  if (modal) return;
  keys.add(e.code);
  input.x = (keys.has("KeyD") ? 1 : 0) - (keys.has("KeyA") ? 1 : 0);
  input.y = (keys.has("KeyS") ? 1 : 0) - (keys.has("KeyW") ? 1 : 0);
  if (e.code === "KeyE") greet();
  if (e.code === "Escape") window.handleBack();
});
document.addEventListener("keyup", (e) => {
  keys.delete(e.code);
  input.x = (keys.has("KeyD") ? 1 : 0) - (keys.has("KeyA") ? 1 : 0);
  input.y = (keys.has("KeyS") ? 1 : 0) - (keys.has("KeyW") ? 1 : 0);
});
window.pauseGame = () => {
  input = { x: 0, y: 0 };
  keys.clear();
  save();
};
window.handleBack = () => {
  if (modal) closeModal();
  else if (mode === "photo") {
    seated = false;
    setMode("play");
  } else if (mode === "play") {
    save();
    setMode("home");
  } else showSettings();
};
document.addEventListener("visibilitychange", () => {
  paused = document.hidden;
  if (paused) window.pauseGame();
});
window.addEventListener("blur", () => {
  input = { x: 0, y: 0 };
  keys.clear();
});
// Read-only diagnostics for Android UI tests; no commands or elevated capabilities.
window.tokyoCatStatus = () => ({
  area: state.area,
  breed: state.breed,
  lang: state.lang,
  mode,
  modal,
  position: { ...p },
  camera: { yaw, pitch, range: mode === "photo" ? photoRange : 4.2 },
  visited: Object.keys(state.visited),
  friends: [...state.friends],
  terrainReady,
  tilesReady,
  modelsReady,
  npcAnimation: npcs.map((n) => n.model?._walkSpeed || 0),
  stats: { ...cityStats },
  error: lastError,
});
renderText();
status("loading");
$("start").disabled = true;
await setup();
