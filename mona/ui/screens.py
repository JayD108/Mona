"""The screens of the MONA app (Phase 0: display check, home, tokens)."""
from rich.text import Text
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.screen import Screen
from textual.widgets import Button, OptionList, Static
from textual.widgets.option_list import Option

from .text import READY, STAGES, stage_name
from .widgets import Avatar


class DisplayCheckScreen(Screen):
    """First run: make sure Hindi is drawn correctly, or switch to romanized Hindi."""

    def compose(self) -> ComposeResult:
        with Vertical(id="check-box"):
            yield Static(id="check-title", classes="title")
            yield Static("हिंदी   ·   भारत   ·   राम ने धनुष तोड़ा   ·   क्षत्रिय", id="check-sample")
            yield Static(id="check-q")
            with Horizontal(id="check-buttons"):
                yield Button(id="yes", variant="success")
                yield Button(id="no", variant="warning")
            yield Static(id="check-fix")
            yield Button(id="continue", variant="primary")

    def on_mount(self):
        self.query_one("#continue").display = False
        self.refresh_texts()

    def refresh_texts(self):
        tr = self.app.tr
        self.query_one("#check-title", Static).update(tr("check_title"))
        self.query_one("#check-q", Static).update(tr("check_q"))
        self.query_one("#yes", Button).label = tr("yes")
        self.query_one("#no", Button).label = tr("no")
        self.query_one("#continue", Button).label = "→"

    def on_button_pressed(self, event: Button.Pressed):
        state = self.app.state
        if event.button.id == "yes":
            state.romanize, state.display_checked = False, True
            state.save()
            self.app.pop_screen()
        elif event.button.id == "no":
            state.romanize, state.display_checked = True, True
            state.save()
            self.query_one("#check-fix", Static).update(self.app.tr("check_fix"))
            self.query_one("#check-buttons").display = False
            self.query_one("#continue").display = True
        else:
            self.app.pop_screen()


class HomeScreen(Screen):
    BINDINGS = [Binding("l", "app.cycle_lang", "language"), Binding("d", "app.cycle_depth", "depth"),
                Binding("r", "app.toggle_roman", "romanize"), Binding("q", "app.quit", "quit"),
                Binding("s", "story", "story"), Binding("b", "badges", "badges")]

    def action_story(self):
        from .story import StoryScreen
        self.app.push_screen(StoryScreen())

    def action_badges(self):
        from .story import BadgesScreen
        self.app.push_screen(BadgesScreen())

    def compose(self) -> ComposeResult:
        yield Static(id="topbar")
        with Horizontal(id="hello-row"):
            yield Avatar(id="avatar")
            yield Static(id="hello")
        yield Static(id="journey-title", classes="title")
        yield OptionList(id="stages")
        yield Static(id="progress")
        yield Static(id="keys", classes="keys")

    def on_mount(self):
        self.refresh_texts()
        self.query_one("#stages").focus()

    def refresh_texts(self):
        app, s = self.app, self.app.state
        tr = app.tr
        langs = Text()
        for code, name in (("en", "EN"), ("hi", "हिं"), ("hinglish", "Hinglish")):
            langs.append(f" {name} ", style="bold #1b1f3b on #ffd166" if s.lang == code else "#8a8fb0")
        top = Text.assemble((" MONA ", "bold #1b1f3b on #8ecae6"), "  ", (app.tr("tagline"), "italic #c9cce0"))
        top.append("\n")
        top.append_text(langs)
        top.append(f"   ◆ {tr('depth_name')}", style="bold #06d6a0")
        if s.romanize:
            top.append("   abc→अ", style="#f4a3c0")
        self.query_one("#topbar", Static).update(top)
        self.query_one("#hello", Static).update(Text(tr("hello"), style="#e8e8f0"))
        self.query_one("#journey-title", Static).update(tr("journey"))
        stages = self.query_one("#stages", OptionList)
        highlighted = stages.highlighted
        stages.clear_options()
        for i, stage in enumerate(STAGES):
            sid = stage[0]
            mark = "✓" if sid in s.completed else ("●" if sid in READY else "○")
            name = stage_name(stage, s.lang)
            if s.romanize:
                name = app.roman(name)
            label = Text.assemble((f" {i:>2}  {mark}  ", "#ffd166" if sid in READY else "#5a5f7c"),
                                  (name, "bold" if sid in READY else "#8a8fb0"))
            stages.add_option(Option(label, id=sid))
        stages.highlighted = highlighted if highlighted is not None else 2
        done = len([c for c in s.completed if c in {st[0] for st in STAGES}])   # stages only, not story
        bar = "█" * done + "░" * (len(STAGES) - done)
        badges = "   " + "  ".join(f"🏅 {b}" for b in s.badges) if s.badges else ""
        self.query_one("#progress", Static).update(
            Text.assemble((f"{tr('progress')}  ", "#8a8fb0"), (bar, "#06d6a0"), (f"  {done}/{len(STAGES)}", "#8a8fb0"),
                          (badges, "#ffd166")))
        self.query_one("#keys", Static).update(tr("keys_home"))

    def on_option_list_option_selected(self, event: OptionList.OptionSelected):
        lab = open_lab(event.option.id)
        if lab:
            self.app.push_screen(lab)
        else:
            self.app.notify(self.app.tr("soon"), timeout=3)

    def on_screen_resume(self):
        self.refresh_texts()            # progress / badges may have changed inside a lab


def open_lab(stage_id):
    """Labs are imported only when opened, so the app starts instantly."""
    if stage_id == "lm":
        from .labs.lm_game import LMGameLab
        return LMGameLab()
    if stage_id == "embeddings":
        from .labs.embeddings import EmbeddingsLab
        return EmbeddingsLab()
    if stage_id == "evals":
        from .labs.evals import EvalsLab
        return EvalsLab()
    if stage_id == "data":
        from .labs.data import DataLab
        return DataLab()
    if stage_id == "chat":
        from .labs.chat_tuning import ChatTuningLab
        return ChatTuningLab()
    if stage_id == "rag":
        from .labs.rag import RagLab
        return RagLab()
    if stage_id == "tokens":
        from .labs.tokens import TokensLab
        return TokensLab()
    if stage_id == "attention":
        from .labs.attention import AttentionLab
        return AttentionLab()
    if stage_id == "training":
        from .labs.timemachine import TimeMachineLab
        return TimeMachineLab()
    if stage_id == "layers":
        from .labs.layers import LayersLab
        return LayersLab()
    if stage_id == "next":
        from .labs.sampling import SamplingLab
        return SamplingLab()
    return None
