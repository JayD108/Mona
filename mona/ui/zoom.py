"""Inside MONA: an animated zoom from the whole model down to a single neuron.

Seven scenes. Every number on screen is MONA's real data (see zoomdata.py); the narration is written by hand.
The camera "dives" into a box of each scene to get to the next one. Controls: Space pause / resume autoplay,
Enter or → next, ← back, R replay the scene, Esc leave.
"""
import math
import time

from rich.text import Text
from textual import work
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical
from textual.screen import Screen
from textual.widgets import Static

from . import zoomdata
from .brain import LEVELS
from .canvas import Canvas

W, H = 96, 17
FPS = 30
TRANSITION = 1.1
CPS = 62                                  # narration typing speed
HOLD = 3.5                                # seconds to linger after a scene has finished

CYAN, AMBER, GREEN, PINK, TEXT, MUTE, MAUVE, LAV = ("#89dceb", "#f9e2af", "#a6e3a1", "#f5c2e7", "#cdd6f4", "#9399b2",
                                                    "#cba6f7", "#b4befe")
BASE = (0x31, 0x32, 0x44)


def _rgb(h):
    return tuple(int(h[i:i + 2], 16) for i in (1, 3, 5))


def mix(a, b, t):
    a, b = (_rgb(a) if isinstance(a, str) else a), (_rgb(b) if isinstance(b, str) else b)
    t = max(0.0, min(1.0, t))
    return "#%02x%02x%02x" % tuple(round(a[i] + (b[i] - a[i]) * t) for i in range(3))


def heat(v):
    """0 -> dark, 1 -> bright: dark blue, cyan, then amber."""
    v = max(0.0, min(1.0, v)) ** 0.6
    return mix("#313244", CYAN, v * 2) if v < 0.5 else mix(CYAN, AMBER, (v - 0.5) * 2)


def typed(s, t, t0, cps=40):
    return s[: max(0, int((t - t0) * cps))]


def ease(x):
    x = max(0.0, min(1.0, x))
    return x * x * (3 - 2 * x)


def num(n):
    return f"{n:,}"


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
        n = int(ease((t - 2.0) / 0.8) * 34)
        c.put(2, 8, "━" * max(0, n - 1) + ("►" if n else ""), AMBER)
    if t >= 2.4:                                                   # real weights, flickering past
        W_ = D["weights"]
        off = int(t * 7)
        for r in range(9):
            row = W_[(off + r * 3) % len(W_)]
            c.put(40, 3 + r, " ".join(f"{row[(off // 3 + k) % len(row)]:+.3f}" for k in range(4)), mix(MUTE, CYAN, 0.5 + 0.5 * math.sin(t * 3 + r)))
    if t >= 3.8:
        c.put(74, 8, "►", AMBER)
        c.put(76, 3, "NEXT WORD GUESS", f"bold {AMBER}")
        for i, g in enumerate(D["final"][:3]):
            if t >= 3.9 + 0.35 * i:
                word = g.token.text.strip()[:6]
                filled = max(1, round(8 * g.prob / D["final"][0].prob))
                c.put(76, 5 + i, f"{word:<6}", f"bold {TEXT}")
                c.put(83, 5 + i, "█" * filled + "░" * (8 - filled), CYAN)
                c.put(92, 5 + i, f"{g.prob:3.0%}", f"bold {GREEN}")
    if t >= 5.0:
        c.center(14, f"{num(P['total'])} numbers  ·  {P['n_layers']} blocks  ·  one job: guess the next word", f"bold {MUTE}")


def target_whole(D):
    return (38, 2, 34, 11)


