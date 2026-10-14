"""Your words, step by step: a 12-page animated lesson that follows the text YOU type through MONA.

    1 you type  2 clean-up  3 cut into pieces  4 into bytes  5 merging  6 token ids  7 embeddings  8 position
    9 through the 12 blocks  10 attention  11 scores  12 pick one, repeat

Everything shown is computed from MONA's real tokenizer and weights for your own text (see pathdata.py); the
narration is written by hand. It uses the same player as "Inside MONA": pause / play, speed, next / back, replay.
"""
import unicodedata

from rich.text import Text
from textual.widgets import Input

from . import pathdata
from .lesson import AMBER, CYAN, GREEN, LAV, MUTE, PINK, TEXT, LessonScreen, ease, heat, human, mix, num, typed, word
from .zoom import scene_attention, scene_blocks, target_attention, target_blocks

CHIP = ["#f9e2af", "#a6e3a1", "#89dceb", "#f5c2e7", "#cba6f7"]


def title(c, s):
    c.put(2, 0, s, f"bold {AMBER}")


def chips(c, labels, x, y, t, t0, per, maxx=94, ids=None):
    """Coloured chips, left to right, wrapping at logical column maxx. Returns the physical (px, py, width) of each."""
    px, py, out = c.X(x), c.Y(y), []
    for i, label in enumerate(labels):
        w = len(label) + 2
        if px + w > c.X(maxx):
            px, py = c.X(x), py + 2
        out.append((px, py, w))
        if t >= t0 + per * i:
            c.rput(px, py, f" {label} ", f"bold #1e1e2e on {CHIP[i % 5]}")
            if ids is not None:
                c.rput(px, py + 1, f"{ids[i]:^{w}}", f"bold {CHIP[i % 5]}")
        px += w + 1
    return out


# ── 1 you type ────────────────────────────────────────────────────────────────
def scene_type(c, t, D, S):
    title(c, "1 · YOU TYPE")
    c.box(8, 3, 80, 5, CYAN, title="your text")
    cur = "▌" if int(t * 2) % 2 == 0 else " "
    c.put_in(8, 5, 80, typed(D["text"], t, 0.4, 16) + cur, f"bold {TEXT}")
    if t >= 3.0:
        c.center(9, f"{len(D['text'])} characters", f"bold {GREEN}")
        c.center(10, f"= {len(D['text'].encode('utf-8'))} bytes once saved as UTF-8", MUTE)
    if t >= 4.2:
        c.center(13, "a model cannot read letters: it can only read numbers", f"bold {AMBER}")
        c.center(14.2, "so the first job is to turn these letters into numbers", MUTE)


def target_type(D, c):
    return c.R(8, 3, 80, 5)


# ── 2 clean-up ────────────────────────────────────────────────────────────────
def scene_clean(c, t, D, S):
    title(c, "2 · CLEAN-UP (Unicode NFC)")
    c.box(2, 2, 42, 4, MUTE, title="what you typed")
    c.put_in(2, 4, 42, D["text"][:38], TEXT)
    if t >= 1.0:
        c.arrow(44, 49, 4, AMBER)
        c.box(50, 2, 44, 4, GREEN, title="after clean-up")
        c.put_in(50, 4, 44, D["norm"][:40], f"bold {GREEN}")
    if t >= 1.8:
        c.center(6.4, "unchanged: already tidy" if not D["changed"] else "I changed it! Same letters, one standard spelling", f"bold {AMBER}")
    if t >= 2.4:
        c.put(2, 8, "every character already has a number (its code point):", MUTE)
        px = c.X(2)
        for i, ch in enumerate(D["norm"][:9]):
            if t >= 2.6 + 0.15 * i:
                c.rput(px, c.Y(9.3), f"{ch:^8}", f"bold {TEXT}")
                c.rput(px, c.Y(10.3), f"U+{ord(ch):04X}", CYAN)
                px += 9
    if t >= 4.5:
        before, after = D["demo"]
        c.put(2, 12.6, f"why clean up?  the letter é can be saved as {len(before)} code points (e + accent) or as {len(after)}.", MUTE)
        c.put(2, 13.8, f"NFC makes it always the same: “e + accent”  →  “{after}”  ({unicodedata.name(after)})", f"bold {GREEN}")


