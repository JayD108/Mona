"""Stage 7 — Training: a time machine through MONA's real training run."""
import torch
from rich.text import Text
from textual import work
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, VerticalScroll
from textual.screen import Screen
from textual.widgets import Input, Static

from ...engine.lessons import checkpoints, load_model, training_curves
from ..text import register
from ..widgets import Avatar

register({
    "tm_title": {"en": "Training: watch MONA learn", "hi": "ट्रेनिंग: MONA को सीखते देखिए", "hinglish": "Training: MONA ko seekhte dekho"},
    "tm_explain": {
        "en": {"simple": "MONA started knowing nothing. It read billions of words and slowly learned. Here is the SAME "
                         "question asked to MONA at different moments of its training.",
               "student": "Training = show MONA text, let it guess each next token, measure how wrong it was (the loss), nudge "
                          "all 110M numbers to be a little less wrong, repeat. Below: the same prompt answered by MONA at "
                          "different points of its real training run, and its real loss curve.",
               "engineer": "Next-token cross-entropy, AdamW (β=0.9/0.95, wd 0.1), bf16, 524K tokens/step, WSD LR schedule "
                           "(peak 6e-4). Rows: the same prompt + seed sampled from each saved snapshot (T=0.8, top-p 0.9)."},
        "hi": {"simple": "MONA शुरू में कुछ नहीं जानती थी। उसने अरबों शब्द पढ़े और धीरे-धीरे सीखा। यहाँ एक ही सवाल "
                         "ट्रेनिंग के अलग-अलग समय पर MONA से पूछा गया है।",
               "student": "ट्रेनिंग = MONA को पाठ दिखाओ, हर अगले टोकन का अंदाज़ा लगवाओ, नापो कितनी गलती हुई (loss), सभी 11 करोड़ "
                          "संख्याओं को थोड़ा कम गलत की ओर खिसकाओ, दोहराओ। नीचे: एक ही प्रॉम्प्ट का जवाब असली ट्रेनिंग के अलग-अलग "
                          "पड़ाव पर, और असली loss वक्र।",
               "engineer": "Next-token cross-entropy, AdamW (β=0.9/0.95, wd 0.1), bf16, 524K टोकन/कदम, WSD LR (शिखर 6e-4)। "
                           "हर पंक्ति: हर snapshot से एक ही prompt + seed (T=0.8, top-p 0.9)।"},
        "hinglish": {"simple": "MONA shuru mein kuch nahi jaanti thi. Usne arabon words padhe aur dheere-dheere seekha. Yahan "
                               "ek hi sawaal training ke alag-alag time par MONA se poochha gaya hai.",
                     "student": "Training = MONA ko text dikhao, har agle token ka guess karwao, naapo kitni galti hui (loss), "
                                "saare 11 crore numbers ko thoda kam galat ki taraf khiskao, repeat. Neeche: ek hi prompt ka "
                                "jawab asli training ke alag-alag padaav par, aur asli loss curve.",
                     "engineer": "Next-token cross-entropy, AdamW (β=0.9/0.95, wd 0.1), bf16, 524K tokens/step, WSD LR "
                                 "(peak 6e-4). Har row: har snapshot se same prompt + seed (T=0.8, top-p 0.9)."},
    },
    "tm_prompt": {"en": "Ask every version of MONA the same thing (Enter)…", "hi": "MONA के हर संस्करण से एक ही बात पूछिए (Enter)…",
                  "hinglish": "MONA ke har version se same cheez poochho (Enter)…"},
    "tm_versions": {"en": "The same prompt, across MONA's training", "hi": "एक ही प्रॉम्प्ट, MONA की पूरी ट्रेनिंग में",
                    "hinglish": "Same prompt, MONA ki poori training mein"},
    "tm_loading": {"en": "loading this version of MONA…", "hi": "MONA का यह संस्करण लोड हो रहा है…",
                   "hinglish": "MONA ka yeh version load ho raha hai…"},
    "tm_loss": {"en": "Loss while training (lower = better guesses)", "hi": "ट्रेनिंग के दौरान loss (कम = बेहतर अंदाज़े)",
                "hinglish": "Training ke dauraan loss (kam = behtar guesses)"},
    "tm_eval": {"en": "Held-out text, per language (text MONA never trained on)", "hi": "अनदेखा पाठ, हर भाषा में (जिस पर MONA ने ट्रेनिंग नहीं की)",
                "hinglish": "Unseen text, har bhasha mein (jis par MONA ne train nahi kiya)"},
    "tm_noeval": {"en": "(the first per-language check happens at step 250)", "hi": "(हर भाषा की पहली जाँच कदम 250 पर होती है)",
                  "hinglish": "(har bhasha ki pehli check step 250 par hoti hai)"},
    "tm_lr": {"en": "Learning-rate plan (WSD: warm up · stay · cool down)  ▲ = now",
              "hi": "Learning-rate योजना (WSD: गरम करो · टिको · ठंडा करो)  ▲ = अभी",
              "hinglish": "Learning-rate plan (WSD: warm up · stay · cool down)  ▲ = abhi"},
    "tm_facts": {"en": "{tokens:.2f}B tokens read · step {step:,} of 4,769 · {pages:,} pages per step · GPU {temp}°C",
                 "hi": "{tokens:.2f}B टोकन पढ़े · कदम {step:,} / 4,769 · हर कदम में {pages:,} पन्ने · GPU {temp}°C",
                 "hinglish": "{tokens:.2f}B tokens padhe · step {step:,} / 4,769 · har step mein {pages:,} pages · GPU {temp}°C"},
    "tm_keys": {"en": "Enter ask again   R refresh logs   Esc back   F2 language  F3 depth  F4 romanize",
                "hi": "Enter फिर पूछें   R लॉग ताज़ा करें   Esc वापस   F2 भाषा  F3 गहराई  F4 रोमन",
                "hinglish": "Enter phir poochho   R logs refresh   Esc wapas   F2 bhasha  F3 depth  F4 roman"},
})

