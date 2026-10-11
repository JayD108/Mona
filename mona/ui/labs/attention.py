"""Stage 4 — Attention: which earlier words each word looks at, in every layer and head."""
import random

import torch
from rich.cells import cell_len
from rich.text import Text
from textual import work
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, VerticalScroll
from textual.screen import Screen
from textual.widgets import Input, Static

from ...engine.lessons import head_roles
from ..text import register
from ..widgets import Avatar, show_piece

register({
    "att_title": {"en": "Attention: what each word looks at", "hi": "अटेंशन: हर शब्द किसे देखता है",
                  "hinglish": "Attention: har word kise dekhta hai"},
    "att_explain": {
        "en": {"simple": "To understand a word, MONA looks back at earlier words. Brighter square = looks more. "
                         "Each row is a word; the squares show which earlier words it looked at.",
               "student": "Attention lets every token gather information from earlier tokens. MONA has 12 layers × 12 heads "
                          "= 144 attention patterns; each head learns its own job. Row = the token doing the looking, "
                          "column = the token being looked at. Brighter = more attention.",
               "engineer": "softmax(QKᵀ/√64 + causal mask) per head, computed explicitly from MONA's weights (the fused "
                           "kernel hides it). Rows sum to 1. Shown: layer L, head H, or the mean over heads."},
        "hi": {"simple": "किसी शब्द को समझने के लिए MONA पीछे के शब्दों को देखती है। ज़्यादा चमकीला खाना = ज़्यादा ध्यान। "
                         "हर पंक्ति एक शब्द है; खाने दिखाते हैं उसने पीछे के किन शब्दों को देखा।",
               "student": "Attention से हर टोकन पिछले टोकनों से जानकारी इकट्ठा करता है। MONA में 12 लेयर × 12 हेड = 144 "
                          "अटेंशन पैटर्न हैं; हर हेड अपना काम सीखता है। पंक्ति = देखने वाला टोकन, स्तंभ = जिसे देखा गया। "
                          "ज़्यादा चमक = ज़्यादा ध्यान।",
               "engineer": "हर हेड के लिए softmax(QKᵀ/√64 + causal mask), MONA के वज़न से सीधे गणना (fused kernel इसे छिपाता है)। "
                           "हर पंक्ति का जोड़ 1। दिखाया: लेयर L, हेड H, या सभी हेड का औसत।"},
        "hinglish": {"simple": "Kisi word ko samajhne ke liye MONA peeche ke words dekhti hai. Zyada chamakdaar box = zyada dhyaan. "
                               "Har row ek word hai; boxes dikhate hain usne peeche ke kaunse words dekhe.",
                     "student": "Attention se har token pichhle tokens se jaankari jama karta hai. MONA mein 12 layers × 12 heads "
                                "= 144 attention patterns hain; har head apna kaam seekhta hai. Row = dekhne wala token, "
                                "column = jise dekha gaya. Zyada chamak = zyada attention.",
                     "engineer": "Har head ke liye softmax(QKᵀ/√64 + causal mask), MONA ke weights se seedha compute (fused kernel "
                                 "ise chhupata hai). Har row ka total 1. Dikhaya: layer L, head H, ya saare heads ka average."},
    },
    "att_prompt": {"en": "A sentence to look inside (Enter)…", "hi": "अंदर झाँकने के लिए एक वाक्य (Enter)…",
                   "hinglish": "Andar jhaankne ke liye ek sentence (Enter)…"},
    "att_where": {"en": "layer {l}/11 · {h}", "hi": "लेयर {l}/11 · {h}", "hinglish": "layer {l}/11 · {h}"},
    "att_head": {"en": "head {h}/11", "hi": "हेड {h}/11", "hinglish": "head {h}/11"},
    "att_avg": {"en": "average of 12 heads", "hi": "12 हेड का औसत", "hinglish": "12 heads ka average"},
    "att_focus": {"en": "“{w}” looks at:", "hi": "“{w}” इन्हें देखता है:", "hinglish": "“{w}” inhe dekhta hai:"},
    "att_roles": {"en": "Heads MONA taught itself (found in this sentence)", "hi": "MONA ने खुद सीखे हेड (इस वाक्य में मिले)",
                  "hinglish": "MONA ne khud seekhe heads (is sentence mein mile)"},
    "att_prev": {"en": "previous-word heads: always look at the word just before", "hi": "पिछला-शब्द हेड: हमेशा ठीक पिछले शब्द को देखते हैं",
                 "hinglish": "previous-word heads: hamesha theek pichhle word ko dekhte hain"},
    "att_sink": {"en": "first-word heads: park attention on the first token when nothing else matters",
                 "hi": "पहला-शब्द हेड: जब कुछ ख़ास न हो तो ध्यान पहले टोकन पर टिका देते हैं",
                 "hinglish": "first-word heads: jab kuch khaas na ho to dhyaan pehle token par tika dete hain"},
    "att_quiz": {"en": "🕵 Detective: in layer {l}, head {h}, which word does “{w}” look at MOST? Press its number.",
                 "hi": "🕵 जासूस: लेयर {l}, हेड {h} में “{w}” सबसे ज़्यादा किसे देखता है? उसका नंबर दबाइए।",
                 "hinglish": "🕵 Detective: layer {l}, head {h} mein “{w}” sabse zyada kise dekhta hai? Uska number dabao."},
    "att_right": {"en": "✓ Right! ({n}/3)", "hi": "✓ सही! ({n}/3)", "hinglish": "✓ Sahi! ({n}/3)"},
    "att_wrong": {"en": "✗ It was “{w}”. Look at the brightest square in that row.", "hi": "✗ जवाब था “{w}”। उस पंक्ति का सबसे चमकीला खाना देखिए।",
                  "hinglish": "✗ Jawab tha “{w}”. Us row ka sabse chamakdaar box dekho."},
    "att_badge": {"en": "🏅 Badge: Attention Detective", "hi": "🏅 बैज: Attention Detective", "hinglish": "🏅 Badge: Attention Detective"},
    "att_keys": {"en": "←→ layer  ↑↓ head  A average  [ ] pick word  V view  J best previous-word head  ? detective  X example  / edit  Esc",
                 "hi": "←→ लेयर  ↑↓ हेड  A औसत  [ ] शब्द चुनें  V दृश्य  J पिछला-शब्द हेड  ? जासूस  X उदाहरण  / बदलें  Esc",
                 "hinglish": "←→ layer  ↑↓ head  A average  [ ] word chuno  V view  J prev-word head  ? detective  X example  / edit  Esc"},
})

