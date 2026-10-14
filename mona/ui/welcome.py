"""The welcome screen: an animated MONA logo, a welcome message, then how the learner would like to be addressed
(Sir / Ma'am / their name).

Asked on every launch (the project owner's choice); the last answer is already highlighted, so one Enter
keeps it. F7 opens this screen again from anywhere. Any key skips the animation; set MONA_REDUCED_MOTION=1
to show everything at once.
"""
import datetime as dt
import os
import time

from rich.text import Text
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical
from textual.screen import Screen
from textual.widgets import Input, OptionList, Static
from textual.widgets.option_list import Option

from . import logo
from .text import STAGES, register

register({
    "wel_title": {"en": "understand AI from the inside", "hi": "AI को अंदर से समझिए", "hinglish": "AI ko andar se samjho"},
    "wel_first": {
        "en": "Hi, I'm MONA: a real language model, 110 million numbers trained from scratch on one laptop, and I'm fully open.\n"
              "Here you can look inside me while I think, run experiments on me, investigate my mistakes, "
              "and train a small model of your own.\nEverything you see uses my real weights.",
        "hi": "नमस्ते, मैं MONA हूँ: एक असली भाषा मॉडल, 11 करोड़ संख्याएँ, शुरू से ट्रेन की गई, और पूरी तरह खुली।",
        "hinglish": "Hi, main MONA hoon: ek asli language model, 11 crore numbers, scratch se trained, aur poori tarah open.",
    },
    "wel_back": {"en": "{greet}! Welcome back. I'm glad you're here.\nReady to look inside?",
                 "hi": "{greet}! फिर से मिलकर अच्छा लगा।", "hinglish": "{greet}! Phir se milkar achha laga."},
    "wel_done": {"en": "You have completed {n} of {total} stages.", "hi": "{n}/{total}", "hinglish": "{n}/{total}"},
    "wel_ask": {"en": "What should I call you?", "hi": "मैं आपको क्या कहकर बुलाऊँ?", "hinglish": "Main aapko kya kehkar bulaun?"},
    "wel_sir": {"en": "Sir", "hi": "सर", "hinglish": "Sir"},
    "wel_maam": {"en": "Ma'am", "hi": "मैम", "hinglish": "Ma'am"},
    "wel_name": {"en": "By my name…", "hi": "मेरे नाम से…", "hinglish": "Mere naam se…"},
    "wel_other": {"en": "A different name…", "hi": "कोई और नाम…", "hinglish": "Koi aur naam…"},
    "wel_name_is": {"en": "By my name: {n}", "hi": "मेरे नाम से: {n}", "hinglish": "Mere naam se: {n}"},
    "wel_type": {"en": "Type your name and press Enter", "hi": "अपना नाम लिखकर Enter दबाइए", "hinglish": "Apna naam likho aur Enter dabao"},
    "wel_keys": {"en": "↑↓ choose   Enter continue   (change later anytime: F7)",
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

# the animation timeline, in seconds
LOGO_END = 1.5            # the logo wipes in
TAG_START, TAG_CPS = 1.6, 45          # the tagline types out
MSG_START, MSG_CPS = 2.4, 110         # the welcome message types out
FPS = 30


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

    def compose(self) -> ComposeResult:
        with Vertical(id="wel-box"):
            yield Static(id="wel-logo")
            yield Static(id="wel-tag")
            yield Static(id="wel-text")
            yield Static(id="wel-ask", classes="subtitle")
            yield OptionList(id="wel-choices")
            yield Input(id="wel-name")
            yield Static(id="wel-keys", classes="dim")

    def on_mount(self):
        name = self.query_one("#wel-name", Input)
        name.value = self.app.state.user_name
        name.display = False
        self.query_one("#wel-text").border_title = "Welcome"
        self.skip = reduced_motion()
        self.ready = False
        self.start = time.monotonic()
        self.refresh_texts()
        self.timer = self.set_interval(1 / FPS, self.tick)
        self.tick()

    # ── texts ─────────────────────────────────────────────────────────────────
    def refresh_texts(self):
        app, s = self.app, self.app.state
        tr = app.tr
        if s.address:
            who = app.addr()
            done = len([c for c in s.completed if c in {st[0] for st in STAGES}])
            self.message = tr("wel_back", greet=tr(greeting_key()) + (f", {who}" if who else ""))
            if done:
                self.message += "\n" + tr("wel_done", n=done, total=len(STAGES))
        else:
            self.message = tr("wel_first")
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
        self.query_one("#wel-logo", Static).update(logo.frame(min(1.0, e / LOGO_END), max(0.0, e - LOGO_END)))
        n_tag = len(self.tagline) if e >= 1e8 else max(0, int((e - TAG_START) * TAG_CPS))
        self.query_one("#wel-tag", Static).update(Text(self.tagline[:n_tag], style="italic #bac2de"))
        n_msg = len(self.message) if e >= 1e8 else max(0, int((e - MSG_START) * MSG_CPS))
        box = self.query_one("#wel-text", Static)
        box.display = n_msg > 0
        typing = n_msg < len(self.message)
        text = Text(self.message[:n_msg], style="#cdd6f4")
        if typing:
            text.append("▌", style="#f9e2af")
        box.update(text)
        if not typing and not self.ready:
            self.show_choices()
        elif typing and not self.ready:
            self.query_one("#wel-ask").display = False
            self.query_one("#wel-choices").display = False
            self.query_one("#wel-keys").display = False

    def show_choices(self):
        self.ready = True
        for wid in ("#wel-ask", "#wel-choices", "#wel-keys"):
            self.query_one(wid).display = True
        self.query_one("#wel-choices", OptionList).focus()

    def skip_animation(self):
        self.skip = True
        self.tick()

    def on_key(self, event):
        if not self.ready:                       # any key skips straight to the end of the animation
            event.stop()
            event.prevent_default()
            self.skip_animation()

    # ── choosing ──────────────────────────────────────────────────────────────
    def on_option_list_option_selected(self, event: OptionList.OptionSelected):
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
        self.action_done()

    def action_done(self):
        if not self.ready:
            self.skip_animation()
            return
        self.app.pop_screen()                   # Esc without choosing: MONA just won't use a form of address
        self.app._refresh_all()