def target_clean(D, c):
    return c.R(50, 2, 44, 4)


# ── 3 cut into pieces ─────────────────────────────────────────────────────────
def scene_pieces(c, t, D, S):
    title(c, "3 · CUT INTO PIECES")
    shown = [p.replace(" ", "▁") if p.startswith(" ") else p for p in D["pieces"]]
    chips(c, shown, 2, 3, t, 0.6, 0.35)
    if t >= 0.6 + 0.35 * len(shown):
        c.put(2, 9, f"{len(D['norm'])} characters  →  {len(shown)} pieces", f"bold {GREEN}")
    if t >= 4.0:
        c.put(2, 11, "a regex splits the text: words, numbers and punctuation each become their own piece.", TEXT)
        c.put(2, 12.2, "a space stays attached to the front of its word (shown as ▁), so “cat” and “ cat” are different.", MUTE)
    if t >= 5.5:
        c.put(2, 14, "Hindi letters with their vowel signs stay together, too: the splitter knows they belong to one word.", f"italic {MUTE}")


def target_pieces(D, c):
    return c.R(2, 2.5, 60, 3)


# ── 4 into bytes ──────────────────────────────────────────────────────────────
def scene_bytes(c, t, D, S):
    title(c, "4 · EVERY PIECE BECOMES BYTES")
    for i, (piece, bs) in enumerate(D["byte_rows"]):
        if t < 0.5 + 0.5 * i:
            break
        y = 2 + i
        shown = piece.replace(" ", "▁")
        c.put(2, y, f"{shown[:12]:<12}", f"bold {CHIP[i % 5]}")
        c.put(16, y, "→", AMBER)
        c.rput(c.X(18), c.Y(y), " ".join(bs[:14]) + (" …" if len(bs) > 14 else ""), TEXT)
    if t >= 4.0:
        ch, bs = D["hindi"]
        c.put(2, 12, f"even one Hindi letter, “{ch}”, is {len(bs)} bytes:  {' '.join(bs)}", f"bold {GREEN}")
    if t >= 5.0:
        c.put(2, 13.4, "there are only 256 possible bytes, and I know all of them, so no text is ever “unknown”:", MUTE)
        c.put(2, 14.4, "emoji, Hindi, code, a typo: it can always be written in bytes.", MUTE)


def target_bytes(D, c):
    return c.R(2, 2, 60, 9)


# ── 5 merging ─────────────────────────────────────────────────────────────────
def scene_merge(c, t, D, S):
    title(c, "5 · MERGE THE BYTES (BPE)")
    merges = D["merges"]
    if not merges:
        c.center(7, "these short words are already single pieces I know: nothing to merge", f"bold {GREEN}")
        return
    piece = D["merge_piece"].replace(" ", "▁")
    c.center(2, f"the piece  “{piece}”", f"bold {AMBER}")
    k = min(len(merges) - 1, max(0, int((t - 0.8) / 0.75)))
    first = max(0, k - 6)
    for j in range(first, k + 1):
        if t < 0.8 + 0.75 * j:
            break
        state, merged = merges[j]
        y = 4 + (j - first)
        last = j == k
        c.put(4, y, state[:60], f"bold {GREEN}" if last else MUTE)
        if merged and last:
            c.put(70, y, f"+ “{merged.replace(' ', '▁')[:12]}”", f"bold {AMBER}")
    if k == len(merges) - 1 and t >= 0.8 + 0.75 * len(merges):
        pieces_left = len(merges[-1][0].split())
        c.center(12.5, f"{len(merges) - 1} merges: “{piece}” ends up as {pieces_left} token{'s' if pieces_left != 1 else ''}", f"bold {GREEN}")
    c.put(2, 15, "the merge list was learned from billions of words: it joins the pairs that appear together most often.", f"italic {MUTE}")