EXAMPLES = ["The cat sat on the mat because it was tired.",
            "राम ने धनुष तोड़ा और सीता ने माला पहनाई।",
            "Mujhe chai pasand hai kyunki woh garam hoti hai.",
            "1 2 3 4 5 1 2 3 4 5"]
HEAT = ["#1b1f3b", "#2b2f55", "#3d3a70", "#5a3f86", "#7e4a92", "#a85a8f", "#d0707e", "#ee9468", "#fbbf5e", "#ffe28a"]
MAX_TOKENS = 22


def heat(w):
    return HEAT[min(int((w ** 0.5) * len(HEAT)), len(HEAT) - 1)]     # sqrt: small weights stay visible


class Grid(Static, can_focus=True):
    BINDINGS = [Binding("left", "screen.layer(-1)"), Binding("right", "screen.layer(1)"),
                Binding("up", "screen.head(-1)"), Binding("down", "screen.head(1)"), Binding("a", "screen.avg"),
                Binding("left_square_bracket", "screen.word(-1)"), Binding("right_square_bracket", "screen.word(1)"),
                Binding("v", "screen.view"), Binding("j", "screen.jump"), Binding("question_mark", "screen.quiz"),
                Binding("x", "screen.example"), Binding("slash", "screen.edit")] + \
               [Binding(str(i), f"screen.answer({i})") for i in range(1, 10)]


