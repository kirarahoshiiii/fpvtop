import struct
import time

MSP_API_VERSION = 1
MSP_FC_VARIANT = 2
MSP_FC_VERSION = 3
MSP_BOARD_INFO = 4
MSP_NAME = 10
MSP_STATUS = 101
MSP_RAW_IMU = 102
MSP_MOTOR = 104
MSP_RC = 105
MSP_ATTITUDE = 108
MSP_ANALOG = 110
MSP_BATTERY_STATE = 130
MSP_MOTOR_TELEMETRY = 139
MSP_STATUS_EX = 150
MSP_UID = 160

BAUD_RATE = 115200

SENSOR_BITS = {"gyro": 5, "acc": 0, "baro": 1, "mag": 2, "gps": 3, "range": 4}

ARMING_DISABLE_FLAGS = [
    "NO_GYRO", "FAILSAFE", "RX_FAILSAFE", "NOT_DISARMED", "BOXFAILSAFE",
    "RUNAWAY", "CRASH", "THROTTLE", "ANGLE", "BOOT_GRACE", "NOPREARM",
    "LOAD", "CALIBRATING", "CLI", "CMS_MENU", "BST", "MSP", "PARALYZE",
    "GPS", "RESC", "RPMFILTER", "REBOOT_REQD", "DSHOT_BITBANG",
    "ACC_CALIB", "MOTOR_PROTO", "ARM_SWITCH",
]


def build(cmd, payload=b""):
    frame = bytes([len(payload), cmd]) + payload
    crc = 0
    for byte in frame:
        crc ^= byte
    return b"$M<" + frame + bytes([crc])


class Parser:
    def __init__(self):
        self.buf = bytearray()

    def feed(self, data):
        self.buf.extend(data)
        frames = []
        while True:
            start = self.buf.find(b"$M")
            if start < 0:
                self.buf.clear()
                break
            if start > 0:
                del self.buf[:start]
            if len(self.buf) < 5:
                break
            direction = self.buf[2]
            if direction not in (0x3E, 0x21):
                del self.buf[:2]
                continue
            size = self.buf[3]
            total = 6 + size
            if len(self.buf) < total:
                break
            cmd = self.buf[4]
            payload = bytes(self.buf[5:5 + size])
            crc = 0
            for byte in self.buf[3:5 + size]:
                crc ^= byte
            ok = crc == self.buf[5 + size] and direction == 0x3E
            del self.buf[:total]
            frames.append((ok, cmd, payload))
        return frames


class Link:
    def __init__(self, port):
        import serial
        self.ser = serial.Serial()
        self.ser.port = port
        self.ser.baudrate = BAUD_RATE
        self.ser.timeout = 0.05
        self.ser.write_timeout = 0.5
        try:
            self.ser.exclusive = True
        except (AttributeError, ValueError):
            pass
        self.ser.open()
        time.sleep(0.1)
        self.ser.reset_input_buffer()
        self.parser = Parser()

    def close(self):
        try:
            self.ser.close()
        except Exception:
            pass

    def request(self, cmd, payload=b"", timeout=0.35):
        self.ser.write(build(cmd, payload))
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            chunk = self.ser.read(256)
            if not chunk:
                continue
            for ok, rcmd, rpayload in self.parser.feed(chunk):
                if rcmd == cmd:
                    return rpayload if ok else None
        return None


def find_port():
    try:
        from serial.tools import list_ports
    except ImportError:
        return None
    candidates = []
    for info in list_ports.comports():
        if info.vid == 0x0483 and info.pid == 0x5740:
            return info.device
        if "ACM" in info.device or "usbmodem" in info.device:
            candidates.append(info.device)
    return candidates[0] if candidates else None


def parse_status(payload):
    out = {}
    if len(payload) >= 11:
        cycle, i2c, sensors, mode, profile = struct.unpack_from("<HHHIB", payload, 0)
        out.update(cycle=cycle, i2c=i2c, profile=profile,
                   sensors={name: bool(sensors >> bit & 1) for name, bit in SENSOR_BITS.items()},
                   armed=bool(mode & 1))
    if len(payload) >= 13:
        out["cpuload"] = struct.unpack_from("<H", payload, 11)[0]
    if len(payload) >= 20:
        flags = struct.unpack_from("<I", payload, 16)[0]
        out["arming"] = [name for bit, name in enumerate(ARMING_DISABLE_FLAGS) if flags >> bit & 1]
    return out


def parse_raw_imu(payload):
    if len(payload) < 18:
        return {}
    values = struct.unpack_from("<9h", payload, 0)
    return {
        "acc": tuple(v / 512.0 for v in values[0:3]),
        "gyro": tuple(float(v) for v in values[3:6]),
        "mag": values[6:9],
    }


def parse_attitude(payload):
    if len(payload) < 6:
        return {}
    roll, pitch, yaw = struct.unpack_from("<hhh", payload, 0)
    return {"att": (roll / 10.0, pitch / 10.0, float(yaw))}


def parse_analog(payload):
    if len(payload) < 7:
        return {}
    legacy_v, mah, rssi, amps = struct.unpack_from("<BHHh", payload, 0)
    vbat = legacy_v / 10.0
    if len(payload) >= 9:
        vbat = struct.unpack_from("<H", payload, 7)[0] / 100.0
    return {"vbat": vbat, "mah": mah, "rssi": round(rssi * 100 / 1023), "amps": amps / 100.0}


def parse_battery_state(payload):
    if len(payload) < 8:
        return {}
    cells, capacity, legacy_v, mah, amps = struct.unpack_from("<BHBHh", payload, 0)
    out = {"cells": cells, "capacity": capacity, "mah": mah, "amps": amps / 100.0,
           "vbat": legacy_v / 10.0}
    if len(payload) >= 9:
        out["batt_state"] = payload[8]
    if len(payload) >= 11:
        out["vbat"] = struct.unpack_from("<H", payload, 9)[0] / 100.0
    return out


def parse_motor(payload):
    count = len(payload) // 2
    values = struct.unpack_from("<%dH" % count, payload, 0)
    return {"motors": [v for v in values if v > 0]}


def parse_motor_telemetry(payload):
    if not payload:
        return {}
    count = payload[0]
    telem = []
    offset = 1
    for _ in range(count):
        if offset + 13 > len(payload):
            break
        rpm, invalid, temp, volts, amps, mah = struct.unpack_from("<IHBHHH", payload, offset)
        telem.append({"rpm": rpm, "invalid": invalid / 100.0, "temp": temp,
                      "volts": volts / 100.0, "amps": amps / 100.0, "mah": mah})
        offset += 13
    return {"telem": telem}


def parse_rc(payload):
    count = len(payload) // 2
    return {"channels": list(struct.unpack_from("<%dH" % count, payload, 0))}


def clean_ascii(raw):
    return "".join(chr(b) for b in raw if 32 <= b < 127).strip()


def read_ident(link):
    ident = {}
    payload = link.request(MSP_API_VERSION)
    if payload and len(payload) >= 3:
        ident["api"] = "%d.%d" % (payload[1], payload[2])
    payload = link.request(MSP_FC_VARIANT)
    if payload:
        ident["variant"] = clean_ascii(payload)
    payload = link.request(MSP_FC_VERSION)
    if payload and len(payload) >= 3:
        ident["version"] = "%d.%d.%d" % (payload[0], payload[1], payload[2])
    payload = link.request(MSP_BOARD_INFO)
    if payload and len(payload) >= 4:
        ident["board"] = clean_ascii(payload[:4])
    payload = link.request(MSP_NAME)
    if payload is not None:
        ident["name"] = clean_ascii(payload)
    return ident