def target_merge(D, c):
    return c.R(4, 4, 64, 8)


# ── 6 token ids ───────────────────────────────────────────────────────────────
def scene_ids(c, t, D, S):
    title(c, "6 · EACH TOKEN GETS ITS NUMBER")
    chips(c, D["tokens"], 2, 3, t, 0.5, 0.4, ids=D["ids"])
    if t >= 0.5 + 0.4 * len(D["tokens"]):
        c.put(2, 9, f"{D['n_words']} word{'s' if D['n_words'] != 1 else ''}  →  {D['n']} tokens", f"bold {GREEN}")
        c.put(2, 10.4, f"my vocabulary has {num(D['n_vocab'])} tokens; each one has a fixed number between 0 and {num(D['n_vocab'] - 1)}.", TEXT)
    if t >= 4.5:
        c.put(2, 12, "these numbers are all the model ever receives. It never sees a single letter.", f"bold {AMBER}")
    if D["trimmed"] and t >= 5.5:
        c.put(2, 13.4, "(to keep the pictures readable I kept only the first 12 tokens of what you typed)", f"italic {MUTE}")


def target_ids(D, c):
    return c.R(2, 2.5, 90, 4)


# ── 7 embeddings ──────────────────────────────────────────────────────────────
def scene_embed(c, t, D, S):
    title(c, "7 · EACH NUMBER LOOKS UP A LIST OF 768 NUMBERS")
    cells = D["cells"]
    amax = float(abs(cells).max()) or 1.0
    cw = max(1, round(c.sx))
    for i, row in enumerate(cells):
        if t < 0.5 + 0.4 * i:
            break
        y = 2 + i
        c.put(2, y, f"{D['tokens'][i][:9]:>9}", f"bold {CHIP[i % 5]}")
        c.put(12, y, f"#{D['ids'][i]:<5}", MUTE)
        x0 = c.X(20)
        for k, v in enumerate(row):
            m = min(1.0, abs(v) / amax) ** 0.6
            c.rput(x0 + k * cw, c.Y(y), "█" * cw, mix("#313244", CYAN if v >= 0 else PINK, 0.15 + 0.85 * m))
    if t >= 0.5 + 0.4 * len(cells):
        e = D["emb"][0]
        c.put(2, 14, f"the first token begins:  {', '.join(f'{v:+.3f}' for v in e[:6])}, …  (768 numbers, drawn as 48 cells)", MUTE)
        c.put(2, 15.2, "these numbers are MONA's idea of the word: similar words get similar numbers.", f"bold {AMBER}")


def target_embed(D, c):
    return c.R(2, 2, 70, 11)


# ── 8 position ────────────────────────────────────────────────────────────────
ARROWS = "→↗↑↖←↙↓↘"


def scene_position(c, t, D, S):
    title(c, "8 · POSITION: HOW I KNOW THE ORDER")
    px = c.X(4)
    for i, tok in enumerate(D["tokens"]):
        if t < 0.5 + 0.35 * i:
            break
        label = tok[:8]
        w = 10
        x = px + i * w
        if x + w > c.w:
            break
        c.rput(x, c.Y(3), f"{label:^{w - 1}}", f"bold #1e1e2e on {CHIP[i % 5]}")
        c.rput(x, c.Y(5), f"{i:^{w - 1}}", MUTE)
        if i < len(D["fast"]):
            if t >= 2.5 + 0.2 * i:
                ang = D["fast"][i]
                c.rput(x, c.Y(7), f"{ARROWS[round((ang % 360) / 45) % 8]:^{w - 1}}", f"bold {AMBER}")
                c.rput(x, c.Y(8), f"{ang:+.0f}°".center(w - 1), TEXT)
    if t >= 2.5:
        c.put(2, 10.5, "I add no position number. I ROTATE each word's numbers by an angle that grows with its position (RoPE).", TEXT)
        c.put(2, 11.8, "the arrow shows one of those dials turning: word 0 does not turn; word 1 turns 57°, and so on.", MUTE)
    if t >= 5.0:
        c.put(2, 13.5, "so when two words meet in attention, the angle between them tells me how far apart they are.", f"bold {GREEN}")