def scene_blocks(c, t, D, S):
    P, B = D["params"], D["brain"]
    if t >= 0.3:
        x = 2
        for i, tok in enumerate(D["tokens"]):
            shown = typed(tok, t, 0.3 + i * 0.12, 60)
            if shown:
                c.put(x, 1, f" {shown} ", f"bold #1e1e2e on {['#f9e2af', '#a6e3a1', '#89dceb', '#f5c2e7', '#cba6f7'][i % 5]}")
            x += len(tok) + 3
    if t >= 1.0:
        c.put(4, 2, "↓", AMBER)
    c.box(1, 3, 8, 3, GREEN if t >= 1.2 else CYAN, title=None)
    c.put(2, 4, "embed", f"bold {TEXT}")
    pulse = (t - 1.2) * 5.0                                        # the pulse climbs 5 blocks per second
    n = P["n_layers"]
    c.put(9, 4, "─", MUTE)
    for i in range(n):
        x = 11 + 6 * i
        lit = pulse >= i
        c.box(x, 3, 5, 3, GREEN if lit else MUTE)
        c.put(x + 1, 4, f"{i + 1:^3}", f"bold {AMBER if lit else MUTE}")
        c.put(x + 5, 4, "─", MUTE)
        if lit:
            conf = B.confidence[i] / max(B.confidence)
            c.put(x + 2, 7, LEVELS[min(7, int(conf * 7.999))], f"bold {GREEN if i + 1 >= B.lock_layer else CYAN}")
            c.put(x, 8, B.guesses[i].strip()[:5].ljust(5), TEXT if i + 1 >= B.lock_layer else MUTE)
    c.box(84, 3, 10, 3, GREEN if pulse >= n else MUTE)
    c.put(86, 4, "output", f"bold {TEXT}")
    c.put(82, 4, "►", MUTE)
    if 1.2 <= t and 0 <= pulse < n + 1:                            # the travelling pulse
        px = 10 + 6 * min(pulse, n)
        c.put(int(px), 4, "●", f"bold {AMBER}")
    if t >= 1.2:
        c.put(1, 7, "bars", MUTE)
        c.put(1, 8, "guess", MUTE)
    if pulse >= n:
        lx = 11 + 6 * (B.lock_layer - 1) + 2
        c.put(lx, 9, "◆", f"bold {AMBER}")
        c.put(max(1, lx - 20), 10, f"the answer “{S['word']}” is settled by block {B.lock_layer}", f"bold {AMBER}")
        c.put(84 + 1, 7, f"“{S['word']}”", f"bold {GREEN}")
        c.put(84 + 1, 8, f"{D['final'][0].prob:.0%}", f"bold {GREEN}")
    if t >= 4.6:
        c.center(13, f"word table: {num(P['embed'])} numbers   ·   {n} blocks × {num(P['block'])} = {num(P['blocks'])}", f"bold {MUTE}")
        c.center(14, "every block has the same shape, but its own numbers", MUTE)


def target_blocks(D):
    return (11 + 6 * 5, 3, 5, 3)


