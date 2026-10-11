"""Stage 9 — Evals: how do we know if a language model is any good?"""
import math

import torch
import torch.nn.functional as F
from rich.cells import cell_len
from rich.text import Text
from textual import work
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, VerticalScroll
from textual.screen import Screen
from textual.widgets import Input, Static, TabbedContent, TabPane

from ...engine.lessons import training_curves
from ..text import register
from ..widgets import Avatar, show_piece

register({
    "ev_title": {"en": "Evals: testing a language model", "hi": "Evals: भाषा मॉडल की परीक्षा", "hinglish": "Evals: language model ka test"},
    "ev_tab_exam": {"en": "Mini exam", "hi": "छोटी परीक्षा", "hinglish": "Mini exam"},
    "ev_tab_own": {"en": "Make your own exam", "hi": "अपनी परीक्षा बनाइए", "hinglish": "Apna exam banao"},
    "ev_tab_surprise": {"en": "Surprise meter", "hi": "हैरानी मीटर", "hinglish": "Surprise meter"},
    "ev_explain": {
        "en": {"simple": "How do we know if MONA is good? We test it, like an exam. MONA picks the answer that sounds most "
                         "natural to it. Random guessing would get 25%.",
               "student": "Real benchmarks (HellaSwag, MMLU…) often score a base model like this: for each answer option, "
                          "measure how likely MONA finds it after the question, and pick the most likely. No chat needed. "
                          "Compare with chance (25% for 4 options).",
               "engineer": "Log-likelihood multiple choice: score(option) = mean log p(option tokens | question), argmax over "
                           "options (length-normalised, like acc_norm). The surprise meter shows −log₂ p per token and bits/byte."},
        "hi": {"simple": "कैसे पता चले कि MONA अच्छी है? परीक्षा लेकर। MONA वह जवाब चुनती है जो उसे सबसे स्वाभाविक लगे। "
                         "तुक्के से 25% सही आते।",
               "student": "असली बेंचमार्क (HellaSwag, MMLU…) अक्सर base मॉडल को ऐसे जाँचते हैं: हर विकल्प के लिए नापो कि सवाल "
                          "के बाद MONA को वह कितना संभावित लगता है, और सबसे संभावित चुनो। चैट की ज़रूरत नहीं। तुक्के (25%) से तुलना करें।",
               "engineer": "Log-likelihood बहुविकल्पी: score(option) = mean log p(option tokens | प्रश्न), विकल्पों पर argmax "
                           "(length-normalised, acc_norm जैसा)। हैरानी मीटर हर टोकन का −log₂ p और bits/byte दिखाता है।"},
        "hinglish": {"simple": "Kaise pata chale ki MONA achhi hai? Exam lekar. MONA woh jawab chunti hai jo use sabse natural lage. "
                               "Tukke se 25% sahi aate.",
                     "student": "Asli benchmarks (HellaSwag, MMLU…) aksar base model ko aise check karte hain: har option ke liye "
                                "naapo ki sawaal ke baad MONA ko woh kitna likely lagta hai, aur sabse likely chuno. Chat ki zaroorat "
                                "nahi. Tukke (25%) se compare karo.",
                     "engineer": "Log-likelihood multiple choice: score(option) = mean log p(option tokens | question), options par "
                                 "argmax (length-normalised, acc_norm jaisa). Surprise meter har token ka −log₂ p aur bits/byte dikhata hai."},
    },
    "ev_run": {"en": "Press R to run the exam.", "hi": "परीक्षा चलाने के लिए R दबाइए।", "hinglish": "Exam chalane ke liye R dabao."},
    "ev_score": {"en": "MONA scored {k}/{n} = {p:.0%}   (random guessing ≈ 25%)", "hi": "MONA का स्कोर {k}/{n} = {p:.0%}   (तुक्का ≈ 25%)",
                 "hinglish": "MONA ka score {k}/{n} = {p:.0%}   (tukka ≈ 25%)"},
    "ev_own_help": {"en": "Write:  question | right answer* | wrong | wrong   (mark the right one with *), then Enter.",
                    "hi": "लिखिए:  प्रश्न | सही उत्तर* | गलत | गलत   (सही उत्तर पर * लगाइए), फिर Enter।",
                    "hinglish": "Likho:  sawaal | sahi jawab* | galat | galat   (sahi wale par * lagao), phir Enter."},
    "ev_own_bad": {"en": "Need a question, 2-4 options, and exactly one marked with *.", "hi": "एक प्रश्न, 2-4 विकल्प, और ठीक एक पर * चाहिए।",
                   "hinglish": "Ek sawaal, 2-4 options, aur theek ek par * chahiye."},
    "ev_badge": {"en": "🏅 Badge: Exam Maker", "hi": "🏅 बैज: Exam Maker", "hinglish": "🏅 Badge: Exam Maker"},
    "ev_sur_help": {"en": "Type a sentence: each piece is coloured by how surprised MONA was (red = very surprised).",
                    "hi": "एक वाक्य लिखिए: हर टुकड़ा इस बात से रंगा है कि MONA कितनी हैरान हुई (लाल = बहुत हैरान)।",
                    "hinglish": "Ek sentence likho: har tukda is baat se ranga hai ki MONA kitni hairaan hui (laal = bahut hairaan)."},
    "ev_bpb": {"en": "{bits:.1f} bits of surprise over {bytes} bytes = {bpb:.2f} bits per byte  (lower = MONA finds it more natural)",
               "hi": "{bytes} बाइट पर {bits:.1f} बिट हैरानी = {bpb:.2f} bits per byte  (कम = MONA को ज़्यादा स्वाभाविक लगा)",
               "hinglish": "{bytes} bytes par {bits:.1f} bits surprise = {bpb:.2f} bits per byte  (kam = MONA ko zyada natural laga)"},
    "ev_trend": {"en": "MONA's real held-out loss during training (per language):", "hi": "ट्रेनिंग के दौरान MONA का असली held-out loss (हर भाषा):",
                 "hinglish": "Training ke dauraan MONA ka asli held-out loss (har bhasha):"},
    "ev_keys": {"en": "Esc back   F5 Mini exam  F6 Make your own  F7 Surprise meter   R run   F2 language  F3 depth  F4 romanize",
                "hi": "Esc वापस   F5 परीक्षा  F6 अपनी परीक्षा  F7 हैरानी मीटर   R चलाएँ   F2 भाषा  F3 गहराई  F4 रोमन",
                "hinglish": "Esc wapas   F5 Mini exam  F6 Apna exam  F7 Surprise meter   R run   F2 bhasha  F3 depth  F4 roman"},
})

