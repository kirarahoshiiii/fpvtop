import os

DEFAULT = {
    "main_bg": "#00",
    "main_fg": "#cc",
    "title": "#ee",
    "hi_fg": "#b54040",
    "selected_bg": "#6a2f2f",
    "selected_fg": "#ee",
    "inactive_fg": "#40",
    "graph_text": "#60",
    "meter_bg": "#40",
    "proc_misc": "#0de756",
    "cpu_box": "#556d59",
    "mem_box": "#6c6c4b",
    "net_box": "#5c588d",
    "proc_box": "#805252",
    "div_line": "#30",
    "temp_start": "#4897d4",
    "temp_mid": "#5474e8",
    "temp_end": "#ff40b6",
    "cpu_start": "#77ca9b",
    "cpu_mid": "#cbc06c",
    "cpu_end": "#dc4c4c",
    "free_start": "#384f21",
    "free_mid": "#b5e685",
    "free_end": "#dcff85",
    "cached_start": "#163350",
    "cached_mid": "#74e6fc",
    "cached_end": "#26c5ff",
    "available_start": "#4e3f0e",
    "available_mid": "#ffd77a",
    "available_end": "#ffb814",
    "used_start": "#592b26",
    "used_mid": "#d9626d",
    "used_end": "#ff4769",
    "download_start": "#291f75",
    "download_mid": "#4f43a3",
    "download_end": "#b0a9de",
    "upload_start": "#620665",
    "upload_mid": "#7d4180",
    "upload_end": "#dcafde",
    "process_start": "#80d0a3",
    "process_mid": "#dcd179",
    "process_end": "#d45454",
}

BG_NAMES = {"main_bg", "selected_bg"}
GRADIENT_BASES = [
    "temp", "cpu", "free", "cached", "available",
    "used", "download", "upload", "process",
]
THEME_DIRS = [
    os.path.expanduser("~/.config/btop/themes"),
    "/usr/share/btop/themes",
    "/usr/local/share/btop/themes",
]


def parse_hex(value):
    value = value.strip().strip('"').strip("'")
    if not value.startswith("#"):
        return None
    value = value[1:]
    try:
        if len(value) == 2:
            v = int(value, 16)
            return (v, v, v)
        if len(value) == 6:
            return tuple(int(value[i:i + 2], 16) for i in (0, 2, 4))
    except ValueError:
        return None
    return None


def escape(rgb, bg=False):
    return "\x1b[%d;2;%d;%d;%dm" % (48 if bg else 38, rgb[0], rgb[1], rgb[2])


def read_theme_file(path):
    out = {}
    with open(path, encoding="utf-8", errors="replace") as fh:
        for line in fh:
            line = line.strip()
            if not line.startswith("theme["):
                continue
            name, _, value = line[6:].partition("]")
            _, _, value = value.partition("=")
            out[name.strip()] = value.strip()
    return out


def find_btop_theme():
    conf = os.path.expanduser("~/.config/btop/btop.conf")
    name = None
    background = True
    if os.path.isfile(conf):
        with open(conf, encoding="utf-8", errors="replace") as fh:
            for line in fh:
                line = line.strip()
                if line.startswith("color_theme"):
                    name = line.partition("=")[2].strip().strip('"')
                elif line.startswith("theme_background"):
                    background = "true" in line.partition("=")[2].lower()
    return name, background


def resolve_theme_path(name):
    if not name or name.lower() in ("default", "default.theme"):
        return None
    if os.path.isfile(name):
        return name
    for d in THEME_DIRS:
        for candidate in (name, name + ".theme"):
            path = os.path.join(d, candidate)
            if os.path.isfile(path):
                return path
    return None


class Theme:
    def __init__(self, source, background=True):
        self.colors = {}
        self.rgbs = {}
        merged = dict(DEFAULT)
        merged.update(source)
        for name, value in merged.items():
            rgb = parse_hex(value)
            if rgb is None:
                self.rgbs[name] = (0, 0, 0)
                self.colors[name] = ""
                continue
            self.rgbs[name] = rgb
            self.colors[name] = escape(rgb, name in BG_NAMES)
        if not background:
            self.colors["main_bg"] = ""
        self.gradients = {}
        for base in GRADIENT_BASES:
            self.gradients[base] = self._gradient(base)

    def _gradient(self, base):
        start = self.rgbs.get(base + "_start")
        mid = self.rgbs.get(base + "_mid") if self.colors.get(base + "_mid") else None
        end = self.rgbs.get(base + "_end") if self.colors.get(base + "_end") else None
        if start is None:
            return [""] * 101
        if end is None:
            return [escape(start)] * 101
        out = []
        if mid is not None:
            for i in range(50):
                t = i / 50
                out.append(escape(tuple(round(start[c] + (mid[c] - start[c]) * t) for c in range(3))))
            for i in range(51):
                t = i / 50
                out.append(escape(tuple(round(mid[c] + (end[c] - mid[c]) * t) for c in range(3))))
        else:
            for i in range(101):
                t = i / 100
                out.append(escape(tuple(round(start[c] + (end[c] - start[c]) * t) for c in range(3))))
        return out

    def c(self, name):
        return self.colors.get(name, "")

    def g(self, base):
        return self.gradients[base]

    @classmethod
    def load(cls, name=None):
        background = True
        if name is None:
            name, background = find_btop_theme()
        path = resolve_theme_path(name)
        if path is None:
            return cls({}, background)
        try:
            return cls(read_theme_file(path), background)
        except OSError:
            return cls({}, background)