def scene_block(c, t, D, S):
    P = D["params"]
    c.center(0, f"BLOCK {D['ffn_layer'] + 1} OF {P['n_layers']}  ·  {num(P['block'])} numbers", f"bold {AMBER}")
    if t >= 0.4:
        c.hline(3, 81, 3, "━", mix(AMBER, "#1e1e2e", 0.45))
        c.put(24, 2, "residual stream: the notes every part adds to", f"italic {MUTE}")
    parts = [("in", 2, None), ("norm1", 7, 9), ("attn", 19, 19), ("plus1", 40, 3), ("norm2", 45, 9), ("ffn", 57, 21), ("plus2", 80, 3)]
    dot = (t - 1.0) * 15 % 90 if t >= 1.0 else -10                 # a dot of data flows through, over and over

    def inside(x, w):
        return x <= dot <= x + w
    def sty(x, w, base):
        return GREEN if inside(x, w) else base
    shows = {"norm1": 0.8, "attn": 1.2, "plus1": 1.6, "norm2": 2.0, "ffn": 2.4, "plus2": 2.9}
    c.put(1, 7, "──┬──►" if t >= 0.5 else "", CYAN)
    c.vline(3, 4, 6, "│", mix(AMBER, "#1e1e2e", 0.45))
    if t >= shows["norm1"]:
        c.box(7, 5, 9, 5, sty(7, 9, CYAN), title="Norm")
        c.put(8, 7, "steady", MUTE)
        c.put(8, 8, "size", MUTE)
        c.put(16, 7, "──►", MUTE)
    if t >= shows["attn"]:
        c.box(19, 5, 19, 5, sty(19, 19, LAV), title="Attention")
        c.put(21, 7, "looks around at", TEXT)
        c.put(21, 8, "the other words", TEXT)
        c.put(38, 7, "──", MUTE)
    if t >= shows["plus1"]:
        c.put(40, 7, "(+)", f"bold {sty(40, 3, AMBER)}")
        c.vline(41, 4, 6, "│", mix(AMBER, "#1e1e2e", 0.45))
        c.put(41, 6, "▼", AMBER)
        c.put(43, 7, "──►", MUTE)
    if t >= shows["norm2"]:
        c.box(45, 5, 9, 5, sty(45, 9, CYAN), title="Norm")
        c.put(46, 7, "steady", MUTE)
        c.put(46, 8, "size", MUTE)
        c.put(54, 7, "──►", MUTE)
    if t >= shows["ffn"]:
        c.box(57, 5, 21, 5, sty(57, 21, PINK), title="Feed-forward")
        c.put(59, 7, "thinks about what", TEXT)
        c.put(59, 8, "it found", TEXT)
        c.put(78, 7, "──", MUTE)
    if t >= shows["plus2"]:
        c.put(80, 7, "(+)", f"bold {sty(80, 3, AMBER)}")
        c.vline(81, 4, 6, "│", mix(AMBER, "#1e1e2e", 0.45))
        c.put(81, 6, "▼", AMBER)
        c.put(83, 7, "─► next", MUTE)
    if 1.0 <= t and 0 <= dot < 88:
        if c.ch[7][int(dot)] in " ─►":                             # never draw over a letter
            c.put(int(dot), 7, "●", f"bold {AMBER}")
        c.put(min(max(int(dot), 3), 80), 3, "●", f"bold {AMBER}")
    if t >= 3.2:
        c.put(8, 11, f"{num(P['norms'] // 2)} numbers", MUTE)
        c.put(21, 11, f"{num(P['attn'])} numbers", LAV)
        c.put(21, 12, f"{P['n_heads']} heads", MUTE)
        c.put(59, 11, f"{num(P['ffn'])} numbers", PINK)
        c.put(59, 12, f"{num(P['hidden'])} neurons", MUTE)
    if t >= 4.2:
        c.center(15, "first: look around (attention)   ·   then: think (feed-forward)   ·   repeat", f"bold {MUTE}")


def target_block(D):
    return (19, 5, 19, 5)


def scene_attention(c, t, D, S):
    hd, toks = D["head"], D["tokens"]
    T = len(toks)
    M = hd["matrix"]
    c.put(2, 0, f"BLOCK {hd['layer'] + 1} · HEAD {hd['head'] + 1}: who does each word look at?", f"bold {AMBER}")
    for r in range(T):
        if t < 0.6 + 0.35 * r:
            break
        c.put(0, 2 + r, toks[r].replace("▁", " ").strip()[:9].rjust(9), f"bold {AMBER if r == T - 1 else TEXT}")
        for k in range(r + 1):
            c.put(11 + 3 * k, 2 + r, "██", heat(float(M[r, k])))
        if r == T - 1:
            c.put(11 + 3 * T + 1, 2 + r, "◄ asking", AMBER)
    if t >= 3.6:
        c.put(2, 11, "dark = ignores   bright = looks a lot", MUTE)
        c.put(2, 13, f"“{toks[-1].replace('▁', '')}” puts {hd['p']:.0%} of its attention on", f"bold {TEXT}")
        c.put(2, 14, f"“{toks[hd['target']].replace('▁', '')}”", f"bold {GREEN}")
    if t >= 2.0:
        c.put(52, 0, f"ALL {len(D['heads_here'])} HEADS OF BLOCK {hd['layer'] + 1}", f"bold {AMBER}")
        c.put(52, 1, f"where does “{toks[-1].replace('▁', '')}” look?", MUTE)
        for h, tgt, p in D["heads_here"]:
            if t < 2.0 + 0.18 * h:
                break
            mark = h == hd["head"]
            word = toks[tgt].replace("▁", "")[:8]
            c.put(52, 3 + h, f"head {h + 1:>2}", f"bold {AMBER}" if mark else MUTE)
            c.put(60, 3 + h, f"{word:<8}", f"bold {GREEN}" if mark else TEXT)
            c.put(69, 3 + h, "█" * max(1, round(p * 14)), GREEN if mark else CYAN)
            c.put(84, 3 + h, f"{p:4.0%}", f"bold {TEXT}")
    if t >= 5.0:
        c.put(52, 16, "most heads rest on the first word when idle", f"italic {MUTE}")