EXAM = [  # (question, [options], index of the right one)
    ("The sun rises in the", ["east", "west", "south", "north"], 0),
    ("Water boils at 100 degrees", ["Celsius", "kilometres", "rupees", "minutes"], 0),
    ("A week has seven", ["days", "months", "cats", "rivers"], 0),
    ("The capital of India is New", ["Delhi", "York", "Zealand", "Jersey"], 0),
    ("Birds can fly because they have", ["wings", "wheels", "roots", "engines"], 0),
    ("She drank a glass of cold", ["water", "stone", "paper", "iron"], 0),
    ("सूरज पूरब में", ["उगता है", "डूबता है", "सोता है", "पढ़ता है"], 0),
    ("एक साल में बारह", ["महीने होते हैं", "दिन होते हैं", "घंटे होते हैं", "साल होते हैं"], 0),
    ("गाय हमें", ["दूध देती है", "पत्थर देती है", "बिजली देती है", "किताब देती है"], 0),
    ("भारत की राजधानी नई", ["दिल्ली है", "मुंबई है", "चेन्नई है", "कोलकाता है"], 0),
    ("Main roz subah chai", ["peeta hoon", "khata hoon", "sota hoon", "likhta hoon"], 0),
]
SURPRISE = ["#06d6a0", "#b5e48c", "#ffd166", "#f78c6b", "#ef476f"]


@torch.no_grad()
def option_scores(gb, question, options):
    """Mean log-probability of each option's tokens after the question (higher = more natural to MONA)."""
    q = gb.encode(question)
    scores = []
    for opt in options:
        o = gb.encode(" " + opt)
        ids = torch.tensor([q + o])
        logits, _ = gb.model(ids[:, :-1], ids[:, 1:])            # full logits (targets given)
        logp = F.log_softmax(logits.view(-1, logits.size(-1)), dim=-1)
        tgt = ids[0, 1:]
        lp = logp[torch.arange(len(tgt)), tgt][-len(o):]
        scores.append(lp.mean().item())
    return scores


class Run(Static, can_focus=True):
    BINDINGS = [Binding("r", "screen.run_exam")]


