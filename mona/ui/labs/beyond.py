"""Stage 11 — Beyond: shrinking MONA (quantization), tools, and the KV-cache speed trick."""
import ast
import math
import operator
import re
import time

import numpy as np
import torch
import torch.nn.functional as F
from rich.text import Text
from textual import work
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, VerticalScroll
from textual.screen import Screen
from textual.widgets import Input, Static, TabbedContent, TabPane

from ... import config
from ...model import MONA
from ..text import register
from ..widgets import Avatar, prob_bars

register({
    "by_title": {"en": "Beyond: shrink, tools, speed", "hi": "आगे: छोटा करना, औज़ार, रफ़्तार", "hinglish": "Aage: chhota karna, tools, speed"},
    "by_tab_q": {"en": "Shrink MONA", "hi": "MONA छोटी करें", "hinglish": "MONA chhoti karo"},
    "by_tab_tool": {"en": "Tools", "hi": "औज़ार", "hinglish": "Tools"},
    "by_tab_speed": {"en": "Speed", "hi": "रफ़्तार", "hinglish": "Speed"},
    "by_q_explain": {
        "en": {"simple": "MONA is 110 million numbers. If we store each number with fewer digits, MONA gets much smaller "
                         "(fits on a phone!) but a little less accurate. How much less? Let's measure.",
               "student": "Quantization stores weights with fewer bits: 32-bit floats → 16 → 8 → 4-bit integers. Each "
                          "step halves the size. Small errors creep into every weight; we measure the damage on unseen text "
                          "(bits per byte, lower = better) and by reading the output.",
               "engineer": "Fake-quantization of all 2-D weights (incl. tied embedding): symmetric, per-group (64) scales, "
                           "round-to-nearest, then dequantize for CPU inference. Real int4 kernels (GPTQ/AWQ) do better."},
        "hi": {"simple": "MONA 11 करोड़ संख्याएँ हैं। अगर हर संख्या कम अंकों में रखें, तो MONA बहुत छोटी हो जाती है (फ़ोन में "
                         "आ जाए!) पर थोड़ी कम सटीक। कितनी कम? नापते हैं।",
               "student": "Quantization वज़न को कम बिट में रखता है: 32-bit → 16 → 8 → 4-bit। हर कदम पर आकार आधा। हर वज़न में "
                          "छोटी गलती आती है; नुकसान अनदेखे पाठ पर (bits per byte, कम = बेहतर) और आउटपुट पढ़कर नापते हैं।",
               "engineer": "सभी 2-D वज़न की fake-quantization: symmetric, प्रति-समूह (64) scale, round-to-nearest, फिर dequantize। "
                           "असली int4 kernels (GPTQ/AWQ) बेहतर करते हैं।"},
        "hinglish": {"simple": "MONA 11 crore numbers hai. Agar har number kam digits mein rakhein, to MONA bahut chhoti ho jaati "
                               "hai (phone mein aa jaaye!) par thodi kam accurate. Kitni kam? Naapte hain.",
                     "student": "Quantization weights ko kam bits mein rakhta hai: 32-bit → 16 → 8 → 4-bit. Har step par size "
                                "aadha. Har weight mein chhoti galti aati hai; nuksaan unseen text par (bits per byte, kam = "
                                "behtar) aur output padhkar naapte hain.",
                     "engineer": "Saare 2-D weights ki fake-quantization: symmetric, per-group (64) scales, round-to-nearest, "
                                 "phir dequantize. Asli int4 kernels (GPTQ/AWQ) behtar karte hain."},
    },
    "by_q_run": {"en": "Press R to shrink MONA four ways and measure (about a minute on CPU).",
                 "hi": "MONA को चार तरह छोटा करके नापने के लिए R दबाइए (CPU पर लगभग एक मिनट)।",
                 "hinglish": "MONA ko chaar tarah chhota karke naapne ke liye R dabao (CPU par lagbhag ek minute)."},
    "by_q_working": {"en": "measuring {name}…", "hi": "{name} नाप रहे हैं…", "hinglish": "{name} naap rahe hain…"},
    "by_tool_explain": {
        "en": {"simple": "MONA is bad at maths: it only guesses what number LOOKS likely. Smart assistants don't calculate "
                         "in their head; they call a calculator, then read the answer.",
               "student": "LLMs predict tokens, they don't compute, so arithmetic is unreliable. Tool use: the model writes a "
                          "special request (\"calculator: 23*47\"), a program runs it, and the result is pasted back into the "
                          "prompt for the model to continue. Agents are this loop, repeated.",
               "engineer": "Tool-use loop: model emits a structured call → the runtime parses and executes it (here a safe AST "
                           "calculator) → the observation is appended → generation continues. Chat models are SFT'd to emit "
                           "the call format; this demo runs the loop around base MONA."},
        "hi": {"simple": "MONA गणित में कमज़ोर है: वह बस अंदाज़ा लगाती है कि कौन-सी संख्या ठीक लगती है। समझदार सहायक मन में "
                         "हिसाब नहीं लगाते; वे कैलकुलेटर बुलाते हैं, फिर जवाब पढ़ते हैं।",
               "student": "LLM टोकन का अनुमान लगाते हैं, हिसाब नहीं करते, इसलिए गणित अविश्वसनीय है। Tool use: मॉडल एक ख़ास अनुरोध "
                          "लिखता है (\"calculator: 23*47\"), एक प्रोग्राम उसे चलाता है, और नतीजा प्रॉम्प्ट में वापस जुड़ता है। "
                          "Agents इसी चक्र को दोहराते हैं।",
               "engineer": "Tool-use loop: मॉडल structured call लिखता है → runtime उसे पार्स करके चलाता है (यहाँ सुरक्षित AST "
                           "calculator) → नतीजा जोड़ा जाता है → generation आगे बढ़ता है।"},
        "hinglish": {"simple": "MONA maths mein kamzor hai: woh bas guess karti hai ki kaunsa number theek lagta hai. Smart "
                               "assistants mann mein hisaab nahi lagate; woh calculator bulate hain, phir jawab padhte hain.",
                     "student": "LLMs tokens predict karte hain, calculate nahi karte, isliye maths unreliable hai. Tool use: "
                                "model ek special request likhta hai (\"calculator: 23*47\"), ek program use chalata hai, aur "
                                "result prompt mein wapas judta hai. Agents yahi loop repeat karte hain.",
                     "engineer": "Tool-use loop: model structured call likhta hai → runtime parse karke chalata hai (yahan safe "
                                 "AST calculator) → observation append → generation continue."},
    },
    "by_tool_prompt": {"en": "A sum, e.g. 23 * 47 (Enter)…", "hi": "कोई हिसाब, जैसे 23 * 47 (Enter)…", "hinglish": "Koi hisaab, jaise 23 * 47 (Enter)…"},
    "by_tool_mona": {"en": "① MONA alone (no tool):", "hi": "① अकेली MONA (बिना औज़ार):",
                     "hinglish": "① Akeli MONA (bina tool):"},
    "by_tool_loop": {"en": "② With a tool: the loop", "hi": "② औज़ार के साथ: चक्र", "hinglish": "② Tool ke saath: loop"},
    "by_tool_true": {"en": "The right answer is {v}. MONA wrote “{g}”: {m}",
                     "hi": "सही जवाब {v} है। MONA ने लिखा “{g}”: {m}",
                     "hinglish": "Sahi jawab {v} hai. MONA ne likha “{g}”: {m}"},
    "by_speed_explain": {
        "en": {"simple": "To write each new word, MONA would normally re-read the whole text from the start. The KV-cache "
                         "remembers what it already read, so each new word is quick.",
               "student": "Without a cache, generating token n re-processes all n tokens (total work grows like n²). The "
                          "KV-cache stores every layer's keys and values, so each step only processes the one new token.",
               "engineer": "Prefill once, then decode 1 token/step attending to cached K/V per layer (mona/model.py generate). "
                           "Timed on CPU below, same seed and length."},
        "hi": {"simple": "हर नया शब्द लिखने के लिए MONA आम तौर पर पूरा पाठ शुरू से दोबारा पढ़ती। KV-cache याद रखता है कि वह क्या "
                         "पढ़ चुकी, इसलिए हर नया शब्द जल्दी आता है।",
               "student": "Cache के बिना टोकन n बनाने के लिए सारे n टोकन दोबारा चलते हैं (काम n² की तरह बढ़ता है)। KV-cache हर लेयर "
                          "के keys और values रखता है, इसलिए हर कदम पर केवल नया टोकन चलता है।",
               "engineer": "एक बार prefill, फिर हर कदम 1 टोकन, cached K/V पर attention (mona/model.py generate)। नीचे CPU पर समय।"},
        "hinglish": {"simple": "Har naya word likhne ke liye MONA normally poora text shuru se dobara padhti. KV-cache yaad rakhta "
                               "hai ki woh kya padh chuki, isliye har naya word jaldi aata hai.",
                     "student": "Cache ke bina token n banane ke liye saare n tokens dobara chalte hain (kaam n² ki tarah badhta "
                                "hai). KV-cache har layer ke keys aur values rakhta hai, isliye har step par sirf naya token chalta hai.",
                     "engineer": "Ek baar prefill, phir har step 1 token, cached K/V par attention (mona/model.py generate). "
                                 "Neeche CPU par timing."},
    },
    "by_speed_run": {"en": "Press R to race: 100 tokens with and without the KV-cache.", "hi": "दौड़ के लिए R: KV-cache के साथ और बिना 100 टोकन।",
                     "hinglish": "Race ke liye R: KV-cache ke saath aur bina 100 tokens."},
    "by_keys": {"en": "Esc back   F5 Shrink  F6 Tools  F7 Speed   R run   F3 depth",
                "hi": "Esc वापस   F5 छोटा करें  F6 औज़ार  F7 रफ़्तार   R चलाएँ   F2 भाषा  F3 गहराई  F4 रोमन",
                "hinglish": "Esc wapas   F5 Shrink  F6 Tools  F7 Speed   R run   F2 bhasha  F3 depth  F4 roman"},
})

