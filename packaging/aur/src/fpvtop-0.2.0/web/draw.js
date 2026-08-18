const GRAPH_UP = [
  " ", "⢀", "⢠", "⢰", "⢸",
  "⡀", "⣀", "⣠", "⣰", "⣸",
  "⡄", "⣄", "⣤", "⣴", "⣼",
  "⡆", "⣆", "⣦", "⣶", "⣾",
  "⡇", "⣇", "⣧", "⣷", "⣿",
];

const GRAPH_DOWN = [
  " ", "⠈", "⠘", "⠸", "⢸",
  "⠁", "⠉", "⠙", "⠹", "⢹",
  "⠃", "⠋", "⠛", "⠻", "⢻",
  "⠇", "⠏", "⠟", "⠿", "⢿",
  "⡇", "⡏", "⡟", "⡿", "⣿",
];

const METER_CH = "■";

function clampv(v, lo, hi) {
  return v < lo ? lo : v > hi ? hi : v;
}

function span(color, text) {
  return '<span style="color:' + color + '">' + text + "</span>";
}

class Graph {
  constructor(width, height, gradient, invert = false, noZero = false) {
    this.width = width;
    this.height = height;
    this.gradient = gradient;
    this.invert = invert;
    this.noZero = noZero;
    this.current = true;
    this.last = 0;
    this.graphs = { true: [], false: [] };
    for (const key of [true, false]) {
      for (let r = 0; r < height; r++) this.graphs[key].push(Array(width).fill(" "));
    }
  }

  add(value) {
    value = clampv(Math.round(value), 0, 100);
    this.current = !this.current;
    for (const row of this.graphs[this.current]) if (row.length) row.shift();
    const syms = this.invert ? GRAPH_DOWN : GRAPH_UP;
    const mod = this.height === 1 ? 0.3 : 0.1;
    for (let horizon = 0; horizon < this.height; horizon++) {
      const curHigh = this.height > 1 ? Math.round((100 * (this.height - horizon)) / this.height) : 100;
      const curLow = this.height > 1 ? Math.round((100 * (this.height - horizon - 1)) / this.height) : 0;
      const result = [this.last, value].map((v, ai) => {
        const clampMin = this.noZero && horizon === this.height - 1 ? 1 : 0;
        if (v >= curHigh) return 4;
        if (v <= curLow) return clampMin;
        return clampv(Math.round(((v - curLow) * 4) / (curHigh - curLow) + mod), clampMin, 4);
      });
      const sym = syms[result[0] * 5 + result[1]];
      if (this.height === 1 && this.gradient) {
        const color = this.gradient[clampv(Math.max(this.last, value), 0, 100)];
        this.graphs[this.current][horizon].push(result[0] + result[1] === 0 ? " " : span(color, sym));
      } else {
        this.graphs[this.current][horizon].push(sym);
      }
    }
    this.last = value;
  }

  html() {
    const rows = [];
    for (let i = 1; i <= this.height; i++) {
      const row = this.graphs[this.current][this.invert ? this.height - i : i - 1].join("");
      if (this.height === 1) {
        rows.push(row);
      } else if (this.gradient) {
        const idx = this.invert ? Math.floor((i * 100) / this.height) : 100 - Math.floor(((i - 1) * 100) / this.height);
        rows.push(span(this.gradient[idx], row));
      } else {
        rows.push(row);
      }
    }
    return rows.join("\n");
  }
}

class MeterDraw {
  constructor(width, gradient) {
    this.width = width;
    this.gradient = gradient;
    this.cache = {};
  }

  html(value) {
    value = clampv(Math.round(value), 0, 100);
    if (this.cache[value]) return this.cache[value];
    let out = "";
    for (let i = 1; i <= this.width; i++) {
      const y = Math.round((i * 100) / this.width);
      if (value >= y) {
        out += span(this.gradient[y], METER_CH);
      } else {
        out += span(THEME.meter_bg, METER_CH.repeat(this.width + 1 - i));
        break;
      }
    }
    this.cache[value] = out;
    return out;
  }
}

function padLeft(text, width) {
  text = String(text);
  return text.length >= width ? text.slice(0, width) : " ".repeat(width - text.length) + text;
}

function padRight(text, width) {
  text = String(text);
  return text.length >= width ? text.slice(0, width) : text + " ".repeat(width - text.length);
}

function divLabel(label, value, cols) {
  const fill = cols - label.length - 1 - value.length - 3;
  return (
    span(THEME.div_line, "─") +
    span(THEME.title, label + ":") +
    span(THEME.div_line, "─".repeat(Math.max(1, fill))) +
    span(THEME.title, value.replace(/ /g, "─")) +
    span(THEME.div_line, "─")
  );
}
