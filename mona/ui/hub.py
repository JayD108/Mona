"""The home screen: the Transformer from "Attention Is All You Need" (2017), drawn in the terminal, as a map of MONA.

The left tower of the picture (the encoder) is the part MONA does NOT have. The right tower (the decoder) is her, with
Llama-style upgrades. Move through the parts with ↑↓: the part lights up in the picture, the panel explains what it does
in MONA, and Enter opens the animated lesson chapter about it. K, Z, W and C open the other ways in; Q quits.
"""
from rich.text import Text
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.screen import Screen
from textual.widgets import Button, OptionList, Static
from textual.widgets.option_list import Option

from .. import config
from .canvas import Canvas
from .lesson import AMBER, BG, CYAN, GREEN, LAV, MUTE, PINK, TEXT, mix
from .screens import ExploreActions

COLORS = dict(embed="#f5c2e7", cross="#fab387", masked="#fab387", addnorm="#f9e2af", ff="#89dceb", linear="#b4befe",
              softmax="#a6e3a1")
DIAGRAM_W = 72
X_LEFT, W_LEFT = 3, 24
X_RIGHT, W_RIGHT = 31, 29
ROWS = 25                              # rows the picture needs (arrows between every block)

# (id, label in the list, lesson it opens: (kind, chapter index) )
PARTS = [
    ("words", "Words in (outputs, shifted right)", ("path", 5)),
    ("embed", "Output embedding", ("path", 6)),
    ("pos", "Positional encoding", ("path", 7)),
    ("masked", "Masked multi-head attention", ("zoom", 3)),
    ("addnorm", "Add & Norm (three of them)", ("zoom", 2)),
    ("cross", "Multi-head attention (cross)", ("zoom", 8)),
    ("ff", "Feed forward", ("zoom", 4)),
    ("nx", "N× the whole stack", ("zoom", 1)),
    ("linear", "Linear", ("path", 10)),
    ("softmax", "Softmax", ("path", 10)),
    ("probs", "Output probabilities", ("path", 11)),
    ("encoder", "The encoder (MONA has none)", ("zoom", 8)),
]


def about(part):
    c = config.MONA_M
    embed = c.vocab_size * c.d_model
    return {
        "words": f"Your text as token numbers. In training it is shifted by one token, so every position practises guessing the NEXT one. "
                 f"MONA reads up to {c.context:,} tokens at once.",
        "embed": f"Each token number looks up a list of {c.d_model} numbers in a {c.vocab_size:,} × {c.d_model} table: {embed:,} numbers, "
                 "the biggest single piece of MONA. She reuses this same table at the very end (tied embeddings).",
        "pos": "The 2017 design ADDS wave patterns to say where each word sits. MONA uses RoPE instead: it ROTATES each token's numbers "
              "by an angle that depends on its position, so what matters is the distance between two words.",
        "masked": f"Every word looks only at the words BEFORE it; the mask hides the future. MONA has {c.n_heads} heads in every block, "
                  "each learning its own way of looking.",
        "addnorm": "Add: keep what you already know (the shortcut line). Norm: keep the numbers a steady size. MONA uses RMSNorm, "
                   "a simpler norm, and applies it before each part rather than after.",
        "cross": "In the 2017 design the decoder also looked at what the encoder wrote (that is how translation worked). MONA is "
                 "decoder-only, so this part does not exist in her. Llama, GPT and Mistral dropped it too.",
        "ff": f"Two weighted sums with a bend in between: {c.d_model} → {c.ffn_hidden:,} → {c.d_model}. MONA uses SwiGLU, a gated version, "
              f"and this is where most of a block's {c.ffn_hidden * c.d_model * 3:,} feed-forward numbers live.",
        "nx": f"The whole stack repeats N times. N is {c.n_layers} for MONA; GPT-3 has 96. Each block has its own numbers, and a "
              "guess forms a little more with every block.",
        "linear": f"Turns the last {c.d_model} numbers into {c.vocab_size:,} scores, one for every token MONA knows. It is the same table as "
                  "the embedding, read backwards.",
        "softmax": "Turns the scores into probabilities that add up to 100%. A temperature knob decides how much MONA favours the favourite.",
        "probs": "MONA picks one token, adds it to the text, and goes round again. Writing a story is this loop, one token at a time.",
        "encoder": "The left tower of the original (it read a sentence to be translated). MONA is a decoder-only transformer, "
                   "like Llama and GPT, so she keeps only the right tower.",
    }[part]


