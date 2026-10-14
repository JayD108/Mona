"""MONA: the interactive terminal app.   Run:  mona   (or  python -m mona)"""
from pathlib import Path

from textual import work
from textual.app import App
from textual.binding import Binding

from .palette import MonaCommands
from .screens import HomeScreen
from .state import DEPTHS, State
from .text import romanize, t
from .welcome import WelcomeScreen, address

# each lab's main explanation opens with a short line addressed to the learner (by their chosen name)
LAB_INTROS = {"lm_explain", "dat_explain", "tok_explain", "emb_explain", "att_explain", "lay_explain", "smp_explain",
              "tm_explain", "ct_explain", "ev_explain", "rag_explain", "by_q_explain", "cmp_explain"}
BRIEFING = "💡 {a}, here's the idea:\n"

CSS = """
/* Look: soft navy, pastel borders with the title set into the border line, one frame per screen. */
Screen { background: #1e1e2e; color: #cdd6f4; border: round #b4befe; border-title-align: center;
         border-title-color: #f9e2af; border-title-style: bold; padding: 0 1; }
GlossaryScreen, CodeScreen { border: none; padding: 0; }
.title { text-style: bold underline; color: #f9e2af; margin: 1 0 0 0; }
.subtitle { text-style: bold; color: #89dceb; margin: 1 0 0 0; }
.dim { color: #9399b2; }
.keys { dock: bottom; height: auto; min-height: 3; max-height: 5; color: #9399b2; background: #1e1e2e;
        border: round #89dceb; border-title-align: center; border-title-color: #f9e2af; border-title-style: bold;
        padding: 0 1; }

OptionList { background: #1e1e2e; border: round #89dceb; border-title-align: center; border-title-color: #f9e2af;
             border-title-style: bold; padding: 0 1; }
OptionList:focus { border: round #b4befe; background: #1e1e2e; }
OptionList > .option-list--option-highlighted { background: #45475a; color: #cdd6f4; text-style: bold; }
OptionList:focus > .option-list--option-highlighted { background: #45475a; color: #cdd6f4; text-style: bold; }
OptionList > .option-list--option-hover { background: #313244; }
OptionList > .option-list--separator { color: #45475a; }

* { scrollbar-background: #181825; scrollbar-background-hover: #181825; scrollbar-background-active: #181825;
    scrollbar-color: #45475a; scrollbar-color-hover: #b4befe; scrollbar-color-active: #b4befe; scrollbar-corner-color: #181825; }
Input { margin: 1 1 0 1; background: #181825; border: round #89dceb; color: #cdd6f4; }
Input:focus { border: round #b4befe; }
Button { background: #313244; color: #cdd6f4; border: round #89dceb; }
Button:hover { background: #45475a; }
TabbedContent Tabs { background: #1e1e2e; }
Tab { color: #9399b2; }
Tab.-active { color: #f9e2af; text-style: bold underline; }

/* Colour language: cyan = navigation and information, green = done or succeeded, amber = key ideas and
   warnings, red only for real errors. */
/* home */
#main { height: 1fr; border: round #89dceb; border-title-align: center; border-title-color: #f9e2af;
        border-title-style: bold; padding: 0 1; }
#top-row { height: 11; }
#hello { width: 1fr; height: 100%; border: round #89dceb; border-title-align: center; border-title-color: #f9e2af;
         border-title-style: bold; padding: 0 2; }
#brain { width: 66; height: 100%; border: round #89dceb; border-title-align: center; border-title-color: #f9e2af;
         border-title-style: bold; padding: 0 2; }
#home-cols { height: 1fr; }
#stage-col { width: 1fr; background: #1e1e2e; }
#desk-col { width: 50; background: #1e1e2e; }
#stages, #desk { height: 1fr; }
#mission { height: auto; min-height: 7; max-height: 8; border: round #89dceb; border-title-align: center;
           border-title-color: #f9e2af; border-title-style: bold; padding: 0 2; }
#telemetry { height: auto; min-height: 4; max-height: 5; border: round #89dceb; border-title-align: center;
             border-title-color: #f9e2af; border-title-style: bold; padding: 0 2; }
CommandPalette { background: rgba(10, 12, 30, 0.7); border: none; padding: 0; }

/* labs */
.lab-head { height: 6; margin: 1 1 0 1; }
.lab-avatar { width: 11; }
.lab-title { text-style: bold; color: #f9e2af; padding: 2 1; }
.explain { color: #bac2de; margin: 1 1 0 1; height: auto; }
.count { margin: 1 0 0 0; }
.chips { margin: 1 0 0 0; }
.panel { margin: 1 1; padding: 1 2; border: round #89dceb; height: auto; min-height: 5; }
.panel:focus { border: round #b4befe; }
.race-input { margin: 0 1; }
TabbedContent { height: 1fr; }
.knobs { margin: 1 1 0 1; height: 1; }
#cmp-cols { height: auto; }
#te-cols { height: 1fr; }
#te-stages { width: 34; border: round #45475a; }
#te-right { width: 1fr; }
.cmp-col { width: 1fr; }
.gen-text { margin: 0 1 1 1; padding: 1 2; border: round #45475a; height: auto; }
TabPane { padding: 0 1; }

#check-box { align: center middle; padding: 2 4; }
#wel-box { align: center middle; padding: 1 4; }
#wel-box #avatar { height: 5; }
#wel-text { margin: 1 0; color: #cdd6f4; width: 120; }
#wel-choices { width: 44; height: 5; border: round #89dceb; margin: 1 0 0 0; }
#wel-name { width: 44; }
#wel-keys { margin: 1 0 0 0; }

/* explore screens: a list on the left, the details on the right */
#tour-cols { height: 1fr; }
#teams, #chapters, #incidents, #steps { width: 42; margin: 1 0 1 1; border: round #45475a; background: #1e1e2e; }
#teams:focus, #chapters:focus, #incidents:focus, #steps:focus { border: round #f9e2af; }
#tour-right { width: 1fr; }

/* F1 glossary popup */
GlossaryScreen { align: center middle; background: rgba(10, 12, 30, 0.7); }
#gl-box { width: 110; height: 32; border: round #f9e2af; background: #181825; padding: 0 1; }
#gl-cols { height: 1fr; }
#gl-list { width: 32; border: round #45475a; background: #1e1e2e; }
#gl-detail { width: 1fr; padding: 1 2; }

/* F8 code view */
CodeScreen { align: center middle; background: rgba(10, 12, 30, 0.7); }
#cv-box { width: 96%; height: 92%; border: round #f9e2af; background: #181825; padding: 0 1; }
#cv-cols { height: 1fr; }
#cv-list { width: 34; border: round #45475a; background: #1e1e2e; }
#cv-right { width: 1fr; padding: 0 1; }
#cases { width: 42; margin: 1 0 1 1; border: round #45475a; background: #1e1e2e; }
#cases:focus { border: round #f9e2af; }
#check-sample { text-style: bold; color: #f9e2af; padding: 1 2; border: round #f9e2af; width: auto; margin: 1 0; }
#check-buttons { height: auto; margin: 1 0; }
#check-buttons Button { margin-right: 2; }
#check-fix { color: #bac2de; margin: 1 0; }
"""