def target_position(D, c):
    return c.R(4, 2.5, 88, 7)


# ── 9 blocks (shared with Inside MONA) and 10 attention ──────────────────────
def scene_blocks_wrap(c, t, D, S):
    scene_blocks(c, t, D, S)
    c.put(2, 0, "9 · THROUGH ALL 12 BLOCKS", f"bold {AMBER}")


def scene_attention_wrap(c, t, D, S):
    scene_attention(c, t, D, S)


# ── 11 scores ─────────────────────────────────────────────────────────────────
def scene_scores(c, t, D, S):
    title(c, f"11 · {num(D['n_vocab'])} SCORES, ONE FOR EVERY TOKEN I KNOW")
    sc = D["scores"]
    top = max(p for _, _, p in sc) or 1.0
    c.put(2, 2, "the five highest scores", MUTE)
    for i, (text, logit, p) in enumerate(sc):
        if t < 0.8 + 0.45 * i:
            break
        y = 4 + i
        c.put(2, y, f"{show(text)[:9]:<9}", f"bold {CHIP[i % 5]}")
        c.put(12, y, f"score {logit:5.1f}", TEXT)
        bar = max(1, round(18 * c.sx / 2 * p / top))
        c.rput(c.X(25), c.Y(y), "█" * bar, CHIP[i % 5])
        c.rput(c.X(25) + bar + 1, c.Y(y), f"{p:4.0%}", f"bold {GREEN}")
    if t >= 3.4:
        c.put(2, 10, "scores → probabilities (softmax): they all add up to 100%.", MUTE)
    if t >= 4.0:
        c.put(52, 2, "THE TEMPERATURE KNOB", f"bold {AMBER}")
        c.put(52, 3, "same scores, different temperature:", MUTE)
        for j, temp in enumerate((0.5, 1.0, 1.5)):
            if t < 4.4 + 0.8 * j:
                break
            ps = D["temps"][temp]
            y0 = 5 + 3 * j
            c.put(52, y0, f"T = {temp}", f"bold {GREEN if temp == 1.0 else TEXT}")
            c.rput(c.X(62), c.Y(y0), " ".join(f"{show(sc[k][0])[:5]:>5} {ps[k]:3.0%}" for k in range(3)), TEXT)
            for k in range(5):
                h = max(1, round(8 * ps[k] / max(ps[0], 0.01)))
                c.rput(c.X(52) + k * 4, c.Y(y0) + 1, "▂▃▄▅▆▇█"[min(6, h - 1)] * 3, CHIP[k % 5])
    if t >= 7.5:
        c.put(2, 14.5, "low temperature: bet on the favourite. high temperature: give the underdogs a chance.", f"bold {AMBER}")


def show(text):
    return text.replace(" ", "▁").strip("▁") or "▁"


def target_scores(D, c):
    return c.R(2, 3.5, 44, 7)


