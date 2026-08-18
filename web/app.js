const state = initialState();
const demo = new DemoSource();
let serial = null;
let updateMs = 100;
let charW = 8;
let graphs = {};
let panels = {};

function el(id) {
  return document.getElementById(id);
}

function measureChar() {
  const probe = document.createElement("span");
  probe.style.cssText = "position:absolute;visibility:hidden;white-space:pre";
  probe.className = "mono";
  probe.textContent = "⣿".repeat(20);
  document.body.appendChild(probe);
  charW = probe.getBoundingClientRect().width / 20 || 8;
  probe.remove();
}

function cols(element, pad = 0) {
  return Math.max(10, Math.floor(element.clientWidth / charW) - pad);
}

function rebuild() {
  measureChar();
  panels = {
    big: el("gyro-big"), info: el("gyro-info"),
    power: el("power-pre"), rc: el("rc-pre"), motors: el("motors-pre"),
  };
  const bigC = cols(panels.big, 1);
  const bigR = Math.max(4, Math.floor(panels.big.clientHeight / 17) - 1);
  const infoG = 22;
  const powC = cols(panels.power, 1);
  const rcC = cols(panels.rc, 1);
  const motC = cols(panels.motors, 1);
  graphs = {
    big: new Graph(bigC, bigR, GRADIENTS.cpu),
    gx: new Graph(infoG, 1, GRADIENTS.cpu),
    gy: new Graph(infoG, 1, GRADIENTS.cpu),
    gz: new Graph(infoG, 1, GRADIENTS.cpu),
    loop: new Graph(infoG, 1, GRADIENTS.temp),
    cpuMeter: new MeterDraw(infoG, GRADIENTS.cpu),
    volt: new Graph(powC - 7, 1, GRADIENTS.available, false, true),
    amp: new Graph(powC - 7, 1, GRADIENTS.used, false, true),
    usedMeter: new MeterDraw(powC - 7, GRADIENTS.used),
    thr: new Graph(rcC, 4, GRADIENTS.download),
    rssi: new Graph(rcC, 4, GRADIENTS.upload, true),
    motMeter: new MeterDraw(Math.max(5, motC - 30), GRADIENTS.process),
    motC, powC, rcC,
  };
}

function fg(text) {
  return span(THEME.main_fg, text);
}

function dim(text) {
  return span(THEME.graph_text, text);
}

function drawGyro() {
  graphs.big.add(Math.min(100, Math.hypot(...state.gyro) / 5));
  panels.big.innerHTML = graphs.big.html();
  const lines = [];
  const axes = [["GYR X", graphs.gx], ["GYR Y", graphs.gy], ["GYR Z", graphs.gz]];
  axes.forEach(([label, graph], i) => {
    graph.add(Math.min(100, Math.abs(state.gyro[i]) / 3));
    lines.push(dim(label + " ") + graph.html() + fg(padLeft(state.gyro[i].toFixed(0), 7)) + dim("°/s"));
  });
  graphs.loop.add(Math.min(100, state.cycle / 10));
  lines.push(dim("LOOP  ") + graphs.loop.html() + fg(padLeft(state.cycle, 6)) + dim("µs"));
  lines.push(dim("CPU   ") + graphs.cpuMeter.html(state.cpuload) + fg(padLeft(state.cpuload, 6)) + dim("%"));
  const [r, p, y] = state.att;
  lines.push(dim("ATT   ") + fg("R" + padLeft(r.toFixed(1), 7) + " P" + padLeft(p.toFixed(1), 7) + " Y" + padLeft(y.toFixed(0), 5)));
  lines.push(dim("I2C   ") + span(state.i2c ? THEME.hi_fg : THEME.main_fg, state.i2c + " errors"));
  panels.info.innerHTML = lines.join("\n");
  el("gyro-name").textContent = state.ident.name || state.ident.board || "flight controller";
  const badge = el("source-badge");
  badge.textContent = state.source;
  badge.className = "chip badge " + state.source;
}

function drawPower() {
  const c = graphs.powC;
  const cells = state.cells || (state.vbat > 1 ? Math.round(state.vbat / 3.9) : 0);
  const cell = cells ? state.vbat / cells : 0;
  const voltPct = cells ? Math.max(0, Math.min(100, ((cell - 3.2) / 1.0) * 100)) : 0;
  const ampPct = Math.min(100, (state.amps * 100) / 40);
  const usedPct = state.capacity ? Math.min(100, (state.mah * 100) / state.capacity) : 0;
  graphs.volt.add(voltPct);
  graphs.amp.add(ampPct);
  const pct = (v) => fg(padLeft(Math.round(v), 4)) + dim("%");
  const lines = [
    divLabel("Voltage", state.vbat.toFixed(2) + " V", c),
    " " + graphs.volt.html() + pct(voltPct),
    divLabel("Cell", cells + "S  " + cell.toFixed(2) + " V", c),
    divLabel("Current", state.amps.toFixed(1) + " A", c),
    " " + graphs.amp.html() + pct(ampPct),
    divLabel("Used", state.mah + " mAh", c),
    " " + graphs.usedMeter.html(usedPct) + pct(usedPct),
    divLabel("Power", (state.vbat * state.amps).toFixed(1) + " W", c),
  ];
  panels.power.innerHTML = lines.join("\n");
}