class EvalsLab(Screen):
    BINDINGS = [Binding("escape", "app.pop_screen", "back"), Binding("f5", "tab('exam')"),
                Binding("f6", "tab('own')"), Binding("f7", "tab('surprise')")]

    def compose(self) -> ComposeResult:
        with Horizontal(classes="lab-head"):
            yield Avatar(id="avatar", classes="lab-avatar")
            yield Static(id="title", classes="lab-title")
        yield Static(id="explain", classes="explain")
        with TabbedContent(id="tabs"):
            with TabPane("Mini exam", id="exam"):
                with VerticalScroll():
                    yield Run(id="exam-view", classes="panel")
            with TabPane("Make your own exam", id="own"):
                yield Static(id="own-help", classes="explain")
                yield Input(id="own-input")
                with VerticalScroll():
                    yield Static(id="own-view", classes="panel")
            with TabPane("Surprise meter", id="surprise"):
                yield Static(id="sur-help", classes="explain")
                yield Input(id="sur-input")
                with VerticalScroll():
                    yield Static(id="sur-view", classes="panel")
                    yield Static(id="trend", classes="panel")
        yield Static(id="keys", classes="keys")

    def on_mount(self):
        self.exam_results, self.own = None, list(self.app.state.records.get("own_exam", []))
        self.query_one("#own-input", Input).value = "The opposite of hot is | cold* | blue | fast | loud"
        self.query_one("#sur-input", Input).value = getattr(self, "seed", None) or "भारत एक विशाल देश है। India is a vast country."
        self.refresh_texts()
        self.query_one("#exam-view").focus()
        if getattr(self, "seed", None):
            self.call_after_refresh(self.action_tab, "surprise")

    def refresh_texts(self):
        tr = self.app.tr
        self.query_one("#title", Static).update(tr("ev_title"))
        self.query_one("#explain", Static).update(tr("ev_explain"))
        self.query_one("#own-help", Static).update(tr("ev_own_help"))
        self.query_one("#sur-help", Static).update(tr("ev_sur_help"))
        self.query_one("#keys", Static).update(tr("ev_keys"))
        tabs = self.query_one("#tabs", TabbedContent)
        for pane, key in (("exam", "ev_tab_exam"), ("own", "ev_tab_own"), ("surprise", "ev_tab_surprise")):
            tabs.get_tab(pane).label = tr(key)
        self.draw_exam()
        self.draw_own()
        self.draw_trend()
        if self.app.gb:
            self.surprise()

    def on_engine_ready(self):
        self.surprise()

    def action_tab(self, pane):
        self.query_one("#tabs", TabbedContent).active = pane
        self.query_one({"exam": "#exam-view", "own": "#own-input", "surprise": "#sur-input"}[pane]).focus()

    @property
    def rr(self):
        return self.app.roman if self.app.state.romanize else (lambda s: s)

    # ── built-in exam ────────────────────────────────────────────────────────
    @work(thread=True, exclusive=True, group="exam")
    def action_run_exam(self):
        gb = self.app.gb
        if gb is None:
            return
        results = [(q, opts, right, option_scores(gb, q, opts)) for q, opts, right in EXAM]
        self.app.call_from_thread(self._exam_done, results)

    def _exam_done(self, results):
        self.exam_results = results
        self.app.state.complete("evals")
        self.draw_exam()

    def render_question(self, out, q, opts, right, scores):
        pick = max(range(len(opts)), key=lambda i: scores[i])
        ok = pick == right
        out.append(("✓ " if ok else "✗ "), style="bold #06d6a0" if ok else "bold #ef476f")
        out.append(self.rr(q) + " …\n", style="bold #e8e8f0")
        lo, hi = min(scores), max(scores)
        for i, (o, s) in enumerate(zip(opts, scores)):
            bar = "█" * max(1, round(18 * (s - lo) / ((hi - lo) or 1)))
            style = "#06d6a0" if i == right else "#8a8fb0"
            out.append(f"     {'★' if i == right else ' '} ", style="#ffd166")
            piece = self.rr(o)
            out.append(piece + " " * max(1, 18 - cell_len(piece)), style=style)
            out.append(bar, style="#ffd166" if i == pick else "#3a3f5c")
            out.append(f" {s:6.2f}{'  ← MONA' if i == pick else ''}\n", style=style)
        return ok

    def draw_exam(self):
        tr, view = self.app.tr, self.query_one("#exam-view", Static)
        if not self.exam_results:
            view.update(Text(tr("ev_run"), style="bold #ffd166"))
            return
        out, k = Text(), 0
        for q, opts, right, scores in self.exam_results:
            k += self.render_question(out, q, opts, right, scores)
        n = len(self.exam_results)
        out.append("\n" + tr("ev_score", k=k, n=n, p=k / n), style="bold #8ecae6")
        view.update(out)
        self.query_one("#avatar", Avatar).set_mood("wow" if k / n > 0.5 else "thinking")

    # ── your own exam ────────────────────────────────────────────────────────
    def on_input_submitted(self, event: Input.Submitted):
        if event.input.id == "own-input":
            self.add_own(event.value)
        elif event.input.id == "sur-input":
            self.surprise()

    def add_own(self, line):
        parts = [p.strip() for p in line.split("|")]
        q, opts = parts[0], parts[1:]
        if not q or not 2 <= len(opts) <= 4 or sum(o.endswith("*") for o in opts) != 1:
            self.app.notify(self.app.tr("ev_own_bad"), severity="warning", timeout=4)   # keep the list visible
            return
        right = next(i for i, o in enumerate(opts) if o.endswith("*"))
        opts = [o.rstrip("*").strip() for o in opts]
        self.score_own(q, opts, right)

    @work(thread=True, exclusive=True, group="own")
    def score_own(self, q, opts, right):
        scores = option_scores(self.app.gb, q, opts)
        self.app.call_from_thread(self._own_done, [q, opts, right, scores])

    def _own_done(self, item):
        self.own.append(item)
        st = self.app.state
        st.records["own_exam"] = self.own[-20:]
        st.save()
        if len(self.own) >= 3:
            st.complete("evals", badge="Exam Maker")
        self.query_one("#own-input", Input).value = ""
        self.draw_own()

    def draw_own(self):
        if not self.own:
            self.query_one("#own-view", Static).update("")
            return
        out, k = Text(), 0
        for q, opts, right, scores in self.own:
            k += self.render_question(out, q, opts, right, scores)
        out.append("\n" + self.app.tr("ev_score", k=k, n=len(self.own), p=k / len(self.own)), style="bold #8ecae6")
        if len(self.own) >= 3:
            out.append("\n" + self.app.tr("ev_badge"), style="bold #ffd166")
        self.query_one("#own-view", Static).update(out)

    # ── surprise meter ───────────────────────────────────────────────────────
    @work(thread=True, exclusive=True, group="surprise")
    def surprise(self):
        gb = self.app.gb
        text = self.query_one("#sur-input", Input).value
        ids = gb.encode(text)
        if gb is None or len(ids) < 2:
            return
        x = torch.tensor([ids])
        with torch.no_grad():
            logits, _ = gb.model(x[:, :-1], x[:, 1:])
        logp = F.log_softmax(logits[0], dim=-1)
        bits = [-logp[i, ids[i + 1]].item() / math.log(2) for i in range(len(ids) - 1)]
        self.app.call_from_thread(self._surprised, ids, bits)

    def _surprised(self, ids, bits):
        gb, tr = self.app.gb, self.app.tr
        out = Text()
        out.append(self.rr(show_piece(gb.tok.decode([ids[0]]))), style="#8a8fb0")
        for tid, b in zip(ids[1:], bits):
            out.append(self.rr(gb.tok.decode([tid])), style=f"bold {SURPRISE[min(int(b / 4), 4)]}")
        total_bytes = len(gb.tok.decode(ids[1:]).encode("utf-8"))
        out.append("\n\n" + tr("ev_bpb", bits=sum(bits), bytes=total_bytes, bpb=sum(bits) / max(total_bytes, 1)),
                   style="#c9cce0")
        legend = Text("\n")
        for i, lab in enumerate(["0-4", "4-8", "8-12", "12-16", "16+"]):
            legend.append(f" {lab} bits ", style=f"bold #14172b on {SURPRISE[i]}")
            legend.append(" ")
        out.append_text(legend)
        self.query_one("#sur-view", Static).update(out)

    def draw_trend(self):
        _, evals = training_curves()
        out = Text(self.app.tr("ev_trend") + "\n", style="bold #8ecae6")
        if evals:
            langs = [k for k in evals[0] if k not in ("step", "tokens")]
            out.append(f"{'tokens':>8} " + "".join(f"{l:>10}" for l in langs) + "\n", style="#5a5f7c")
            for r in evals[-6:]:
                out.append(f"{int(r['tokens']) / 1e9:7.2f}B " + "".join(f"{float(r[l]):10.3f}" for l in langs) + "\n",
                           style="#c9cce0")
        self.query_one("#trend", Static).update(out)
