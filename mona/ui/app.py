"""MONA: the interactive terminal app.   Run:  mona   (or  python -m mona)"""
from pathlib import Path

from textual import work
from textual.app import App
from textual.binding import Binding

from .screens import DisplayCheckScreen, HomeScreen
from .state import DEPTHS, LANGS, State
from .text import romanize, t
from .welcome import WelcomeScreen, address

# each lab's main explanation opens with a short line addressed to the learner (by their chosen name)
LAB_INTROS = {"lm_explain", "dat_explain", "tok_explain", "emb_explain", "att_explain", "lay_explain", "smp_explain",
              "tm_explain", "ct_explain", "ev_explain", "rag_explain", "by_q_explain", "cmp_explain"}
BRIEFING = {"en": "💡 {a}, here's the idea:\n", "hi": "💡 {a}, बात यह है:\n", "hinglish": "💡 {a}, baat yeh hai:\n"}

CSS = """
Screen { background: #14172b; color: #e8e8f0; }
.title { text-style: bold; color: #ffd166; margin: 1 0 0 0; }
.subtitle { text-style: bold; color: #8ecae6; margin: 1 0 0 0; }
.dim { color: #8a8fb0; }
.keys { dock: bottom; height: 1; color: #8a8fb0; background: #1b1f3b; padding: 0 1; }

#topbar { height: 3; padding: 0 1; background: #1b1f3b; }
#hello-row { height: 7; margin: 1 1 0 1; }
#avatar { width: 11; }
#hello { padding: 0 2; border: round #8ecae6; height: 7; width: 1fr; }
#home-cols { height: 1fr; }
#stage-col { width: 1fr; }
#desk-col { width: 46; }
#journey-title, #desk-title { margin: 1 2 0 2; }
#stages, #desk { margin: 0 2; height: 1fr; border: round #3a3f5c; background: #14172b; }
#stages:focus, #desk:focus { border: round #ffd166; }
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
.knobs { margin: 1 1 0 1; height: 1; }
#cmp-cols { height: auto; }
#te-cols { height: 1fr; }
#te-stages { width: 34; border: round #3a3f5c; }
#te-right { width: 1fr; }
.cmp-col { width: 1fr; }
.gen-text { margin: 0 1 1 1; padding: 1 2; border: round #3a3f5c; height: auto; }
TabPane { padding: 0 1; }
Input { margin: 1 1 0 1; border: tall #3a3f5c; }
Input:focus { border: tall #ffd166; }

#check-box { align: center middle; padding: 2 4; }
#wel-box { align: center middle; padding: 1 4; }
#wel-box #avatar { height: 5; }
#wel-text { margin: 1 0; color: #e8e8f0; width: 120; }
#wel-choices { width: 44; height: 5; border: round #8ecae6; margin: 1 0 0 0; }
#wel-name { width: 44; }
#wel-keys { margin: 1 0 0 0; }

/* explore screens: a list on the left, the details on the right */
#tour-cols { height: 1fr; }
#teams, #chapters, #incidents, #steps { width: 42; margin: 1 0 1 1; border: round #3a3f5c; background: #14172b; }
#teams:focus, #chapters:focus, #incidents:focus, #steps:focus { border: round #ffd166; }
#tour-right { width: 1fr; }

/* F1 glossary popup */
GlossaryScreen { align: center middle; background: rgba(10, 12, 30, 0.7); }
#gl-box { width: 110; height: 32; border: round #ffd166; background: #1b1f3b; padding: 0 1; }
#gl-cols { height: 1fr; }
#gl-list { width: 32; border: round #3a3f5c; background: #14172b; }
#gl-detail { width: 1fr; padding: 1 2; }

/* F8 code view */
CodeScreen { align: center middle; background: rgba(10, 12, 30, 0.7); }
#cv-box { width: 96%; height: 92%; border: round #ffd166; background: #1b1f3b; padding: 0 1; }
#cv-cols { height: 1fr; }
#cv-list { width: 34; border: round #3a3f5c; background: #14172b; }
#cv-right { width: 1fr; padding: 0 1; }
#cases { width: 42; margin: 1 0 1 1; border: round #3a3f5c; background: #14172b; }
#cases:focus { border: round #ffd166; }
#check-sample { text-style: bold; color: #ffd166; padding: 1 2; border: round #ffd166; width: auto; margin: 1 0; }
#check-buttons { height: auto; margin: 1 0; }
#check-buttons Button { margin-right: 2; }
#check-fix { color: #c9cce0; margin: 1 0; }
"""


