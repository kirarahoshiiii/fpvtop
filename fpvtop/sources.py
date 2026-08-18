import math
import random
import threading
import time

from . import msp

FAST = 0.05
MEDIUM = 0.25
SLOW = 0.5


class State:
    def __init__(self):
        self.lock = threading.Lock()
        self.data = {
            "source": "scan",
            "port": None,
            "ident": {},
            "cycle": 0,
            "cpuload": 0,
            "i2c": 0,
            "profile": 0,
            "armed": False,
            "arming": [],
            "sensors": {},
            "gyro": (0.0, 0.0, 0.0),
            "acc": (0.0, 0.0, 0.0),
            "att": (0.0, 0.0, 0.0),
            "vbat": 0.0,
            "cells": 0,
            "amps": 0.0,
            "mah": 0,
            "capacity": 0,
            "rssi": 0,
            "channels": [],
            "motors": [],
            "telem": [],
            "started": time.monotonic(),
        }

    def update(self, values):
        with self.lock:
            self.data.update(values)

    def snapshot(self):
        with self.lock:
            return dict(self.data)


class Demo:
    def __init__(self):
        self.t0 = time.monotonic()
        self.mah = 0.0
        self.sag = 0.0

    def tick(self):
        t = time.monotonic() - self.t0
        throttle = 0.32 + 0.22 * math.sin(t * 0.31) + 0.08 * math.sin(t * 1.7)
        throttle = max(0.05, min(0.95, throttle + random.uniform(-0.02, 0.02)))
        stick = math.sin(t * 0.13) ** 3
        gyro = (
            180 * stick * math.sin(t * 2.4) + random.uniform(-9, 9),
            120 * stick * math.sin(t * 1.9 + 1.2) + random.uniform(-9, 9),
            60 * math.sin(t * 0.7) * abs(stick) + random.uniform(-6, 6),
        )
        att = (
            22 * math.sin(t * 0.5),
            14 * math.sin(t * 0.36 + 0.8),
            (t * 9) % 360 - 180,
        )
        motors = []
        for i in range(4):
            wob = 0.05 * math.sin(t * (2.1 + i * 0.33) + i)
            out = throttle + wob + 0.05 * stick * (1 if i % 2 else -1)
            motors.append(int(1000 + max(0.03, min(1.0, out)) * 1000))
        amps = 1.6 + throttle * 34 + random.uniform(-0.6, 0.6)
        self.mah += amps * FAST / 3.6
        self.sag += (throttle * 0.9 - self.sag) * 0.1
        vbat = 16.8 - (t / 90) * 0.35 - self.sag - random.uniform(0, 0.02)
        telem = []
        for m in motors:
            frac = (m - 1000) / 1000
            telem.append({
                "rpm": int(frac * 27000 + random.uniform(-300, 300)),
                "temp": int(24 + frac * 38),
                "amps": round(amps / 4, 1),
                "invalid": 0.0,
                "volts": round(vbat, 2),
                "mah": int(self.mah / 4),
            })
        channels = [
            1500 + int(220 * stick),
            1500 + int(160 * math.sin(t * 0.4)),
            int(1000 + throttle * 1000),
            1500 + int(90 * math.sin(t * 0.9)),
            2000 if int(t / 8) % 2 else 1000,
            1500, 1000, 1000,
        ]
        return {
            "source": "demo",
            "port": None,
            "ident": {"variant": "DEMO", "version": "4.5.2", "board": "SIML",
                      "name": "bench sim", "api": "1.46"},
            "cycle": int(125 + random.uniform(-4, 12)),
            "cpuload": int(18 + throttle * 40 + random.uniform(-2, 2)),
            "i2c": 0,
            "armed": True,
            "arming": [],
            "sensors": {"gyro": True, "acc": True, "baro": True, "mag": False,
                        "gps": False, "range": False},
            "gyro": gyro,
            "acc": (att[0] / 57.3, att[1] / 57.3, 1.0 + 0.05 * math.sin(t * 3)),
            "att": att,
            "vbat": round(vbat, 2),
            "cells": 4,
            "amps": round(amps, 1),
            "mah": int(self.mah),
            "capacity": 1300,
            "rssi": int(88 + 10 * math.sin(t * 0.21) + random.uniform(-2, 2)),
            "channels": channels,
            "motors": motors,
            "telem": telem,
        }


class Collector(threading.Thread):
    def __init__(self, state, force_demo=False, port=None):
        super().__init__(daemon=True)
        self.state = state
        self.force_demo = force_demo
        self.port = port
        self.stop_event = threading.Event()
        self.demo = Demo()
        self.link = None
        self.timers = {}

    def due(self, name, interval):
        now = time.monotonic()
        if now - self.timers.get(name, 0) >= interval:
            self.timers[name] = now
            return True
        return False

    def run(self):
        last_scan = 0.0
        while not self.stop_event.is_set():
            if self.force_demo:
                self.state.update(self.demo.tick())
                time.sleep(FAST)
                continue
            if self.link is None:
                now = time.monotonic()
                if now - last_scan >= 1.0:
                    last_scan = now
                    port = self.port or msp.find_port()
                    if port:
                        try:
                            self.link = msp.Link(port)
                            ident = msp.read_ident(self.link)
                            self.timers.clear()
                            self.state.update({"source": "live", "port": port,
                                               "ident": ident})
                        except Exception:
                            self.link = None
                if self.link is None:
                    self.state.update(self.demo.tick())
                    time.sleep(FAST)
                    continue
            try:
                self.poll()
                time.sleep(FAST)
            except Exception:
                try:
                    self.link.close()
                except Exception:
                    pass
                self.link = None
                self.state.update({"source": "scan", "port": None})

    def poll(self):
        updates = {}
        for cmd, parser in ((msp.MSP_RAW_IMU, msp.parse_raw_imu),
                            (msp.MSP_ATTITUDE, msp.parse_attitude),
                            (msp.MSP_MOTOR, msp.parse_motor),
                            (msp.MSP_RC, msp.parse_rc)):
            payload = self.link.request(cmd)
            if payload:
                updates.update(parser(payload))
        if self.due("medium", MEDIUM):
            payload = self.link.request(msp.MSP_MOTOR_TELEMETRY)
            if payload:
                updates.update(msp.parse_motor_telemetry(payload))
        if self.due("slow", SLOW):
            payload = self.link.request(msp.MSP_STATUS_EX)
            if not payload:
                payload = self.link.request(msp.MSP_STATUS)
            if payload:
                updates.update(msp.parse_status(payload))
            payload = self.link.request(msp.MSP_ANALOG)
            if payload:
                updates.update(msp.parse_analog(payload))
            payload = self.link.request(msp.MSP_BATTERY_STATE)
            if payload:
                updates.update(msp.parse_battery_state(payload))
        if updates:
            self.state.update(updates)

    def stop(self):
        self.stop_event.set()