OPS = {ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul, ast.Div: operator.truediv,
       ast.Pow: operator.pow, ast.USub: operator.neg}


def calculator(expr):
    """A safe calculator tool: + - * / ** and brackets only (no eval of arbitrary code)."""
    def ev(node):
        if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
            return node.value
        if isinstance(node, ast.BinOp) and type(node.op) in OPS:
            return OPS[type(node.op)](ev(node.left), ev(node.right))
        if isinstance(node, ast.UnaryOp) and type(node.op) in OPS:
            return OPS[type(node.op)](ev(node.operand))
        raise ValueError("unsupported")
    v = ev(ast.parse(expr.replace("×", "*").replace("x", "*"), mode="eval").body)
    return int(v) if float(v).is_integer() else round(v, 4)


def fake_quant(w, bits, group=64):
    """Symmetric per-group quantize -> dequantize (what the weights look like after shrinking)."""
    qmax = 2 ** (bits - 1) - 1
    flat = w.reshape(-1, group)
    scale = flat.abs().amax(dim=1, keepdim=True).clamp(min=1e-8) / qmax
    return (torch.round(flat / scale).clamp(-qmax, qmax) * scale).reshape(w.shape)


class Runner(Static, can_focus=True):
    BINDINGS = [Binding("r", "screen.run")]