class MonaApp(App):
    CSS = CSS
    TITLE = "MONA"
    BINDINGS = [Binding("f2", "cycle_lang", "language", show=False), Binding("f3", "cycle_depth", "depth", show=False),
                Binding("f4", "toggle_roman", "romanize", show=False), Binding("f9", "export", "export", show=False),
                Binding("f7", "address", "address", show=False), Binding("f1", "glossary", "glossary", show=False),
                Binding("f8", "code", "code", show=False)]

    def __init__(self, weights=None):
        super().__init__()
        self.state = State.load()
        self.gb = None
        self.weights = weights

    # ── text helpers used by every screen ────────────────────────────────────
    def tr(self, key, **fmt):
        who = self.addr()
        shown = who or {"en": "friend", "hi": "दोस्त", "hinglish": "dost"}[self.state.lang]
        if fmt:                                    # texts with other {fields} may also say {addr}
            fmt.setdefault("addr", shown)
        text = t(key, self.state.lang, self.state.depth, **fmt).replace("{addr}", shown)
        if key in LAB_INTROS and who:
            text = BRIEFING[self.state.lang].format(a=who) + text
        return self.roman(text) if self.state.romanize else text

    def addr(self):
        """How MONA addresses the user right now: 'Sir', 'मैम', 'Priya जी' … ('' if not chosen)."""
        return address(self.state)

    def roman(self, text):
        return romanize(text)

    @property
    def tokenizer(self):
        """MONA's tokenizer, available instantly (before the model has finished loading)."""
        if self.gb is not None:
            return self.gb.tok
        if getattr(self, "_tok", None) is None:
            from tokenizers import Tokenizer
            from ..paths import TOKENIZER_PATH
            self._tok = Tokenizer.from_file(str(TOKENIZER_PATH))
        return self._tok

    # ── start-up ──────────────────────────────────────────────────────────────
    def on_mount(self):
        self.push_screen(HomeScreen())
        if not self.state.display_checked:
            self.push_screen(DisplayCheckScreen())
        self.push_screen(WelcomeScreen())          # every launch: "how should I address you?" (Enter keeps it)
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

    def action_export(self):
        """F9 anywhere: save a screenshot; labs that support it also save a report (.md) and a script (.py)."""
        import datetime as dt
        out_dir = Path.home() / "mona_exports"
        out_dir.mkdir(exist_ok=True)
        stamp = f"{dt.datetime.now():%Y%m%d_%H%M%S}_{type(self.screen).__name__.lower()}"
        saved = [self.save_screenshot(filename=f"{stamp}.svg", path=str(out_dir))]
        if hasattr(self.screen, "export"):
            title, report, script = self.screen.export()
            (out_dir / f"{stamp}.md").write_text(f"# {title}\n\n{report}\n", encoding="utf-8")
            (out_dir / f"{stamp}.py").write_text(script, encoding="utf-8")
            saved += [str(out_dir / f"{stamp}.md"), str(out_dir / f"{stamp}.py")]
        self.notify("Saved: " + "  ".join(Path(s).name for s in saved) + f"  →  {out_dir}", timeout=6)

    def action_address(self):
        if not isinstance(self.screen, WelcomeScreen):
            self.push_screen(WelcomeScreen())

    def action_glossary(self):
        from .glossary import GlossaryScreen
        if not isinstance(self.screen, GlossaryScreen):
            self.push_screen(GlossaryScreen())

    def action_code(self):
        """F8: the real code behind whatever is on screen."""
        from .codeview import DEFAULT, SCREEN_CODE, CodeScreen
        screen = self.screen
        if isinstance(screen, CodeScreen):
            return
        keys = screen.code_targets() if hasattr(screen, "code_targets") else SCREEN_CODE.get(type(screen).__name__, DEFAULT)
        self.push_screen(CodeScreen(keys))

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
    from ..assets import ensure
    ensure()                                   # pip installs: fetch weights + demo data once
    MonaApp(args.weights).run()


if __name__ == "__main__":
    main()