# ── 12 pick one, repeat ───────────────────────────────────────────────────────
def scene_pick(c, t, D, S):
    title(c, "12 · PICK ONE, ADD IT, REPEAT")
    steps = D["steps"]
    c.put(2, 2, "the text so far:", MUTE)
    added = "".join(st["text"] for i, st in enumerate(steps) if t >= 1.0 + 2.6 * i + 1.5)
    c.put(2, 3.4, "“" + (D["text"] + added)[-72:] + "”", f"bold {GREEN if added else TEXT}")
    for i, st in enumerate(steps):
        t0 = 1.0 + 2.6 * i
        if t < t0:
            break
        y = 6 + 2.2 * i
        piece = st["text"].replace(" ", "▁")
        c.put(2, y, f"step {i + 1}:", MUTE)
        c.put(10, y, f"I pick token #{st['id']}", TEXT)
        if t >= t0 + 0.8:
            c.put(34, y, f"→ the piece “{piece}”", f"bold {CHIP[i % 5]}")
        if t >= t0 + 1.5:
            c.put(58, y, f"({st['prob']:.0%} sure)  → added", MUTE)
    if t >= 1.0 + 2.6 * len(steps):
        c.center(13, "token ids → pieces → text  ·  the new text goes back in, and the whole journey starts again", f"bold {AMBER}")
        c.center(14.4, "that is everything I do: one token at a time", f"italic {MUTE}")


def target_pick(D, c):
    return c.R(2, 2, 90, 10)


SCENES = [
    dict(title="You type", draw=scene_type, target=target_type, caption="into the clean-up", anim=5.5,
         say="You typed {quoted}. That is {nchar} characters, or {nbytes} bytes. But I can't read letters: I can only "
             "read numbers. So before anything else, your text goes through a small factory that turns it into "
             "numbers. Let's follow it, step by step."),
    dict(title="Clean-up", draw=scene_clean, target=target_clean, caption="into the splitter", anim=6.5,
         say="Step one is a clean-up called Unicode NFC. The same visible letter can be saved in more than one way, "
             "and I want it to always look the same to me. {changed_note} Every character already has a number, its "
             "code point."),
    dict(title="Pieces", draw=scene_pieces, target=target_pieces, caption="into the bytes", anim=6.5,
         say="Next, a splitter cuts your text into {npieces} pieces: words, numbers and punctuation. A space stays "
             "stuck to the front of its word, so “cat” and “ cat” are different pieces. This is not yet my "
             "tokens; it's just the rough cut."),
    dict(title="Bytes", draw=scene_bytes, target=target_bytes, caption="into the merges", anim=6.0,
         say="Each piece is written as bytes, the 0s and 1s computers use for text. There are only 256 possible bytes, "
             "and I know all of them, so nothing is ever an unknown word. English letters take one byte each. A "
             "single Hindi letter takes three."),
    dict(title="Merges", draw=scene_merge, target=target_merge, caption="into the token numbers", anim=8.0,
         say="Bytes are too small to be useful, so my tokenizer glues them back together. {merge_note} It joins pairs "
             "that were most common in the billions of words I was trained on. Common words become one token; rare "
             "words stay in several."),
    dict(title="Token ids", draw=scene_ids, target=target_ids, caption="into the embeddings", anim=7.0,
         say="Now your text is {ntok} tokens, and each token has a number from my vocabulary of {vocab}. "
             "{ratio_note} These numbers are all that enters my model. From here on, I never see a single letter."),
    dict(title="Embeddings", draw=scene_embed, target=target_embed, caption="into the positions", anim=6.5,
         say="A token number alone means nothing, so each one looks itself up in a big table and gets a list of 768 "
             "numbers: my idea of that token. This table holds {embed} numbers, the biggest single part of me. "
             "Similar words end up with similar lists."),
    dict(title="Position", draw=scene_position, target=target_position, caption="into the 12 blocks", anim=6.5,
         say="There is one more problem: a list of numbers doesn't say which word came first. I don't add a position "
             "number. Instead I rotate each token's numbers by an angle that grows with its position. This trick is "
             "called RoPE, and Llama uses it too."),
    dict(title="12 blocks", draw=scene_blocks_wrap, target=target_blocks, caption="into attention", anim=5.5,
         say="Now the numbers climb through my {nb} blocks. In each block the tokens look at each other (attention) "
             "and then I think about what I found (the feed-forward part). After every block I already have a guess "
             "for the next token: watch it improve until it settles on “{word}”."),
    dict(title="Attention", draw=scene_attention_wrap, target=target_attention, caption="into the scores", anim=6.0,
         say="Here is attention in block {l}, on YOUR text. Each row is a token, and the bright squares show which "
             "earlier tokens it looks at. The last token, “{last}”, puts {p} of its attention on “{tw}”. This is "
             "how context gets mixed in."),
    dict(title="Scores", draw=scene_scores, target=target_scores, caption="into the pick", anim=8.5,
         say="At the very end, the last token's numbers are turned into {vocab} scores, one for every token I know. "
             "The highest is “{top}”. Scores become probabilities, and the temperature knob decides how much I "
             "favour the favourite: low means safe, high means adventurous."),
    dict(title="Pick and repeat", draw=scene_pick, target=target_pick, caption="", anim=9.5,
         say="Finally I pick one token, turn its number back into a piece of text, and add it to yours. Then the whole "
             "new text goes back in and the journey starts again. Writing a story, answering a question: it's always "
             "this loop, one token at a time. That's what happens to every word you type."),
]


