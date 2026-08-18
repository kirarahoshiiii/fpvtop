function initialState() {
  return {
    source: "offline",
    ident: {},
    cycle: 0, cpuload: 0, i2c: 0, armed: false, arming: [],
    sensors: { gyro: false, acc: false, baro: false, mag: false, gps: false, range: false },
    gyro: [0, 0, 0], acc: [0, 0, 1], att: [0, 0, 0],
    vbat: 0, cells: 0, amps: 0, mah: 0, capacity: 0,
    rssi: 0, channels: [], motors: [], telem: [],
    started: performance.now(),
  };
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
    Object.assign(this.state, initialState(), { source: "live", started: performance.now() });
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
    Object.assign(this.state, initialState());
    this.onChange();
  }
}
