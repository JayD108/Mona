"""Inside MONA: an animated zoom from the whole model down to a single neuron, then what kind of model she is.

Eleven scenes. Every number on screen is MONA's real data (see zoomdata.py); the narration is written by hand.
The camera "dives" into a box of each scene to reach the next one. The drawing is scaled to fill the terminal.
Controls: Space pause / resume autoplay, Enter or → next, ← back, R replay the scene, Esc leave.
"""
import math

from . import zoomdata
from .brain import LEVELS
from .lesson import (AMBER, BG, CYAN, GREEN, LAV, MUTE, PINK, TEXT, LessonScreen, ease, heat, human, mix, num, typed, word)

# ───────────────────────────── the scenes ─────────────────────────────
def scene_whole(c, t, D, S):
    P = D["params"]
    if t >= 0.3:
        c.box(38, 2, 34, 11, CYAN, title="MONA")
    if t >= 0.8:
        c.put(2, 3, "WORDS IN", f"bold {AMBER}")
        words = D["sentence"].split()
        c.put(2, 5, typed(" ".join(words[:4]), t, 0.9, 28), f"bold {TEXT}")
        c.put(2, 6, typed(" ".join(words[4:]), t, 1.9, 28), f"bold {TEXT}")
    if t >= 2.0:
        c.arrow(2, 2 + 35 * ease((t - 2.0) / 0.8), 8, AMBER, line="━")
    if t >= 2.4:                                                   # real weights, flickering past
        px, py, pw, ph = c.R(38, 2, 34, 11)
        cols = max(2, (pw - 4) // 8)
        wm, off = D["weights"], int(t * 7)
        for r in range(ph - 2):
            row = wm[(off + r * 3) % len(wm)]
            line = " ".join(f"{row[(off // 3 + k) % len(row)]:+.3f}" for k in range(cols))
            c.rput(px + 2, py + 1 + r, line, mix(MUTE, CYAN, 0.5 + 0.5 * math.sin(t * 3 + r)))
    if t >= 3.8:
        c.put(73, 8, "►", AMBER)
        c.put(76, 3, "NEXT WORD GUESS", f"bold {AMBER}")
        bar = max(8, round(8 * c.sx))
        for i, g in enumerate(D["final"][:3]):
            if t >= 3.9 + 0.35 * i:
                filled = max(1, round(bar * g.prob / D["final"][0].prob))
                c.put(76, 5 + i * 1.5, f"{g.token.text.strip()[:6]:<6}", f"bold {TEXT}")
                c.rput(c.X(76) + 7, c.Y(5 + i * 1.5), "█" * filled + "░" * (bar - filled), CYAN)
                c.rput(c.X(76) + 8 + bar, c.Y(5 + i * 1.5), f"{g.prob:3.0%}", f"bold {GREEN}")
    if t >= 5.0:
        c.center(14.5, f"{num(P['total'])} numbers  ·  {P['n_layers']} blocks  ·  one job: guess the next word", f"bold {MUTE}")


def target_whole(D, c):
    return c.R(38, 2, 34, 11)


def scene_blocks(c, t, D, S):
    P, B = D["params"], D["brain"]
    if t >= 0.3:
        px = c.X(2)
        for i, tok in enumerate(D["tokens"]):
            shown = typed(tok, t, 0.3 + i * 0.12, 60)
            if shown:
                c.rput(px, c.Y(1), f" {shown} ", f"bold #1e1e2e on {['#f9e2af', '#a6e3a1', '#89dceb', '#f5c2e7', '#cba6f7'][i % 5]}")
            px += len(tok) + 3
    if t >= 1.0:
        c.put(3, 2, "↓", AMBER)
    c.box(1, 3, 8, 3, GREEN if t >= 1.2 else CYAN)
    c.put_in(1, 4.5, 8, "embed", f"bold {TEXT}")
    pulse = (t - 1.2) * 5.0                                        # the pulse climbs 5 blocks per second
    n = P["n_layers"]
    c.hline(9, 11, 4.5, "─", MUTE)
    for i in range(n):
        x = 11 + 6 * i
        lit = pulse >= i
        c.hline(x + 5, x + 6, 4.5, "─", MUTE)
        c.box(x, 3, 5, 3, GREEN if lit else MUTE)
        c.put_in(x, 4.5, 5, str(i + 1), f"bold {AMBER if lit else MUTE}")
        if lit:
            conf = B.confidence[i] / max(B.confidence)
            c.put_in(x, 7, 5, LEVELS[min(7, int(conf * 7.999))], f"bold {GREEN if i + 1 >= B.lock_layer else CYAN}")
            c.put_in(x, 8, 5, B.guesses[i].strip()[:5], TEXT if i + 1 >= B.lock_layer else MUTE)
    c.hline(81, 84, 4.5, "─", MUTE)
    c.box(84, 3, 10, 3, GREEN if pulse >= n else MUTE)
    c.put_in(84, 4.5, 10, "output", f"bold {TEXT}")
    if 1.2 <= t and 0 <= pulse < n + 1:                            # the travelling pulse
        c.put(10 + 6 * min(pulse, n), 4.5, "●", f"bold {AMBER}")
    if t >= 1.2:
        c.put(1, 7, "bars", MUTE)
        c.put(1, 8, "guess", MUTE)
    if pulse >= n:
        lx = 11 + 6 * (B.lock_layer - 1)
        c.put_in(lx, 9.5, 5, "◆", f"bold {AMBER}")
        c.put(max(1, lx - 18), 10.5, f"the answer “{S['word']}” is settled by block {B.lock_layer}", f"bold {AMBER}")
        c.put_in(84, 7, 10, f"“{S['word']}”", f"bold {GREEN}")
        c.put_in(84, 8, 10, f"{D['final'][0].prob:.0%}", f"bold {GREEN}")
    if t >= 4.6:
        c.center(13, f"word table: {num(P['embed'])} numbers   ·   {n} blocks × {num(P['block'])} = {num(P['blocks'])}", f"bold {MUTE}")
        c.center(14.5, "every block has the same shape, but its own numbers", MUTE)


def target_blocks(D, c):
    return c.R(11 + 6 * 5, 3, 5, 3)


def scene_block(c, t, D, S):
    P = D["params"]
    c.center(0, f"BLOCK {D['ffn_layer'] + 1} OF {P['n_layers']}  ·  {num(P['block'])} numbers", f"bold {AMBER}")
    dim_amber = mix(AMBER, BG, 0.45)
    if t >= 0.4:
        c.hline(3, 81, 3, "━", dim_amber)
        c.put(24, 1.5, "residual stream: the notes every part adds to", f"italic {MUTE}")
    dot = (t - 1.0) * 15 % 90 if t >= 1.0 else -10                 # a dot of data flows through, over and over
    sty = lambda x, w, base: GREEN if x <= dot <= x + w else base
    if t >= 0.5:
        c.arrow(1, 6.5, 7, CYAN)
        c.vline(3, 3, 6.5, "│", dim_amber)
    if t >= 0.8:
        c.box(7, 5, 9, 5, sty(7, 9, CYAN), title="Norm")
        c.put_in(7, 7, 9, "steady", MUTE)
        c.put_in(7, 8, 9, "size", MUTE)
        c.arrow(16, 19, 7, MUTE)
    if t >= 1.2:
        c.box(19, 5, 19, 5, sty(19, 19, LAV), title="Attention")
        c.put_in(19, 7, 19, "looks around at", TEXT)
        c.put_in(19, 8, 19, "the other words", TEXT)
        c.hline(38, 40, 7, "─", MUTE)
    if t >= 1.6:
        c.put_in(40, 7, 3, "(+)", f"bold {sty(40, 3, AMBER)}")
        c.vline(41, 3, 6, "│", dim_amber)
        c.put(41, 6.3, "▼", AMBER)
        c.arrow(43, 45, 7, MUTE)
    if t >= 2.0:
        c.box(45, 5, 9, 5, sty(45, 9, CYAN), title="Norm")
        c.put_in(45, 7, 9, "steady", MUTE)
        c.put_in(45, 8, 9, "size", MUTE)
        c.arrow(54, 57, 7, MUTE)
    if t >= 2.4:
        c.box(57, 5, 21, 5, sty(57, 21, PINK), title="Feed-forward")
        c.put_in(57, 7, 21, "thinks about what", TEXT)
        c.put_in(57, 8, 21, "it found", TEXT)
        c.hline(78, 80, 7, "─", MUTE)
    if t >= 2.9:
        c.put_in(80, 7, 3, "(+)", f"bold {sty(80, 3, AMBER)}")
        c.vline(81, 3, 6, "│", dim_amber)
        c.put(81, 6.3, "▼", AMBER)
        c.arrow(83, 90, 7, MUTE)
        c.put(91, 7, "next", MUTE)
    if 1.0 <= t and 0 <= dot < 88:
        if c.at(c.X(dot), c.Y(7)) in " ─►":                        # never draw over a letter
            c.put(dot, 7, "●", f"bold {AMBER}")
        c.put(min(max(dot, 3), 80), 3, "●", f"bold {AMBER}")
    if t >= 3.2:
        c.put_in(7, 11, 9, f"{num(P['norms'] // 2)} numbers", MUTE)
        c.put_in(19, 11, 19, f"{num(P['attn'])} numbers", LAV)
        c.put_in(19, 12, 19, f"{P['n_heads']} heads", MUTE)
        c.put_in(57, 11, 21, f"{num(P['ffn'])} numbers", PINK)
        c.put_in(57, 12, 21, f"{num(P['hidden'])} neurons", MUTE)
    if t >= 4.2:
        c.center(15, "first: look around (attention)   ·   then: think (feed-forward)   ·   repeat", f"bold {MUTE}")


def target_block(D, c):
    return c.R(19, 5, 19, 5)


def scene_attention(c, t, D, S):
    hd, toks = D["head"], D["tokens"]
    T, M = len(toks), hd["matrix"]
    c.put(2, 0, f"BLOCK {hd['layer'] + 1} · HEAD {hd['head'] + 1}: who does each word look at?", f"bold {AMBER}")
    for r in range(T):
        if t < 0.6 + 0.35 * r:
            break
        lbl = word(toks[r])[:9]
        py = c.Y(2 + r)
        rows = max(1, (c.Y(3 + r) - py) - (1 if c.Y(3 + r) - py > 2 else 0))
        c.rput(c.X(10) - len(lbl), py, lbl, f"bold {AMBER if r == T - 1 else TEXT}")
        for k in range(r + 1):
            px = c.X(11 + 3 * k)
            cw = max(2, c.X(11 + 3 * (k + 1)) - px - 1)
            for dy in range(rows):
                c.rput(px, py + dy, "█" * cw, heat(float(M[r, k])))
        if r == T - 1:
            c.rput(c.X(11 + 3 * T) + 2, py, "◄ asking", AMBER)
    if t >= 3.6:
        c.put(2, 11.5, "dark = ignores   bright = looks a lot", MUTE)
        c.put(2, 13, f"“{word(toks[-1])}” puts {hd['p']:.0%} of its attention on", f"bold {TEXT}")
        c.put(2, 14.2, f"“{word(toks[hd['target']])}”", f"bold {GREEN}")
    if t >= 2.0:
        c.put(52, 0, f"ALL {len(D['heads_here'])} HEADS OF BLOCK {hd['layer'] + 1}", f"bold {AMBER}")
        c.put(52, 1.1, f"where does “{word(toks[-1])}” look?", MUTE)
        for h, tgt, p in D["heads_here"]:
            if t < 2.0 + 0.18 * h:
                break
            mark = h == hd["head"]
            y = 2.6 + 1.0 * h
            c.put(52, y, f"head {h + 1:>2}", f"bold {AMBER}" if mark else MUTE)
            c.put(60, y, f"{word(toks[tgt])[:8]:<8}", f"bold {GREEN}" if mark else TEXT)
            c.rput(c.X(69), c.Y(y), "█" * max(1, round(p * 14 * c.sx)), GREEN if mark else CYAN)
            c.put(86, y, f"{p:4.0%}", f"bold {TEXT}")
    if t >= 5.0:
        c.put(52, 15.7, "most heads rest on the first word when idle", f"italic {MUTE}")


def target_attention(D, c):
    return c.R(51, 0, 45, 16)


def scene_ffn(c, t, D, S):
    a, nn = D["acts"], D["neuron"]
    amax = float(abs(a).max())
    cols = 64
    x0 = c.X(2)
    dw = max(1, (c.X(66) - x0) // cols)                            # screen columns per neuron
    dh = c.sy                                                      # screen rows per pair of neurons
    reveal = (t - 0.5) * 22
    for col in range(cols):
        for cell in range(16):
            vals = []
            for half in range(2):
                idx = (cell * 2 + half) * cols + col
                if col < reveal:
                    v = float(a[idx]) / amax
                    m = min(1.0, abs(v))
                    vals.append(mix("#313244", CYAN if v >= 0 else PINK, m / 0.25 * 0.3 if m < 0.25 else 0.6 + 0.4 * m))
                else:
                    vals.append("#26273a")
            top, bot = vals
            n = nn["index"]
            if t >= 3.4 and int(t * 4) % 2 == 0 and n % cols == col:
                if n // cols == cell * 2:
                    top = "#ffffff"
                elif n // cols == cell * 2 + 1:
                    bot = "#ffffff"
            for dy in range(dh):
                c.rput(x0 + col * dw, c.Y(0) + cell * dh + dy, "▀" * dw, f"{top} on {bot}")
    lit = int((abs(a) > 0.25 * amax).sum())
    x = 70
    c.put(x, 1, f"BLOCK {D['ffn_layer'] + 1} · FEED-FORWARD", f"bold {AMBER}")
    if t >= 1.5:
        c.put(x, 3, f"{num(len(a))} neurons,", TEXT)
        c.put(x, 4, "one dot each", TEXT)
    if t >= 3.0:
        c.put(x, 6, f"{lit} of {num(len(a))} light up", f"bold {GREEN}")
        c.put(x, 7, f"for “{word(D['tokens'][-1])}”", f"bold {GREEN}")
        c.put(x, 8, "(above ¼ of the strongest)", MUTE)
    if t >= 3.8:
        c.put(x, 10, "▀", CYAN)
        c.put(x + 2, 10, "positive", MUTE)
        c.put(x, 11, "▀", PINK)
        c.put(x + 2, 11, "negative", MUTE)
    if t >= 4.4:
        c.put(x, 13, f"brightest: neuron #{nn['index']}", f"bold {TEXT}")
        c.put(x, 14, "blinking: zooming in", MUTE)


def target_ffn(D, c):
    n = D["neuron"]["index"]
    dw = max(1, (c.X(66) - c.X(2)) // 64)
    dh = c.sy
    return (c.X(2) + (n % 64) * dw, c.Y(0) + ((n // 64) // 2) * dh, dw, dh)


def silu(v):
    return v / (1 + math.exp(-v))


def scene_neuron(c, t, D, S):
    nn = D["neuron"]
    c.put(2, 0, f"NEURON #{nn['index']} OF BLOCK {D['ffn_layer'] + 1}", f"bold {AMBER}")
    c.put(2, 1.5, "input", MUTE)
    c.put(12, 1.5, "weight", MUTE)
    c.put(22, 1.5, "input × weight", MUTE)
    for i, (idx, h, w, p) in enumerate(nn["top"]):
        if t >= 0.8 + 0.5 * i:
            y = 3 + i
            c.put(2, y, f"x{idx:<4}{h:+7.2f}", TEXT)
            c.put(14, y, f"× {w:+6.3f}", TEXT)
            c.put(26, y, f"= {p:+7.3f}", f"bold {CYAN if p >= 0 else PINK}")
    if t >= 3.4:
        c.put(2, 8, f"… and {nn['n_inputs'] - 5} more inputs", MUTE)
        c.put(26, 8, f"= {nn['rest']:+7.3f}", f"bold {CYAN if nn['rest'] >= 0 else PINK}")
    if t >= 3.9:
        c.hline(2, 38, 9, "─", MUTE)
        c.put(2, 10, f"ADD THEM ALL UP  = {nn['pre'] * ease((t - 3.9) / 0.8):+7.3f}", f"bold {AMBER}")
    if t >= 5.0:                                                   # the bend
        px, py, pw, ph = c.R(48, 2, 46, 11)
        c.rbox(px, py, pw, ph, MUTE, title="the bend (SiLU)")
        iw, ih = pw - 4, ph - 3
        lo, hi = -0.5, 4.0
        row_of = lambda v: py + ph - 2 - round((v - lo) / (hi - lo) * (ih - 1))
        for ix in range(iw):
            c.rput(px + 2 + ix, max(py + 1, min(py + ph - 2, row_of(silu(-4 + 8 * ix / (iw - 1))))), "▪", CYAN)
        c.rput(px + 3, py + 1, "out", MUTE)
        c.rput(px + pw - 6, py + ph - 1, "in →", MUTE)
        pos = ease((t - 5.4) / 1.4) * (nn["pre"] + 4) - 4 if t >= 5.4 else -4
        c.rput(px + 2 + round((pos + 4) / 8 * (iw - 1)), max(py + 1, min(py + ph - 2, row_of(silu(pos)))), "●", f"bold {AMBER}")
    if t >= 6.9:
        c.put(2, 12, f"after the bend  = {nn['silu']:+7.3f}", TEXT)
        c.put(2, 13.2, f"× a second sum  = {nn['up']:+7.3f}", TEXT)
    if t >= 7.6:
        c.put(2, 15, f"NEURON OUTPUT   = {nn['out']:+7.3f}", f"bold {GREEN}")


def target_neuron(D, c):
    return c.R(2, 12, 38, 4)


def scene_out(c, t, D, S):
    P = D["params"]
    levels = [
        (0, 0, 96, 17, f" MONA · {num(P['total'])} numbers ", f"+ {num(P['embed'])} numbers in the word table"),
        (12, 2, 72, 13, f" {P['n_layers']} blocks · {num(P['blocks'])} numbers ", None),
        (23, 4, 50, 9, f" 1 block · {num(P['block'])} numbers ", None),
        (33, 6, 30, 5, f" {num(P['hidden'])} neurons ", None),
        (42, 7, 12, 3, None, None),
    ]
    for step, idx in enumerate((4, 3, 2, 1, 0)):                    # inner to outer
        if t < 0.6 + 0.9 * step:
            continue
        x, y, w, h, title, foot = levels[idx]
        style = [CYAN, LAV, PINK, GREEN, AMBER][step]
        c.box(x, y, w, h, style, title=title, title_style=f"bold {style}")
        if idx == 4:
            c.put_in(x, y + 1.2, w, "1 neuron", f"bold {AMBER}")
        if foot:
            px, py, pw, ph = c.R(x, y, w, h)
            c.rput(px + 2, py + ph - 1, f" {foot} ", f"bold {MUTE}")
    if t >= 5.2:
        c.center(15.3, "inside every neuron: multiply, add, bend", f"bold {AMBER}")


def target_out(D, c):
    return c.R(42, 7, 12, 3)


# ── what kind of model she is ────────────────────────────────────────────────
PUBLISHED = [("Llama 3 · 8B", 8e9), ("Llama 3 · 70B", 70e9), ("GPT-3 · 175B", 175e9), ("Llama 3.1 · 405B", 405e9)]


def scene_mini(c, t, D, S):
    P = D["params"]
    c.center(0.3, "I AM AN LLM: A LARGE LANGUAGE MODEL, BUT A VERY SMALL ONE", f"bold {AMBER}")
    rows = [("MONA (me)", float(P["total"]), CYAN)] + [(name, v, MUTE) for name, v in PUBLISHED]
    for i, (name, v, colour) in enumerate(rows):
        t0 = 0.8 + 0.7 * i
        if t < t0:
            continue
        y = 2.8 + 2.0 * i
        c.put(2, y, name, f"bold {AMBER if i == 0 else TEXT}")
        frac = (math.log10(v) - 7) / 5                              # log scale: 10 million .. 10 trillion
        full = round(46 * frac * c.sx)
        n = round(full * ease((t - t0) / 0.8))
        c.rput(c.X(24), c.Y(y), "█" * n, colour)
        if n >= full:
            c.rput(c.X(24) + full + 2, c.Y(y), human(v) + " numbers", f"bold {GREEN if i == 0 else MUTE}")
    if t >= 4.8:
        c.put(24, 13, "log scale: every step to the right is 10 times bigger", f"italic {MUTE}")
    if t >= 5.5:
        c.put(2, 14.2, f"text read:  MONA {human(2.5e9)} tokens   ·   Llama 3: 15 trillion tokens", MUTE)
        c.put(2, 15.4, "(the Llama and GPT-3 figures are the published ones)", f"italic {MUTE}")


def target_mini(D, c):
    return c.R(2, 2.4, 40, 1.6)


def scene_transformer(c, t, D, S):
    toks = D["tokens"]
    c.put(2, 0.3, "A TRANSFORMER READS LEFT TO RIGHT", f"bold {AMBER}")
    n = min(8, len(toks))
    cell_rows = max(1, c.sy - 1) if c.sy > 1 else 1
    for r in range(n):
        if t < 0.5 + 0.3 * r:
            break
        py = c.Y(2 + r)
        lbl = word(toks[r])[:7]
        c.rput(c.X(9) - len(lbl), py, lbl, TEXT)
        for k in range(n):
            px = c.X(10 + 3 * k)
            cw = max(2, c.X(10 + 3 * (k + 1)) - px - 1)
            ok = k <= r
            for dy in range(cell_rows):
                c.rput(px, py + dy, ("█" if ok else "░") * cw, CYAN if ok else "#313244")
    if t >= 3.4:
        c.put(2, 11.5, "each word may look only at the words before it:", TEXT)
        c.put(2, 12.7, "the “causal mask” (dark = not allowed)", MUTE)
    # right: write one word at a time, with MONA's real numbers
    c.put(40, 0.3, "…AND WRITES ONE WORD AT A TIME  (my real numbers)", f"bold {AMBER}")
    steps, per = D["steps"], 2.6
    if t >= 1.5:
        cur = min(int((t - 1.5) / per), len(steps) - 1)
        st, phase = steps[cur], t - 1.5 - per * cur
        picked = phase >= 1.5 or t >= 1.5 + per * len(steps)
        shown_ctx = D["prompt"] + "".join(x["text"] for x in steps[:cur]) + (st["text"] if picked else "")
        c.put(40, 2, "“" + shown_ctx[-52:] + ("▌" if not picked else "") + "”", f"bold {TEXT}")
        c.put(40, 3.4, f"step {cur + 1} of {len(steps)}: what could come next?", MUTE)
        alts = st["alts"][:5]
        top = max(p for _, p in alts) or 1.0
        for j, (a, p) in enumerate(alts):
            y = 5 + 1.0 * j
            chosen = a == st["text"] and picked
            bar = max(1, round(24 * c.sx / 2 * p / top))
            c.put(40, y, f"{a.strip()[:9]:<9}", f"bold {GREEN if chosen else TEXT}")
            c.rput(c.X(50), c.Y(y), "█" * bar, GREEN if chosen else CYAN)
            c.rput(c.X(50) + bar + 1, c.Y(y), f"{p:4.0%}" + ("  ◄ picked" if chosen else ""), f"bold {GREEN if chosen else MUTE}")
    if t >= 1.5 + per * len(steps):
        c.center(12.8, "guess  →  pick  →  add the word  →  guess again", f"bold {AMBER}", x0=38)
    c.put(40, 14.6, "that loop is all that generating text ever is", f"italic {MUTE}")


def target_transformer(D, c):
    return c.R(40, 1.5, 55, 12)


ARROWS = "→↗↑↖←↙↓↘"


def arrow_for(deg):
    return ARROWS[round((deg % 360) / 45) % 8]


def scene_llama(c, t, D, S):
    P, nn, rope = D["params"], D["neuron"], D["rope"]
    c.center(0, "MY BLUEPRINT IS LLAMA-STYLE: FOUR UPGRADES OVER THE 2017 TRANSFORMER", f"bold {AMBER}")
    panels = [(1, 1, "1  RMSNorm: tidy the numbers", LAV), (49, 1, "2  RoPE: position by rotation", PINK),
              (1, 9, "3  SwiGLU: a gate decides", GREEN), (49, 9, "4  Tied embeddings: one table, two jobs", CYAN)]
    for i, (x, y, title, colour) in enumerate(panels):
        if t >= 0.6 + 1.9 * i:
            c.box(x, y, 46, 7, colour, title=title, title_style=f"bold {colour}")
    f = lambda v: f"{v:+.2f}"
    if t >= 1.0:
        c.put(3, 3, "before: " + " ".join(f"{f(v):>6}" for v in D["rms_in"]), TEXT)
        c.put(3, 4, f"÷ rms {D['rms']:.2f}  (the typical size)", MUTE)
        c.put(3, 5, "after:  " + " ".join(f"{f(v):>6}" for v in D["rms_out"]), GREEN)
    if t >= 2.9:
        c.put(51, 2, "word:     " + "  ".join(f"{i}" for i in range(8)), MUTE)
        c.put(51, 3, "fast dial " + "  ".join(arrow_for(a) for a in rope["fast"]), TEXT)
        c.put(51, 4, "slow dial " + "  ".join(arrow_for(a) for a in rope["slow"]), TEXT)
        c.put(51, 6, f"the fast dial turns {rope['fast'][1]:.0f}° per word", MUTE)
    if t >= 4.8:
        c.put(3, 11, f"gate  = silu({nn['pre']:+.2f}) = {nn['silu']:+.2f}", TEXT)
        c.put(3, 12, f"up    = {nn['up']:+.2f}", TEXT)
        c.put(3, 13, f"out   = gate × up = {nn['out']:+.2f}", f"bold {GREEN}")
    if t >= 6.7:
        c.put(51, 11, "reading words  : table → numbers", TEXT)
        c.put(51, 12, "writing words  : numbers → table", TEXT)
        c.put(51, 13, f"same {num(P['embed'])} numbers: saves {P['embed'] / P['total']:.0%}", f"bold {GREEN}")
    if t >= 8.0:
        c.center(16, "also: flash attention (same maths, much faster)  ·  KV-cache (never redo old work)", f"bold {MUTE}")


def target_llama(D, c):
    return c.R(1, 1, 94, 15)


def scene_final(c, t, D, S):
    P = D["params"]
    c.box(8, 1, 80, 12, CYAN, title="WHAT I AM")
    lines = [
        (f"an LLM: a large language model, but a small one ({human(P['total'])} numbers)", TEXT),
        (f"a decoder-only TRANSFORMER: attention + feed-forward, {P['n_layers']} blocks", TEXT),
        ("LLAMA-STYLE: RMSNorm · RoPE · SwiGLU · tied embeddings", TEXT),
        (f"I read up to {num(P['context'])} tokens at once, from {num(P['vocab'])} word-pieces", TEXT),
        (f"trained from scratch on {human(2.5e9)} tokens, on one laptop", TEXT),
        ("not smart · not always right · completely open", f"bold {GREEN}"),
    ]
    for i, (line, style) in enumerate(lines):
        if t >= 0.6 + 0.8 * i:
            c.put_in(8, 3 + 1.4 * i, 80, line, style)
    if t >= 6.0:
        c.center(14.6, "ENTER  →  begin the course", f"bold {GREEN}")


def target_final(D, c):
    return c.R(8, 1, 80, 12)


SCENES = [
    dict(title="Meet MONA", draw=scene_whole, target=target_whole, caption="into the box", anim=5.5,
         say="This is me, MONA. Words go in, and out comes one thing: a guess for the next word. Inside this box are "
             "{total} numbers, and nothing else. No rules, no dictionary, no grammar book. Let's open the box and see "
             "how numbers can guess words."),
    dict(title="12 blocks", draw=scene_blocks, target=target_blocks, caption="into block 6", anim=5.0,
         say="First your words are turned into numbers. Then they climb through {nb} blocks, one after another. Watch "
             "the bars: after every block I already have a guess, and it gets better as the numbers climb. For this "
             "sentence my answer, “{word}”, was settled by block {lock}. Let's dive into one block."),
    dict(title="One block", draw=scene_block, target=target_block, caption="into attention", anim=4.5,
         say="Every block is built the same way. First comes attention: each word looks around at the other words. Then "
             "comes the feed-forward part: I think about what I found. A shortcut line, the residual stream, carries "
             "what I already know so nothing gets lost. One block holds {block} numbers, and I have {nb} of them. "
             "First, attention."),
    dict(title="Attention", draw=scene_attention, target=target_attention, caption="into the feed-forward", anim=5.5,
         say="In attention, every word asks: which earlier words matter to me? This is block {l}, head {h}. When it "
             "reads “{last}”, {p} of its attention goes to “{tw}”{tw_note}. Each block has {nh} heads, each learning its "
             "own way of looking, and most rest on the first word when they have nothing to do. Now, the thinking part."),
    dict(title="Neurons", draw=scene_ffn, target=target_ffn, caption="into one neuron", anim=5.0,
         say="Here is the thinking part: {hidden} tiny workers called neurons, one dot each. For the word “{last}”, only "
             "{lit} of them light up strongly; the rest stay quiet. Cyan means positive, pink means negative. "
             "Let's zoom into the brightest one, neuron number {nidx}."),
    dict(title="One neuron", draw=scene_neuron, target=target_neuron, caption="zooming back out", anim=8.2,
         say="A neuron is simpler than it sounds. It looks at {n_in} numbers, multiplies each by its own weight, and adds "
             "everything up. Here that sum is {pre}. Then comes a gentle bend, called SiLU, and a second weighted sum "
             "scales it. The result: {out}. That's all: multiply, add, bend. No magic."),
    dict(title="Zoom out", draw=scene_out, target=target_out, caption="so what am I?", anim=6.0,
         say="Zoom back out. One neuron. {hidden} of them make a feed-forward layer. Add attention and you get a block. "
             "{nb} blocks, plus a table that turns words into numbers, make {total} numbers: me. So what kind of "
             "thing am I, exactly? Let me tell you."),
    dict(title="A mini LLM", draw=scene_mini, target=target_mini, caption="how I write", anim=6.5,
         say="I am an LLM, a large language model: a model that learned from a huge amount of text to guess the next "
             "word. But I am a very small one. I have {total} numbers. GPT-3 has 175 billion, and the biggest Llama has "
             "405 billion. They also read thousands of times more text than I did. The recipe is the same, which is "
             "why I can show you all of it."),
    dict(title="A transformer", draw=scene_transformer, target=target_transformer, caption="my blueprint", anim=13.0,
         say="My design is called a transformer, invented in 2017, and its big idea is attention. I am a decoder-only "
             "transformer: I read left to right, and every word may look only at the words before it, never ahead. "
             "That triangle is the causal mask. To write, I repeat one loop: guess the next word, pick one, add it, and "
             "guess again. Here it is with my real numbers."),
    dict(title="Llama-style", draw=scene_llama, target=target_llama, caption="so, in short", anim=9.0,
         say="My blueprint is the one Llama uses, so I'm called Llama-style. Four upgrades over the original 2017 "
             "transformer. RMSNorm keeps numbers tidy with less work. RoPE tells me word order by rotating each "
             "word's numbers. SwiGLU gives the feed-forward part a gate. And tied embeddings reuse one word table for "
             "reading and writing, saving {embed} numbers. Llama, Mistral and Qwen use these same ideas."),
    dict(title="That's me", draw=scene_final, target=target_final, caption="", anim=7.0,
         say="That's me: a small, honest LLM. A decoder-only transformer with a Llama-style blueprint, built from "
             "scratch on one laptop. I will make mistakes, and that is part of the lesson. Everything you explore from "
             "here is one of the pieces you just saw. Press Enter, and let's begin."),
]


def derive(D):
    """Words and numbers used in the narration, all taken from the real data."""
    P, hd, nn = D["params"], D["head"], D["neuron"]
    toks = D["tokens"]
    a = D["acts"]
    return dict(total=num(P["total"]), nb=P["n_layers"], block=num(P["block"]), hidden=num(P["hidden"]), embed=num(P["embed"]),
                word=D["final"][0].token.text.strip(), lock=D["brain"].lock_layer, l=hd["layer"] + 1, h=hd["head"] + 1,
                last=word(toks[-1]), p=f"{hd['p']:.0%}", tw=word(toks[hd["target"]]),
                tw_note=", the word right before it" if hd["target"] == len(toks) - 2 else "", nh=P["n_heads"],
                lit=int((abs(a) > 0.25 * abs(a).max()).sum()), nidx=nn["index"], n_in=nn["n_inputs"],
                pre=f"{nn['pre']:+.3f}", out=f"{nn['out']:+.3f}")


class ZoomScreen(LessonScreen):
    SCENES = SCENES

    def compute(self, gb):
        return zoomdata.compute(gb)

    def derive(self, D):
        return derive(D)

    def finished(self):
        self.app.state.complete("zoom")
        self.app.pop_screen()
