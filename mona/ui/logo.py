"""The MONA logo: big block letters in a purple-to-cyan gradient, drawn frame by frame.

    frame(progress, t)   progress 0 -> 1 wipes the letters in from the left (a diagonal reveal);
                         once it reaches 1, `t` (seconds) moves a soft highlight across the letters.
"""
from rich.text import Text

# 5 rows of 5 "pixels" per letter; every pixel is drawn two cells wide so the letters look chunky.
GLYPHS = {
    "M": ["X...X", "XX.XX", "X.X.X", "X...X", "X...X"],
    "O": [".XXX.", "X...X", "X...X", "X...X", ".XXX."],
    "N": ["X...X", "XX..X", "X.X.X", "X..XX", "X...X"],
    "A": [".XXX.", "X...X", "XXXXX", "X...X", "X...X"],
}
WORD = "MONA"
STOPS = [(0xCB, 0xA6, 0xF7), (0xB4, 0xBE, 0xFE), (0x89, 0xDC, 0xEB)]      # mauve -> lavender -> sky
WHITE = (0xFF, 0xFF, 0xFF)


def _rows():
    rows = []
    for r in range(5):
        line = ""
        for ch in WORD:
            line += "".join("██" if px == "X" else "  " for px in GLYPHS[ch][r]) + "  "
        rows.append(line.rstrip())
    return rows


ROWS = _rows()
WIDTH = max(len(r) for r in ROWS)
HEIGHT = len(ROWS)


def _mix(a, b, t):
    t = max(0.0, min(1.0, t))
    return tuple(round(a[i] + (b[i] - a[i]) * t) for i in range(3))


def _gradient(x):
    pos = x / max(WIDTH - 1, 1) * (len(STOPS) - 1)
    i = min(int(pos), len(STOPS) - 2)
    return _mix(STOPS[i], STOPS[i + 1], pos - i)


def _hex(c):
    return "#%02x%02x%02x" % c


def frame(progress=1.0, t=0.0):
    """One frame of the logo as Rich text (HEIGHT lines, WIDTH cells wide)."""
    out = Text(no_wrap=True)
    edge = progress * (WIDTH + 2 * HEIGHT)                 # the wipe is diagonal: lower rows lag behind
    band = ((t * 24) % (WIDTH + 24)) - 12 if progress >= 1 else None
    for r, row in enumerate(ROWS):
        for x in range(WIDTH):
            ch = row[x] if x < len(row) else " "
            if ch == " " or x > edge - 2 * r:
                out.append(" ")
                continue
            colour = _gradient(x)
            if x > edge - 2 * r - 3 and progress < 1:       # the leading edge glows white while it draws
                colour = _mix(colour, WHITE, 0.85)
            elif band is not None:
                colour = _mix(colour, WHITE, max(0.0, 1 - abs(x - band) / 5) * 0.8)
            out.append(ch, style="bold " + _hex(colour))
        if r < HEIGHT - 1:
            out.append("\n")
    return out