def draw_diagram(c, sel):
    """The picture. `sel` is the id of the highlighted part. Returns nothing: draws on Canvas `c` (physical cells)."""
    k = 2 if c.h >= ROWS * 2 + 2 else 1
    y0 = max(0, (c.h - ((ROWS - 1) * k + 1)) // 2)
    Y = lambda row: y0 + row * k

    def bar(x, row, w, label, key, dim=False):
        on = key == sel or (key == "addnorm" and sel == "addnorm")
        base = COLORS[key]
        if on:
            style, text = "bold #1e1e2e on #ffffff", f"▶ {label} ◀" if len(label) + 4 <= w else label
        elif dim:
            style, text = f"{MUTE} on {mix(base, BG, 0.72)}", label
        else:
            style, text = f"bold #1e1e2e on {base}", label
        c.rput(x, Y(row), text.center(w), style)

    def arrow(x, row, on=False):
        c.rput(x, Y(row), "▲", f"bold {AMBER}" if on else MUTE)

    def container(x, w, top, bottom, on, label_right=True):
        style = f"bold {AMBER}" if on else MUTE
        c.rbox(x - 1, Y(top), w + 2, Y(bottom) - Y(top) + 1, style)
        if label_right:
            c.rput(x + w + 2, (Y(top) + Y(bottom)) // 2, "N×", f"bold {AMBER if on else TEXT}")

    cxR, cxL = X_RIGHT + W_RIGHT // 2, X_LEFT + W_LEFT // 2
    enc = sel == "encoder"
    # ── the right tower: MONA ──
    c.rput(X_RIGHT, Y(0), "Output Probabilities".center(W_RIGHT), f"bold {AMBER if sel == 'probs' else TEXT}")
    arrow(cxR, 1, sel in ("probs", "softmax"))
    bar(X_RIGHT, 2, W_RIGHT, "Softmax", "softmax")
    arrow(cxR, 3, sel in ("softmax", "linear"))
    bar(X_RIGHT, 4, W_RIGHT, "Linear", "linear")
    arrow(cxR, 5)
    container(X_RIGHT, W_RIGHT, 6, 18, sel == "nx")
    for row, label, key in ((7, "Add & Norm", "addnorm"), (9, "Feed Forward", "ff"), (11, "Add & Norm", "addnorm"),
                            (13, "Multi-Head Attention", "cross"), (15, "Add & Norm", "addnorm"),
                            (17, "Masked Multi-Head Attention", "masked")):
        if key == "cross" and sel != "cross":
            label = "Multi-Head Attn (unused)"
        bar(X_RIGHT, row, W_RIGHT, label, key, dim=(key == "cross" and sel != "cross"))
        if row < 17:
            arrow(cxR, row + 1)
    arrow(cxR, 19)
    on_pos = sel == "pos"
    c.rput(cxR - 1, Y(20), "(+)", f"bold {AMBER if on_pos else TEXT}")
    c.rput(cxR + 2, Y(20), "◂∿ Positional Encoding", f"bold {AMBER}" if on_pos else MUTE)
    arrow(cxR, 21, on_pos)
    bar(X_RIGHT, 22, W_RIGHT, "Output Embedding", "embed")
    arrow(cxR, 23, sel in ("embed", "words"))
    c.rput(X_RIGHT, Y(24), "Outputs (shifted right)".center(W_RIGHT), f"bold {AMBER if sel == 'words' else TEXT}")
    # ── the left tower: the encoder, which MONA does not have ──
    container(X_LEFT, W_LEFT, 10, 18, enc, label_right=False)
    c.rput(X_LEFT - 3, (Y(10) + Y(18)) // 2, "N×", f"bold {AMBER if enc else MUTE}")
    for row, label, key in ((11, "Add & Norm", "addnorm"), (13, "Feed Forward", "ff"), (15, "Add & Norm", "addnorm"),
                            (17, "Multi-Head Attention", "cross")):
        on = enc
        c.rput(X_LEFT, Y(row), (f"▶ {label} ◀" if on else label).center(W_LEFT),
               "bold #1e1e2e on #ffffff" if on else f"{MUTE} on {mix(COLORS[key], BG, 0.72)}")
        if row < 17:
            arrow(cxL, row + 1, enc)
    c.rput(cxL - 1, Y(20), "(+)", f"bold {AMBER}" if enc else MUTE)
    c.rput(cxL - 6, Y(20), "∿─▸", f"bold {AMBER}" if enc else MUTE)
    arrow(cxL, 19, enc)
    arrow(cxL, 21, enc)
    c.rput(X_LEFT, Y(22), "Input Embedding".center(W_LEFT), f"{MUTE} on {mix(COLORS['embed'], BG, 0.72)}")
    arrow(cxL, 23, enc)
    c.rput(X_LEFT, Y(24), "Inputs".center(W_LEFT), MUTE)
    # the encoder's output feeds the decoder's cross-attention
    xj = X_RIGHT - 3
    c.rput(cxL, Y(9), "┌" + "─" * (xj - cxL - 1) + "┐", MUTE)
    for r in range(10, 13):
        c.rput(xj, Y(r), "│", MUTE)
    c.rput(xj, Y(13), "└" + "─" * (X_RIGHT - 1 - xj - 1) + "►", MUTE)
    # legend, top left
    c.rput(X_LEFT, Y(1), "MONA IS THE RIGHT TOWER", f"bold {AMBER}")
    for i, line in enumerate(("her Llama-style upgrades:", " Add & Norm  →  RMSNorm", " sine waves   →  RoPE",
                              " plain MLP    →  SwiGLU", " encoder       →  none")):
        c.rput(X_LEFT, Y(3 + i), line, TEXT if i else MUTE)


class HubScreen(ExploreActions, Screen):
    BINDINGS = [Binding("q", "quit_app", "quit"), Binding("escape", "root_hint", "back", show=False),
                Binding("k", "talk", "talk"), Binding("z", "zoom", "inside MONA"), Binding("w", "words", "your words"),
                Binding("c", "dashboard", "the course")]

    def compose(self) -> ComposeResult:
        with Horizontal(id="hub-cols"):
            yield Static(id="hub-diagram")
            with Vertical(id="hub-side"):
                yield OptionList(id="hub-parts")
                yield Static(id="hub-info")
                with Horizontal(id="hub-actions"):
                    yield Button("K Talk", id="hub-talk")
                    yield Button("Z Inside", id="hub-zoom")
                    yield Button("W Words", id="hub-words")
                    yield Button("C Course", id="hub-course")
                    yield Button("Q Quit", id="hub-quit", variant="error")

    def on_mount(self):
        self.sel = PARTS[0][0]
        self.query_one("#hub-diagram").border_title = "The Transformer (2017)  ·  MONA = the right tower"
        parts = self.query_one("#hub-parts", OptionList)
        parts.border_title = "Pick a part  ·  ↑↓ explore  ·  Enter opens its lesson"
        for pid, label, _ in PARTS:
            parts.add_option(Option(Text(f" {label}", style="bold"), id=pid))
        parts.highlighted = 0
        parts.focus()
        self.query_one("#hub-info").border_title = "In MONA"
        for button in self.query(Button):
            button.can_focus = False
        self.redraw()

    def on_screen_resume(self):
        self.query_one("#hub-parts", OptionList).focus()
        self.redraw()

    def refresh_texts(self):
        if self.is_attached:
            self.redraw()

    def on_resize(self):
        self.redraw()

    def redraw(self):
        box = self.query_one("#hub-diagram", Static)
        size = box.content_size
        w, h = min(max(size.width, DIAGRAM_W), 200), max(size.height, ROWS)
        canvas = Canvas(w, h)
        draw_diagram(canvas, self.sel)
        box.update(canvas.render())
        lesson = next(l for pid, _, l in PARTS if pid == self.sel)
        kind = "Inside MONA" if lesson[0] == "zoom" else "Your words, step by step (you type a sentence first)"
        text = Text("Enter ", style=f"bold {GREEN}")
        text.append(f"→ {kind}, chapter {lesson[1] + 1}\n\n", style=MUTE)
        text.append(about(self.sel), style=TEXT)
        self.query_one("#hub-info", Static).update(text)

    def on_option_list_option_highlighted(self, event: OptionList.OptionHighlighted):
        self.sel = event.option.id
        self.redraw()

    def on_option_list_option_selected(self, event: OptionList.OptionSelected):
        kind, chapter = next(l for pid, _, l in PARTS if pid == event.option.id)
        if kind == "zoom":
            from .zoom import ZoomScreen
            self.app.push_screen(ZoomScreen(start=chapter))
        else:
            from .path import PathScreen
            self.app.push_screen(PathScreen(start=chapter))

    def on_button_pressed(self, event: Button.Pressed):
        {"hub-talk": self.action_talk, "hub-zoom": self.action_zoom, "hub-words": self.action_words,
         "hub-course": self.action_dashboard, "hub-quit": self.action_quit_app}[event.button.id]()

    def action_dashboard(self):
        """The course dashboard: the 12-stage learning path and everything else to explore."""
        from .screens import HomeScreen
        self.app.push_screen(HomeScreen())

    def action_quit_app(self):
        self.app.exit()

    def action_root_hint(self):
        self.app.notify("This is the home screen, where every path starts. Press Q (or click Quit) to leave.", timeout=3)
