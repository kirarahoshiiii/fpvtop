const THEME = {
  main_bg: "#000000",
  main_fg: "#cccccc",
  title: "#eeeeee",
  hi_fg: "#b54040",
  inactive_fg: "#404040",
  graph_text: "#606060",
  meter_bg: "#404040",
  proc_misc: "#0de756",
  cpu_box: "#556d59",
  mem_box: "#6c6c4b",
  net_box: "#5c588d",
  proc_box: "#805252",
  div_line: "#303030",
};

const GRADIENT_STOPS = {
  cpu: ["#77ca9b", "#cbc06c", "#dc4c4c"],
  temp: ["#4897d4", "#5474e8", "#ff40b6"],
  available: ["#4e3f0e", "#ffd77a", "#ffb814"],
  used: ["#592b26", "#d9626d", "#ff4769"],
  download: ["#291f75", "#4f43a3", "#b0a9de"],
  upload: ["#620665", "#7d4180", "#dcafde"],
  process: ["#80d0a3", "#dcd179", "#d45454"],
};

function hexRgb(hex) {
  return [1, 3, 5].map((i) => parseInt(hex.slice(i, i + 2), 16));
}

function mix(a, b, t) {
  return "rgb(" + a.map((v, i) => Math.round(v + (b[i] - v) * t)).join(",") + ")";
}

function buildGradient(stops) {
  const [start, mid, end] = stops.map(hexRgb);
  const out = [];
  for (let i = 0; i < 50; i++) out.push(mix(start, mid, i / 50));
  for (let i = 0; i <= 50; i++) out.push(mix(mid, end, i / 50));
  return out;
}

const GRADIENTS = {};
for (const name in GRADIENT_STOPS) GRADIENTS[name] = buildGradient(GRADIENT_STOPS[name]);
