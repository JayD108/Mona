"""The welcome flow.

    logo animation  ->  what should I call you?  ->  MONA writes her own welcome (live, on your computer)
                    ->  "Talk with MONA"  or  "See how MONA works"

The name question comes every launch (the project owner's choice; the last answer is pre-selected, so one Enter keeps
it). F7 opens just the name question again, from anywhere. Any key skips the logo animation; Esc skips the rest.
Set MONA_REDUCED_MOTION=1 to skip the logo animation.
"""
import datetime as dt
import os
import threading
import time

from rich.text import Text
from textual import work
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical
from textual.screen import Screen
from textual.widgets import Input, OptionList, Static
from textual.widgets.option_list import Option

from . import chatmodel, intro, logo
from .text import register

register({
    "wel_title": {"en": "understand AI from the inside", "hi": "AI को अंदर से समझिए", "hinglish": "AI ko andar se samjho"},
    "wel_ask": {"en": "What should I call you?", "hi": "मैं आपको क्या कहकर बुलाऊँ?", "hinglish": "Main aapko kya kehkar bulaun?"},
    "wel_sir": {"en": "Sir", "hi": "सर", "hinglish": "Sir"},
    "wel_maam": {"en": "Ma'am", "hi": "मैम", "hinglish": "Ma'am"},
    "wel_name": {"en": "By my name…", "hi": "मेरे नाम से…", "hinglish": "Mere naam se…"},
    "wel_other": {"en": "A different name…", "hi": "कोई और नाम…", "hinglish": "Koi aur naam…"},
    "wel_name_is": {"en": "By my name: {n}", "hi": "मेरे नाम से: {n}", "hinglish": "Mere naam se: {n}"},
    "wel_type": {"en": "Type your name and press Enter", "hi": "अपना नाम लिखकर Enter दबाइए", "hinglish": "Apna naam likho aur Enter dabao"},
    "wel_keys": {"en": "↑↓ choose   Enter continue   Esc skip   (change later anytime: F7)",
                 "hi": "↑↓ चुनें   Enter आगे बढ़ें", "hinglish": "↑↓ chuno   Enter aage"},
    "greet_morning": {"en": "Good morning", "hi": "सुप्रभात", "hinglish": "Good morning"},
    "greet_afternoon": {"en": "Good afternoon", "hi": "नमस्कार", "hinglish": "Namaskar"},
    "greet_evening": {"en": "Good evening", "hi": "शुभ संध्या", "hinglish": "Good evening"},
    "greet_night": {"en": "Working late", "hi": "देर रात तक काम", "hinglish": "Late night kaam"},
})

ADDRESS = {  # how each choice is said (the app is English-only; {n} = the user's name)
    "sir": {"en": "Sir", "hi": "सर", "hinglish": "Sir"},
    "maam": {"en": "Ma'am", "hi": "मैम", "hinglish": "Ma'am"},
    "name": {"en": "{n}", "hi": "{n} जी", "hinglish": "{n} ji"},
}

# the logo animation timeline, in seconds
LOGO_END = 1.5            # the logo wipes in
TAG_START, TAG_CPS = 1.6, 45          # the tagline types out
FPS = 30
SPINNER = "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏"
STATUS = {"thinking": "MONA is thinking", "writing": "MONA is writing", "metamorphosing": "MONA is metamorphosing"}


def address(state):
    """'Sir' / 'Ma'am' / 'Priya' … ('' until the user has chosen)."""
    forms = ADDRESS.get(state.address)
    if not forms or (state.address == "name" and not state.user_name):
        return ""
    return forms[state.lang].format(n=state.user_name)


def greeting_key(now=None):
    h = (now or dt.datetime.now()).hour
    return "greet_morning" if 5 <= h < 12 else "greet_afternoon" if h < 17 else "greet_evening" if h < 23 else "greet_night"


def reduced_motion():
    return os.environ.get("MONA_REDUCED_MOTION", "").lower() in ("1", "true", "yes")


