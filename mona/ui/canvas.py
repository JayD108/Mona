"""A character canvas for animated terminal diagrams that scales to any terminal size.

Drawing code uses a fixed LOGICAL grid (96 x 17). The canvas is created at the real size of the stage (any number of
columns and rows) and every logical position and size is scaled up, so boxes, lines and gaps grow to fill the space
while text stays at its normal size.

    c = Canvas(230, 40)               # physical size = what the terminal gives us
    c.box(2, 1, 20, 5, "#89dceb")     # logical coordinates: scaled automatically
    c.put(4, 3, "hello", "bold")      # text starts at the scaled position (its length is not scaled)
    c.rput(10, 5, "x")                # r... methods use physical cells directly (for dense drawings)
    text = c.render()
"""
from rich.text import Text

DIM = "#45475a"
LW, LH = 96, 17                       # the logical grid every scene is drawn on


class Canvas:
    def __init__(self, pw=LW, ph=LH):
        self.w, self.h = pw, ph
        self.sx = pw / LW                                  # columns scale smoothly
        self.sy = max(1, ph // LH)                         # rows scale in whole steps, so lines stay evenly spaced
        self.oy = (ph - LH * self.sy) // 2                 # and the drawing is centred vertically
        self.ch = [[" "] * pw for _ in range(ph)]
        self.st = [[""] * pw for _ in range(ph)]

    # ── scaling ──────────────────────────────────────────────────────────────
    def X(self, x):
        return round(x * self.sx)

    def Y(self, y):
        return self.oy + round(y * self.sy)

    def R(self, x, y, w, h):
        """A logical rectangle as a physical one: (px, py, pw, ph)."""
        px, py = self.X(x), self.Y(y)
        return px, py, max(1, self.X(x + w) - px), max(1, self.Y(y + h) - py)

    # ── physical drawing ──────────────────────────────────────────────────────
    def rput(self, px, py, s, style=""):
        if not 0 <= py < self.h:
            return
        for i, c in enumerate(s):
            if 0 <= px + i < self.w:
                self.ch[py][px + i] = c
                self.st[py][px + i] = style

    def rclear(self, px, py, pw, ph):
        for yy in range(py, py + ph):
            for xx in range(px, px + pw):
                if 0 <= xx < self.w and 0 <= yy < self.h:
                    self.ch[yy][xx], self.st[yy][xx] = " ", ""

    def rbox(self, px, py, pw, ph, style="#89dceb", title=None, title_style="bold #f9e2af", fill=False):
        if pw < 2 or ph < 2:
            return
        if fill:
            self.rclear(px + 1, py + 1, pw - 2, ph - 2)
        for x in range(px + 1, px + pw - 1):
            self.rput(x, py, "─", style)
            self.rput(x, py + ph - 1, "─", style)
        for y in range(py + 1, py + ph - 1):
            self.rput(px, y, "│", style)
            self.rput(px + pw - 1, y, "│", style)
        for cx, cy, c in ((px, py, "╭"), (px + pw - 1, py, "╮"), (px, py + ph - 1, "╰"), (px + pw - 1, py + ph - 1, "╯")):
            self.rput(cx, cy, c, style)
        if title:
            self.rput(px + 2, py, f" {title} ", title_style)

    def at(self, px, py):
        return self.ch[py][px] if 0 <= py < self.h and 0 <= px < self.w else " "

    # ── logical drawing (scaled) ──────────────────────────────────────────────
    def put(self, x, y, s, style=""):
        self.rput(self.X(x), self.Y(y), s, style)

    def put_in(self, x, y, w, s, style=""):
        """Centre text inside the logical span [x, x + w) on row y."""
        px, pw = self.X(x), self.X(x + w) - self.X(x)
        self.rput(px + max(0, (pw - len(s)) // 2), self.Y(y), s, style)

    def hline(self, x0, x1, y, ch="─", style=""):
        py = self.Y(y)
        for px in range(self.X(min(x0, x1)), self.X(max(x0, x1)) + 1):
            self.rput(px, py, ch, style)

    def vline(self, x, y0, y1, ch="│", style=""):
        px = self.X(x)
        for py in range(self.Y(min(y0, y1)), self.Y(max(y0, y1)) + 1):
            self.rput(px, py, ch, style)

    def arrow(self, x0, x1, y, style="", head="►", line="─"):
        """A line from logical x0 to x1 with an arrow head at the end."""
        px0, px1, py = self.X(x0), self.X(x1), self.Y(y)
        for px in range(px0, px1):
            self.rput(px, py, line, style)
        self.rput(px1, py, head, style)

    def clear(self, x, y, w, h):
        self.rclear(*self.R(x, y, w, h))

    def box(self, x, y, w, h, style="#89dceb", title=None, title_style="bold #f9e2af", fill=False):
        self.rbox(*self.R(x, y, w, h), style=style, title=title, title_style=title_style, fill=fill)

    def center(self, y, s, style="", x0=0, x1=None):
        x1 = LW if x1 is None else x1
        self.put_in(x0, y, x1 - x0, s, style)

    # ── output ────────────────────────────────────────────────────────────────
    def dimmed(self):
        out = Canvas(self.w, self.h)
        out.ch = [row[:] for row in self.ch]
        out.st = [[DIM if c != " " else "" for c in row] for row in self.ch]
        return out

    def copy_from(self, other):
        self.ch = [row[:] for row in other.ch]
        self.st = [row[:] for row in other.st]

    def render(self):
        text = Text(no_wrap=True, overflow="crop")
        for y in range(self.h):
            x = 0
            while x < self.w:
                style = self.st[y][x]
                x2 = x
                while x2 < self.w and self.st[y][x2] == style:
                    x2 += 1
                text.append("".join(self.ch[y][x:x2]), style=style or None)
                x = x2
            if y < self.h - 1:
                text.append("\n")
        return text