class AttentionLab(Screen):
    BINDINGS = [Binding("escape", "app.pop_screen", "back")]

    def compose(self) -> ComposeResult:
        with Horizontal(classes="lab-head"):
            yield Avatar(id="avatar", classes="lab-avatar")
            yield Static(id="title", classes="lab-title")
        yield Static(id="explain", classes="explain")
        yield Input(id="sentence")
        with VerticalScroll():
            yield Grid(id="grid", classes="panel")
            yield Static(id="roles", classes="panel")
        yield Static(id="keys", classes="keys")

    def on_mount(self):
        self.cur_layer, self.cur_head, self.avg, self.focus_i, self.view_focus = 0, 0, False, None, False
        self.example_i, self.trace, self.quiz_q, self.quiz_wins = 0, None, None, 0
        self.query_one("#sentence", Input).value = getattr(self, "seed", None) or EXAMPLES[0]
        self.refresh_texts()
        self.run_trace()

    def refresh_texts(self):
        tr = self.app.tr
        self.query_one("#title", Static).update(tr("att_title"))
        self.query_one("#explain", Static).update(tr("att_explain"))
        self.query_one("#sentence", Input).placeholder = tr("att_prompt")
        self.query_one("#keys", Static).update(tr("att_keys"))
        self.draw()

    def on_engine_ready(self):
        self.run_trace()

    def on_input_submitted(self, event: Input.Submitted):
        self.run_trace()

    @work(thread=True, exclusive=True)
    def run_trace(self):
        gb = self.app.gb
        if gb is None:
            return
        text = self.query_one("#sentence", Input).value
        ids = gb.encode(text)[:MAX_TOKENS]
        trace = gb.trace(gb.tok.decode(ids)) if ids else None
        self.app.call_from_thread(self._traced, trace)

    def _traced(self, trace):
        self.trace = trace
        self.roles = head_roles(trace.attention) if trace and len(trace.tokens) > 2 else []
        self.focus_i = len(trace.tokens) - 1 if trace else None
        self.quiz_q = None
        self.query_one("#grid").focus()
        self.draw()

    # ── controls ─────────────────────────────────────────────────────────────
    def action_layer(self, d: int):
        self.cur_layer = (self.cur_layer + d) % 12
        self.draw()

    def action_head(self, d: int):
        self.cur_head, self.avg = (self.cur_head + d) % 12, False
        self.draw()

    def action_avg(self):
        self.avg = not self.avg
        self.draw()

    def action_word(self, d: int):
        if self.trace:
            self.focus_i = (self.focus_i + d) % len(self.trace.tokens)
            self.draw()

    def action_view(self):
        self.view_focus = not self.view_focus
        self.draw()

    def action_jump(self):
        if self.roles:
            best = max(self.roles, key=lambda r: r["previous"])
            self.cur_layer, self.cur_head, self.avg = best["layer"], best["head"], False
            self.app.state.complete("attention")
            self.draw()

    def action_example(self):
        self.example_i = (self.example_i + 1) % len(EXAMPLES)
        self.query_one("#sentence", Input).value = EXAMPLES[self.example_i]
        self.run_trace()

    def action_edit(self):
        self.query_one("#sentence").focus()

    def action_quiz(self):
        """Pick a (layer, head, word) whose attention is clearly focused on one earlier word (not itself / not the 1st)."""
        if not self.trace or len(self.trace.tokens) < 4:
            return
        A = self.trace.attention
        options = []
        for l in range(12):
            for h in range(12):
                for i in range(2, len(self.trace.tokens)):
                    row = A[l, h, i, :i + 1]
                    j = int(row.argmax())
                    if 0 < j < i and row[j] > 0.5 and j >= i - 8:
                        options.append((l, h, i, j))
        if not options:
            return
        l, h, i, j = random.choice(options)
        self.cur_layer, self.cur_head, self.avg, self.focus_i, self.view_focus = l, h, False, i, True
        self.quiz_q = (i, j, max(0, i - 8))
        self.draw()

    def action_answer(self, n: int):
        if not self.quiz_q:
            return
        i, j, start = self.quiz_q
        guess = start + n - 1
        right = guess == j
        if right:
            self.quiz_wins += 1
        self.quiz_result = (right, j)
        self.quiz_q = None
        if self.quiz_wins >= 3:
            self.app.state.complete("attention", badge="Attention Detective")
        self.draw(answered=True)

    # ── drawing ──────────────────────────────────────────────────────────────
    def label(self, tok):
        piece = show_piece(tok.text)
        return self.app.roman(piece) if self.app.state.romanize else piece

    def current(self):
        A = self.trace.attention[self.cur_layer]
        return A.mean(0) if self.avg else A[self.cur_head]

    def draw(self, answered=False):
        tr, grid = self.app.tr, self.query_one("#grid", Static)
        if self.trace is None:
            grid.update(tr("loading"))
            return
        toks = [self.label(t) for t in self.trace.tokens]
        W = self.current()
        where = tr("att_avg") if self.avg else tr("att_head", h=self.cur_head)
        out = Text(tr("att_where", l=self.cur_layer, h=where) + "\n\n", style="bold #8ecae6")
        if self.view_focus and self.focus_i is not None:
            i = self.focus_i
            out.append(tr("att_focus", w=toks[i]) + "\n\n", style="bold #ffd166")
            start = max(0, i - 8) if self.quiz_q or answered else 0
            label_w = max(cell_len(t) for t in toks[:i + 1]) + 2
            for n, j in enumerate(range(start, i + 1), 1):
                w = W[i, j].item()
                out.append(f"{n} " if self.quiz_q else "  ", style="#ffd166")
                out.append(toks[j] + " " * (label_w - cell_len(toks[j])), style="bold")
                if not self.quiz_q:
                    out.append("█" * max(1, round(40 * w)), style=heat(w))
                    out.append(f" {w:5.1%}", style="#c9cce0")
                out.append("\n")
        else:
            label_w = max(cell_len(t) for t in toks) + 1
            for i, row_tok in enumerate(toks):
                mark = "▶" if i == self.focus_i else " "
                out.append(f"{mark}{row_tok}" + " " * (label_w - cell_len(row_tok)), style="bold #ffd166" if mark == "▶" else "#c9cce0")
                for j in range(len(toks)):
                    out.append("██" if j <= i else "  ", style=heat(W[i, j].item()) if j <= i else "")
                out.append("\n")
            out.append(" " * (label_w + 1) + "".join(f"{j % 10} " for j in range(len(toks))) + "\n", style="#5a5f7c")
            out.append(" " * (label_w + 1) + "  ".join(f"{j}={t}" for j, t in enumerate(toks)), style="#5a5f7c")
        if self.quiz_q:
            i, j, _ = self.quiz_q
            out.append("\n" + tr("att_quiz", l=self.cur_layer, h=self.cur_head, w=toks[i]), style="bold #f4a3c0")
        elif answered:
            right, j = self.quiz_result
            out.append("\n" + (tr("att_right", n=self.quiz_wins) if right else tr("att_wrong", w=toks[j])),
                       style="bold #06d6a0" if right else "bold #f4a3c0")
            if self.quiz_wins >= 3:
                out.append("   " + tr("att_badge"), style="bold #ffd166")
            self.query_one("#avatar", Avatar).set_mood("wow" if right else "thinking")
        grid.update(out)

        roles = Text(tr("att_roles") + "\n", style="bold #8ecae6")
        if self.roles:
            prev = sorted(self.roles, key=lambda r: -r["previous"])[:3]
            sink = sorted(self.roles, key=lambda r: -r["first"])[:3]
            roles.append(tr("att_prev") + ":  ", style="#c9cce0")
            roles.append("   ".join(f"L{r['layer']}·H{r['head']} ({r['previous']:.0%})" for r in prev) + "\n", style="bold #06d6a0")
            roles.append(tr("att_sink") + ":  ", style="#c9cce0")
            roles.append("   ".join(f"L{r['layer']}·H{r['head']} ({r['first']:.0%})" for r in sink), style="bold #cdb4db")
        self.query_one("#roles", Static).update(roles)

    def export(self):
        from .. import exports
        if not self.trace:
            return "Attention", "(nothing traced yet)", ""
        head = None if self.avg else self.cur_head
        return exports.attention(self.query_one("#sentence", Input).value, self.trace.tokens,
                                 self.current().tolist(), self.cur_layer, head)
