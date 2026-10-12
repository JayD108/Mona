"""Budget planner: the CEO picks a compute budget and a model size; scaling laws predict the rest.

Uses the two rules real labs use before spending money:
  compute  C ≈ 6 × N × D            (N parameters, D training tokens)
  quality  L(N, D) = E + A/N^α + B/D^β   (Chinchilla fit, Hoffmann et al. 2022)
For a fixed budget, a model that is too small *or* too big ends up worse: the U-shaped curve.
"""
from rich.text import Text
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, VerticalScroll
from textual.screen import Screen
from textual.widgets import Static

from .text import register
from .widgets import Avatar

register({
    "bud_title": {"en": "Budget planner: how big should your model be?", "hi": "बजट प्लानर: आपका मॉडल कितना बड़ा हो?",
                  "hinglish": "Budget planner: aapka model kitna bada ho?"},
    "bud_explain": {
        "en": "{addr}, every lab has a fixed amount of computing to spend. Spend it on a bigger brain (more parameters) or on "
              "more reading (more tokens)? Choose a budget with ↑↓ and a model size with ←→. The bars predict quality "
              "(lower = better), using the same formula real labs use.",
        "hi": "{addr}, हर लैब के पास ख़र्च करने के लिए तय कंप्यूटिंग होती है। उसे बड़े दिमाग़ (ज़्यादा पैरामीटर) पर ख़र्च करें या ज़्यादा पढ़ाई "
              "(ज़्यादा टोकन) पर? ↑↓ से बजट और ←→ से मॉडल का आकार चुनिए। पट्टियाँ गुणवत्ता का अनुमान दिखाती हैं (कम = बेहतर), उसी "
              "सूत्र से जो असली लैब इस्तेमाल करती हैं।",
        "hinglish": "{addr}, har lab ke paas kharch karne ke liye fixed computing hoti hai. Use bade dimaag (zyada parameters) par kharch "
                    "karein ya zyada padhai (zyada tokens) par? ↑↓ se budget aur ←→ se model size chuno. Bars quality predict karti hain "
                    "(kam = behtar), usi formula se jo asli labs use karti hain.",
    },
    "bud_budget": {"en": "Budget", "hi": "बजट", "hinglish": "Budget"},
    "bud_size": {"en": "Your model", "hi": "आपका मॉडल", "hinglish": "Aapka model"},
    "bud_tokens": {"en": "It can read {d} tokens  ({r} tokens per parameter)", "hi": "यह {d} टोकन पढ़ सकता है  ({r} टोकन प्रति पैरामीटर)",
                   "hinglish": "Yeh {d} tokens padh sakta hai  ({r} tokens per parameter)"},
    "bud_time": {"en": "Time: {h} H100-GPU-hours ≈ ${c} in the cloud  ·  on MONA's laptop: {l}",
                 "hi": "समय: {h} H100-GPU-घंटे ≈ क्लाउड में ${c}  ·  MONA के लैपटॉप पर: {l}",
                 "hinglish": "Time: {h} H100-GPU-hours ≈ cloud mein ${c}  ·  MONA ke laptop par: {l}"},
    "bud_curve": {"en": "Predicted loss for every size at this budget (lower = better):",
                  "hi": "इस बजट पर हर आकार का अनुमानित लॉस (कम = बेहतर):",
                  "hinglish": "Is budget par har size ka predicted loss (kam = behtar):"},
    "bud_best": {"en": "★ best size for this budget", "hi": "★ इस बजट का सबसे अच्छा आकार", "hinglish": "★ is budget ka best size"},
    "bud_you": {"en": "◀ your choice", "hi": "◀ आपकी पसंद", "hinglish": "◀ aapki choice"},
    "bud_verdict_small": {"en": "Too small, {addr}: this brain can't hold everything it reads. A bigger model would be better for the same money.",
                          "hi": "बहुत छोटा, {addr}: यह दिमाग़ जो पढ़ता है वह सब नहीं समा पाता। उसी पैसे में बड़ा मॉडल बेहतर रहेगा।",
                          "hinglish": "Bahut chhota, {addr}: yeh dimaag jo padhta hai woh sab nahi samaa paata. Usi paise mein bada model behtar rahega."},
    "bud_verdict_big": {"en": "Too big, {addr}: a huge brain that barely gets to read. A smaller model trained longer would be better.",
                        "hi": "बहुत बड़ा, {addr}: विशाल दिमाग़ जिसे पढ़ने को बहुत कम मिलता है। छोटा मॉडल ज़्यादा देर ट्रेन करना बेहतर होगा।",
                        "hinglish": "Bahut bada, {addr}: bada dimaag jise padhne ko bahut kam milta hai. Chhota model zyada der train karna behtar hoga."},
    "bud_verdict_ok": {"en": "Well balanced, {addr}! This is close to the best possible model for your budget.",
                       "hi": "अच्छा संतुलन, {addr}! यह आपके बजट में लगभग सबसे अच्छा मॉडल है।",
                       "hinglish": "Achha balance, {addr}! Yeh aapke budget mein lagbhag sabse achha model hai."},
    "bud_famous": {"en": "Famous models, for comparison:", "hi": "तुलना के लिए मशहूर मॉडल:", "hinglish": "Comparison ke liye famous models:"},
    "bud_note": {"en": "Note: the formula comes from a 2022 study on English web text, so the numbers are a guide, not exact. "
                       "Modern small models are often trained far beyond the 'best' point on purpose: a smaller model is cheaper to run "
                       "for millions of users.",
                 "hi": "ध्यान दें: सूत्र 2022 के एक अध्ययन (अंग्रेज़ी वेब पाठ) से है, इसलिए अंक दिशा बताते हैं, सटीक नहीं। आधुनिक छोटे मॉडल अक्सर "
                       "जानबूझकर 'सबसे अच्छे' बिंदु से कहीं ज़्यादा ट्रेन होते हैं: करोड़ों लोगों के लिए छोटा मॉडल चलाना सस्ता है।",
                 "hinglish": "Dhyaan do: formula 2022 ki ek study (English web text) se hai, isliye numbers direction batate hain, exact nahi. "
                             "Modern chhote models aksar jaan-boojhkar 'best' point se kahin zyada train hote hain: crore-on users ke liye "
                             "chhota model chalana sasta hai."},
    "bud_keys": {"en": "↑↓ budget   ←→ model size   Esc back   F1 explain a word", "hi": "↑↓ बजट   ←→ मॉडल का आकार   Esc वापस   F1 शब्द का मतलब",
                 "hinglish": "↑↓ budget   ←→ model size   Esc wapas   F1 word ka matlab"},
})

