"""Stage 5 — Layers: watch MONA's guess form, layer by layer (the "logit lens")."""
from rich.cells import cell_len
from rich.text import Text
from textual import work
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, VerticalScroll
from textual.screen import Screen
from textual.widgets import Input, Static

from ..text import register
from ..widgets import Avatar, show_piece, token_chips

register({
    "lay_title": {"en": "Layers: watch a thought form", "hi": "लेयर: एक विचार को बनते देखिए", "hinglish": "Layers: ek soch ko bante dekho"},
    "lay_explain": {
        "en": {"simple": "MONA thinks in 12 steps called layers. After each step we ask: “if you had to answer NOW, "
                         "what would the next word be?” Watch the answer get better step by step.",
               "student": "Each of MONA's 12 layers adds information to every token's vector (the “residual stream”). "
                          "The logit lens peeks at it after each layer by sending it straight to the output: you see "
                          "what MONA would predict if it stopped there. Early layers guess, later layers decide.",
               "engineer": "Logit lens: softmax(lm_head(RMSNorm(h_l))) for every layer l, using the final norm and the tied "
                           "unembedding. ←/→ moves the position; the column shows top-3 per layer with probabilities."},
        "hi": {"simple": "MONA 12 कदमों में सोचती है, जिन्हें लेयर कहते हैं। हर कदम के बाद हम पूछते हैं: “अगर अभी जवाब देना हो तो "
                         "अगला शब्द क्या होगा?” देखिए जवाब कदम-दर-कदम कैसे बेहतर होता है।",
               "student": "MONA की हर लेयर हर टोकन के वेक्टर में जानकारी जोड़ती है (“residual stream”)। Logit lens हर लेयर के बाद "
                          "उसे सीधे आउटपुट पर भेजकर झाँकता है: अगर MONA वहीं रुक जाए तो क्या कहती। शुरुआती लेयर अंदाज़ा "
                          "लगाती हैं, बाद की लेयर फ़ैसला करती हैं।",
               "engineer": "Logit lens: हर लेयर l के लिए softmax(lm_head(RMSNorm(h_l))), अंतिम norm और tied unembedding के साथ। "
                           "←/→ स्थान बदलता है; हर लेयर के शीर्ष 3 संभावना सहित।"},
        "hinglish": {"simple": "MONA 12 steps mein sochti hai, jinhe layers kehte hain. Har step ke baad hum poochte hain: “agar "
                               "abhi jawab dena ho to agla word kya hoga?” Dekho jawab step-by-step kaise behtar hota hai.",
                     "student": "MONA ki har layer har token ke vector mein jaankari jodti hai (“residual stream”). Logit lens "
                                "har layer ke baad use seedha output par bhejkar jhaankta hai: agar MONA wahin ruk jaaye to kya "
                                "kehti. Shuru ki layers guess karti hain, baad ki layers faisla karti hain.",
                     "engineer": "Logit lens: har layer l ke liye softmax(lm_head(RMSNorm(h_l))), final norm aur tied unembedding "
                                 "ke saath. ←/→ position badalta hai; har layer ke top 3 probability ke saath."},
    },
    "lay_prompt": {"en": "A sentence (Enter)…", "hi": "एक वाक्य (Enter)…", "hinglish": "Ek sentence (Enter)…"},
    "lay_at": {"en": "After reading up to “{w}”, MONA's guess for the NEXT piece, after each layer:",
               "hi": "“{w}” तक पढ़ने के बाद, हर लेयर के बाद अगले टुकड़े का अंदाज़ा:",
               "hinglish": "“{w}” tak padhne ke baad, har layer ke baad agle tukde ka guess:"},
    "lay_layer": {"en": "layer", "hi": "लेयर", "hinglish": "layer"},
    "lay_change": {"en": "← changed its mind", "hi": "← राय बदली", "hinglish": "← mind badla"},
    "lay_keys": {"en": "←/→ move along the sentence   / edit   Esc back   F2 language  F3 depth  F4 romanize",
                 "hi": "←/→ वाक्य में आगे-पीछे   / बदलें   Esc वापस   F2 भाषा  F3 गहराई  F4 रोमन",
                 "hinglish": "←/→ sentence mein aage-peeche   / edit   Esc wapas   F2 bhasha  F3 depth  F4 roman"},
})


