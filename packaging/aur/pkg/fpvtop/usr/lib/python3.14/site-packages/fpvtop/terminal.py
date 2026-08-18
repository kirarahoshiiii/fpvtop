import os
import signal
import sys
import time

WINDOWS = sys.platform == "win32"

if WINDOWS:
    import ctypes
    import msvcrt
else:
    import select
    import termios


class Fx:
    e = "\x1b["
    b = e + "1m"
    ub = e + "22m"
    d = e + "2m"
    ud = e + "22m"
    i = e + "3m"
    ui = e + "23m"
    ul = e + "4m"
    uul = e + "24m"
    reset_base = e + "0m"
    reset = reset_base

    @classmethod
    def set_reset(cls, fg, bg):
        cls.reset = cls.reset_base + bg + fg


class Mv:
    @staticmethod
    def to(line, col):
        return "\x1b[%d;%df" % (line, col)

    @staticmethod
    def r(x):
        return "\x1b[%dC" % x

    @staticmethod
    def l(x):
        return "\x1b[%dD" % x

    @staticmethod
    def u(x):
        return "\x1b[%dA" % x

    @staticmethod
    def d(x):
        return "\x1b[%dB" % x


HIDE_CURSOR = "\x1b[?25l"
SHOW_CURSOR = "\x1b[?25h"
ALT_SCREEN = "\x1b[?1049h"
NORMAL_SCREEN = "\x1b[?1049l"
CLEAR = "\x1b[2J\x1b[0;0f"
SYNC_START = "\x1b[?2026h"
SYNC_END = "\x1b[?2026l"

WIN_KEYMAP = {
    "H": "\x1b[A", "P": "\x1b[B", "M": "\x1b[C", "K": "\x1b[D",
    "G": "\x1b[H", "O": "\x1b[F",
}


class Term:
    def __init__(self):
        self.width = 0
        self.height = 0
        self.resized = False
        self._saved = None

    def init(self):
        if WINDOWS:
            kernel32 = ctypes.windll.kernel32
            kernel32.SetConsoleOutputCP(65001)
            for handle_id in (-11, -12):
                handle = kernel32.GetStdHandle(handle_id)
                mode = ctypes.c_uint32()
                if kernel32.GetConsoleMode(handle, ctypes.byref(mode)):
                    kernel32.SetConsoleMode(handle, mode.value | 0x0004)
        else:
            fd = sys.stdin.fileno()
            try:
                self._saved = termios.tcgetattr(fd)
                mode = termios.tcgetattr(fd)
                mode[3] &= ~(termios.ECHO | termios.ICANON)
                mode[6][termios.VMIN] = 0
                mode[6][termios.VTIME] = 0
                termios.tcsetattr(fd, termios.TCSANOW, mode)
            except termios.error:
                self._saved = None
        if hasattr(signal, "SIGWINCH"):
            signal.signal(signal.SIGWINCH, self._on_winch)
        self.write(ALT_SCREEN + HIDE_CURSOR + CLEAR)
        self.refresh()

    def _on_winch(self, *_):
        self.resized = True

    def refresh(self):
        try:
            size = os.get_terminal_size()
        except OSError:
            size = os.terminal_size((80, 24))
        changed = (size.columns, size.lines) != (self.width, self.height)
        self.width, self.height = size.columns, size.lines
        self.resized = False
        return changed

    def write(self, text):
        data = text.encode()
        if WINDOWS:
            sys.stdout.buffer.write(data)
            sys.stdout.buffer.flush()
        else:
            os.write(sys.stdout.fileno(), data)

    def _check_size(self):
        try:
            size = os.get_terminal_size()
        except OSError:
            return
        if (size.columns, size.lines) != (self.width, self.height):
            self.resized = True

    def read_keys(self, timeout):
        if WINDOWS:
            return self._read_keys_win(timeout)
        try:
            ready, _, _ = select.select([sys.stdin], [], [], timeout)
        except (OSError, ValueError):
            return []
        if not ready:
            return []
        try:
            raw = os.read(sys.stdin.fileno(), 128).decode(errors="replace")
        except OSError:
            return []
        keys = []
        i = 0
        while i < len(raw):
            ch = raw[i]
            if ch == "\x1b":
                if raw[i + 1:i + 2] == "[":
                    j = i + 2
                    while j < len(raw) and not raw[j].isalpha() and raw[j] != "~":
                        j += 1
                    keys.append(raw[i:j + 1])
                    i = j + 1
                else:
                    keys.append("escape")
                    i += 1
            else:
                keys.append(ch)
                i += 1
        return keys

    def _read_keys_win(self, timeout):
        deadline = time.monotonic() + timeout
        keys = []
        while True:
            while msvcrt.kbhit():
                ch = msvcrt.getwch()
                if ch in ("\x00", "\xe0"):
                    keys.append(WIN_KEYMAP.get(msvcrt.getwch(), ""))
                else:
                    keys.append(ch)
            if keys:
                return [k for k in keys if k]
            self._check_size()
            if self.resized or time.monotonic() >= deadline:
                return []
            time.sleep(min(0.02, max(0.0, deadline - time.monotonic())))

    def restore(self):
        self.write(SYNC_END + NORMAL_SCREEN + SHOW_CURSOR + Fx.reset_base)
        if not WINDOWS and self._saved is not None:
            try:
                termios.tcsetattr(sys.stdin.fileno(), termios.TCSANOW, self._saved)
            except termios.error:
                pass