def derive(D):
    P, hd = D["params"], D["head"]
    toks = D["tokens"]
    n_merge = len(D["merges"]) - 1
    return dict(
        quoted="“" + D["text"] + "”", nchar=len(D["text"]), nbytes=len(D["text"].encode("utf-8")),
        changed_note=("Your text changed a little." if D["changed"] else "Yours was already tidy, so nothing changed."),
        npieces=len(D["pieces"]), ntok=D["n"], vocab=num(D["n_vocab"]), embed=num(P["embed"]), nb=P["n_layers"],
        merge_note=(f"Take “{D['merge_piece'].strip()}”: it starts as {n_merge + 1} pieces and ends as one or two, "
                    f"after {n_merge} merges." if D["merges"] else "Your words are short and common, so they are already single tokens."),
        ratio_note=f"{D['n_words']} word{'s' if D['n_words'] != 1 else ''} became {D['n']} tokens.",
        word=D["final"][0].token.text.strip(), l=hd["layer"] + 1, last=word(toks[-1]), p=f"{hd['p']:.0%}",
        tw=word(toks[hd["target"]]), top=D["scores"][0][0].strip())


class PathScreen(LessonScreen):
    SCENES = SCENES

    def compose_extra(self):
        yield Input(id="path-input")

    asking = True
    text = ""

    def after_mount(self):
        self.ask()

    def ask(self):
        self.asking, self.D = True, None
        box = self.query_one("#path-input", Input)
        box.display, box.placeholder = True, "Type a sentence (any language!) and press Enter. Leave it empty for an example."
        box.value = self.text
        box.focus()
        self.query_one("#zoom-stage").update(Text(
            "\n\nType any sentence below, in English, हिंदी, or anything else.\n\n"
            "I will follow YOUR words through my whole body, in 12 pages:\n"
            "tokens, numbers, blocks, and the word I pick next.", style=TEXT, justify="center"))
        self.query_one("#zoom-stage").border_title = "Type your sentence"
        self.query_one("#zoom-say").update("")

    def start(self):
        if not self.asking and self.D is None and self.app.gb is not None:
            self.load()

    def on_engine_ready(self):
        if not self.asking and self.D is None:
            self.load()

    def on_input_submitted(self, event: Input.Submitted):
        self.text = event.value.strip() or pathdata.DEFAULT
        self.asking = False
        event.input.display = False
        self.set_focus(None)
        self.query_one("#zoom-stage").update(Text("\n\nMONA is reading your words…", style=MUTE, justify="center"))
        if self.app.gb is not None:
            self.load()

    def compute(self, gb):
        return pathdata.compute(gb, self.text)

    def derive(self, D):
        return derive(D)

    def finished(self):
        self.app.state.complete("words")
        self.app.pop_screen()

    def action_back(self):
        if self.asking:
            self.app.pop_screen()
        else:
            self.ask()                                   # Esc = back to what I was doing: typing the text