class LensView(Static, can_focus=True):
    BINDINGS = [Binding("left", "screen.move(-1)"), Binding("right", "screen.move(1)"), Binding("slash", "screen.edit")]


class LayersLab(Screen):
    BINDINGS = [Binding("escape", "app.pop_screen", "back")]
    EXAMPLE = "The capital of France is Paris and the capital of India is"

    def compose(self) -> ComposeResult:
        with Horizontal(classes="lab-head"):
            yield Avatar(id="avatar", classes="lab-avatar")
            yield Static(id="title", classes="lab-title")
        yield Static(id="explain", classes="explain")
        yield Input(id="sentence")
        with VerticalScroll():
            yield Static(id="chips", classes="chips")
            yield LensView(id="lens", classes="panel")
        yield Static(id="keys", classes="keys")

    def on_mount(self):
        self.trace, self.pos = None, 0
        self.query_one("#sentence", Input).value = getattr(self, "seed", None) or self.EXAMPLE
        self.refresh_texts()
        self.run()

    def refresh_texts(self):
        tr = self.app.tr
        self.query_one("#title", Static).update(tr("lay_title"))
        self.query_one("#explain", Static).update(tr("lay_explain"))
        self.query_one("#sentence", Input).placeholder = tr("lay_prompt")
        self.query_one("#keys", Static).update(tr("lay_keys"))
        self.draw()

    def on_engine_ready(self):
        self.run()

    def on_input_submitted(self, event):
        self.run()

    def action_edit(self):
        self.query_one("#sentence").focus()

    def action_move(self, d: int):
        if self.trace:
            self.pos = min(max(self.pos + d, 0), len(self.trace.tokens) - 1)
            self.draw()

    @work(thread=True, exclusive=True)
    def run(self):
        gb = self.app.gb
        if gb is None:
            return
        text = self.query_one("#sentence", Input).value
        trace = gb.trace(text, lens_top=3) if text.strip() else None
        self.app.call_from_thread(self._done, trace)

    def _done(self, trace):
        self.trace = trace
        self.pos = len(trace.tokens) - 1 if trace else 0
        self.query_one("#lens").focus()
        self.app.state.complete("layers")
        self.draw()

    def draw(self):
        tr = self.app.tr
        if not self.trace:
            self.query_one("#lens", Static).update(tr("loading"))
            return
        roman = self.app.roman if self.app.state.romanize else None
        rr = roman or (lambda s: s)
        # sentence with the current position highlighted
        chips = token_chips(self.trace.tokens[:self.pos + 1], roman)
        chips.append(" ▶ ?", style="bold #ffd166")
        self.query_one("#chips", Static).update(chips)

        word = rr(show_piece(self.trace.tokens[self.pos].text))
        out = Text(tr("lay_at", w=word) + "\n\n", style="bold #8ecae6")
        guesses = [layer[self.pos] for layer in self.trace.layer_guesses]       # [layer][top-3]
        width = max(cell_len(rr(show_piece(gs[0].token.text))) for gs in guesses) + 2
        peak = max(gs[0].prob for gs in guesses) or 1          # bars relative to the most confident layer
        prev_top = None
        for l, gs in enumerate(guesses):
            top = gs[0]
            out.append(f"{tr('lay_layer')} {l + 1:>2}  ", style="#5a5f7c")
            bar = "█" * max(1, round(20 * top.prob / peak))
            colour = "#06d6a0" if top.prob > 0.4 else ("#ffd166" if top.prob > 0.1 else "#8a8fb0")
            piece = rr(show_piece(top.token.text))
            out.append(piece + " " * (width - cell_len(piece)), style=f"bold {colour}")
            out.append(f"{bar:<20} {top.prob:5.1%}   ", style=colour)
            for g in gs[1:]:
                p = rr(show_piece(g.token.text))
                out.append(f"{p} {g.prob:.0%}   ", style="#5a5f7c")
            if prev_top is not None and top.token.id != prev_top:
                out.append(tr("lay_change"), style="italic #f4a3c0")
            prev_top = top.token.id
            out.append("\n")
        self.query_one("#lens", Static).update(out)
        final = guesses[-1][0].prob
        self.query_one("#avatar", Avatar).set_mood("wow" if final > 0.4 else "thinking")