TOTAL_TOKENS, STEP_TOKENS = 2.5e9, 524_288


def area_chart(values, width=64, height=8, colour="#06d6a0"):
    """A filled line chart made of block characters (8 sub-levels per cell)."""
    if not values:
        return Text("")
    if len(values) > width:                       # average into `width` columns
        step = len(values) / width
        values = [sum(values[int(i * step):int((i + 1) * step)]) / max(1, int((i + 1) * step) - int(i * step))
                  for i in range(width)]
    elif len(values) < width:                     # few points so far: stretch them across the width
        values = [values[min(int(i * len(values) / width), len(values) - 1)] for i in range(width)]
    lo, hi = min(values), max(values)
    span = (hi - lo) or 1
    levels = [round((v - lo) / span * height * 8) for v in values]
    blocks = " ▁▂▃▄▅▆▇█"
    out = Text()
    for row in range(height - 1, -1, -1):
        label = f"{hi:5.2f} " if row == height - 1 else (f"{lo:5.2f} " if row == 0 else "      ")
        out.append(label, style="#5a5f7c")
        for lv in levels:
            fill = min(max(lv - row * 8, 0), 8)
            out.append(blocks[fill], style=colour)
        out.append("\n")
    return out


def lr_plan(frac_now, width=64):
    out = Text()
    shape = []
    for i in range(width):
        f = i / (width - 1)
        lr = f / 0.01 if f < 0.01 else (1.0 if f < 0.85 else 1 - 0.95 * (f - 0.85) / 0.15)
        shape.append(lr)
    blocks = "▁▂▃▄▅▆▇█"
    out.append("      ")
    for v in shape:
        out.append(blocks[min(int(v * 7.99), 7)], style="#cdb4db")
    out.append("\n      ")
    pos = min(int(frac_now * (width - 1)), width - 1)
    out.append(" " * pos + "▲", style="bold #ffd166")
    return out


