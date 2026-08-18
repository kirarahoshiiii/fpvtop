from collections import deque

from . import symbols as Sym
from .terminal import Fx, Mv


def clamp(value, low, high):
    return low if value < low else high if value > high else value


class Graph:
    def __init__(self, width, height, gradient=None, invert=False, no_zero=False,
                 max_value=0, offset=0):
        self.width = width
        self.height = height
        self.gradient = gradient
        self.invert = invert
        self.no_zero = no_zero
        self.offset = offset
        self.max_value = 100 if (max_value == 0 and offset > 0) else max_value
        self.current = True
        self.last = 0
        self.out = ""
        self.data = deque(maxlen=width * 2 + 4)
        self.graphs = {
            True: [[" "] * width for _ in range(height)],
            False: [[" "] * width for _ in range(height)],
        }
        self._build_out()

    def _create(self, data, data_offset):
        mult = (len(data) - data_offset) > 1
        syms = Sym.GRAPH_DOWN if self.invert else Sym.GRAPH_UP
        mod = 0.3 if self.height == 1 else 0.1
        data_value = 0
        if mult and data_offset > 0:
            self.last = data[data_offset - 1]
            if self.max_value > 0:
                self.last = clamp((self.last + self.offset) * 100 // self.max_value, 0, 100)
        for i in range(data_offset, len(data)):
            if mult:
                self.current = not self.current
            if i < 0:
                data_value = 0
                self.last = 0
            else:
                data_value = data[i]
                if self.max_value > 0:
                    data_value = clamp((data_value + self.offset) * 100 // self.max_value, 0, 100)
            for horizon in range(self.height):
                cur_high = round(100.0 * (self.height - horizon) / self.height) if self.height > 1 else 100
                cur_low = round(100.0 * (self.height - (horizon + 1)) / self.height) if self.height > 1 else 0
                result = []
                for ai, value in enumerate((self.last, data_value)):
                    clamp_min = 1 if (self.no_zero and horizon == self.height - 1
                                      and not (mult and i == data_offset and ai == 0)) else 0
                    if value >= cur_high:
                        result.append(4)
                    elif value <= cur_low:
                        result.append(clamp_min)
                    else:
                        result.append(clamp(int(round((value - cur_low) * 4 / (cur_high - cur_low) + mod)),
                                            clamp_min, 4))
                if self.height == 1:
                    if result[0] + result[1] == 0:
                        self.graphs[self.current][horizon].append(" ")
                    else:
                        cell = ""
                        if self.gradient:
                            cell = self.gradient[clamp(max(self.last, data_value), 0, 100)]
                        self.graphs[self.current][horizon].append(cell + syms[result[0] * 5 + result[1]])
                else:
                    self.graphs[self.current][horizon].append(syms[result[0] * 5 + result[1]])
            if mult and i >= 0:
                self.last = data_value
        self.last = data_value
        self._build_out()

    def _build_out(self):
        if self.height == 1:
            row = self.graphs[self.current][0]
            self.out = "".join(row) + (Fx.reset if self.gradient else "")
            return
        parts = []
        for i in range(1, self.height + 1):
            if i > 1:
                parts.append(Mv.d(1) + Mv.l(self.width))
            if self.gradient:
                idx = i * 100 // self.height if self.invert else 100 - ((i - 1) * 100 // self.height)
                parts.append(self.gradient[idx])
            row = self.graphs[self.current][self.height - i] if self.invert else self.graphs[self.current][i - 1]
            parts.append("".join(row))
        parts.append(Fx.reset)
        self.out = "".join(parts)

    def add(self, value):
        self.data.append(int(value))
        self.current = not self.current
        for row in self.graphs[self.current]:
            if row:
                row.pop(0)
        self._create(self.data, len(self.data) - 1)
        return self.out

    def __call__(self):
        return self.out


class Meter:
    def __init__(self, width, gradient, bg_color, invert=False):
        self.width = width
        self.gradient = gradient
        self.bg_color = bg_color
        self.invert = invert
        self.cache = {}

    def __call__(self, value):
        value = clamp(int(value), 0, 100)
        if value in self.cache:
            return self.cache[value]
        out = []
        for i in range(1, self.width + 1):
            y = round(i * 100 / self.width)
            if value >= y:
                out.append(self.gradient[100 - y if self.invert else y] + Sym.METER)
            else:
                out.append(self.bg_color + Sym.METER * (self.width + 1 - i))
                break
        out.append(Fx.reset)
        result = "".join(out)
        self.cache[value] = result
        return result


def create_box(x, y, width, height, theme, line_color=None, fill=False,
               title="", title2="", num=0):
    if not line_color:
        line_color = theme.c("div_line")
    numbering = "" if num == 0 else theme.c("hi_fg") + Sym.SUPERSCRIPT[clamp(num, 0, 9)]
    out = [Fx.reset, line_color]
    for hpos in (y, y + height - 1):
        out.append(Mv.to(hpos, x) + Sym.H_LINE * (width - 1))
    for hpos in range(y + 1, y + height - 1):
        out.append(Mv.to(hpos, x) + Sym.V_LINE
                   + (" " * (width - 2) if fill else Mv.r(width - 2))
                   + Sym.V_LINE)
    out.append(Mv.to(y, x) + Sym.ROUND_LEFT_UP)
    out.append(Mv.to(y, x + width - 1) + Sym.ROUND_RIGHT_UP)
    out.append(Mv.to(y + height - 1, x) + Sym.ROUND_LEFT_DOWN)
    out.append(Mv.to(y + height - 1, x + width - 1) + Sym.ROUND_RIGHT_DOWN)
    if title:
        out.append(Mv.to(y, x + 2) + Sym.TITLE_LEFT + Fx.b + numbering
                   + theme.c("title") + title + Fx.ub + line_color + Sym.TITLE_RIGHT)
    if title2:
        out.append(Mv.to(y + height - 1, x + 2) + Sym.TITLE_LEFT_DOWN + Fx.b + numbering
                   + theme.c("title") + title2 + Fx.ub + line_color + Sym.TITLE_RIGHT_DOWN)
    out.append(Fx.reset + Mv.to(y + 1, x + 1))
    return "".join(out)


def embed_title(theme, line_color, text, bold=False):
    inner = (Fx.b if bold else "") + theme.c("title") + text + (Fx.ub if bold else "")
    return line_color + Sym.TITLE_LEFT + inner + line_color + Sym.TITLE_RIGHT


def embed_title_down(theme, line_color, text):
    return (line_color + Sym.TITLE_LEFT_DOWN + theme.c("title") + text
            + line_color + Sym.TITLE_RIGHT_DOWN)
