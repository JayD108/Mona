"""The screens of the MONA app (Phase 0: display check, home, tokens)."""
from rich.text import Text
from textual import work
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.screen import Screen
from textual.widgets import Button, Input, OptionList, Static
from textual.widgets.option_list import Option

from .text import READY, STAGES, stage_name
from .widgets import Avatar, prob_bars, token_chips


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
                Binding("r", "app.toggle_roman", "romanize"), Binding("q", "app.quit", "quit")]

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
        done = len(s.completed)
        bar = "█" * done + "░" * (len(STAGES) - done)
        badges = "   " + "  ".join(f"🏅 {b}" for b in s.badges) if s.badges else ""
        self.query_one("#progress", Static).update(
            Text.assemble((f"{tr('progress')}  ", "#8a8fb0"), (bar, "#06d6a0"), (f"  {done}/{len(STAGES)}", "#8a8fb0"),
                          (badges, "#ffd166")))
        self.query_one("#keys", Static).update(tr("keys_home"))

    def on_option_list_option_selected(self, event: OptionList.OptionSelected):
        sid = event.option.id
        if sid == "tokens":
            self.app.push_screen(TokenScreen())
        else:
            self.app.notify(self.app.tr("soon"), timeout=3)


class TokenScreen(Screen):
    """Stage 2 (Phase 0 teaser): type anything -> see the tokens and MONA's next-token guesses."""
    BINDINGS = [Binding("escape", "app.pop_screen", "back")]
    EXAMPLE = "भारत एक विशाल देश है और"

    def compose(self) -> ComposeResult:
        with Horizontal(id="tok-head"):
            yield Avatar(id="tok-avatar")
            with Vertical():
                yield Static(id="tok-title", classes="title")
                yield Static(id="tok-explain")
        yield Input(id="tok-input")
        with VerticalScroll(id="tok-body"):
            yield Static(id="tok-count")
            yield Static(id="tok-chips")
            yield Static(id="next-title", classes="subtitle")
            yield Static(id="next-explain", classes="dim")
            yield Static(id="next-bars")
        yield Static(id="tok-keys", classes="keys")

    def on_mount(self):
        inp = self.query_one("#tok-input", Input)
        inp.value = self.EXAMPLE
        inp.focus()
        self.refresh_texts()
        self.recompute()

    def refresh_texts(self):
        tr = self.app.tr
        self.query_one("#tok-title", Static).update(tr("tok_title"))
        self.query_one("#tok-explain", Static).update(tr("tok_explain"))
        self.query_one("#tok-input", Input).placeholder = tr("tok_prompt")
        self.query_one("#next-title", Static).update(tr("next_title"))
        self.query_one("#next-explain", Static).update(tr("next_explain"))
        self.query_one("#tok-keys", Static).update(f"{tr('back')}   F2 language   F3 depth   F4 romanize")
        self.recompute()

    def on_engine_ready(self):
        self.recompute()

    def on_input_changed(self, event: Input.Changed):
        self.recompute()

    def recompute(self):
        text = self.query_one("#tok-input", Input).value
        if self.app.gb is None:
            self.query_one("#tok-chips", Static).update(self.app.tr("loading"))
            self.query_one("#tok-avatar", Avatar).set_mood("sleepy")
            return
        self.query_one("#tok-avatar", Avatar).set_mood("thinking")
        self.analyse(text, self.app.state.depth)

    @work(thread=True, exclusive=True)
    def analyse(self, text, depth):
        gb = self.app.gb
        tokens = gb.tokens(text) if text else []
        guesses = gb.next_word(text, top=8) if text else []
        self.app.call_from_thread(self.show, text, tokens, guesses, depth)

    def show(self, text, tokens, guesses, depth):
        roman = self.app.roman if self.app.state.romanize else None
        self.query_one("#tok-count", Static).update(
            Text(self.app.tr("tok_count", chars=len(text), n=len(tokens)), style="bold #06d6a0"))
        self.query_one("#tok-chips", Static).update(token_chips(tokens, roman, show_ids=depth != "simple"))
        self.query_one("#next-bars", Static).update(prob_bars(guesses, roman) if guesses else "")
        self.query_one("#tok-avatar", Avatar).set_mood("wow" if guesses and guesses[0].prob > 0.3 else "happy")
        if tokens and "tokens" not in self.app.state.completed and len(text) > 3:
            self.app.state.complete("tokens")
