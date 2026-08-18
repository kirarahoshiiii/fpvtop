const MSP = {
  API_VERSION: 1,
  FC_VARIANT: 2,
  FC_VERSION: 3,
  BOARD_INFO: 4,
  NAME: 10,
  STATUS: 101,
  RAW_IMU: 102,
  MOTOR: 104,
  RC: 105,
  ATTITUDE: 108,
  ANALOG: 110,
  BATTERY_STATE: 130,
  MOTOR_TELEMETRY: 139,
  STATUS_EX: 150,
};

const SENSOR_BITS = { gyro: 5, acc: 0, baro: 1, mag: 2, gps: 3, range: 4 };

const ARMING_DISABLE_FLAGS = [
  "NO_GYRO", "FAILSAFE", "RX_FAILSAFE", "NOT_DISARMED", "BOXFAILSAFE",
  "RUNAWAY", "CRASH", "THROTTLE", "ANGLE", "BOOT_GRACE", "NOPREARM",
  "LOAD", "CALIBRATING", "CLI", "CMS_MENU", "BST", "MSP", "PARALYZE",
  "GPS", "RESC", "RPMFILTER", "REBOOT_REQD", "DSHOT_BITBANG",
  "ACC_CALIB", "MOTOR_PROTO", "ARM_SWITCH",
];

function mspBuild(cmd, payload = new Uint8Array(0)) {
  const frame = new Uint8Array(6 + payload.length);
  frame.set([0x24, 0x4d, 0x3c, payload.length, cmd]);
  frame.set(payload, 5);
  let crc = 0;
  for (let i = 3; i < frame.length - 1; i++) crc ^= frame[i];
  frame[frame.length - 1] = crc;
  return frame;
}

class MspParser {
  constructor() {
    this.buf = [];
  }

  feed(chunk) {
    for (const b of chunk) this.buf.push(b);
    const frames = [];
    for (;;) {
      let start = -1;
      for (let i = 0; i + 1 < this.buf.length; i++) {
        if (this.buf[i] === 0x24 && this.buf[i + 1] === 0x4d) { start = i; break; }
      }
      if (start < 0) { this.buf.length = Math.min(this.buf.length, 1); break; }
      if (start > 0) this.buf.splice(0, start);
      if (this.buf.length < 5) break;
      const dir = this.buf[2];
      if (dir !== 0x3e && dir !== 0x21) { this.buf.splice(0, 2); continue; }
      const size = this.buf[3];
      if (this.buf.length < 6 + size) break;
      const cmd = this.buf[4];
      const payload = new Uint8Array(this.buf.slice(5, 5 + size));
      let crc = 0;
      for (let i = 3; i < 5 + size; i++) crc ^= this.buf[i];
      const ok = crc === this.buf[5 + size] && dir === 0x3e;
      this.buf.splice(0, 6 + size);
      if (ok) frames.push({ cmd, payload });
    }
    return frames;
  }
}

function dv(payload) {
  return new DataView(payload.buffer, payload.byteOffset, payload.byteLength);
}

function parseStatus(p) {
  const out = {};
  if (p.length < 11) return out;
  const d = dv(p);
  out.cycle = d.getUint16(0, true);
  out.i2c = d.getUint16(2, true);
  const sensors = d.getUint16(4, true);
  out.sensors = {};
  for (const name in SENSOR_BITS) out.sensors[name] = !!((sensors >> SENSOR_BITS[name]) & 1);
  out.armed = !!(d.getUint32(6, true) & 1);
  if (p.length >= 13) out.cpuload = d.getUint16(11, true);
  if (p.length >= 20) {
    const flags = d.getUint32(16, true);
    out.arming = ARMING_DISABLE_FLAGS.filter((_, bit) => (flags >> bit) & 1);
  }
  return out;
}

function parseRawImu(p) {
  if (p.length < 18) return {};
  const d = dv(p);
  const v = [];
  for (let i = 0; i < 9; i++) v.push(d.getInt16(i * 2, true));
  return { acc: v.slice(0, 3).map((x) => x / 512), gyro: v.slice(3, 6) };
}

function parseAttitude(p) {
  if (p.length < 6) return {};
  const d = dv(p);
  return { att: [d.getInt16(0, true) / 10, d.getInt16(2, true) / 10, d.getInt16(4, true)] };
}

function parseAnalog(p) {
  if (p.length < 7) return {};
  const d = dv(p);
  const out = {
    vbat: d.getUint8(0) / 10,
    mah: d.getUint16(1, true),
    rssi: Math.round((d.getUint16(3, true) * 100) / 1023),
    amps: d.getInt16(5, true) / 100,
  };
  if (p.length >= 9) out.vbat = d.getUint16(7, true) / 100;
  return out;
}

function parseBatteryState(p) {
  if (p.length < 8) return {};
  const d = dv(p);
  const out = {
    cells: d.getUint8(0),
    capacity: d.getUint16(1, true),
    vbat: d.getUint8(3) / 10,
    mah: d.getUint16(4, true),
    amps: d.getInt16(6, true) / 100,
  };
  if (p.length >= 11) out.vbat = d.getUint16(9, true) / 100;
  return out;
}

function parseMotor(p) {
  const d = dv(p);
  const motors = [];
  for (let i = 0; i + 1 < p.length; i += 2) {
    const v = d.getUint16(i, true);
    if (v > 0) motors.push(v);
  }
  return { motors };
}

function parseMotorTelemetry(p) {
  if (!p.length) return {};
  const d = dv(p);
  const count = d.getUint8(0);
  const telem = [];
  let off = 1;
  for (let i = 0; i < count && off + 13 <= p.length; i++, off += 13) {
    telem.push({
      rpm: d.getUint32(off, true),
      temp: d.getUint8(off + 6),
      amps: d.getUint16(off + 9, true) / 100,
    });
  }
  return { telem };
}

function parseRc(p) {
  const d = dv(p);
  const channels = [];
  for (let i = 0; i + 1 < p.length; i += 2) channels.push(d.getUint16(i, true));
  return { channels };
}

function cleanAscii(p) {
  let out = "";
  for (const b of p) if (b >= 32 && b < 127) out += String.fromCharCode(b);
  return out.trim();
}

const MSP_PARSERS = {
  [MSP.STATUS]: parseStatus,
  [MSP.STATUS_EX]: parseStatus,
  [MSP.RAW_IMU]: parseRawImu,
  [MSP.ATTITUDE]: parseAttitude,
  [MSP.ANALOG]: parseAnalog,
  [MSP.BATTERY_STATE]: parseBatteryState,
  [MSP.MOTOR]: parseMotor,
  [MSP.MOTOR_TELEMETRY]: parseMotorTelemetry,
  [MSP.RC]: parseRc,
};
