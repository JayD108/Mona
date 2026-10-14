"""Small building blocks shared by every screen."""
from rich.cells import cell_len
from rich.text import Text
from textual.widgets import Static

# Token chip colours: soft backgrounds, dark text (readable on dark and light terminals)
CHIP_COLOURS = ["#f9e2af", "#a6e3a1", "#89dceb", "#f5c2e7", "#cba6f7", "#fab387", "#94e2d5", "#f38ba8"]

FACES = {"happy": "◕‿◕", "thinking": "◔_◔", "wow": "⊙▽⊙", "sleepy": "－_－"}


class Avatar(Static):
    """MONA's face. Its mood changes with what's happening."""

    def __init__(self, mood="happy", **kw):
        super().__init__(**kw)
        self.mood = mood

    def on_mount(self):
        self.set_mood(self.mood)

    def set_mood(self, mood):
        self.mood = mood
        self.update(Text.assemble(("╭─────╮\n", "#89dceb"), ("│ ", "#89dceb"), (FACES[mood], "bold #f9e2af"),
                                  (" │\n", "#89dceb"), ("╰─────╯\n", "#89dceb"), (" MONA", "bold #89dceb")))


def show_piece(text):
    """Make invisible things visible: a leading space becomes ▁, a newline becomes ↵."""
    if text.startswith(" "):
        text = "▁" + text[1:]
    return text.replace("\n", "↵").replace("\t", "⇥")


def token_chips(tokens, romanize=None, show_ids=False):
    """Coloured boxes, one per token. With show_ids, each chip also shows the number MONA actually sees."""
    out = Text()
    for i, tok in enumerate(tokens):
        piece = show_piece(tok.text)
        if romanize:
            piece = romanize(piece)
        style = f"bold #181825 on {CHIP_COLOURS[i % len(CHIP_COLOURS)]}"
        # terminals measure Devanagari vowel signs inconsistently: give those chips one cell of breathing room
        pad = "  " if any("ऀ" <= ch <= "ॿ" for ch in piece) else " "
        out.append(f" {piece}{pad}", style=style)
        if show_ids:
            out.append(f"{tok.id}", style="dim")
        out.append(" ")
    return out


def prob_bars(guesses, romanize=None, width=28):
    """One bar per candidate next token: longer bar = MONA is more sure."""
    out = Text()
    label_w = max([cell_len(show_piece(g.token.text)) for g in guesses] + [6]) + 2
    top = max(g.prob for g in guesses) or 1
    for i, g in enumerate(guesses):
        piece = show_piece(g.token.text)
        if romanize:
            piece = romanize(piece)
        filled = max(1, round(width * g.prob / top))
        out.append(f"{piece}", style=f"bold {CHIP_COLOURS[i % len(CHIP_COLOURS)]}")
        out.append(" " * max(1, label_w - cell_len(piece)))
        out.append("█" * filled, style=CHIP_COLOURS[i % len(CHIP_COLOURS)])
        out.append("░" * (width - filled), style="#45475a")
        out.append(f" {g.prob:6.1%}\n", style="bold")
    return out
