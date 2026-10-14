"""A tiny character canvas for drawing animated diagrams in the terminal.

    c = Canvas(96, 17)
    c.box(2, 1, 20, 5, "#89dceb", title="MONA")
    c.put(4, 3, "hello", "bold #f9e2af")
    text = c.render()            # a Rich Text, one style run per colour change
"""
from rich.text import Text

DIM = "#45475a"


class Canvas:
    def __init__(self, w, h):
        self.w, self.h = w, h
        self.ch = [[" "] * w for _ in range(h)]
        self.st = [[""] * w for _ in range(h)]

    def put(self, x, y, s, style=""):
        if not 0 <= y < self.h:
            return
        for i, c in enumerate(s):
            if 0 <= x + i < self.w:
                self.ch[y][x + i] = c
                self.st[y][x + i] = style

    def hline(self, x0, x1, y, ch="─", style=""):
        for x in range(min(x0, x1), max(x0, x1) + 1):
            self.put(x, y, ch, style)

    def vline(self, x, y0, y1, ch="│", style=""):
        for y in range(min(y0, y1), max(y0, y1) + 1):
            self.put(x, y, ch, style)

    def clear(self, x, y, w, h):
        for yy in range(y, y + h):
            for xx in range(x, x + w):
                if 0 <= xx < self.w and 0 <= yy < self.h:
                    self.ch[yy][xx], self.st[yy][xx] = " ", ""

    def box(self, x, y, w, h, style="#89dceb", title=None, title_style="bold #f9e2af", fill=False):
        if w < 2 or h < 2:
            return
        if fill:
            self.clear(x + 1, y + 1, w - 2, h - 2)
        self.hline(x + 1, x + w - 2, y, "─", style)
        self.hline(x + 1, x + w - 2, y + h - 1, "─", style)
        self.vline(x, y + 1, y + h - 2, "│", style)
        self.vline(x + w - 1, y + 1, y + h - 2, "│", style)
        for cx, cy, c in ((x, y, "╭"), (x + w - 1, y, "╮"), (x, y + h - 1, "╰"), (x + w - 1, y + h - 1, "╯")):
            self.put(cx, cy, c, style)
        if title:
            self.put(x + 2, y, f" {title} ", title_style)

    def center(self, y, s, style="", x0=0, x1=None):
        x1 = self.w if x1 is None else x1
        self.put(x0 + max(0, (x1 - x0 - len(s)) // 2), y, s, style)

    def dimmed(self):
        out = Canvas(self.w, self.h)
        out.ch = [row[:] for row in self.ch]
        out.st = [[DIM if c != " " else "" for c in row] for row in self.ch]
        return out

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
