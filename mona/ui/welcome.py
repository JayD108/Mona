"""The welcome screen: what MONA is, and how the learner would like to be addressed (Sir / Ma'am / their name).

Asked on every launch (the project owner's choice); the last answer is already highlighted, so one Enter
keeps it. F7 opens this screen again from anywhere.
"""
import datetime as dt

from rich.text import Text
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical
from textual.screen import Screen
from textual.widgets import Input, OptionList, Static
from textual.widgets.option_list import Option

from .text import register
from .widgets import Avatar

register({
    "wel_title": {"en": "MONA  ·  understand AI from the inside", "hi": "MONA  ·  AI को अंदर से समझिए",
                  "hinglish": "MONA  ·  AI ko andar se samjho"},
    "wel_first": {
        "en": "Hi, I'm MONA: a real language model, 110 million numbers trained from scratch, and I'm fully open.\n"
              "Here you can 👀 look inside me while I think, 🧪 run experiments on me, 🔍 investigate my mistakes,\n"
              "and 🛠 train a small model of your own. Everything you see uses my real weights.",
        "hi": "नमस्ते, मैं MONA हूँ: एक असली भाषा मॉडल, 11 करोड़ संख्याएँ, शुरू से ट्रेन की गई, और पूरी तरह खुली।\n"
              "यहाँ आप 👀 सोचते समय मेरे अंदर झाँक सकते हैं, 🧪 मुझ पर प्रयोग कर सकते हैं, 🔍 मेरी ग़लतियों की जाँच कर सकते हैं,\n"
              "और 🛠 अपना एक छोटा मॉडल ट्रेन कर सकते हैं। जो भी दिखेगा, मेरे असली वज़न से बनेगा।",
        "hinglish": "Hi, main MONA hoon: ek asli language model, 11 crore numbers, scratch se trained, aur poori tarah open.\n"
                    "Yahan aap 👀 sochte waqt mere andar jhaank sakte ho, 🧪 mujh par experiments kar sakte ho, 🔍 meri galtiyon ki\n"
                    "jaanch kar sakte ho, aur 🛠 apna ek chhota model train kar sakte ho. Jo bhi dikhega, mere asli weights se banega.",
    },
    "wel_back": {"en": "{greet}! Good to see you again. Ready to look inside?", "hi": "{greet}! फिर से मिलकर अच्छा लगा। अंदर झाँकने के लिए तैयार?",
                 "hinglish": "{greet}! Phir se milkar achha laga. Andar jhaankne ke liye ready?"},
    "wel_ask": {"en": "What should I call you?", "hi": "मैं आपको क्या कहकर बुलाऊँ?", "hinglish": "Main aapko kya kehkar bulaun?"},
    "wel_sir": {"en": "Sir", "hi": "सर", "hinglish": "Sir"},
    "wel_maam": {"en": "Ma'am", "hi": "मैम", "hinglish": "Ma'am"},
    "wel_name": {"en": "By my name…", "hi": "मेरे नाम से…", "hinglish": "Mere naam se…"},
    "wel_other": {"en": "A different name…", "hi": "कोई और नाम…", "hinglish": "Koi aur naam…"},
    "wel_name_is": {"en": "By my name: {n}", "hi": "मेरे नाम से: {n}", "hinglish": "Mere naam se: {n}"},
    "wel_type": {"en": "Type your name and press Enter", "hi": "अपना नाम लिखकर Enter दबाइए", "hinglish": "Apna naam likho aur Enter dabao"},
    "wel_keys": {"en": "↑↓ choose   Enter continue   F2 language   (change later anytime: F7)",
                 "hi": "↑↓ चुनें   Enter आगे बढ़ें   F2 भाषा   (बाद में कभी भी बदलें: F7)",
                 "hinglish": "↑↓ chuno   Enter aage   F2 bhasha   (baad mein kabhi bhi badlo: F7)"},
    "greet_morning": {"en": "Good morning", "hi": "सुप्रभात", "hinglish": "Good morning"},
    "greet_afternoon": {"en": "Good afternoon", "hi": "नमस्कार", "hinglish": "Namaskar"},
    "greet_evening": {"en": "Good evening", "hi": "शुभ संध्या", "hinglish": "Good evening"},
    "greet_night": {"en": "Working late", "hi": "देर रात तक काम", "hinglish": "Late night kaam"},
})

ADDRESS = {  # how each choice is said in each language ({n} = the user's name)
    "sir": {"en": "Sir", "hi": "सर", "hinglish": "Sir"},
    "maam": {"en": "Ma'am", "hi": "मैम", "hinglish": "Ma'am"},
    "name": {"en": "{n}", "hi": "{n} जी", "hinglish": "{n} ji"},
}


def address(state):
    """'Sir' / 'मैम' / 'Priya जी' … in the current language ('' until the user has chosen)."""
    forms = ADDRESS.get(state.address)
    if not forms or (state.address == "name" and not state.user_name):
        return ""
    return forms[state.lang].format(n=state.user_name)


def greeting_key(now=None):
    h = (now or dt.datetime.now()).hour
    return "greet_morning" if 5 <= h < 12 else "greet_afternoon" if h < 17 else "greet_evening" if h < 23 else "greet_night"


class WelcomeScreen(Screen):
    BINDINGS = [Binding("escape", "done", "continue", show=False)]

    def compose(self) -> ComposeResult:
        with Vertical(id="wel-box"):
            yield Avatar(id="avatar")
            yield Static(id="wel-title", classes="title")
            yield Static(id="wel-text")
            yield Static(id="wel-ask", classes="subtitle")
            yield OptionList(id="wel-choices")
            yield Input(id="wel-name")
            yield Static(id="wel-keys", classes="dim")

    def on_mount(self):
        name = self.query_one("#wel-name", Input)
        name.value = self.app.state.user_name
        name.display = False
        self.refresh_texts()
        choices = self.query_one("#wel-choices", OptionList)
        choices.highlighted = ["sir", "maam", "name"].index(self.app.state.address) if self.app.state.address else 0
        choices.focus()

    def refresh_texts(self):
        app, s = self.app, self.app.state
        tr = app.tr
        self.query_one("#wel-title", Static).update(tr("wel_title"))
        if s.address:
            who = app.addr()
            text = tr("wel_back", greet=tr(greeting_key()) + (f", {who}" if who else ""))
        else:
            text = tr("wel_first")
        self.query_one("#wel-text", Static).update(Text(text, style="#e8e8f0"))
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
        choices.highlighted = keep
        self.query_one("#wel-name", Input).placeholder = tr("wel_type")
        self.query_one("#wel-keys", Static).update(tr("wel_keys"))

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
        self.app.pop_screen()                   # Esc without choosing: MONA just won't use a form of address
        self.app._refresh_all()
