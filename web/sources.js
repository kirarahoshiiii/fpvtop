function initialState() {
  return {
    source: "demo",
    ident: { variant: "DEMO", version: "4.5.2", board: "SIML", name: "bench sim", api: "1.46" },
    cycle: 0, cpuload: 0, i2c: 0, armed: false, arming: [],
    sensors: { gyro: true, acc: true, baro: true, mag: false, gps: false, range: false },
    gyro: [0, 0, 0], acc: [0, 0, 1], att: [0, 0, 0],
    vbat: 0, cells: 0, amps: 0, mah: 0, capacity: 0,
    rssi: 0, channels: [], motors: [], telem: [],
    started: performance.now(),
  };
}

class DemoSource {
  constructor() {
    this.t0 = performance.now();
    this.mah = 0;
    this.sag = 0;
    this.lastTick = this.t0;
  }

  tick(state) {
    const now = performance.now();
    const dt = (now - this.lastTick) / 1000;
    this.lastTick = now;
    const t = (now - this.t0) / 1000;
    const rnd = (a) => (Math.random() * 2 - 1) * a;
    let throttle = 0.32 + 0.22 * Math.sin(t * 0.31) + 0.08 * Math.sin(t * 1.7) + rnd(0.02);
    throttle = Math.max(0.05, Math.min(0.95, throttle));
    const stick = Math.pow(Math.sin(t * 0.13), 3);
    state.gyro = [
      180 * stick * Math.sin(t * 2.4) + rnd(9),
      120 * stick * Math.sin(t * 1.9 + 1.2) + rnd(9),
      60 * Math.sin(t * 0.7) * Math.abs(stick) + rnd(6),
    ];
    state.att = [22 * Math.sin(t * 0.5), 14 * Math.sin(t * 0.36 + 0.8), ((t * 9) % 360) - 180];
    state.motors = [];
    for (let i = 0; i < 4; i++) {
      const wob = 0.05 * Math.sin(t * (2.1 + i * 0.33) + i);
      const out = throttle + wob + 0.05 * stick * (i % 2 ? 1 : -1);
      state.motors.push(Math.round(1000 + Math.max(0.03, Math.min(1, out)) * 1000));
    }
    const amps = 1.6 + throttle * 34 + rnd(0.6);
    this.mah += (amps * dt) / 3.6;
    this.sag += (throttle * 0.9 - this.sag) * 0.1;
    const vbat = 16.8 - (t / 90) * 0.35 - this.sag - Math.random() * 0.02;
    state.telem = state.motors.map((m) => ({
      rpm: Math.round(((m - 1000) / 1000) * 27000 + rnd(300)),
      temp: Math.round(24 + ((m - 1000) / 1000) * 38),
      amps: +(amps / 4).toFixed(1),
    }));
    state.channels = [
      1500 + Math.round(220 * stick),
      1500 + Math.round(160 * Math.sin(t * 0.4)),
      Math.round(1000 + throttle * 1000),
      1500 + Math.round(90 * Math.sin(t * 0.9)),
      Math.floor(t / 8) % 2 ? 2000 : 1000,
      1500, 1000, 1000,
    ];
    Object.assign(state, {
      source: "demo",
      cycle: Math.round(125 + rnd(4) + Math.random() * 8),
      cpuload: Math.round(18 + throttle * 40 + rnd(2)),
      i2c: 0,
      armed: true,
      arming: [],
      vbat: +vbat.toFixed(2),
      cells: 4,
      amps: +amps.toFixed(1),
      mah: Math.round(this.mah),
      capacity: 1300,
      rssi: Math.round(88 + 10 * Math.sin(t * 0.21) + rnd(2)),
      ident: { variant: "DEMO", version: "4.5.2", board: "SIML", name: "bench sim", api: "1.46" },
    });
  }
}

class SerialSource {
  constructor(state, onChange) {
    this.state = state;
    this.onChange = onChange;
    this.port = null;
    this.writer = null;
    this.parser = new MspParser();
    this.timers = { medium: 0, slow: 0 };
    this.running = false;
  }

  async connect() {
    this.port = await navigator.serial.requestPort();
    await this.port.open({ baudRate: 115200 });
    this.writer = this.port.writable.getWriter();
    this.running = true;
    this.state.source = "live";
    this.state.ident = {};
    this.readLoop();
    this.pollLoop();
    for (const cmd of [MSP.API_VERSION, MSP.FC_VARIANT, MSP.FC_VERSION, MSP.BOARD_INFO, MSP.NAME]) {
      await this.send(cmd);
      await new Promise((r) => setTimeout(r, 50));
    }
    this.onChange();
  }

  async send(cmd) {
    if (!this.writer) return;
    try {
      await this.writer.write(mspBuild(cmd));
    } catch (e) {
      this.disconnect();
    }
  }

  async readLoop() {
    while (this.running && this.port.readable) {
      const reader = this.port.readable.getReader();
      try {
        for (;;) {
          const { value, done } = await reader.read();
          if (done) break;
          for (const frame of this.parser.feed(value)) this.handle(frame);
        }
      } catch (e) {
        break;
      } finally {
        reader.releaseLock();
      }
    }
    if (this.running) this.disconnect();
  }

  handle(frame) {
    const parser = MSP_PARSERS[frame.cmd];
    if (parser) {
      Object.assign(this.state, parser(frame.payload));
      return;
    }
    const p = frame.payload;
    if (frame.cmd === MSP.API_VERSION && p.length >= 3) this.state.ident.api = p[1] + "." + p[2];
    else if (frame.cmd === MSP.FC_VARIANT) this.state.ident.variant = cleanAscii(p);
    else if (frame.cmd === MSP.FC_VERSION && p.length >= 3) this.state.ident.version = p[0] + "." + p[1] + "." + p[2];
    else if (frame.cmd === MSP.BOARD_INFO && p.length >= 4) this.state.ident.board = cleanAscii(p.slice(0, 4));
    else if (frame.cmd === MSP.NAME) this.state.ident.name = cleanAscii(p);
  }

  async pollLoop() {
    while (this.running) {
      const now = performance.now();
      for (const cmd of [MSP.RAW_IMU, MSP.ATTITUDE, MSP.MOTOR, MSP.RC]) await this.send(cmd);
      if (now - this.timers.medium > 250) {
        this.timers.medium = now;
        await this.send(MSP.MOTOR_TELEMETRY);
      }
      if (now - this.timers.slow > 500) {
        this.timers.slow = now;
        await this.send(MSP.STATUS_EX);
        await this.send(MSP.ANALOG);
        await this.send(MSP.BATTERY_STATE);
      }
      await new Promise((r) => setTimeout(r, 50));
    }
  }

  async disconnect() {
    this.running = false;
    try { this.writer && this.writer.releaseLock(); } catch (e) {}
    try { this.port && (await this.port.close()); } catch (e) {}
    this.writer = null;
    this.port = null;
    this.state.source = "demo";
    this.onChange();
  }
}
