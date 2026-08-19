import time

from . import symbols as Sym
from .draw import Graph, Meter, clamp, create_box, embed_title, embed_title_down
from .terminal import Fx, Mv


def fit(text, width):
    if len(text) > width:
        return text[:width]
    return text.ljust(width)


class CpuBox:
    def __init__(self, theme):
        self.theme = theme
        self.last_ident = None
        self.history = []

    def resize(self, x, y, w, h):
        self.x, self.y, self.w, self.h = x, y, w, h
        self.sb_w = min(48, max(34, w * 2 // 5))
        self.sb_x = x + w - self.sb_w - 1
        self.sb_y = y + 1
        self.sb_h = h - 2
        self.gw = self.sb_x - x - 2
        self.gh = h - 2
        self.row_gw = max(5, self.sb_w - 20)
        t = self.theme
        self.big = Graph(self.gw, self.gh, t.g("cpu"))
        self.gcore = Graph(self.row_gw, 1, t.g("cpu"))
        self.gloop = Graph(self.row_gw, 1, t.g("temp"))
        self.last_ident = None

    def load_avg(self, now, load):
        self.history.append((now, load))
        while self.history and now - self.history[0][0] > 900:
            self.history.pop(0)
        avgs = []
        for span in (60, 300, 900):
            samples = [v for ts, v in self.history if now - ts <= span]
            avgs.append(sum(samples) / len(samples) if samples else 0.0)
        return avgs

    def static(self, st):
        t = self.theme
        ident = st["ident"]
        name = ident.get("name") or ident.get("board") or "flight controller"
        out = [create_box(self.x, self.y, self.w, self.h, t, t.c("cpu_box"),
                          True, "cpu", "", 1)]
        out.append(create_box(self.sb_x, self.sb_y, self.sb_w, self.sb_h, t,
                              "", False, name[:self.sb_w - 8]))
        port = st.get("port")
        if port:
            label = port.rsplit("/", 1)[-1]
        elif st["source"] == "demo":
            label = "sim"
        else:
            label = "no board"
        out.append(Mv.to(self.sb_y + self.sb_h - 1, self.sb_x + 2)
                   + embed_title_down(t, t.c("div_line"), label))
        self.last_ident = (st["source"], name, port)
        return "".join(out)

    def draw(self, st, redraw):
        t = self.theme
        ident = st["ident"]
        key = (st["source"], ident.get("name") or ident.get("board") or "flight controller",
               st.get("port"))
        out = []
        if redraw or key != self.last_ident:
            out.append(self.static(st))
        line_color = t.c("cpu_box")
        clock = time.strftime("%H:%M:%S")
        out.append(Mv.to(self.y, self.x + self.w // 2 - 5)
                   + embed_title(t, line_color, clock, bold=True))
        if st["source"] != "live":
            badge = "demo" if st["source"] == "demo" else "scan"
            out.append(Mv.to(self.y, self.x + 9)
                       + line_color + Sym.TITLE_LEFT + Fx.b + t.c("hi_fg") + badge
                       + Fx.ub + line_color + Sym.TITLE_RIGHT + Fx.reset)
        else:
            out.append(Mv.to(self.y, self.x + 9) + line_color + Sym.H_LINE * 6 + Fx.reset)
        load = clamp(int(st["cpuload"]), 0, 100)
        cycle = st["cycle"]
        freq = 1000.0 / cycle if cycle else 0.0
        badge = "%.1f kHz" % freq
        out.append(Mv.to(self.y, self.x + self.w - len(badge) - 17)
                   + embed_title(t, line_color, badge))
        self.big.add(load)
        out.append(Mv.to(self.y + 1, self.x + 1) + self.big())
        up = int(time.monotonic() - st["started"])
        out.append(Mv.to(self.y + self.h - 2, self.x + 2) + t.c("graph_text")
                   + "up %d:%02d:%02d" % (up // 3600, up % 3600 // 60, up % 60) + Fx.reset)
        rows = []
        self.gcore.add(load)
        rows.append(t.c("graph_text") + "C0    " + Fx.reset + self.gcore()
                    + t.c("main_fg") + "%6d" % load + t.c("graph_text") + "%  " + Fx.reset)
        self.gloop.add(clamp(int(cycle / 10), 0, 100))
        rows.append(t.c("graph_text") + "LOOP  " + Fx.reset + self.gloop()
                    + t.c("main_fg") + "%6d" % cycle + t.c("graph_text") + "µs " + Fx.reset)
        avgs = self.load_avg(time.monotonic(), load)
        rows.append("")
        rows.append(t.c("main_fg") + Fx.b + "Load AVG:" + Fx.ub
                    + t.c("main_fg") + " %3.0f%% %3.0f%% %3.0f%%" % tuple(avgs) + Fx.reset)
        inner = self.sb_h - 2
        pad = " " * (self.sb_w - 2)
        for i in range(inner):
            out.append(Mv.to(self.sb_y + 1 + i, self.sb_x + 1) + pad)
            if i < len(rows):
                out.append(Mv.to(self.sb_y + 1 + i, self.sb_x + 2) + rows[i])
        return "".join(out)


class PowerBox:
    def __init__(self, theme):
        self.theme = theme

    def resize(self, x, y, w, h):
        self.x, self.y, self.w, self.h = x, y, w, h
        t = self.theme
        gw = w - 10
        self.gvolt = Graph(gw, 1, t.g("available"), no_zero=True)
        self.gamp = Graph(gw, 1, t.g("used"), no_zero=True)
        self.used_meter = Meter(gw, t.g("used"), t.c("meter_bg"))

    def static(self):
        t = self.theme
        return create_box(self.x, self.y, self.w, self.h, t, t.c("mem_box"),
                          True, "power", "", 2)

    def div_label(self, row, label, value):
        t = self.theme
        fill = self.w - 4 - len(label) - 1 - len(value) - 1
        if fill < 1:
            return ""
        return (Mv.to(row, self.x) + t.c("div_line") + Sym.DIV_LEFT + Sym.H_LINE
                + t.c("title") + label + ":" + t.c("div_line") + Sym.H_LINE * fill
                + t.c("title") + value.replace(" ", Sym.H_LINE)
                + t.c("div_line") + Sym.H_LINE + Sym.DIV_RIGHT + Fx.reset)

    def graph_row(self, row, graph, pct):
        t = self.theme
        return (Mv.to(row, self.x + 1) + " " + graph()
                + t.c("main_fg") + "%4d" % pct + t.c("graph_text") + "% " + Fx.reset)

    def draw(self, st, redraw):
        t = self.theme
        out = [self.static()] if redraw else []
        cells = st["cells"] or (round(st["vbat"] / 3.9) if st["vbat"] > 1 else 0)
        cell = st["vbat"] / cells if cells else 0.0
        volt_pct = clamp(int((cell - 3.2) / 1.0 * 100), 0, 100) if cells else 0
        amp_pct = clamp(int(st["amps"] * 100 / 40), 0, 100)
        used_pct = clamp(int(st["mah"] * 100 / st["capacity"]), 0, 100) if st["capacity"] else 0
        self.gvolt.add(volt_pct)
        self.gamp.add(amp_pct)
        watts = st["vbat"] * st["amps"]
        rows = []
        rows.append(("div", "Voltage", "%5.2f V" % st["vbat"]))
        rows.append(("graph", self.gvolt, volt_pct))
        rows.append(("div", "Cell", "%dS  %4.2f V" % (cells, cell)))
        rows.append(("div", "Current", "%5.1f A" % st["amps"]))
        rows.append(("graph", self.gamp, amp_pct))
        rows.append(("div", "Used", "%d mAh" % st["mah"]))
        if st["capacity"]:
            rows.append(("meter", self.used_meter, used_pct))
        rows.append(("div", "Power", "%5.1f W" % watts))
        inner = self.h - 2
        pad = " " * (self.w - 2)
        for i in range(inner):
            row = self.y + 1 + i
            if i >= len(rows):
                out.append(Mv.to(row, self.x + 1) + pad)
                continue
            kind = rows[i][0]
            if kind == "div":
                out.append(self.div_label(row, rows[i][1], rows[i][2]))
            elif kind == "graph":
                out.append(self.graph_row(row, rows[i][1], rows[i][2]))
            else:
                out.append(Mv.to(row, self.x + 1) + " " + rows[i][1](rows[i][2])
                           + t.c("main_fg") + "%4d" % rows[i][2]
                           + t.c("graph_text") + "% " + Fx.reset)
        return "".join(out)


class RcBox:
    def __init__(self, theme):
        self.theme = theme

    def resize(self, x, y, w, h):
        self.x, self.y, self.w, self.h = x, y, w, h
        t = self.theme
        self.gh_up = max(1, (h - 2 + 1) // 2)
        self.gh_dn = max(1, h - 2 - self.gh_up)
        self.gthr = Graph(w - 2, self.gh_up, t.g("download"))
        self.grssi = Graph(w - 2, self.gh_dn, t.g("upload"), invert=True)

    def static(self):
        t = self.theme
        return create_box(self.x, self.y, self.w, self.h, t, t.c("net_box"),
                          True, "rc link", "", 3)

    def draw(self, st, redraw):
        t = self.theme
        out = [self.static()] if redraw else []
        channels = st["channels"]
        thr = channels[2] if len(channels) > 2 else 1000
        thr_pct = clamp((thr - 1000) // 10, 0, 100)
        rssi = clamp(st["rssi"], 0, 100)
        self.gthr.add(thr_pct)
        self.grssi.add(rssi)
        out.append(Mv.to(self.y + 1, self.x + 1) + self.gthr())
        out.append(Mv.to(self.y + 1 + self.gh_up, self.x + 1) + self.grssi())
        out.append(Mv.to(self.y + 1, self.x + 2) + t.c("graph_text")
                   + Sym.UP + " thr %d%% %dµs" % (thr_pct, thr) + Fx.reset)
        out.append(Mv.to(self.y + self.h - 2, self.x + 2) + t.c("graph_text")
                   + Sym.DOWN + " rssi %d%%" % rssi + Fx.reset)
        count = "ch %d" % len(channels)
        out.append(Mv.to(self.y, self.x + self.w - len(count) - 4)
                   + embed_title(t, t.c("net_box"), count))
        return "".join(out)


class MotorsBox:
    def __init__(self, theme):
        self.theme = theme
        self.meters = []

    def resize(self, x, y, w, h):
        self.x, self.y, self.w, self.h = x, y, w, h
        t = self.theme
        self.mw = max(5, w - 32)
        self.meters = [Meter(self.mw, t.g("process"), t.c("meter_bg")) for _ in range(8)]

    def static(self, st):
        t = self.theme
        ident = st["ident"]
        out = [create_box(self.x, self.y, self.w, self.h, t, t.c("proc_box"),
                          True, "motors", "", 4)]
        fc = " ".join(v for v in (ident.get("variant"), ident.get("version")) if v)
        parts = [("q quit", self.x + 2), ("+ - rate", self.x + 11)]
        for text, col in parts:
            out.append(Mv.to(self.y + self.h - 1, col)
                       + embed_title_down(t, t.c("proc_box"), text))
        if fc:
            out.append(Mv.to(self.y + self.h - 1, self.x + self.w - len(fc) - 4)
                       + embed_title_down(t, t.c("proc_box"), fc))
        header = " MOT  OUT% " + " " * (self.mw - 1) + "%7s%6s%7s" % ("RPM", "T", "A")
        out.append(Mv.to(self.y + 1, self.x + 1) + Fx.b + t.c("title")
                   + fit(header, self.w - 2) + Fx.ub + Fx.reset)
        self.last_ident = fc
        return "".join(out)

    def draw(self, st, redraw):
        t = self.theme
        ident = st["ident"]
        fc = " ".join(v for v in (ident.get("variant"), ident.get("version")) if v)
        out = []
        if redraw or fc != getattr(self, "last_ident", None):
            out.append(self.static(st))
        motors = st["motors"]
        telem = st["telem"]
        inner = self.h - 3
        pad = " " * (self.w - 2)
        row_i = 0
        for i, value in enumerate(motors[:min(8, inner - 2)]):
            pct = clamp((value - 1000) // 10, 0, 100)
            tele = telem[i] if i < len(telem) else {}
            rpm = tele.get("rpm")
            temp = tele.get("temp")
            amps = tele.get("amps")
            line = (t.c("main_fg") + " M%d " % (i + 1)
                    + "%4d%% " % pct
                    + self.meters[i](pct)
                    + t.c("main_fg")
                    + "%7s" % (rpm if rpm is not None else "-")
                    + "%6s" % ("%d°" % temp if temp is not None else "-")
                    + "%7s" % ("%.1f" % amps if amps is not None else "-")
                    + Fx.reset)
            out.append(Mv.to(self.y + 2 + row_i, self.x + 1) + pad)
            out.append(Mv.to(self.y + 2 + row_i, self.x + 1) + line)
            row_i += 1
        sensor_row = []
        for name in ("gyro", "acc", "baro", "mag", "gps"):
            ok = st["sensors"].get(name)
            dot = (t.c("proc_misc") + "●") if ok else (t.c("inactive_fg") + "○")
            sensor_row.append(dot + (t.c("main_fg") if ok else t.c("inactive_fg"))
                              + " " + name)
        if row_i < inner:
            out.append(Mv.to(self.y + 2 + row_i, self.x + 1) + pad)
            row_i += 1
        if row_i < inner:
            out.append(Mv.to(self.y + 2 + row_i, self.x + 1) + pad)
            out.append(Mv.to(self.y + 2 + row_i, self.x + 2) + "  ".join(sensor_row) + Fx.reset)
            row_i += 1
        status_lines = []
        if st["armed"]:
            status_lines.append(Fx.b + t.c("hi_fg") + "ARMED" + Fx.ub + Fx.reset)
        elif st["arming"]:
            flags = " ".join(st["arming"])
            width = self.w - 4
            prefix = t.c("graph_text") + "DISARM " + t.c("hi_fg")
            while flags and len(status_lines) < 3:
                status_lines.append(prefix + flags[:width - 7] + Fx.reset)
                prefix = t.c("hi_fg") + "       "
                flags = flags[width - 7:]
        else:
            status_lines.append(t.c("proc_misc") + "ready to arm" + Fx.reset)
        for line in status_lines:
            if row_i >= inner:
                break
            out.append(Mv.to(self.y + 2 + row_i, self.x + 1) + pad)
            out.append(Mv.to(self.y + 2 + row_i, self.x + 2) + line)
            row_i += 1
        while row_i < inner:
            out.append(Mv.to(self.y + 2 + row_i, self.x + 1) + pad)
            row_i += 1
        return "".join(out)