class MonaApp(App):
    CSS = CSS
    TITLE = "MONA"
    COMMANDS = App.COMMANDS | {MonaCommands}      # Ctrl+P: search every lesson, experiment and command
    BINDINGS = [Binding("f3", "cycle_depth", "depth", show=False), Binding("f9", "export", "export", show=False),
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
        shown = who or "friend"
        if fmt:                                    # texts with other {fields} may also say {addr}
            fmt.setdefault("addr", shown)
        text = t(key, self.state.lang, self.state.depth, **fmt).replace("{addr}", shown)
        if key in LAB_INTROS and who:
            text = BRIEFING.format(a=who) + text
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

    # ── the frame: every screen gets a title set into its border, and its key hints sit in a "Help" box ─
    FRAME_TITLES = {"HomeScreen": "", "WelcomeScreen": "MONA", "LMGameLab": "Stage 0 · What is a language model?",
                    "DataLab": "Stage 1 · Data", "TokensLab": "Stage 2 · Tokens", "EmbeddingsLab": "Stage 3 · Embeddings",
                    "AttentionLab": "Stage 4 · Attention", "LayersLab": "Stage 5 · Layers", "SamplingLab": "Stage 6 · Next word",
                    "TimeMachineLab": "Stage 7 · Training", "ChatTuningLab": "Stage 8 · Chat tuning",
                    "EvalsLab": "Stage 9 · Evals", "RagLab": "Stage 10 · RAG", "BeyondLab": "Stage 11 · Beyond",
                    "CompareLab": "MONA vs a big model", "MysteryScreen": "Model mysteries",
                    "IncidentScreen": "Training failures", "CourseScreen": "Train a model yourself",
                    "JourneyScreen": "How MONA was trained", "BudgetScreen": "Scaling laws explorer",
                    "TourScreen": "How AI labs build models", "StoryScreen": "Follow one sentence",
                    "TeacherScreen": "Teacher mode", "BadgesScreen": "Progress & certificate"}

    def push_screen(self, screen, *args, **kwargs):
        if not isinstance(screen, str):
            name = type(screen).__name__
            screen.border_title = self.FRAME_TITLES.get(name, "")
            screen.call_after_refresh(self._decorate, screen)
        return super().push_screen(screen, *args, **kwargs)

    @staticmethod
    def _decorate(screen):
        for box in screen.query(".keys"):
            box.border_title = "Help"

    # ── start-up ──────────────────────────────────────────────────────────────
    def on_mount(self):
        self.push_screen(HomeScreen())
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


def main():
    import argparse
    p = argparse.ArgumentParser(prog="mona", description="MONA: understand AI from the inside.")
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
