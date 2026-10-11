"""Stage 6 — Next word & sampling: how MONA picks what to write."""
import torch
from rich.cells import cell_len
from rich.text import Text
from textual import work
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, VerticalScroll
from textual.screen import Screen
from textual.widgets import Input, Static

from ...engine.lessons import shape
from ..text import register
from ..widgets import Avatar, show_piece

register({
    "smp_title": {"en": "Next word: how MONA chooses", "hi": "अगला शब्द: MONA कैसे चुनती है",
                  "hinglish": "Agla shabd: MONA kaise chunti hai"},
    "smp_explain": {
        "en": {"simple": "MONA doesn't know the next word. It guesses, and each guess has a chance. Then it rolls a dice "
                         "to pick one. Temperature changes how bold the dice is.",
               "student": "Every step, MONA gives each of its 32,768 tokens a probability, then picks one at random by those "
                          "chances (sampling). Temperature sharpens (low) or flattens (high) the chances. Top-k keeps only the "
                          "k most likely; top-p keeps the smallest set that adds up to p.",
               "engineer": "p = softmax(logits / T); top-k / nucleus (top-p) filter, renormalise, multinomial sample. "
                           "Generated text is coloured by p(chosen token) under T=1."},
        "hi": {"simple": "MONA को अगला शब्द पता नहीं होता। वह अंदाज़ा लगाती है, और हर अंदाज़े की एक संभावना होती है। फिर वह "
                         "पासा फेंककर एक चुनती है। Temperature तय करता है कि पासा कितना साहसी हो।",
               "student": "हर कदम पर MONA अपने 32,768 टोकनों को एक संभावना देती है, फिर उन्हीं संभावनाओं के हिसाब से एक को चुनती "
                          "है (sampling)। Temperature कम हो तो संभावनाएँ तीखी, ज़्यादा हो तो सपाट। Top-k केवल k सबसे संभावित रखता है; "
                          "top-p सबसे छोटा समूह रखता है जिसका जोड़ p हो।",
               "engineer": "p = softmax(logits / T); top-k / nucleus (top-p) छँटाई, फिर से normalise, multinomial sample। "
                           "लिखा गया पाठ T=1 पर p(चुना गया टोकन) से रंगा है।"},
        "hinglish": {"simple": "MONA ko agla word pata nahi hota. Woh guess karti hai, aur har guess ka ek chance hota hai. Phir "
                               "woh dice phenk kar ek chunti hai. Temperature batata hai dice kitna bold hai.",
                     "student": "Har step par MONA apne 32,768 tokens ko ek probability deti hai, phir unhi chances se ek random "
                                "chunti hai (sampling). Kam temperature = chances tez, zyada = flat. Top-k sirf k sabse likely "
                                "rakhta hai; top-p sabse chhota group rakhta hai jiska total p ho.",
                     "engineer": "p = softmax(logits / T); top-k / nucleus (top-p) filter, renormalise, multinomial sample. "
                                 "Generated text T=1 par p(chosen token) se coloured hai."},
    },
    "smp_prompt": {"en": "Start a sentence (Enter)…", "hi": "कोई वाक्य शुरू कीजिए (Enter)…", "hinglish": "Koi sentence shuru karo (Enter)…"},
    "smp_dist": {"en": "MONA's next-token chances", "hi": "अगले टोकन की संभावनाएँ", "hinglish": "Agle token ke chances"},
    "smp_text": {"en": "The text so far  (green = MONA was sure, red = a long shot)",
                 "hi": "अब तक का पाठ  (हरा = MONA को भरोसा था, लाल = तुक्का)",
                 "hinglish": "Ab tak ka text  (hara = MONA sure thi, laal = tukka)"},
    "smp_excluded": {"en": "greyed = removed by top-k / top-p", "hi": "धूसर = top-k / top-p ने हटाया",
                     "hinglish": "grey = top-k / top-p ne hataya"},
    "smp_keys": {"en": "Space next  G write 20  1-9 YOU pick  Bksp undo  ←→ temperature  ↑↓ top-k  P top-p  / edit  Esc back",
                 "hi": "Space अगला  G 20 लिखें  1-9 आप चुनें  Bksp वापस  ←→ temperature  ↑↓ top-k  P top-p  / बदलें  Esc",
                 "hinglish": "Space agla  G 20 likho  1-9 TUM chuno  Bksp undo  ←→ temperature  ↑↓ top-k  P top-p  / edit  Esc"},
    "smp_ch": {"en": "Challenges:  {a} make MONA repeat itself (low temperature)   {b} make MONA go wild (temperature ≥ 1.6, 20 tokens)",
               "hi": "चुनौतियाँ:  {a} MONA से बातें दोहरवाइए (कम temperature)   {b} MONA को बेकाबू कीजिए (temperature ≥ 1.6, 20 टोकन)",
               "hinglish": "Challenges:  {a} MONA se repeat karwao (kam temperature)   {b} MONA ko wild karo (temperature ≥ 1.6, 20 tokens)"},
    "smp_badge": {"en": "🏅 Both done! Badge: Temperature Tamer", "hi": "🏅 दोनों पूरी! बैज: Temperature Tamer",
                  "hinglish": "🏅 Dono done! Badge: Temperature Tamer"},
})