E, A, B, ALPHA, BETA = 1.69, 406.4, 410.7, 0.34, 0.28          # Chinchilla fit (Hoffmann et al., 2022)
H100 = 4e14            # useful bf16 FLOP/s per H100 at ~40% utilisation
H100_PRICE = 2.5       # rough cloud price, US$ per GPU-hour
LAPTOP = 2.2e13        # MONA's laptop, measured: 6 × 85M × 43K tokens/s

BUDGETS = [  # (FLOPs, en, hi, hinglish)
    (7e17, "One laptop, one night", "एक लैपटॉप, एक रात", "Ek laptop, ek raat"),
    (1.65e18, "Your lab: MONA's two nights", "आपकी लैब: MONA की दो रातें", "Aapki lab: MONA ki do raatein"),
    (1.9e21, "A university: 8 GPUs for a week", "एक यूनिवर्सिटी: 8 GPU एक हफ़्ते", "Ek university: 8 GPUs ek hafte"),
    (3.1e23, "GPT-3's budget (2020)", "GPT-3 का बजट (2020)", "GPT-3 ka budget (2020)"),
    (6.3e24, "Llama-3-70B's budget (2024)", "Llama-3-70B का बजट (2024)", "Llama-3-70B ka budget (2024)"),
    (5e25, "A frontier run today (estimate)", "आज की बड़ी ट्रेनिंग (अनुमान)", "Aaj ki badi training (andaaza)"),
]
SIZES = [10e6, 30e6, 110e6, 350e6, 1e9, 3e9, 8e9, 30e9, 70e9, 175e9, 400e9, 1e12]
FAMOUS = [("MONA", 110e6, 2.5e9), ("GPT-3", 175e9, 300e9), ("Chinchilla", 70e9, 1.4e12), ("Llama 3 8B", 8e9, 15e12)]


def loss(n, d):
    return E + A / n ** ALPHA + B / d ** BETA


def human(x):
    for unit, v in (("T", 1e12), ("B", 1e9), ("M", 1e6), ("K", 1e3)):
        if x >= v:
            return f"{x / v:.3g}{unit}"
    return f"{x:.3g}"


def duration(seconds, lang):
    words = {"en": ("hours", "days", "years"), "hi": ("घंटे", "दिन", "साल"), "hinglish": ("ghante", "din", "saal")}[lang]
    h = seconds / 3600
    if h < 48:
        return f"{h:.0f} {words[0]}"
    if h < 24 * 730:
        return f"{h / 24:.0f} {words[1]}"
    return f"{h / 24 / 365:,.0f} {words[2]}"