function drawRc() {
  const thr = state.channels[2] || 1000;
  const thrPct = Math.max(0, Math.min(100, (thr - 1000) / 10));
  const rssi = Math.max(0, Math.min(100, state.rssi));
  graphs.thr.add(thrPct);
  graphs.rssi.add(rssi);
  const c = graphs.rcC;
  const top = dim("↑ thr " + Math.round(thrPct) + "% " + thr + "µs");
  const bottom = dim("↓ rssi " + rssi + "%") + fg(padLeft("ch " + state.channels.length, c - 11 - String(rssi).length));
  panels.rc.innerHTML = top + "\n" + graphs.thr.html() + "\n" + graphs.rssi.html() + "\n" + bottom;
}

function drawMotors() {
  const c = graphs.motC;
  const lines = [span(THEME.title, padRight(" MOT  OUT% " + " ".repeat(Math.max(5, c - 30) - 1) + padLeft("RPM", 7) + padLeft("T", 6) + padLeft("A", 7), c))];
  state.motors.slice(0, 8).forEach((value, i) => {
    const pctV = Math.max(0, Math.min(100, (value - 1000) / 10));
    const t = state.telem[i] || {};
    lines.push(
      fg(" M" + (i + 1) + " " + padLeft(Math.round(pctV), 4) + "% ") +
      graphs.motMeter.html(pctV) +
      fg(padLeft(t.rpm != null ? t.rpm : "-", 7) +
         padLeft(t.temp != null ? t.temp + "°" : "-", 6) +
         padLeft(t.amps != null ? t.amps.toFixed(1) : "-", 7))
    );
  });
  lines.push("");
  const sensors = ["gyro", "acc", "baro", "mag", "gps"].map((name) => {
    const ok = state.sensors[name];
    return span(ok ? THEME.proc_misc : THEME.inactive_fg, (ok ? "●" : "○") + " " + name);
  });
  lines.push(" " + sensors.join("  "));
  if (state.armed) {
    lines.push(" " + span(THEME.hi_fg, "<b>ARMED</b>"));
  } else if (state.arming.length) {
    lines.push(" " + dim("DISARM ") + span(THEME.hi_fg, state.arming.join(" ")));
  } else {
    lines.push(" " + span(THEME.proc_misc, "ready to arm"));
  }
  panels.motors.innerHTML = lines.join("\n");
}

function frame() {
  if (state.source === "demo") demo.tick(state);
  el("clock").textContent = new Date().toTimeString().slice(0, 8);
  const up = Math.floor((performance.now() - state.started) / 1000);
  el("uptime").textContent =
    "up " + Math.floor(up / 3600) + ":" + String(Math.floor(up / 60) % 60).padStart(2, "0") + ":" + String(up % 60).padStart(2, "0");
  el("fcid").textContent = [state.ident.variant, state.ident.version].filter(Boolean).join(" ");
  drawGyro();
  drawPower();
  drawRc();
  drawMotors();
}

let timer = null;

function schedule() {
  if (timer) clearInterval(timer);
  timer = setInterval(frame, updateMs);
  el("rate").textContent = updateMs + "ms";
}

function setup() {
  rebuild();
  schedule();
  frame();
  el("rate-minus").onclick = () => { updateMs = Math.min(2000, updateMs + 100); schedule(); };
  el("rate-plus").onclick = () => { updateMs = Math.max(50, updateMs - 100); schedule(); };
  window.addEventListener("resize", () => { rebuild(); frame(); });
  const btn = el("connect");
  if (!("serial" in navigator)) {
    btn.disabled = true;
    btn.textContent = "web serial unsupported";
    return;
  }
  btn.onclick = async () => {
    if (serial && serial.running) {
      await serial.disconnect();
      btn.textContent = "connect board";
      return;
    }
    serial = new SerialSource(state, () => {
      btn.textContent = serial.running ? "disconnect" : "connect board";
    });
    try {
      await serial.connect();
    } catch (e) {
      state.source = "demo";
    }
  };
}

document.addEventListener("DOMContentLoaded", setup);
