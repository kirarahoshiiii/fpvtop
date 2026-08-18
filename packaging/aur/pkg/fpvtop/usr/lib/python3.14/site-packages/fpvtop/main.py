import argparse
import sys
import time

from . import __version__
from . import symbols as Sym
from .boxes import GyroBox, MotorsBox, PowerBox, RcBox
from .draw import embed_title
from .sources import Collector, State
from .terminal import CLEAR, SYNC_END, SYNC_START, Fx, Mv, Term
from .theme import Theme

MIN_W = 80
MIN_H = 24


class App:
    def __init__(self, term, theme, args):
        self.term = term
        self.theme = theme
        self.update_ms = max(50, min(5000, args.update))
        self.state = State()
        self.collector = Collector(self.state, force_demo=args.demo, port=args.port)
        self.gyro = GyroBox(theme)
        self.power = PowerBox(theme)
        self.rc = RcBox(theme)
        self.motors = MotorsBox(theme)
        self.too_small = False
        self.calc_sizes()

    def calc_sizes(self):
        w, h = self.term.width, self.term.height
        self.too_small = w < MIN_W or h < MIN_H
        if self.too_small:
            return
        gyro_h = max(8, round(h * 0.32))
        left_w = round(w * 0.45)
        lower_h = h - gyro_h
        power_h = (lower_h + 1) // 2
        rc_h = lower_h - power_h
        self.gyro.resize(1, 1, w, gyro_h)
        self.power.resize(1, gyro_h + 1, left_w, power_h)
        self.rc.resize(1, gyro_h + power_h + 1, left_w, rc_h)
        self.motors.resize(left_w + 1, gyro_h + 1, w - left_w, lower_h)

    def rate_title(self):
        t = self.theme
        text = ("- " + str(self.update_ms) + "ms +").rjust(10)
        return (Mv.to(1, self.term.width - len(text) - 4)
                + embed_title(t, t.c("cpu_box"), text))

    def frame(self, redraw):
        if self.too_small:
            msg = "fpvtop needs at least %dx%d (now %dx%d)" % (
                MIN_W, MIN_H, self.term.width, self.term.height)
            row = max(1, self.term.height // 2)
            col = max(1, (self.term.width - len(msg)) // 2)
            return CLEAR + Mv.to(row, col) + self.theme.c("title") + msg + Fx.reset
        st = self.state.snapshot()
        parts = [Fx.reset]
        if redraw:
            parts.append(self.theme.c("main_bg") + CLEAR)
        parts.append(self.gyro.draw(st, redraw))
        parts.append(self.rate_title())
        parts.append(self.power.draw(st, redraw))
        parts.append(self.rc.draw(st, redraw))
        parts.append(self.motors.draw(st, redraw))
        parts.append(Mv.to(self.term.height, self.term.width))
        return "".join(parts)

    def loop(self):
        self.collector.start()
        redraw = True
        next_tick = time.monotonic()
        while True:
            now = time.monotonic()
            if now >= next_tick:
                self.term.write(SYNC_START + self.frame(redraw) + SYNC_END)
                redraw = False
                next_tick = now + self.update_ms / 1000
            for key in self.term.read_keys(max(0.0, next_tick - time.monotonic())):
                if key in ("q", "Q", "\x03"):
                    return
                if key in ("+", "="):
                    self.update_ms = min(5000, self.update_ms + 100)
                elif key == "-":
                    self.update_ms = max(50, self.update_ms - 100)
            if self.term.resized:
                time.sleep(0.05)
                self.term.refresh()
                self.calc_sizes()
                redraw = True
                next_tick = time.monotonic()


def parse_args(argv):
    parser = argparse.ArgumentParser(prog="fpvtop",
                                     description="btop-style live monitor for Betaflight flight controllers")
    parser.add_argument("-p", "--port", help="serial port of the flight controller")
    parser.add_argument("-d", "--demo", action="store_true", help="run on simulated data")
    parser.add_argument("-u", "--update", type=int, default=100, metavar="MS",
                        help="update rate in milliseconds (default 100)")
    parser.add_argument("-t", "--theme", help="btop theme name or path")
    parser.add_argument("-V", "--version", action="version",
                        version="fpvtop " + __version__)
    return parser.parse_args(argv)


def run(argv=None):
    args = parse_args(argv if argv is not None else sys.argv[1:])
    theme = Theme.load(args.theme)
    Fx.set_reset(theme.c("main_fg"), theme.c("main_bg"))
    term = Term()
    term.init()
    app = App(term, theme, args)
    try:
        app.loop()
    except KeyboardInterrupt:
        pass
    finally:
        app.collector.stop()
        term.restore()
    return 0


if __name__ == "__main__":
    sys.exit(run())