TEMPS = [0.1, 0.3, 0.5, 0.7, 0.8, 1.0, 1.2, 1.6, 2.0]
TOPKS = [None, 1, 5, 20, 50]
TOPPS = [None, 0.5, 0.9, 0.95]
CONF = ["#ef476f", "#f78c6b", "#ffd166", "#b5e48c", "#06d6a0"]       # red -> green by confidence


def conf_colour(p):
    return CONF[min(int(p * 5 / 0.6), 4)]          # >= 60% counts as very sure


class Panel(Static, can_focus=True):
    BINDINGS = [Binding("space", "screen.next", "next"), Binding("g", "screen.burst", "write 20"),
                Binding("backspace", "screen.undo", "undo"), Binding("left", "screen.temp(-1)"),
                Binding("right", "screen.temp(1)"), Binding("up", "screen.topk(1)"), Binding("down", "screen.topk(-1)"),
                Binding("p", "screen.topp"), Binding("slash", "screen.edit")] + \
               [Binding(str(i), f"screen.pick({i})") for i in range(1, 10)]


class SamplingLab(Screen):
    BINDINGS = [Binding("escape", "app.pop_screen", "back")]
    EXAMPLE = "Once upon a time, in a small village,"

    def compose(self) -> ComposeResult:
        with Horizontal(classes="lab-head"):
            yield Avatar(id="avatar", classes="lab-avatar")
            yield Static(id="title", classes="lab-title")
        yield Static(id="explain", classes="explain")
        yield Input(id="prompt")
        yield Static(id="knobs", classes="knobs")
        with VerticalScroll():
            yield Panel(id="dist", classes="panel")
            yield Static(id="text-title", classes="subtitle")
            yield Static(id="text", classes="gen-text")
            yield Static(id="challenge", classes="dim")
        yield Static(id="keys", classes="keys")

    def on_mount(self):
        self.temp_i, self.topk_i, self.topp_i = TEMPS.index(1.0), 0, 0
        self.ids, self.gen, self.cands = [], [], []     # gen = [(Token, prob)]
        self.done = set(self.app.state.records.get("temp_challenges", []))
        self.query_one("#prompt", Input).value = self.EXAMPLE
        self.refresh_texts()
        self.start()

    def refresh_texts(self):
        tr = self.app.tr
        self.query_one("#title", Static).update(tr("smp_title"))
        self.query_one("#explain", Static).update(tr("smp_explain"))
        self.query_one("#prompt", Input).placeholder = tr("smp_prompt")
        self.query_one("#text-title", Static).update(tr("smp_text"))
        self.query_one("#keys", Static).update(tr("smp_keys"))
        self.draw()

    def on_engine_ready(self):
        self.start()

    # ── state ────────────────────────────────────────────────────────────────
    @property
    def knobs(self):
        return TEMPS[self.temp_i], TOPKS[self.topk_i], TOPPS[self.topp_i]

    def start(self):
        if self.app.gb is None:
            self.query_one("#dist", Static).update(self.app.tr("loading"))
            return
        self.ids = self.app.gb.encode(self.query_one("#prompt", Input).value)
        self.gen = []
        self.query_one("#dist").focus()
        self.predict()

    def on_input_submitted(self, event: Input.Submitted):
        self.start()

    @work(thread=True, exclusive=True, group="predict")
    def predict(self):
        gb = self.app.gb
        p1 = gb.probs(self.ids, temperature=1.0)                   # chances at T=1 (for colouring)
        p, keep = shape(torch.log(p1 + 1e-12), *self.knobs)
        top_p, top_i = torch.topk(p, 10)
        cands = [(gb.piece(i), pv, bool(keep[i]), p1[i].item()) for pv, i in zip(top_p.tolist(), top_i.tolist())]
        self.app.call_from_thread(self._got, p, keep, p1, cands)

    def _got(self, p, keep, p1, cands):
        self.p, self.keep, self.p1, self.cands = p, keep, p1, cands
        self.draw()

    # ── actions ──────────────────────────────────────────────────────────────
    def _append(self, token_id):
        tok = self.app.gb.piece(token_id)
        self.gen.append((tok, self.p1[token_id].item()))
        self.ids.append(token_id)
        self.check_challenges()
        self.predict()

    def action_next(self):
        if not self.cands:
            return
        allowed = self.p * self.keep
        self._append(torch.multinomial(allowed / allowed.sum(), 1).item())

    @work(thread=True, exclusive=True, group="burst")
    def action_burst(self):
        gb = self.app.gb
        for _ in range(20):
            p1 = gb.probs(self.ids, temperature=1.0)
            p, keep = shape(torch.log(p1 + 1e-12), *self.knobs)
            allowed = p * keep
            choice = torch.multinomial(allowed / allowed.sum(), 1).item()
            self.ids.append(choice)
            self.gen.append((gb.piece(choice), p1[choice].item()))
        self.app.call_from_thread(self.check_challenges, burst=True)
        self.app.call_from_thread(self.predict)

    def action_pick(self, n: int):
        if n <= len(self.cands):
            self._append(self.cands[n - 1][0].id)

    def action_undo(self):
        if self.gen:
            self.gen.pop()
            self.ids.pop()
            self.predict()

    def action_temp(self, d: int):
        self.temp_i = min(max(self.temp_i + d, 0), len(TEMPS) - 1)
        self.predict()

    def action_topk(self, d: int):
        self.topk_i = min(max(self.topk_i + d, 0), len(TOPKS) - 1)
        self.predict()

    def action_topp(self):
        self.topp_i = (self.topp_i + 1) % len(TOPPS)
        self.predict()

    def action_edit(self):
        self.query_one("#prompt").focus()

    # ── challenges ───────────────────────────────────────────────────────────
    def check_challenges(self, burst=False):
        temp = self.knobs[0]
        ids = [t.id for t, _ in self.gen]
        grams = [tuple(ids[i:i + 4]) for i in range(len(ids) - 3)]
        if temp <= 0.3 and len(grams) != len(set(grams)):
            self.done.add("repeat")
        if burst and temp >= 1.6:
            self.done.add("wild")
        st = self.app.state
        st.records["temp_challenges"] = sorted(self.done)
        if {"repeat", "wild"} <= self.done:
            st.complete("next", badge="Temperature Tamer")
        st.save()
        self.draw()

    # ── drawing ──────────────────────────────────────────────────────────────
    def draw(self):
        tr = self.app.tr
        roman = self.app.roman if self.app.state.romanize else (lambda s: s)
        temp, k, topp = self.knobs
        knobs = Text()
        knobs.append(" temperature ", style="#8a8fb0")
        knobs.append(f" {temp:.1f} ", style="bold #14172b on #ffd166")
        knobs.append("   top-k ", style="#8a8fb0")
        knobs.append(f" {k or 'off'} ", style="bold #14172b on #8ecae6")
        knobs.append("   top-p ", style="#8a8fb0")
        knobs.append(f" {topp or 'off'} ", style="bold #14172b on #cdb4db")
        knobs.append(f"     {tr('smp_excluded')}", style="#5a5f7c")
        self.query_one("#knobs", Static).update(knobs)

        dist = Text(tr("smp_dist") + "\n\n", style="bold #8ecae6")
        if self.cands:
            label_w = max(cell_len(roman(show_piece(t.text))) for t, *_ in self.cands) + 2
            top = max(c[1] for c in self.cands) or 1
            for n, (tok, pv, ok, _) in enumerate(self.cands, 1):
                piece = roman(show_piece(tok.text))
                filled = max(1, round(30 * pv / top))
                style = "bold #e8e8f0" if ok else "strike #5a5f7c"
                dist.append(f"{n if n <= 9 else ' '} ", style="#ffd166" if ok else "#5a5f7c")
                dist.append(piece + " " * (label_w - cell_len(piece)), style=style)
                dist.append("█" * filled, style="#06d6a0" if ok else "#3a3f5c")
                dist.append(f" {pv:6.1%}\n", style=style)
        self.query_one("#dist", Static).update(dist)

        text = Text(roman(self.query_one("#prompt", Input).value), style="#c9cce0")
        for tok, pv in self.gen:
            text.append(roman(tok.text), style=f"bold {conf_colour(pv)}")
        self.query_one("#text", Static).update(text)

        marks = {c: ("✓" if c in self.done else "○") for c in ("repeat", "wild")}
        ch = Text(tr("smp_ch", a=marks["repeat"], b=marks["wild"]))
        if {"repeat", "wild"} <= self.done:
            ch.append("\n" + tr("smp_badge"), style="bold #ffd166")
        self.query_one("#challenge", Static).update(ch)
        mood = "wow" if self.cands and self.cands[0][1] > 0.5 else ("thinking" if temp >= 1.6 else "happy")
        self.query_one("#avatar", Avatar).set_mood(mood)
