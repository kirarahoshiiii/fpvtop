import os
import struct
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


def main():
    if sys.platform == "win32":
        print("skip test_tui (needs a pty)")
        return 0
    import fcntl
    import pty
    import termios

    pid, fd = pty.fork()
    if pid == 0:
        os.environ["TERM"] = "xterm-256color"
        from fpvtop.main import run
        sys.exit(run(["-d", "-u", "100"]))

    fcntl.ioctl(fd, termios.TIOCSWINSZ, struct.pack("HHHH", 30, 100, 0, 0))
    time.sleep(2.0)
    os.write(fd, b"q")
    deadline = time.time() + 3
    out = b""
    while time.time() < deadline:
        try:
            chunk = os.read(fd, 65536)
        except OSError:
            break
        if not chunk:
            break
        out += chunk
    done, status = os.waitpid(pid, 0)
    os.close(fd)

    checks = {
        "exited cleanly": os.WIFEXITED(status) and os.WEXITSTATUS(status) == 0,
        "entered alt screen": b"\x1b[?1049h" in out,
        "left alt screen": b"\x1b[?1049l" in out,
        "drew braille graphs": b"\xe2\xa3" in out or b"\xe2\xa2" in out,
        "drew box borders": "╭".encode() in out,
        "drew gyro title": b"gyro" in out,
    }
    failures = 0
    for name, ok in checks.items():
        print(("ok   " if ok else "FAIL ") + name)
        if not ok:
            failures += 1
    return failures


if __name__ == "__main__":
    sys.exit(main())
