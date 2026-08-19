const state = initialState();
let serial = null;
let updateMs = 100;
let charW = 8;
let lineH = 17;
let graphs = {};
let panels = {};

function el(id) {
  return document.getElementById(id);
}

function live() {
  return state.source === "live";
}

function measureChar() {
  const probe = document.createElement("span");
  probe.style.cssText = "position:absolute;visibility:hidden;white-space:pre";
  probe.className = "mono";
  probe.textContent = "⣿".repeat(20);
  document.body.appendChild(probe);
  const rect = probe.getBoundingClientRect();
  charW = rect.width / 20 || 8;
  lineH = rect.height || 17;
  probe.remove();
}

function cols(element, pad = 0) {
  return Math.max(10, Math.floor(element.clientWidth / charW) - pad);
}

function innerHeight(box) {
  const cs = getComputedStyle(box);
  return box.clientHeight - parseFloat(cs.paddingTop) - parseFloat(cs.paddingBottom);
}

function rebuild() {
  measureChar();
  panels = {
    big: el("cpu-big"), info: el("cpu-info"),
    power: el("power-pre"), rc: el("rc-pre"), motors: el("motors-pre"),
  };
  const bigC = cols(panels.big, 1);
  const bigR = Math.max(4, Math.floor(panels.big.parentElement.clientHeight / lineH));
  const infoG = 22;
  const powC = cols(panels.power, 1);
  const rcC = cols(panels.rc, 1);
  const motC = cols(panels.motors, 1);
  const rcLines = Math.floor(innerHeight(panels.rc.parentElement) / lineH);
  const rcR = Math.max(2, Math.floor((rcLines - 2) / 2));
  graphs = {
    big: new Graph(bigC, bigR, GRADIENTS.cpu),
    core: new Graph(infoG, 1, GRADIENTS.cpu),
    loop: new Graph(infoG, 1, GRADIENTS.temp),
    volt: new Graph(powC - 7, 1, GRADIENTS.available, false, true),
    amp: new Graph(powC - 7, 1, GRADIENTS.used, false, true),
    usedMeter: new MeterDraw(powC - 7, GRADIENTS.used),
    thr: new Graph(rcC, rcR, GRADIENTS.download),
    rssi: new Graph(rcC, rcR, GRADIENTS.upload, true),
    motMeter: new MeterDraw(Math.max(5, motC - 30), GRADIENTS.process),
    motC, powC, rcC,
    motLines: Math.floor(innerHeight(panels.motors.parentElement) / lineH),
  };
  const histR = graphs.motLines - 11;
  graphs.motHist = histR >= 3 ? new Graph(motC, histR, GRADIENTS.process) : null;
}

function fg(text) {
  return span(THEME.main_fg, text);
}

function dim(text) {
  return span(THEME.graph_text, text);
}

const loadHistory = [];

function loadAvg(now, load) {
  loadHistory.push([now, load]);
  while (loadHistory.length && now - loadHistory[0][0] > 900000) loadHistory.shift();
  return [60000, 300000, 900000].map((span) => {
    const samples = loadHistory.filter(([ts]) => now - ts <= span).map(([, v]) => v);
    return samples.length ? Math.round(samples.reduce((a, v) => a + v, 0) / samples.length) : 0;
  });
}

function drawCpu() {
  const load = Math.max(0, Math.min(100, Math.round(state.cpuload)));
  graphs.big.add(load);
  panels.big.innerHTML = graphs.big.html();
  const lines = [];
  graphs.core.add(load);
  lines.push(dim("C0    ") + graphs.core.html() + fg(padLeft(load, 6)) + dim("%"));
  graphs.loop.add(Math.min(100, state.cycle / 10));
  lines.push(dim("LOOP  ") + graphs.loop.html() + fg(padLeft(state.cycle, 6)) + dim("µs"));
  const avgs = loadAvg(performance.now(), load);
  lines.push("");
  lines.push(span(THEME.title, "<b>Load AVG:</b>") + fg(" " + avgs.map((v) => padLeft(v + "%", 4)).join("")));
  panels.info.innerHTML = lines.join("\n");
  el("cpu-freq").textContent = state.cycle ? (1000 / state.cycle).toFixed(1) + " kHz" : "";
  el("cpu-name").textContent = live() ? (state.ident.name || state.ident.board || "flight controller") : "no board";
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
  const rssi = Math.max(0, Math.min(100, Math.round(state.rssi)));
  graphs.thr.add(thrPct);
  graphs.rssi.add(rssi);
  const c = graphs.rcC;
  const left = "↓ rssi " + rssi + "%";
  const right = "ch " + (state.channels.length || "-");
  const gap = Math.max(1, c - left.length - right.length);
  const top = dim("↑ thr " + Math.round(thrPct) + "% " + thr + "µs");
  const bottom = dim(left) + " ".repeat(gap) + fg(right);
  panels.rc.innerHTML = top + "\n" + graphs.thr.html() + "\n" + graphs.rssi.html() + "\n" + bottom;
}