class BeyondLab(Screen):
    BINDINGS = [Binding("escape", "app.pop_screen", "back"), Binding("f5", "tab('q')"), Binding("f6", "tab('tool')"),
                Binding("f7", "tab('speed')")]

    def compose(self) -> ComposeResult:
        with Horizontal(classes="lab-head"):
            yield Avatar(id="avatar", classes="lab-avatar")
            yield Static(id="title", classes="lab-title")
        with TabbedContent(id="tabs"):
            with TabPane("Shrink MONA", id="q"):
                yield Static(id="q-explain", classes="explain")
                with VerticalScroll():
                    yield Runner(id="q-view", classes="panel")
            with TabPane("Tools", id="tool"):
                yield Static(id="tool-explain", classes="explain")
                yield Input(id="tool-input")
                with VerticalScroll():
                    yield Static(id="tool-view", classes="panel")
            with TabPane("Speed", id="speed"):
                yield Static(id="speed-explain", classes="explain")
                with VerticalScroll():
                    yield Runner(id="speed-view", classes="panel")
        yield Static(id="keys", classes="keys")

    def on_mount(self):
        self.q_rows, self.q_status, self.speed = [], None, None
        self.query_one("#tool-input", Input).value = "23 * 47"
        self.refresh_texts()
        self.query_one("#q-view").focus()
        self.app.state.complete("beyond")

    def refresh_texts(self):
        tr = self.app.tr
        self.query_one("#title", Static).update(tr("by_title"))
        for wid, key in (("q-explain", "by_q_explain"), ("tool-explain", "by_tool_explain"), ("speed-explain", "by_speed_explain"),
                         ("keys", "by_keys")):
            self.query_one(f"#{wid}", Static).update(tr(key))
        self.query_one("#tool-input", Input).placeholder = tr("by_tool_prompt")
        tabs = self.query_one("#tabs", TabbedContent)
        for pane, key in (("q", "by_tab_q"), ("tool", "by_tab_tool"), ("speed", "by_tab_speed")):
            tabs.get_tab(pane).label = tr(key)
        self.draw_q()
        self.draw_speed()

    def action_tab(self, pane):
        self.query_one("#tabs", TabbedContent).active = pane
        self.query_one({"q": "#q-view", "tool": "#tool-input", "speed": "#speed-view"}[pane]).focus()

    def action_run(self):
        pane = self.query_one("#tabs", TabbedContent).active
        if pane == "q":
            self.run_quant()
        elif pane == "speed":
            self.run_speed()

    # ── quantization ─────────────────────────────────────────────────────────
    @work(thread=True, exclusive=True, group="q")
    def run_quant(self):
        gb = self.app.gb
        if gb is None:
            return
        windows = []
        for lang in ("english", "hindi"):
            data = np.memmap(config.TOKENS_DIR / f"{lang}_val.bin", dtype=np.uint16, mode="r")
            for s in np.linspace(0, len(data) - 260, 4).astype(int):
                windows.append(torch.from_numpy(data[s:s + 257].astype(np.int64)))
        block = torch.stack(windows)
        n_bytes = sum(len(gb.tok.decode(r[1:].tolist()).encode()) for r in block)
        base = {k: v.clone() for k, v in gb.model.state_dict().items()}
        n_params = gb.model.num_params()
        rows = []
        for name, bits in (("32-bit (original)", 32), ("16-bit", 16), ("8-bit", 8), ("4-bit", 4)):
            self.app.call_from_thread(self._q_status, name)
            m = MONA(gb.cfg).eval()
            sd = {k: (fake_quant(v, bits) if bits < 16 and v.dim() == 2 else
                      (v.to(torch.bfloat16).float() if bits == 16 else v)) for k, v in base.items()}
            m.load_state_dict(sd)
            with torch.no_grad():
                logits, _ = m(block[:, :-1], block[:, 1:])
                nats = F.cross_entropy(logits.view(-1, logits.size(-1)), block[:, 1:].reshape(-1), reduction="sum").item()
            torch.manual_seed(0)
            sample = gb.tok.decode(list(m.generate(torch.tensor([gb.encode("The history of India")]), 24,
                                                   temperature=0.7, top_p=0.9)))
            rows.append((name, n_params * bits / 8 / 1e6, nats / math.log(2) / n_bytes, sample.replace("\n", " ")))
            self.app.call_from_thread(self._q_row, list(rows))
            del m
        self.app.call_from_thread(self._q_status, None)

    def _q_status(self, name):
        self.q_status = name
        self.draw_q()

    def _q_row(self, rows):
        self.q_rows = rows
        self.draw_q()

    def draw_q(self):
        tr, view = self.app.tr, self.query_one("#q-view", Static)
        if not self.q_rows and not self.q_status:
            view.update(Text(tr("by_q_run"), style="bold #f9e2af"))
            return
        out = Text(f"{'':20s}{'size':>10s}{'bits/byte':>12s}   sample: “The history of India…”\n", style="#6c7086")
        base_bpb = self.q_rows[0][2] if self.q_rows else None
        for name, mb, bpb, sample in self.q_rows:
            worse = f" (+{(bpb / base_bpb - 1):.1%})" if base_bpb and bpb != base_bpb else ""
            out.append(f"{name:20s}", style="bold #cdd6f4")
            out.append(f"{mb:8.0f} MB", style="bold #89dceb")
            out.append(f"{bpb:10.3f}{worse:10s}", style="#a6e3a1" if not worse or bpb / base_bpb < 1.02 else "#f78c6b")
            out.append(f"  {sample[:60]}\n", style="#bac2de")
        if self.q_status:
            out.append("\n" + tr("by_q_working", name=self.q_status), style="italic #9399b2")
        view.update(out)

    # ── tools ────────────────────────────────────────────────────────────────
    def on_input_submitted(self, event):
        if event.input.id == "tool-input":
            self.run_tool(event.value)

    @work(thread=True, exclusive=True, group="tool")
    def run_tool(self, expr):
        gb = self.app.gb
        try:
            value = calculator(expr)
        except Exception:
            return
        prompt = f"{expr.strip()} ="
        guesses = gb.next_word(prompt, top=5)
        torch.manual_seed(0)                                   # MONA's own full answer (greedy, a few tokens)
        written = gb.tok.decode(list(gb.model.generate(torch.tensor([gb.encode(prompt)]), 8, temperature=1e-5, top_p=None)))
        number = re.search(r"-?\d[\d,]*(\.\d+)?", written)
        self.app.call_from_thread(self._tool_done, expr, value, guesses, written, number.group(0) if number else "—")

    def _tool_done(self, expr, value, guesses, written, number):
        tr = self.app.tr
        out = Text(tr("by_tool_mona") + "\n", style="bold #f78c6b")
        out.append(f"   {expr.strip()} =", style="bold #cdd6f4")
        out.append(f"{written.splitlines()[0] if written.strip() else written}\n\n", style="bold #f9e2af")
        out.append_text(prob_bars(guesses))
        g = number.replace(",", "")
        ok = g == str(value)
        out.append(tr("by_tool_true", v=value, g=g, m="✓" if ok else "✗") + "\n\n",
                   style="bold #a6e3a1" if ok else "bold #ef476f")
        out.append(tr("by_tool_loop") + "\n", style="bold #a6e3a1")
        steps = [("MONA writes", f"calculator: {expr.strip()}"), ("program runs", f"calculator({expr.strip()!r})"),
                 ("result goes back", f"→ {value}"), ("MONA continues", f"{expr.strip()} = {value}")]
        for i, (who, what) in enumerate(steps, 1):
            out.append(f"   {i}. {who:18s}", style="#89dceb")
            out.append(f"{what}\n", style="bold #cdd6f4")
        self.query_one("#tool-view", Static).update(out)
        self.query_one("#avatar", Avatar).set_mood("wow")

    # ── KV-cache speed race ──────────────────────────────────────────────────
    @work(thread=True, exclusive=True, group="speed")
    def run_speed(self):
        gb = self.app.gb
        ids = torch.tensor([gb.encode("Once upon a time, in a small village, there lived")])
        n = 100
        torch.manual_seed(0)
        t = time.perf_counter()
        list(gb.model.generate(ids, n, temperature=0.8, top_p=0.9))
        with_cache = time.perf_counter() - t
        torch.manual_seed(0)
        t = time.perf_counter()
        x = ids
        with torch.no_grad():
            for _ in range(n):
                logits, _ = gb.model(x)                       # re-reads the whole text every step
                nxt = torch.multinomial(F.softmax(logits[0, -1] / 0.8, dim=-1), 1)
                x = torch.cat([x, nxt[None]], dim=1)
        without = time.perf_counter() - t
        self.app.call_from_thread(self._speed_done, n, with_cache, without)

    def _speed_done(self, n, with_cache, without):
        self.speed = (n, with_cache, without)
        self.draw_speed()

    def draw_speed(self):
        view = self.query_one("#speed-view", Static)
        if not self.speed:
            view.update(Text(self.app.tr("by_speed_run"), style="bold #f9e2af"))
            return
        n, a, b = self.speed
        top = max(a, b)
        out = Text()
        for label, s, colour in (("with KV-cache", a, "#a6e3a1"), ("without (re-read everything)", b, "#ef476f")):
            out.append(f"{label:30s}", style="bold #cdd6f4")
            out.append("█" * max(1, round(40 * s / top)), style=colour)
            out.append(f"  {s:5.2f} s  ({n / s:5.1f} tokens/s)\n", style="#bac2de")
        out.append(f"\n{b / a:.1f}× faster with the cache", style="bold #f9e2af")
        view.update(out)