def target_attention(D):
    return (51, 0, 45, 16)


def scene_ffn(c, t, D, S):
    a, nn = D["acts"], D["neuron"]
    amax = float(abs(a).max())
    cols, rows = 64, 32
    reveal = (t - 0.5) * 22
    for col in range(cols):
        for cell in range(16):
            vals = []
            for half in range(2):
                idx = (cell * 2 + half) * cols + col
                if col < reveal:
                    v = float(a[idx]) / amax
                    base = CYAN if v >= 0 else PINK
                    m = min(1.0, abs(v))
                    vals.append(mix("#313244", base, m / 0.25 * 0.3 if m < 0.25 else 0.6 + 0.4 * m))
                else:
                    vals.append("#26273a")
            top, bot = vals
            if t >= 3.4 and nn["index"] // cols == cell * 2 + 0 and nn["index"] % cols == col:
                top = "#ffffff" if int(t * 4) % 2 == 0 else top
            if t >= 3.4 and nn["index"] // cols == cell * 2 + 1 and nn["index"] % cols == col:
                bot = "#ffffff" if int(t * 4) % 2 == 0 else bot
            c.put(2 + col, cell, "▀", f"{top} on {bot}")
    lit = int((abs(a) > 0.25 * amax).sum())
    x = 70
    c.put(x, 1, f"BLOCK {D['ffn_layer'] + 1} · FEED-FORWARD", f"bold {AMBER}")
    if t >= 1.5:
        c.put(x, 3, f"{num(len(a))} neurons,", TEXT)
        c.put(x, 4, "one dot each", TEXT)
    if t >= 3.0:
        c.put(x, 6, f"{lit} of {num(len(a))} light up", f"bold {GREEN}")
        c.put(x, 7, f"for “{D['tokens'][-1].replace('▁', '')}”", f"bold {GREEN}")
        c.put(x, 8, "(above ¼ of the strongest)", MUTE)
    if t >= 3.8:
        c.put(x, 10, "▀", CYAN)
        c.put(x + 2, 10, "positive", MUTE)
        c.put(x, 11, "▀", PINK)
        c.put(x + 2, 11, "negative", MUTE)
    if t >= 4.4:
        c.put(x, 13, f"brightest: neuron #{nn['index']}", f"bold {TEXT}")
        c.put(x, 14, "blinking: zooming in", MUTE)