class BudgetScreen(Screen):
    BINDINGS = [Binding("escape", "app.pop_screen", "back"), Binding("up", "budget(1)", show=False),
                Binding("down", "budget(-1)", show=False), Binding("left", "size(-1)", show=False),
                Binding("right", "size(1)", show=False)]

    def compose(self) -> ComposeResult:
        with Horizontal(classes="lab-head"):
            yield Avatar(id="avatar", classes="lab-avatar")
            yield Static(id="title", classes="lab-title")
        yield Static(id="explain", classes="explain")
        with VerticalScroll():
            yield Static(id="plan", classes="panel")
        yield Static(id="keys", classes="keys")

    def on_mount(self):
        self.b, self.s = 1, 2              # start at MONA: two nights, 110M
        self.refresh_texts()

    def refresh_texts(self):
        tr = self.app.tr
        self.query_one("#title", Static).update(tr("bud_title"))
        self.query_one("#explain", Static).update(tr("bud_explain"))
        self.query_one("#keys", Static).update(tr("bud_keys"))
        self.draw()

    def action_budget(self, d: int):
        self.b = min(max(self.b + d, 0), len(BUDGETS) - 1)
        self.draw()

    def action_size(self, d: int):
        self.s = min(max(self.s + d, 0), len(SIZES) - 1)
        self.draw()

    def draw(self):
        app, tr, lang = self.app, self.app.tr, self.app.state.lang
        col = {"en": 1, "hi": 2, "hinglish": 3}[lang]
        c = BUDGETS[self.b][0]
        n = SIZES[self.s]
        d = c / (6 * n)
        out = Text()
        out.append(f"{tr('bud_budget')}:  ", style="bold #8ecae6")
        out.append(f"{BUDGETS[self.b][col]}", style="bold #ffd166")
        out.append(f"   ({c:.1e} FLOPs)\n", style="#8a8fb0")
        out.append(f"{tr('bud_size')}:  ", style="bold #8ecae6")
        out.append(f"{human(n)} parameters\n", style="bold #ffd166")
        out.append(tr("bud_tokens", d=human(d), r=f"{d / n:,.1f}") + "\n", style="#e8e8f0")
        gpu_h = c / H100 / 3600
        out.append(tr("bud_time", h=f"{gpu_h:,.0f}" if gpu_h >= 1 else f"{gpu_h:.2f}", c=f"{gpu_h * H100_PRICE:,.0f}",
                      l=duration(c / LAPTOP, lang)) + "\n\n", style="#e8e8f0")

        losses = [loss(sz, c / (6 * sz)) for sz in SIZES]
        best = losses.index(min(losses))
        lo = min(losses)
        hi = min(max(losses), lo + 3)
        out.append(tr("bud_curve") + "\n", style="bold #8ecae6")
        for i, (sz, ls) in enumerate(zip(SIZES, losses)):
            width = 40 - round(min((ls - lo) / ((hi - lo) or 1), 1) * 34)
            colour = "#06d6a0" if i == best else ("#ffd166" if i == self.s else "#3a3f5c")
            out.append(f"  {human(sz):>5} ", style="bold" if i == self.s else "#8a8fb0")
            out.append("█" * width, style=colour)
            out.append(f" {ls:.2f}", style="#c9cce0")
            if i == best:
                out.append("  " + tr("bud_best"), style="bold #06d6a0")
            if i == self.s:
                out.append("  " + tr("bud_you"), style="bold #ffd166")
            out.append("\n")
        out.append("\n")
        if self.s < best - 1:
            verdict = "bud_verdict_small"
        elif self.s > best + 1:
            verdict = "bud_verdict_big"
        else:
            verdict = "bud_verdict_ok"
        out.append(tr(verdict) + "\n\n", style="bold #f4a3c0" if verdict != "bud_verdict_ok" else "bold #06d6a0")
        out.append(tr("bud_famous") + "\n", style="bold #8ecae6")
        for name, fn, fd in FAMOUS:
            out.append(f"  {name:<11} {human(fn):>5} params · {human(fd):>5} tokens · {fd / fn:7,.0f} tokens/param · "
                       f"{6 * fn * fd:.1e} FLOPs\n", style="#c9cce0")
        out.append("\n" + tr("bud_note"), style="italic #8a8fb0")
        self.query_one("#plan", Static).update(app.roman(out.plain) if app.state.romanize else out)
        if self.b == len(BUDGETS) - 1:
            app.state.complete("budget")