function drawMotors() {
  const c = graphs.motC;
  const mw = Math.max(5, c - 30);
  const lines = [span(THEME.title, padRight(" MOT  OUT% " + " ".repeat(mw - 1) + padLeft("RPM", 7) + padLeft("T", 6) + padLeft("A", 7), c))];
  const motors = state.motors.length ? state.motors : Array(4).fill(1000);
  motors.slice(0, 8).forEach((value, i) => {
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
    const ok = live() && state.sensors[name];
    return span(ok ? THEME.proc_misc : THEME.inactive_fg, (ok ? "●" : "○") + " " + name);
  });
  lines.push(" " + sensors.join("  "));
  if (!live()) {
    lines.push(" " + dim("no board connected"));
  } else if (state.armed) {
    lines.push(" " + span(THEME.hi_fg, "<b>ARMED</b>"));
  } else if (state.arming.length) {
    lines.push(" " + dim("DISARM ") + span(THEME.hi_fg, state.arming.join(" ")));
  } else {
    lines.push(" " + span(THEME.proc_misc, "ready to arm"));
  }
  if (graphs.motHist) {
    const avg = motors.reduce((a, v) => a + Math.max(0, Math.min(100, (v - 1000) / 10)), 0) / motors.length;
    graphs.motHist.add(avg);
    if (lines.length + 2 + graphs.motHist.height <= graphs.motLines) {
      lines.push("", dim(" ↑ avg output"));
      lines.push(graphs.motHist.html());
    }
  }
  panels.motors.innerHTML = lines.join("\n");
}

function frame() {
  el("clock").textContent = new Date().toTimeString().slice(0, 8);
  if (live()) {
    const up = Math.floor((performance.now() - state.started) / 1000);
    el("uptime").textContent =
      "up " + Math.floor(up / 3600) + ":" + String(Math.floor(up / 60) % 60).padStart(2, "0") + ":" + String(up % 60).padStart(2, "0");
  } else {
    el("uptime").textContent = "";
  }
  el("fcid").textContent = [state.ident.variant, state.ident.version].filter(Boolean).join(" ");
  el("offline-hint").hidden = live();
  drawCpu();
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

let resizeTimer = null;

function relayout() {
  if (resizeTimer) clearTimeout(resizeTimer);
  resizeTimer = setTimeout(() => { rebuild(); frame(); }, 80);
}

function setup() {
  rebuild();
  schedule();
  frame();
  el("rate-minus").onclick = () => { updateMs = Math.min(2000, updateMs + 100); schedule(); };
  el("rate-plus").onclick = () => { updateMs = Math.max(50, updateMs - 100); schedule(); };
  window.addEventListener("resize", relayout);
  if (document.fonts && document.fonts.ready) document.fonts.ready.then(relayout);
  if (typeof ResizeObserver !== "undefined") {
    const ro = new ResizeObserver(relayout);
    ro.observe(document.querySelector("main"));
  }
  const btn = el("connect");
  if (!("serial" in navigator)) {
    btn.disabled = true;
    btn.textContent = "web serial unsupported";
    el("offline-hint").textContent = "this browser has no Web Serial — use a chromium browser or Firefox 151+ on desktop";
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
      relayout();
      frame();
    });
    try {
      await serial.connect();
    } catch (e) {
      Object.assign(state, initialState());
    }
    frame();
  };
}

document.addEventListener("DOMContentLoaded", setup);