def target_ffn(D):
    n = D["neuron"]["index"]
    return (2 + n % 64 - 1, (n // 64) // 2 - 1, 3, 3)


def silu(v):
    return v / (1 + math.exp(-v))


def scene_neuron(c, t, D, S):
    nn = D["neuron"]
    c.put(2, 0, f"NEURON #{nn['index']} OF BLOCK {D['ffn_layer'] + 1}", f"bold {AMBER}")
    c.put(2, 1, "input", MUTE)
    c.put(11, 1, "weight", MUTE)
    c.put(22, 1, "input × weight", MUTE)
    shown_sum = 0.0
    for i, (idx, h, w, p) in enumerate(nn["top"]):
        if t >= 0.8 + 0.5 * i:
            c.put(2, 3 + i, f"x{idx:<4}{h:+7.2f}", TEXT)
            c.put(18, 3 + i, f"× {w:+6.3f}", TEXT)
            c.put(29, 3 + i, f"= {p:+7.3f}", f"bold {CYAN if p >= 0 else PINK}")
            shown_sum += p
    if t >= 3.4:
        c.put(2, 8, f"… and {nn['n_inputs'] - 5} more inputs", MUTE)
        c.put(29, 8, f"= {nn['rest']:+7.3f}", f"bold {CYAN if nn['rest'] >= 0 else PINK}")
        shown_sum += nn["rest"]
    if t >= 3.9:
        c.hline(2, 38, 9, "─", MUTE)
        k = ease((t - 3.9) / 0.8)
        c.put(2, 10, f"ADD THEM ALL UP  = {nn['pre'] * k:+7.3f}", f"bold {AMBER}")
    if t >= 5.0:                                                   # the bend
        bx, by, bw, bh = 48, 2, 46, 11
        c.box(bx, by, bw, bh, MUTE, title="the bend (SiLU)")
        xs = [(-4 + 8 * i / (bw - 5)) for i in range(bw - 4)]
        ys = [silu(v) for v in xs]
        lo, hi = -0.5, 4.0
        for i, (xv, yv) in enumerate(zip(xs, ys)):
            row = by + bh - 2 - round((yv - lo) / (hi - lo) * (bh - 3))
            c.put(bx + 2 + i, max(by + 1, min(by + bh - 2, row)), "▪", CYAN)
        c.put(bx + 3, by + 1, "out", MUTE)
        c.put(bx + bw - 6, by + bh - 1, "in →", MUTE)
        pos = ease((t - 5.4) / 1.4) * (nn["pre"] + 4) - 4 if t >= 5.4 else -4
        col = round((pos + 4) / 8 * (bw - 5))
        row = by + bh - 2 - round((silu(pos) - lo) / (hi - lo) * (bh - 3))
        c.put(bx + 2 + col, max(by + 1, min(by + bh - 2, row)), "●", f"bold {AMBER}")
    if t >= 6.9:
        c.put(2, 12, f"after the bend  = {nn['silu']:+7.3f}", TEXT)
        c.put(2, 13, f"× a second sum  = {nn['up']:+7.3f}", TEXT)
    if t >= 7.6:
        c.put(2, 15, f"NEURON OUTPUT   = {nn['out']:+7.3f}", f"bold {GREEN}")


def target_neuron(D):
    return (2, 12, 38, 4)


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
            c.put(x + 2, y + 1, "1 neuron", f"bold {AMBER}")
        if foot:
            c.put(x + 2, y + h - 1, f" {foot} ", f"bold {MUTE}")
    if t >= 5.2:
        c.center(15, "inside every neuron: multiply, add, bend", f"bold {AMBER}")


def target_out(D):
    return (0, 0, 96, 17)


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
    dict(title="Zoom out", draw=scene_out, target=target_out, caption="", anim=6.0,
         say="Zoom back out. One neuron. {hidden} of them make a feed-forward layer. Add attention and you get a block. "
             "{nb} blocks, plus a table that turns words into numbers, make {total} numbers: me. Everything you will "
             "explore in this course is one of these pieces. Press Enter, and let's begin."),
]


def derive(D):
    """Words and numbers used in the narration, all taken from the real data."""
    P, hd, nn = D["params"], D["head"], D["neuron"]
    toks = D["tokens"]
    clean = lambda s: s.replace("▁", "").strip()
    a = D["acts"]
    return dict(total=num(P["total"]), nb=P["n_layers"], block=num(P["block"]), hidden=num(P["hidden"]),
                word=D["final"][0].token.text.strip(), lock=D["brain"].lock_layer, l=hd["layer"] + 1, h=hd["head"] + 1,
                last=clean(toks[-1]), p=f"{hd['p']:.0%}", tw=clean(toks[hd["target"]]),
                tw_note=", the word right before it" if hd["target"] == len(toks) - 2 else "", nh=P["n_heads"],
                lit=int((abs(a) > 0.25 * abs(a).max()).sum()), nidx=nn["index"], n_in=nn["n_inputs"],
                pre=f"{nn['pre']:+.3f}", out=f"{nn['out']:+.3f}")


def duration(scene, S):
    return max(0.3 + len(scene["say"].format(**S)) / CPS, scene["anim"]) + HOLD


def draw_transition(prev, rect, p, caption):
    """The camera dives into `rect`: the old scene dims, and a frame grows from the box to the whole screen."""
    c = Canvas(W, H)
    c.ch = [row[:] for row in prev.ch]
    c.st = [row[:] for row in prev.st]
    x, y, w, h = rect
    w, h = max(w, 5), max(h, 3)
    x, y = x - (w - rect[2]) // 2, y - (h - rect[3]) // 2
    k = ease(p)
    for echo, strength in ((0.0, 1.0), (-0.12, 0.55), (-0.24, 0.3)):
        kk = ease(max(0.0, p + echo))
        if kk <= 0:
            continue
        rx, ry = round(x * (1 - kk)), round(y * (1 - kk))
        rw, rh = round(w + (W - w) * kk), round(h + (H - h) * kk)
        if echo == 0.0:
            c.clear(rx, ry, rw, rh)
        c.box(rx, ry, max(rw, 2), max(rh, 2), mix(AMBER, "#1e1e2e", 1 - strength), title=None)
    if caption and k > 0.25:
        c.center(H // 2, f" {caption} ", f"bold {AMBER}")
    return c


class ZoomScreen(Screen):
    BINDINGS = [Binding("escape", "back", "back"), Binding("space", "pause", "pause"), Binding("enter", "next", "next"),
                Binding("right", "next", "next"), Binding("left", "prev", "back"), Binding("r", "replay", "replay")]

    def compose(self) -> ComposeResult:
        with Vertical(id="zoom-box"):
            yield Static(id="zoom-stage")
            yield Static(id="zoom-say")
        yield Static(id="keys", classes="keys")

    def on_mount(self):
        self.D = self.S = None
        self.i, self.t, self.trans, self.paused = 0, 0.0, None, False
        self.last = time.monotonic()
        self.query_one("#keys", Static).update("Space pause   Enter / → next   ← back   R replay   F8 the real code   Esc leave")
        self.query_one("#zoom-say").border_title = "MONA"
        self.query_one("#zoom-stage", Static).update(Text("MONA is opening herself up…", style=MUTE))
        self.timer = self.set_interval(1 / FPS, self.tick)
        if self.app.gb is not None:
            self.load()

    def on_engine_ready(self):
        if self.D is None:
            self.load()

    @work(thread=True, exclusive=True, group="zoom")
    def load(self):
        D = zoomdata.compute(self.app.gb)
        self.app.call_from_thread(self._loaded, D)

    def _loaded(self, D):
        self.D, self.S = D, derive(D)
        self.last = time.monotonic()

    # ── playback ──────────────────────────────────────────────────────────────
    def tick(self):
        now = time.monotonic()
        dt, self.last = min(now - self.last, 0.2), now
        if self.D is None:
            return
        if not self.paused:
            if self.trans:
                self.trans["t"] += dt
                if self.trans["t"] >= TRANSITION:
                    self.i, self.t, self.trans = self.trans["to"], 0.0, None
            else:
                self.t += dt
                if self.t >= duration(SCENES[self.i], self.S) and self.i < len(SCENES) - 1:
                    self.action_next()
        self.paint()

    def paint(self):
        scene = SCENES[self.i]
        if self.trans:
            canvas = draw_transition(self.trans["prev"], self.trans["rect"], self.trans["t"] / TRANSITION, self.trans["caption"])
            say = ""
        else:
            canvas = Canvas(W, H)
            scene["draw"](canvas, self.t, self.D, self.S)
            say = typed(scene["say"].format(**self.S), self.t, 0.3, CPS)
        stage = self.query_one("#zoom-stage", Static)
        stage.update(canvas.render())
        stage.border_title = f"{self.i + 1} / {len(SCENES)}  ·  {scene['title']}" + ("   ⏸ paused" if self.paused else "")
        self.query_one("#zoom-say", Static).update(Text(say, style="#cdd6f4"))

    def action_next(self):
        if self.D is None or self.trans:
            return
        scene = SCENES[self.i]
        if self.i >= len(SCENES) - 1:
            self.app.state.complete("zoom")
            self.app.pop_screen()
            return
        prev = Canvas(W, H)
        scene["draw"](prev, 1e6, self.D, self.S)
        self.trans = dict(t=0.0, to=self.i + 1, prev=prev.dimmed(), rect=scene["target"](self.D), caption=scene["caption"])

    def action_prev(self):
        if self.D is not None and not self.trans and self.i > 0:
            self.i, self.t = self.i - 1, 0.0

    def action_replay(self):
        if self.D is not None and not self.trans:
            self.t = 0.0

    def action_pause(self):
        self.paused = not self.paused

    def action_back(self):
        self.app.pop_screen()