class WelcomeScreen(Screen):
    BINDINGS = [Binding("escape", "done", "continue", show=False)]

    def __init__(self, name_only=False):
        super().__init__()
        self.name_only = name_only

    def compose(self) -> ComposeResult:
        with Vertical(id="wel-box"):
            yield Static(id="wel-logo")
            yield Static(id="wel-tag")
            yield Static(id="wel-ask", classes="subtitle")
            yield OptionList(id="wel-choices")
            yield Input(id="wel-name")
            yield Static(id="wel-keys", classes="dim")
            yield Static(id="wel-text")
            yield Static(id="wel-status")
            yield Static(id="wel-hw")
            yield Static(id="wel-begin-ask", classes="subtitle")
            yield OptionList(id="wel-begin")

    def on_mount(self):
        name = self.query_one("#wel-name", Input)
        name.value = self.app.state.user_name
        for wid in ("#wel-name", "#wel-text", "#wel-status", "#wel-hw", "#wel-begin-ask", "#wel-begin"):
            self.query_one(wid).display = False
        self.query_one("#wel-text").border_title = "MONA writes her own welcome"
        self.skip = reduced_motion()
        self.phase = "logo"                      # logo -> name -> write -> begin
        self.start = time.monotonic()
        self.cancel = threading.Event()
        self.stage, self.draft, self.live_text, self.n_tok, self.secs = "thinking", 1, "", 0, 0.0
        self.refresh_texts()
        self.timer = self.set_interval(1 / FPS, self.tick)
        self.tick()

    # ── texts ─────────────────────────────────────────────────────────────────
    def refresh_texts(self):
        app, s = self.app, self.app.state
        tr = app.tr
        self.tagline = tr("wel_title")
        self.query_one("#wel-ask", Static).update(tr("wel_ask"))
        choices = self.query_one("#wel-choices", OptionList)
        keep = choices.highlighted
        choices.clear_options()
        options = [("sir", tr("wel_sir")), ("maam", tr("wel_maam"))]
        if s.user_name:                     # a saved name: Enter keeps it; a fourth row lets the user change it
            options += [("name", tr("wel_name_is", n=s.user_name)), ("newname", tr("wel_other"))]
        else:
            options += [("newname", tr("wel_name"))]
        for oid, label in options:
            choices.add_option(Option(Text(f"  {label}", style="bold"), id=oid))
        if keep is not None:
            choices.highlighted = keep
        elif s.address:
            ids = [o[0] for o in options]
            choices.highlighted = ids.index(s.address) if s.address in ids else 0
        else:
            choices.highlighted = 0
        self.query_one("#wel-name", Input).placeholder = tr("wel_type")
        self.query_one("#wel-keys", Static).update(tr("wel_keys"))

    # ── the animation ─────────────────────────────────────────────────────────
    def tick(self):
        e = 1e9 if self.skip else time.monotonic() - self.start
        if self.phase == "logo":
            self.query_one("#wel-logo", Static).update(logo.frame(min(1.0, e / LOGO_END), max(0.0, e - LOGO_END)))
            n_tag = len(self.tagline) if e >= 1e8 else max(0, int((e - TAG_START) * TAG_CPS))
            self.query_one("#wel-tag", Static).update(Text(self.tagline[:n_tag], style="italic #bac2de"))
            for wid in ("#wel-ask", "#wel-choices", "#wel-keys"):
                self.query_one(wid).display = False
            if n_tag >= len(self.tagline):
                self.phase = "name"
                for wid in ("#wel-ask", "#wel-choices", "#wel-keys"):
                    self.query_one(wid).display = True
                self.query_one("#wel-choices", OptionList).focus()
        elif self.phase == "name":
            self.query_one("#wel-logo", Static).update(logo.frame(1.0, time.monotonic() - self.start - LOGO_END))
        elif self.phase == "write":
            self.paint_writing()

    def paint_writing(self):
        t = time.monotonic()
        self.query_one("#wel-logo", Static).update(logo.frame(1.0, t - self.start - LOGO_END))
        spin = SPINNER[int(t * 12) % len(SPINNER)]
        label = STATUS[self.stage] + "." * (int(t * 3) % 4)
        note = ""
        if self.draft > 1:
            note = f"   (draft {self.draft} of {intro.MAX_DRAFTS}: the last one drifted, so I'm rewriting)"
        elif self.stage == "thinking":
            note = "   (loading my weights from disk)"
        elif self.stage == "metamorphosing":
            note = "   (checking my own draft)"
        self.query_one("#wel-status", Static).update(Text.assemble((f"{spin} ", "bold #f9e2af"), (label, "bold #cba6f7"), (note, "#9399b2")))
        tps = f"{self.n_tok / self.secs:.0f} tokens/s" if self.secs > 0 and self.n_tok else "N/A"
        gb = self.app.gb
        params = f"{gb.model.num_params() / 1e6:.1f}M parameters" if gb else "110.1M parameters"
        device = str(gb.device).upper() if gb else "CPU"
        self.query_one("#wel-hw", Static).update(Text(f"using your own hardware  ·  {device}  ·  {params}  ·  {tps}", style="#89dceb"))
        text = Text(self.live_text, style="#cdd6f4")
        text.append("▌", style="#f9e2af")
        self.query_one("#wel-text", Static).update(text)

    def on_key(self, event):
        if self.phase == "logo":                 # any key skips straight to the end of the logo animation
            event.stop()
            event.prevent_default()
            self.skip = True
            self.tick()

    # ── choosing a name ───────────────────────────────────────────────────────
    def on_option_list_option_selected(self, event: OptionList.OptionSelected):
        if event.option_list.id == "wel-begin":
            self.begin(event.option.id)
            return
        if event.option.id == "newname":
            box = self.query_one("#wel-name", Input)
            box.display = True
            box.focus()
            return
        self.choose(event.option.id)

    def on_input_submitted(self, event: Input.Submitted):
        name = " ".join(event.value.split())[:30]
        if name:
            self.app.state.user_name = name
            self.choose("name")

    def choose(self, kind):
        self.app.state.address = kind
        self.app.state.save()
        if self.name_only:
            self.app.pop_screen()
            self.app._refresh_all()
            return
        self.app._refresh_all()
        self.start_writing()

    # ── MONA writes her welcome ───────────────────────────────────────────────
    def start_writing(self):
        self.phase = "write"
        for wid in ("#wel-ask", "#wel-choices", "#wel-keys", "#wel-name"):
            self.query_one(wid).display = False
        for wid in ("#wel-text", "#wel-status", "#wel-hw"):
            self.query_one(wid).display = True
        self.query_one("#wel-tag", Static).update(Text("Esc to skip", style="#6c7086"))
        self.write()

    @work(thread=True, exclusive=True, group="welcome")
    def write(self):
        if not chatmodel.available():
            text, source, drafts = intro.FALLBACK, "fallback", 0
        else:
            self.stage = "thinking"
            model = chatmodel.get_model()
            gb = self.app.gb
            if gb is not None:
                tok = gb.tok
            else:
                from .. import tokenizer as T
                tok = T.load()

            def on_status(stage, draft):
                if stage == "writing":                  # a new draft starts: clear the old one
                    self.live_text, self.n_tok, self.secs = "", 0, 0.0
                self.stage, self.draft = stage, draft

            def on_text(text, n, secs):
                self.live_text, self.n_tok, self.secs = text, n, secs
            text, source, drafts = intro.write_welcome(model, tok, on_status, on_text, cancel=self.cancel)
        self.app.call_from_thread(self._written, text, source, drafts)

    def _written(self, text, source, drafts):
        if self.phase != "write":
            return
        self.phase = "begin"
        self.written = text
        panel = Text(text, style="#cdd6f4")
        if source == "live":
            note = f"Written by MONA, live on your own computer  ·  {drafts} draft{'s' if drafts > 1 else ''}  ·  {self.n_tok} tokens"
        else:
            note = "A pre-written greeting: MONA's live drafts did not pass her quality check this time"
        self.query_one("#wel-text", Static).update(panel)
        self.query_one("#wel-text").border_subtitle = note
        self.query_one("#wel-status", Static).update(Text("✓ MONA is done.", style="bold #a6e3a1"))
        self.query_one("#wel-hw", Static).display = False
        ask = self.query_one("#wel-begin-ask", Static)
        ask.update("How would you like to begin?")
        ask.display = True
        begin = self.query_one("#wel-begin", OptionList)
        begin.clear_options()
        begin.add_option(Option(Text("  Talk with MONA", style="bold"), id="talk"))
        begin.add_option(Option(Text("  See how MONA works: from the whole model to one neuron", style="bold"), id="watch"))
        begin.highlighted = 0
        begin.display = True
        begin.focus()

    def begin(self, what):
        from .chat import ChatScreen
        from .zoom import ZoomScreen
        app = self.app
        app.pop_screen()
        app.push_screen(ChatScreen() if what == "talk" else ZoomScreen())

    def action_done(self):
        if self.phase == "logo":
            self.skip = True
            self.tick()
        elif self.phase == "write":
            self.cancel.set()                    # skip the rest of the writing
        else:
            self.app.pop_screen()                # Esc without choosing: straight to the home screen
            self.app._refresh_all()

    def on_unmount(self):
        self.cancel.set()
