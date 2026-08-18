import struct
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fpvtop import msp


def frame(cmd, payload=b""):
    body = bytes([len(payload), cmd]) + payload
    crc = 0
    for b in body:
        crc ^= b
    return b"$M>" + body + bytes([crc])


def test_build_roundtrip():
    raw = msp.build(101)
    assert raw[:3] == b"$M<"
    assert raw[3] == 0
    assert raw[4] == 101


def test_parser_whole_frame():
    parser = msp.Parser()
    frames = parser.feed(frame(108, struct.pack("<hhh", 125, -32, 900)))
    assert len(frames) == 1
    ok, cmd, payload = frames[0]
    assert ok and cmd == 108
    assert msp.parse_attitude(payload) == {"att": (12.5, -3.2, 900.0)}


def test_parser_garbage_and_split():
    parser = msp.Parser()
    raw = b"\x00\xffnoise" + frame(104, struct.pack("<4H", 1100, 1200, 1300, 1400))
    frames = parser.feed(raw[:9])
    frames += parser.feed(raw[9:])
    assert len(frames) == 1
    ok, cmd, payload = frames[0]
    assert ok and cmd == 104
    assert msp.parse_motor(payload) == {"motors": [1100, 1200, 1300, 1400]}


def test_parser_bad_checksum():
    parser = msp.Parser()
    raw = bytearray(frame(104, b"\x01\x02"))
    raw[-1] ^= 0xFF
    frames = parser.feed(bytes(raw))
    assert len(frames) == 1
    assert frames[0][0] is False


def test_parse_status():
    payload = struct.pack("<HHHIB", 126, 0, 0b101001, 1, 0)
    payload += struct.pack("<H", 34) + b"\x00\x00\x00" + struct.pack("<I", 1 << 13)
    out = msp.parse_status(payload)
    assert out["cycle"] == 126
    assert out["armed"] is True
    assert out["cpuload"] == 34
    assert out["sensors"]["gyro"] and out["sensors"]["acc"] and out["sensors"]["gps"]
    assert not out["sensors"]["baro"]
    assert out["arming"] == ["CLI"]


def test_parse_analog():
    payload = struct.pack("<BHHh", 168, 430, 512, 1240) + struct.pack("<H", 1585)
    out = msp.parse_analog(payload)
    assert out["vbat"] == 15.85
    assert out["mah"] == 430
    assert out["rssi"] == 50
    assert out["amps"] == 12.4


def test_parse_battery_state():
    payload = struct.pack("<BHBHh", 4, 1300, 158, 430, 1240) + b"\x00" + struct.pack("<H", 1582)
    out = msp.parse_battery_state(payload)
    assert out["cells"] == 4
    assert out["capacity"] == 1300
    assert out["vbat"] == 15.82


def test_parse_motor_telemetry():
    rec = struct.pack("<IHBHHH", 12000, 0, 34, 1580, 310, 120)
    out = msp.parse_motor_telemetry(bytes([2]) + rec + rec)
    assert len(out["telem"]) == 2
    assert out["telem"][0]["rpm"] == 12000
    assert out["telem"][0]["temp"] == 34
    assert out["telem"][0]["amps"] == 3.1


def test_parse_rc():
    payload = struct.pack("<8H", *range(1000, 1800, 100))
    assert msp.parse_rc(payload)["channels"][0] == 1000


def main():
    failures = 0
    for name, fn in sorted(globals().items()):
        if name.startswith("test_"):
            try:
                fn()
                print("ok   " + name)
            except AssertionError as exc:
                failures += 1
                print("FAIL " + name + " " + str(exc))
    return failures


if __name__ == "__main__":
    sys.exit(main())
