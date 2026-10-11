"""Stage 2 — Tokens: how MONA reads.   Modes: Peek · Merge · Race · Challenge"""
from rich.cells import cell_len
from rich.text import Text
from textual import work
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.screen import Screen
from textual.widgets import Input, Static, TabbedContent, TabPane

from ...engine.lessons import bpe_replay
from ..text import register
from ..widgets import CHIP_COLOURS, Avatar, prob_bars, show_piece, token_chips

register({
    "tok_title": {"en": "Tokens: how MONA reads", "hi": "टोकन: MONA कैसे पढ़ती है", "hinglish": "Tokens: MONA kaise padhti hai"},
    "tab_peek": {"en": "Peek", "hi": "झाँकें", "hinglish": "Peek"},
    "tab_merge": {"en": "Watch it merge", "hi": "जुड़ते देखें", "hinglish": "Judte dekho"},
    "tab_race": {"en": "Language race", "hi": "भाषा दौड़", "hinglish": "Bhasha race"},
    "tab_challenge": {"en": "Challenge", "hi": "चुनौती", "hinglish": "Challenge"},
    "tok_prompt": {"en": "Type anything, in any language…", "hi": "कुछ भी लिखिए, किसी भी भाषा में…",
                   "hinglish": "Kuch bhi likho, kisi bhi bhasha mein…"},
    "tok_explain": {
        "en": {"simple": "MONA doesn't read letters or whole words. It cuts text into pieces called tokens. "
                         "Common words are one piece; rare words get cut into smaller pieces.",
               "student": "Each coloured box is one token: a piece of text MONA knows. MONA has 32,768 of them, "
                          "learned from data. Every token has a number (its id); MONA only ever sees those numbers.",
               "engineer": "Byte-level BPE, 32,768 merges learned on a balanced EN/HI/Hinglish/Awadhi sample. Words are "
                           "pre-split by a GPT-4-style regex with \\p{M} so Devanagari vowel signs stay attached."},
        "hi": {"simple": "MONA अक्षर या पूरे शब्द नहीं पढ़ती। वह लिखे हुए को छोटे टुकड़ों में काटती है, जिन्हें टोकन कहते हैं। "
                         "आम शब्द एक टुकड़ा होते हैं, कम दिखने वाले शब्द कई टुकड़ों में कटते हैं।",
               "student": "हर रंगीन डिब्बा एक टोकन है: लिखाई का एक टुकड़ा जिसे MONA जानती है। MONA के पास ऐसे 32,768 टुकड़े हैं, "
                          "जो उसने डेटा से सीखे। हर टोकन का एक नंबर (id) होता है; MONA केवल ये नंबर ही देखती है।",
               "engineer": "बाइट-स्तर BPE, 32,768 merges, संतुलित EN/HI/Hinglish/अवधी नमूने पर सीखे गए। शब्दों को पहले "
                           "GPT-4 जैसे regex (\\p{M} सहित) से अलग किया जाता है ताकि मात्राएँ अपने अक्षर से जुड़ी रहें।"},
        "hinglish": {"simple": "MONA letters ya poore words nahi padhti. Woh text ko chhote tukdon mein kaatti hai, jinhe tokens kehte hain. "
                               "Common words ek tukda hote hain, rare words kai tukdon mein katte hain.",
                     "student": "Har rangeen box ek token hai: text ka ek tukda jo MONA jaanti hai. MONA ke paas 32,768 aise tukde hain, "
                                "data se seekhe hue. Har token ka ek number (id) hota hai; MONA sirf yahi numbers dekhti hai.",
                     "engineer": "Byte-level BPE, 32,768 merges, balanced EN/HI/Hinglish/Awadhi sample par seekhe. Words pehle "
                                 "GPT-4-style regex (\\p{M} ke saath) se split hote hain taaki matras apne letter se judi rahein."},
    },
    "tok_count": {"en": "{chars} characters → {n} tokens", "hi": "{chars} अक्षर → {n} टोकन",
                  "hinglish": "{chars} characters → {n} tokens"},
    "next_title": {"en": "What MONA would write next", "hi": "MONA आगे क्या लिखेगी", "hinglish": "MONA aage kya likhegi"},
    "next_explain": {
        "en": {"simple": "Longer bar = MONA is more sure.",
               "student": "MONA gives every one of its 32,768 tokens a probability. These are the top ones.",
               "engineer": "softmax(logits) at the last position, temperature 1.0, top 8 of 32,768."},
        "hi": {"simple": "लंबी पट्टी = MONA को ज़्यादा भरोसा है।",
               "student": "MONA अपने सभी 32,768 टोकनों को एक संभावना देती है। ये सबसे ऊपर वाले हैं।",
               "engineer": "आख़िरी स्थान पर softmax(logits), temperature 1.0, 32,768 में से शीर्ष 8।"},
        "hinglish": {"simple": "Lambi bar = MONA ko zyada bharosa hai.",
                     "student": "MONA apne saare 32,768 tokens ko ek probability deti hai. Yeh sabse upar wale hain.",
                     "engineer": "Last position par softmax(logits), temperature 1.0, 32,768 mein se top 8."},
    },
    # merge
    "merge_explain": {
        "en": {"simple": "Watch MONA glue tiny pieces together until a whole word appears. Space: play/pause, ←/→: step.",
               "student": "MONA starts from raw bytes (a Hindi letter is 3 bytes!). It then applies the merges it learned, "
                          "most common pair first: bytes → letters → syllables → words. Space: play/pause, ←/→: step.",
               "engineer": "BPE inference: repeatedly merge the adjacent pair with the lowest merge rank (rank = order learned). "
                           "⟨E0 A4⟩ are UTF-8 bytes. Space: play/pause, ←/→: step."},
        "hi": {"simple": "देखिए MONA कैसे छोटे टुकड़ों को जोड़ती है जब तक पूरा शब्द न बन जाए। Space: चलाएँ/रोकें, ←/→: एक कदम।",
               "student": "MONA कच्चे बाइट से शुरू करती है (एक हिंदी अक्षर = 3 बाइट!)। फिर सीखे हुए जोड़ (merges) लगाती है, "
                          "सबसे आम जोड़ा पहले: बाइट → अक्षर → शब्दांश → शब्द। Space: चलाएँ/रोकें, ←/→: एक कदम।",
               "engineer": "BPE inference: बार-बार सबसे कम rank वाले पास-पास के जोड़े को मिलाएँ (rank = सीखने का क्रम)। "
                           "⟨E0 A4⟩ UTF-8 बाइट हैं। Space: चलाएँ/रोकें, ←/→: कदम।"},
        "hinglish": {"simple": "Dekho MONA kaise chhote tukdon ko jodti hai jab tak poora word na ban jaaye. Space: play/pause, ←/→: step.",
                     "student": "MONA raw bytes se shuru karti hai (ek Hindi letter = 3 bytes!). Phir seekhe hue merges lagati hai, "
                                "sabse common pair pehle: bytes → letters → syllables → words. Space: play/pause, ←/→: step.",
                     "engineer": "BPE inference: baar-baar sabse kam rank wala adjacent pair merge karo (rank = seekhne ka order). "
                                 "⟨E0 A4⟩ UTF-8 bytes hain. Space: play/pause, ←/→: step."},
    },
    "merge_prompt": {"en": "A word to take apart (Enter)…", "hi": "कोई शब्द लिखिए (Enter)…", "hinglish": "Koi word likho (Enter)…"},
    "merge_step": {"en": "step {i}/{n}", "hi": "कदम {i}/{n}", "hinglish": "step {i}/{n}"},
    "merge_new": {"en": "new piece: {p}   (merge #{r} — learned {when})", "hi": "नया टुकड़ा: {p}   (merge #{r} — {when} सीखा)",
                  "hinglish": "naya tukda: {p}   (merge #{r} — {when} seekha)"},
    "early": {"en": "very early: a very common pair", "hi": "बहुत पहले: बहुत आम जोड़ा", "hinglish": "bahut pehle: bahut common pair"},
    "late": {"en": "late: a rarer pair", "hi": "बाद में: कम आम जोड़ा", "hinglish": "baad mein: rare pair"},
    "start_bytes": {"en": "start: raw bytes", "hi": "शुरुआत: कच्चे बाइट", "hinglish": "shuruaat: raw bytes"},
    # race
    "race_explain": {
        "en": {"simple": "The same sentence in three languages. Guess first: which one costs MONA the most tokens? Press 1, 2 or 3.",
               "student": "More tokens = more work for MONA and less room in its memory (1,024 tokens). Guess first: which "
                          "language uses the most tokens? Press 1, 2 or 3. You can edit the sentences after.",
               "engineer": "Token fertility per language. English-centric tokenizers spend 4-8 tokens per Hindi word; MONA's "
                           "balanced training sample was meant to fix that. Guess (1/2/3), then measure."},
        "hi": {"simple": "एक ही वाक्य तीन भाषाओं में। पहले अंदाज़ा लगाइए: किसमें MONA को सबसे ज़्यादा टोकन लगेंगे? 1, 2 या 3 दबाइए।",
               "student": "ज़्यादा टोकन = MONA के लिए ज़्यादा काम और उसकी याददाश्त (1,024 टोकन) में कम जगह। पहले अंदाज़ा: किस भाषा में "
                          "सबसे ज़्यादा टोकन? 1, 2 या 3 दबाइए। बाद में वाक्य बदल भी सकते हैं।",
               "engineer": "हर भाषा की token fertility। अंग्रेज़ी-केंद्रित tokenizer एक हिंदी शब्द पर 4-8 टोकन खर्च करते हैं; MONA का संतुलित "
                           "नमूना इसे ठीक करने के लिए था। अंदाज़ा (1/2/3), फिर नाप।"},
        "hinglish": {"simple": "Ek hi sentence teen bhashaon mein. Pehle guess karo: kis mein MONA ko sabse zyada tokens lagenge? 1, 2 ya 3 dabao.",
                     "student": "Zyada tokens = MONA ke liye zyada kaam aur uski memory (1,024 tokens) mein kam jagah. Pehle guess: kis "
                                "bhasha mein sabse zyada tokens? 1, 2 ya 3 dabao. Baad mein sentences badal bhi sakte ho.",
                     "engineer": "Har bhasha ki token fertility. English-centric tokenizers ek Hindi word par 4-8 tokens lagate hain; "
                                 "MONA ka balanced sample isse theek karne ke liye tha. Guess (1/2/3), phir measure."},
    },
    "race_guess": {"en": "Your guess: {g}", "hi": "आपका अंदाज़ा: {g}", "hinglish": "Aapka guess: {g}"},
    "race_right": {"en": "✓ Right!", "hi": "✓ सही!", "hinglish": "✓ Sahi!"},
    "race_wrong": {"en": "✗ Not this time. Surprised?", "hi": "✗ इस बार नहीं। हैरानी हुई?", "hinglish": "✗ Is baar nahi. Hairaan?"},
    "race_why": {"en": "Why? The tokenizer learns merges for text it saw a lot. Romanized Hindi was only ~5% of its training "
                        "text, so its words get cut into more pieces. More data in a language = cheaper tokens.",
                  "hi": "क्यों? tokenizer उसी लिखाई के जोड़ सीखता है जो उसने ज़्यादा देखी। रोमन हिंदी उसके प्रशिक्षण पाठ का केवल ~5% थी, "
                        "इसलिए उसके शब्द ज़्यादा टुकड़ों में कटते हैं। किसी भाषा का ज़्यादा डेटा = सस्ते टोकन।",
                  "hinglish": "Kyun? Tokenizer usi text ke merges seekhta hai jo usne zyada dekha. Roman Hindi uske training text ka "
                              "sirf ~5% thi, isliye uske words zyada tukdon mein katte hain. Zyada data = saste tokens."},
    "race_close": {"en": "(they're within 1 token: a near tie!)", "hi": "(1 टोकन का ही फ़र्क: लगभग बराबर!)",
                   "hinglish": "(sirf 1 token ka farak: lagbhag barabar!)"},
    # challenge
    "ch_explain": {
        "en": "Two challenges. Type a single word (no spaces) and press Enter.\n"
              "  A. Make MONA cut one word into at least 6 tokens.   B. Find the longest word MONA reads as ONE token.",
        "hi": "दो चुनौतियाँ। एक शब्द लिखिए (बिना स्पेस) और Enter दबाइए।\n"
              "  A. MONA से एक शब्द को कम से कम 6 टोकन में कटवाइए।   B. सबसे लंबा ऐसा शब्द खोजिए जिसे MONA एक ही टोकन में पढ़े।",
        "hinglish": "Do challenges. Ek word likho (bina space) aur Enter dabao.\n"
                    "  A. MONA se ek word ko kam se kam 6 tokens mein katwao.   B. Sabse lamba aisa word dhoondo jo MONA ek hi token mein padhe.",
    },
    "ch_prompt": {"en": "One word…", "hi": "एक शब्द…", "hinglish": "Ek word…"},
    "ch_a_done": {"en": "🏅 Challenge A done: {n} tokens! Badge: Token Tamer", "hi": "🏅 चुनौती A पूरी: {n} टोकन! बैज: Token Tamer",
                  "hinglish": "🏅 Challenge A done: {n} tokens! Badge: Token Tamer"},
    "ch_a_more": {"en": "{n} tokens. Need 6+. Try a rare, long or made-up word.", "hi": "{n} टोकन। 6+ चाहिए। कोई लंबा, दुर्लभ या बनाया हुआ शब्द आज़माइए।",
                  "hinglish": "{n} tokens. 6+ chahiye. Koi lamba, rare ya banaya hua word try karo."},
    "ch_b_rec": {"en": "One token, {c} characters! New record. (Best so far: {b})", "hi": "एक टोकन, {c} अक्षर! नया रिकॉर्ड। (अब तक का सबसे अच्छा: {b})",
                 "hinglish": "Ek token, {c} characters! Naya record. (Best ab tak: {b})"},
    "ch_b_one": {"en": "One token, {c} characters. Your record: {b}.", "hi": "एक टोकन, {c} अक्षर। आपका रिकॉर्ड: {b}।",
                 "hinglish": "Ek token, {c} characters. Aapka record: {b}."},
    "tok_keys": {"en": "Esc back   F5 Peek  F6 Merge  F7 Race  F8 Challenge   F2 language  F3 depth  F4 romanize",
                 "hi": "Esc वापस   F5 झाँकें  F6 जोड़  F7 दौड़  F8 चुनौती   F2 भाषा  F3 गहराई  F4 रोमन",
                 "hinglish": "Esc wapas   F5 Peek  F6 Merge  F7 Race  F8 Challenge   F2 bhasha  F3 depth  F4 roman"},
})

