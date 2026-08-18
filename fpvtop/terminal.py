import os
import select
import signal
import sys
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


class Term:
    def __init__(self):
        self.width = 0
        self.height = 0
        self.resized = False
        self._saved = None

    def init(self):
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
        os.write(sys.stdout.fileno(), text.encode())

    def read_keys(self, timeout):
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

    def restore(self):
        self.write(SYNC_END + NORMAL_SCREEN + SHOW_CURSOR + Fx.reset_base)
        if self._saved is not None:
            try:
                termios.tcsetattr(sys.stdin.fileno(), termios.TCSANOW, self._saved)
            except termios.error:
                pass