class TimeMachineLab(Screen):
    BINDINGS = [Binding("escape", "app.pop_screen", "back"), Binding("r", "refresh_logs", "refresh")]
    EXAMPLE = "The history of India"

    def compose(self) -> ComposeResult:
        with Horizontal(classes="lab-head"):
            yield Avatar(id="avatar", classes="lab-avatar")
            yield Static(id="title", classes="lab-title")
        yield Static(id="explain", classes="explain")
        yield Input(id="prompt")
        with VerticalScroll():
            yield Static(id="versions", classes="panel")
            yield Static(id="curves", classes="panel")
        yield Static(id="keys", classes="keys")

    def on_mount(self):
        self.rows = []                      # [(label, text or None)]
        self.query_one("#prompt", Input).value = self.EXAMPLE
        self.refresh_texts()
        self.ask()
        self.app.state.complete("training")

    def refresh_texts(self):
        tr = self.app.tr
        self.query_one("#title", Static).update(tr("tm_title"))
        self.query_one("#explain", Static).update(tr("tm_explain"))
        self.query_one("#prompt", Input).placeholder = tr("tm_prompt")
        self.query_one("#keys", Static).update(tr("tm_keys"))
        self.draw_versions()
        self.action_refresh_logs()

    def on_input_submitted(self, event: Input.Submitted):
        self.ask()

    # ── versions: the same prompt through every checkpoint ──────────────────
    def ask(self):
        prompt = self.query_one("#prompt", Input).value
        self.rows = [(label, None) for label, _, _ in checkpoints()]
        self.draw_versions()
        self.generate_all(prompt)

    @work(thread=True, exclusive=True)
    def generate_all(self, prompt):
        tok = self.app.tokenizer
        eot = tok.token_to_id("<|endoftext|>")
        ids0 = tok.encode(prompt).ids
        for n, (label, _, path) in enumerate(checkpoints()):
            model = load_model(path)
            torch.manual_seed(1234)                       # same dice for every version: only the model differs
            out = list(model.generate(torch.tensor([ids0]), 32, temperature=0.8, top_p=0.9, stop_ids={eot}))
            text = tok.decode(out).replace("\n", " ")
            del model
            self.app.call_from_thread(self._row_done, n, label, text)

    def _row_done(self, n, label, text):
        if n < len(self.rows):
            self.rows[n] = (label, text)
        self.draw_versions()

    def draw_versions(self):
        tr = self.app.tr
        roman = self.app.roman if self.app.state.romanize else (lambda s: s)
        prompt = roman(self.query_one("#prompt", Input).value)
        out = Text(tr("tm_versions") + "\n\n", style="bold #8ecae6")
        colours = ["#ef476f", "#f78c6b", "#ffd166", "#b5e48c", "#06d6a0", "#8ecae6"]
        for i, (label, text) in enumerate(self.rows):
            out.append(f"{label:>22}  ", style=f"bold {colours[min(i, len(colours) - 1)]}")
            out.append(prompt, style="#8a8fb0")
            if text is None:
                out.append("  " + tr("tm_loading"), style="italic #5a5f7c")
            else:
                out.append(roman(text), style="#e8e8f0")
            out.append("\n")
        self.query_one("#versions", Static).update(out)
        busy = any(t is None for _, t in self.rows)
        self.query_one("#avatar", Avatar).set_mood("thinking" if busy else "wow")

    # ── the real logs ────────────────────────────────────────────────────────
    def action_refresh_logs(self):
        tr = self.app.tr
        train, evals = training_curves()
        out = Text()
        if train:
            losses = [float(r["loss"]) for r in train]
            last = train[-1]
            tokens = int(last["tokens"]) / 1e9
            out.append(tr("tm_facts", tokens=tokens, step=int(last["step"]), pages=STEP_TOKENS // 1300,
                          temp=last["gpu_temp_c"]) + "\n\n", style="#c9cce0")
            out.append(tr("tm_loss") + "\n", style="bold #8ecae6")
            out.append_text(area_chart(losses))
            out.append(f"      0{' ' * 52}{tokens:.2f}B tokens\n\n", style="#5a5f7c")
            out.append(tr("tm_lr") + "\n", style="bold #8ecae6")
            out.append_text(lr_plan(int(last["tokens"]) / TOTAL_TOKENS))
            out.append("\n\n")
        out.append(tr("tm_eval") + "\n", style="bold #8ecae6")
        if evals:
            langs = [k for k in evals[0] if k not in ("step", "tokens")]
            first, latest = evals[0], evals[-1]
            for lang in langs:
                a, b = float(first[lang]), float(latest[lang])
                out.append(f"  {lang:9s} {a:6.2f} → {b:6.2f}  ", style="#c9cce0")
                out.append("▼ better\n" if b < a else "•\n", style="#06d6a0" if b < a else "#5a5f7c")
        else:
            out.append("  " + tr("tm_noeval"), style="#5a5f7c")
        self.query_one("#curves", Static).update(out)