RACE = [("English", "India is a vast country where many languages are spoken."),
        ("हिंदी", "भारत एक विशाल देश है जहाँ अनेक भाषाएँ बोली जाती हैं।"),
        ("Hinglish", "Bharat ek vishal desh hai jahan anek bhashayein boli jaati hain.")]


class MergeView(Static, can_focus=True):
    """Focusable so Space / arrows control the animation once the word is entered."""
    BINDINGS = [Binding("space", "toggle", "play/pause"), Binding("left", "step(-1)", "back"),
                Binding("right", "step(1)", "forward"), Binding("slash", "edit", "edit")]

    def action_toggle(self):
        self.screen.merge_toggle()

    def action_step(self, d: int):
        self.screen.merge_step(d)

    def action_edit(self):
        self.screen.query_one("#merge-input").focus()


class RaceView(Static, can_focus=True):
    BINDINGS = [Binding("1", "guess(0)"), Binding("2", "guess(1)"), Binding("3", "guess(2)")]

    def action_guess(self, i: int):
        self.screen.race_guess(i)


class TokensLab(Screen):
    BINDINGS = [Binding("escape", "app.pop_screen", "back"), Binding("f5", "tab('peek')"), Binding("f6", "tab('merge')"),
                Binding("f7", "tab('race')"), Binding("f8", "tab('challenge')")]
    EXAMPLE = "भारत एक विशाल देश है और"

    def compose(self) -> ComposeResult:
        with Horizontal(classes="lab-head"):
            yield Avatar(id="avatar", classes="lab-avatar")
            yield Static(id="title", classes="lab-title")
        with TabbedContent(id="tabs"):
            with TabPane("Peek", id="peek"):
                yield Static(id="peek-explain", classes="explain")
                yield Input(id="peek-input")
                with VerticalScroll():
                    yield Static(id="peek-count", classes="count")
                    yield Static(id="peek-chips", classes="chips")
                    yield Static(id="next-title", classes="subtitle")
                    yield Static(id="next-explain", classes="dim")
                    yield Static(id="next-bars")
            with TabPane("Merge", id="merge"):
                yield Static(id="merge-explain", classes="explain")
                yield Input(id="merge-input")
                yield MergeView(id="merge-view", classes="panel")
            with TabPane("Race", id="race"):
                yield Static(id="race-explain", classes="explain")
                for i, (lang, sentence) in enumerate(RACE):
                    yield Input(sentence, id=f"race-{i}", classes="race-input")
                yield RaceView(id="race-view", classes="panel")
            with TabPane("Challenge", id="challenge"):
                yield Static(id="ch-explain", classes="explain")
                yield Input(id="ch-input")
                yield Static(id="ch-result", classes="panel")
        yield Static(id="keys", classes="keys")

    # ── setup ─────────────────────────────────────────────────────────────────
    def on_mount(self):
        self.merge_steps, self.merge_i, self.merge_timer = [], 0, None
        self.race_revealed, self.race_choice = False, None
        self.query_one("#peek-input", Input).value = getattr(self, "seed", None) or self.EXAMPLE
        self.query_one("#merge-input", Input).value = "भारत"
        self.refresh_texts()
        self.query_one("#peek-input").focus()

    def refresh_texts(self):
        tr = self.app.tr
        self.query_one("#title", Static).update(tr("tok_title"))
        tabs = self.query_one("#tabs", TabbedContent)
        for pane, key in (("peek", "tab_peek"), ("merge", "tab_merge"), ("race", "tab_race"), ("challenge", "tab_challenge")):
            tabs.get_tab(pane).label = tr(key)
        for wid, key in (("peek-explain", "tok_explain"), ("next-title", "next_title"), ("next-explain", "next_explain"),
                         ("merge-explain", "merge_explain"), ("race-explain", "race_explain"), ("ch-explain", "ch_explain"),
                         ("keys", "tok_keys")):
            self.query_one(f"#{wid}", Static).update(tr(key))
        self.query_one("#peek-input", Input).placeholder = tr("tok_prompt")
        self.query_one("#merge-input", Input).placeholder = tr("merge_prompt")
        self.query_one("#ch-input", Input).placeholder = tr("ch_prompt")
        self.peek()
        self.merge_load()
        self.race_draw()

    def on_engine_ready(self):
        self.refresh_texts()

    def action_tab(self, pane):
        self.query_one("#tabs", TabbedContent).active = pane
        first = {"peek": "#peek-input", "merge": "#merge-input", "race": "#race-view", "challenge": "#ch-input"}[pane]
        self.query_one(first).focus()

    @property
    def roman(self):
        return self.app.roman if self.app.state.romanize else None

    def on_input_changed(self, event: Input.Changed):
        if event.input.id == "peek-input":
            self.peek()
        elif event.input.id.startswith("race-") and self.race_revealed:
            self.race_draw()

    def on_input_submitted(self, event: Input.Submitted):
        if event.input.id == "merge-input":
            self.merge_load(autoplay=True)
            self.query_one("#merge-view").focus()
        elif event.input.id == "ch-input":
            self.challenge(event.value.strip())
        elif event.input.id.startswith("race-"):
            self.query_one("#race-view").focus()

    # ── Peek ─────────────────────────────────────────────────────────────────
    def peek(self):
        if self.app.gb is None:
            self.query_one("#peek-chips", Static).update(self.app.tr("loading"))
            self.query_one("#avatar", Avatar).set_mood("sleepy")
            return
        self.query_one("#avatar", Avatar).set_mood("thinking")
        self._peek(self.query_one("#peek-input", Input).value, self.app.state.depth)

    @work(thread=True, exclusive=True, group="peek")
    def _peek(self, text, depth):
        gb = self.app.gb
        tokens = gb.tokens(text) if text else []
        guesses = gb.next_word(text, top=8) if text else []
        self.app.call_from_thread(self._peek_show, text, tokens, guesses, depth)

    def _peek_show(self, text, tokens, guesses, depth):
        self.query_one("#peek-count", Static).update(
            Text(self.app.tr("tok_count", chars=len(text), n=len(tokens)), style="bold #06d6a0"))
        self.query_one("#peek-chips", Static).update(token_chips(tokens, self.roman, show_ids=depth != "simple"))
        self.query_one("#next-bars", Static).update(prob_bars(guesses, self.roman) if guesses else "")
        self.query_one("#avatar", Avatar).set_mood("wow" if guesses and guesses[0].prob > 0.3 else "happy")
        if len(text) > 3:
            self.app.state.complete("tokens")

    # ── Merge ────────────────────────────────────────────────────────────────
    def merge_load(self, autoplay=False):
        word = self.query_one("#merge-input", Input).value.strip()
        self.merge_steps = bpe_replay(self.app.tokenizer, word) if word else []
        self.merge_i = 0 if autoplay else max(len(self.merge_steps) - 1, 0)
        if self.merge_timer:
            self.merge_timer.stop()
            self.merge_timer = None
        if autoplay and len(self.merge_steps) > 1:
            self.merge_timer = self.set_interval(0.7, lambda: self.merge_step(1, auto=True))
        self.merge_draw()

    def merge_toggle(self):
        if self.merge_timer:
            self.merge_timer.stop()
            self.merge_timer = None
        else:
            if self.merge_i >= len(self.merge_steps) - 1:
                self.merge_i = 0
            self.merge_timer = self.set_interval(0.7, lambda: self.merge_step(1, auto=True))

    def merge_step(self, d, auto=False):
        if not self.merge_steps:
            return
        self.merge_i = min(max(self.merge_i + d, 0), len(self.merge_steps) - 1)
        if auto and self.merge_i == len(self.merge_steps) - 1 and self.merge_timer:
            self.merge_timer.stop()
            self.merge_timer = None
        self.merge_draw()

    def merge_draw(self):
        tr, view = self.app.tr, self.query_one("#merge-view", Static)
        if not self.merge_steps:
            view.update("")
            return
        step = self.merge_steps[self.merge_i]
        out = Text()
        out.append(tr("merge_step", i=self.merge_i, n=len(self.merge_steps) - 1) + "\n\n", style="bold #8ecae6")
        for k, piece in enumerate(step.pieces):
            shown = self.roman(piece) if self.roman else piece
            is_new = step.merged and piece == step.merged
            style = "bold #14172b on #ffd166" if is_new else f"#1b1f3b on {CHIP_COLOURS[k % len(CHIP_COLOURS)]}"
            out.append(f" {show_piece(shown)} ", style=style)
            out.append(" ")
        out.append("\n\n")
        if step.rank < 0:
            out.append(tr("start_bytes"), style="#f4a3c0")
        else:
            when = tr("early") if step.rank < 1000 else tr("late")
            out.append(tr("merge_new", p=step.merged, r=step.rank, when=when), style="#06d6a0")
        # progress strip: how many pieces at each step
        out.append("\n\n" + "  ".join(str(len(s.pieces)) for s in self.merge_steps), style="#5a5f7c")
        view.update(out)

    # ── Race ─────────────────────────────────────────────────────────────────
    def race_guess(self, i):
        self.race_choice, self.race_revealed = i, True
        self.race_draw()

    def race_draw(self):
        view = self.query_one("#race-view", Static)
        tr = self.app.tr
        if not self.race_revealed:
            view.update(Text("  1 = English     2 = हिंदी     3 = Hinglish      ?", style="bold #ffd166"))
            return
        texts = [self.query_one(f"#race-{i}", Input).value for i in range(3)]
        counts = [len(self.app.tokenizer.encode(t).ids) for t in texts]
        most = max(range(3), key=lambda i: counts[i])
        out = Text()
        out.append(tr("race_guess", g=RACE[self.race_choice][0]) + "   ", style="bold")
        right = counts[self.race_choice] == counts[most]
        out.append(tr("race_right") if right else tr("race_wrong"), style="bold #06d6a0" if right else "bold #f4a3c0")
        if sorted(counts)[-1] - sorted(counts)[-2] <= 1:
            out.append("  " + tr("race_close"), style="#8a8fb0")
        out.append("\n\n")
        top = max(counts) or 1
        label_w = max(cell_len(lang) for lang, _ in RACE) + 2      # pad by screen cells, not characters
        for i, (lang, _) in enumerate(RACE):
            bar = "█" * max(1, round(40 * counts[i] / top))
            words = max(len(texts[i].split()), 1)
            out.append(lang + " " * (label_w - cell_len(lang)), style="bold")
            out.append(bar, style=CHIP_COLOURS[i])
            out.append(f"  {counts[i]} tokens · {counts[i] / words:.2f} per word · {len(texts[i]) / max(counts[i], 1):.1f} chars/token\n",
                       style="#c9cce0")
        out.append("\n" + tr("race_why"), style="italic #8ecae6")
        view.update(out)
        self.query_one("#avatar", Avatar).set_mood("wow" if right else "thinking")

    # ── Challenge ────────────────────────────────────────────────────────────
    def challenge(self, word):
        if not word or " " in word:
            return
        tr, st = self.app.tr, self.app.state
        # tokenized as it appears mid-sentence (" word"), the way MONA usually meets words
        tokens = self.app.gb.tokens(" " + word) if self.app.gb else []
        n = len(tokens)
        out = Text()
        out.append_text(token_chips(tokens, self.roman))
        out.append("\n\n")
        if n >= 6:
            st.complete("tokens", badge="Token Tamer")
            out.append(tr("ch_a_done", n=n) + "\n", style="bold #ffd166")
        else:
            out.append(tr("ch_a_more", n=n) + "\n", style="#c9cce0")
        if n == 1:
            best = max(st.records.get("one_token_chars", 0), len(word))
            new = len(word) > st.records.get("one_token_chars", 0)
            st.records["one_token_chars"] = best
            st.save()
            out.append(tr("ch_b_rec" if new else "ch_b_one", c=len(word), b=best), style="bold #06d6a0")
        self.query_one("#ch-result", Static).update(out)
        self.query_one("#avatar", Avatar).set_mood("wow" if n >= 6 or n == 1 else "happy")

    def export(self):
        from .. import exports
        text = self.query_one("#peek-input", Input).value
        return exports.tokens(text, self.app.gb.tokens(text) if self.app.gb else [])
