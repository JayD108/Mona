"""MONA: the interactive terminal app.   Run:  mona   (or  python -m mona)"""
from pathlib import Path

from textual import work
from textual.app import App
from textual.binding import Binding

from .screens import DisplayCheckScreen, HomeScreen
from .state import DEPTHS, LANGS, State
from .text import romanize, t

CSS = """
Screen { background: #14172b; color: #e8e8f0; }
.title { text-style: bold; color: #ffd166; margin: 1 0 0 0; }
.subtitle { text-style: bold; color: #8ecae6; margin: 1 0 0 0; }
.dim { color: #8a8fb0; }
.keys { dock: bottom; height: 1; color: #8a8fb0; background: #1b1f3b; padding: 0 1; }

#topbar { height: 3; padding: 0 1; background: #1b1f3b; }
#hello-row { height: 6; margin: 1 1 0 1; }
#avatar { width: 11; }
#hello { padding: 1 2; border: round #8ecae6; height: 5; }
#journey-title { margin: 1 2 0 2; }
#stages { margin: 0 2; height: 1fr; border: round #3a3f5c; background: #14172b; }
#progress { margin: 0 2 1 2; height: 1; }

/* labs */
.lab-head { height: 6; margin: 1 1 0 1; }
.lab-avatar { width: 11; }
.lab-title { text-style: bold; color: #ffd166; padding: 2 1; }
.explain { color: #c9cce0; margin: 1 1 0 1; height: auto; }
.count { margin: 1 0 0 0; }
.chips { margin: 1 0 0 0; }
.panel { margin: 1 1; padding: 1 2; border: round #3a3f5c; height: auto; min-height: 5; }
.panel:focus { border: round #ffd166; }
.race-input { margin: 0 1; }
TabbedContent { height: 1fr; }
TabPane { padding: 0 1; }
Input { margin: 1 1 0 1; border: tall #3a3f5c; }
Input:focus { border: tall #ffd166; }

#check-box { align: center middle; padding: 2 4; }
#check-sample { text-style: bold; color: #ffd166; padding: 1 2; border: round #ffd166; width: auto; margin: 1 0; }
#check-buttons { height: auto; margin: 1 0; }
#check-buttons Button { margin-right: 2; }
#check-fix { color: #c9cce0; margin: 1 0; }
"""


class MonaApp(App):
    CSS = CSS
    TITLE = "MONA"
    BINDINGS = [Binding("f2", "cycle_lang", "language", show=False), Binding("f3", "cycle_depth", "depth", show=False),
                Binding("f4", "toggle_roman", "romanize", show=False)]

    def __init__(self, weights=None):
        super().__init__()
        self.state = State.load()
        self.gb = None
        self.weights = weights

    # ── text helpers used by every screen ────────────────────────────────────
    def tr(self, key, **fmt):
        text = t(key, self.state.lang, self.state.depth, **fmt)
        return self.roman(text) if self.state.romanize else text

    def roman(self, text):
        return romanize(text)

    @property
    def tokenizer(self):
        """MONA's tokenizer, available instantly (before the model has finished loading)."""
        if self.gb is not None:
            return self.gb.tok
        if getattr(self, "_tok", None) is None:
            from tokenizers import Tokenizer
            self._tok = Tokenizer.from_file(str(Path(__file__).resolve().parents[2] / "models" / "mona" / "tokenizer.json"))
        return self._tok

    # ── start-up ──────────────────────────────────────────────────────────────
    def on_mount(self):
        self.push_screen(HomeScreen())
        if not self.state.display_checked:
            self.push_screen(DisplayCheckScreen())
        self.load_engine()

    @work(thread=True)
    def load_engine(self):
        from ..engine.glassbox import GlassBox      # imports torch: done off the UI thread
        gb = GlassBox(self.weights)
        self.call_from_thread(self._engine_ready, gb)

    def _engine_ready(self, gb):
        self.gb = gb
        for screen in self.screen_stack:
            if hasattr(screen, "on_engine_ready"):
                screen.on_engine_ready()

    # ── global switches ──────────────────────────────────────────────────────
    def _refresh_all(self):
        for screen in self.screen_stack:
            if hasattr(screen, "refresh_texts"):
                screen.refresh_texts()

    def action_cycle_lang(self):
        self.state.cycle("lang", LANGS)
        self._refresh_all()

    def action_cycle_depth(self):
        self.state.cycle("depth", DEPTHS)
        self._refresh_all()

    def action_toggle_roman(self):
        self.state.romanize = not self.state.romanize
        self.state.save()
        self._refresh_all()


def main():
    import argparse
    p = argparse.ArgumentParser(prog="mona", description="MONA: open up a real language model and see how it thinks.")
    p.add_argument("--weights", help="path to MONA weights (default: newest available)")
    p.add_argument("--reset", action="store_true", help="forget settings and progress")
    args = p.parse_args()
    if args.reset:
        from .state import STATE_PATH
        STATE_PATH.unlink(missing_ok=True)
    MonaApp(args.weights).run()


if __name__ == "__main__":
    main()
