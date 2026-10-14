"""Compare MONA (110M) with a big model running locally in Ollama: what does scale buy?"""
import json
import re
import time
import urllib.request

import torch
from rich.text import Text
from textual import work
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, VerticalScroll
from textual.screen import Screen
from textual.widgets import Input, Static

from ... import config
from ... import tokenizer as T
from ..text import register
from ..widgets import Avatar

OLLAMA = "http://localhost:11434"
CHAT_WEIGHTS = config.chat_weights()

register({
    "cmp_title": {"en": "MONA vs a big model: what does scale buy?", "hi": "MONA बनाम बड़ा मॉडल: आकार से क्या मिलता है?",
                  "hinglish": "MONA vs bada model: size se kya milta hai?"},
    "cmp_explain": {
        "en": {"simple": "Same question, two models: tiny MONA and a big model running on your own computer. "
                         "The big one is much smarter. Why? It is ~75× bigger and read ~14,000× more text.",
               "student": "Both are the same kind of machine: a transformer that predicts the next token. The difference "
                          "is scale: parameters (memory for patterns) and training tokens (experience), plus chat tuning and "
                          "preference training. Also compare how many tokens each needs for the same text.",
               "engineer": "Local model via Ollama's /api/generate (stream off; raw mode for token counts from "
                           "prompt_eval_count). While MONA is training, Ollama is forced onto the CPU (num_gpu=0) so it "
                           "can't steal GPU memory from the training run."},
        "hi": {"simple": "एक ही सवाल, दो मॉडल: छोटी MONA और आपके कंप्यूटर पर चलता एक बड़ा मॉडल। बड़ा वाला कहीं ज़्यादा समझदार है। "
                         "क्यों? वह ~75 गुना बड़ा है और उसने ~14,000 गुना ज़्यादा पाठ पढ़ा है।",
               "student": "दोनों एक ही तरह की मशीन हैं: अगला टोकन बताने वाला transformer। फ़र्क़ आकार का है: पैरामीटर (पैटर्न की "
                          "याददाश्त) और ट्रेनिंग टोकन (अनुभव), साथ में चैट ट्यूनिंग और पसंद-आधारित ट्रेनिंग। यह भी देखिए कि एक ही "
                          "पाठ के लिए किसे कितने टोकन लगते हैं।",
               "engineer": "Ollama के /api/generate से लोकल मॉडल (raw mode से prompt_eval_count = टोकन गिनती)। MONA की ट्रेनिंग "
                           "चलते समय Ollama को CPU पर रखा जाता है (num_gpu=0) ताकि वह GPU मेमोरी न ले।"},
        "hinglish": {"simple": "Ek hi sawaal, do models: chhoti MONA aur tumhare computer par chalta ek bada model. Bada wala kahin "
                               "zyada samajhdaar hai. Kyun? Woh ~75× bada hai aur usne ~14,000× zyada text padha hai.",
                     "student": "Dono ek hi tarah ki machine hain: agla token batane wala transformer. Farak size ka hai: "
                                "parameters (patterns ki memory) aur training tokens (experience), saath mein chat tuning aur "
                                "preference training. Yeh bhi dekho ki same text ke liye kise kitne tokens lagte hain.",
                     "engineer": "Ollama ke /api/generate se local model (raw mode se prompt_eval_count = token count). MONA ki "
                                 "training chalte waqt Ollama ko CPU par rakha jaata hai (num_gpu=0) taaki GPU memory na le."},
    },
    "cmp_prompt": {"en": "Ask both models (Enter)…", "hi": "दोनों मॉडलों से पूछिए (Enter)…", "hinglish": "Dono models se poochho (Enter)…"},
    "cmp_none": {"en": "Ollama isn't running or has no models. Install from ollama.com, then e.g. `ollama pull qwen3`.",
                 "hi": "Ollama नहीं चल रहा या उसमें कोई मॉडल नहीं। ollama.com से इंस्टॉल कीजिए, फिर जैसे `ollama pull qwen3`।",
                 "hinglish": "Ollama nahi chal raha ya usme koi model nahi. ollama.com se install karo, phir jaise `ollama pull qwen3`."},
    "cmp_cpu": {"en": "(MONA is training right now, so the big model runs on the CPU: slower, but it won't disturb training)",
                "hi": "(MONA अभी ट्रेन हो रही है, इसलिए बड़ा मॉडल CPU पर चलेगा: धीमा, पर ट्रेनिंग में बाधा नहीं)",
                "hinglish": "(MONA abhi train ho rahi hai, isliye bada model CPU par chalega: dheema, par training disturb nahi hogi)"},
    "cmp_tokens": {"en": "Tokens needed for your text:  MONA {a}  ·  {name} {b}", "hi": "आपके पाठ के लिए टोकन:  MONA {a}  ·  {name} {b}",
                   "hinglish": "Tumhare text ke liye tokens:  MONA {a}  ·  {name} {b}"},
    "cmp_keys": {"en": "Enter ask both   Esc back   F3 depth",
                 "hi": "Enter दोनों से पूछें   Esc वापस   F2 भाषा  F3 गहराई  F4 रोमन",
                 "hinglish": "Enter dono se poochho   Esc wapas   F2 bhasha  F3 depth  F4 roman"},
})


def ollama(path, payload=None, timeout=600):
    req = urllib.request.Request(OLLAMA + path, data=json.dumps(payload).encode() if payload else None,
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read())


def training_running():
    run = config.RUNS_DIR / "mona_m"
    log = run / "train_log.csv"
    return log.exists() and not (run / "final.pt").exists() and time.time() - log.stat().st_mtime < 600


class CompareLab(Screen):
    BINDINGS = [Binding("escape", "app.pop_screen", "back")]

    def compose(self) -> ComposeResult:
        with Horizontal(classes="lab-head"):
            yield Avatar(id="avatar", classes="lab-avatar")
            yield Static(id="title", classes="lab-title")
        yield Static(id="explain", classes="explain")
        yield Input(id="q")
        with VerticalScroll():
            with Horizontal(id="cmp-cols"):
                yield Static(id="left", classes="panel cmp-col")
                yield Static(id="right", classes="panel cmp-col")
            yield Static(id="tokens", classes="panel")
        yield Static(id="keys", classes="keys")

    def on_mount(self):
        self.big = None
        self.query_one("#q", Input).value = getattr(self, "seed", None) or "भारत की राजधानी क्या है और वह किस नदी के किनारे है?"
        self.refresh_texts()
        self.find_model()

    def refresh_texts(self):
        tr = self.app.tr
        self.query_one("#title", Static).update(tr("cmp_title"))
        self.query_one("#explain", Static).update(tr("cmp_explain"))
        self.query_one("#q", Input).placeholder = tr("cmp_prompt")
        self.query_one("#keys", Static).update(tr("cmp_keys"))

    @work(thread=True, exclusive=True, group="find")
    def find_model(self):
        try:
            models = ollama("/api/tags", timeout=5).get("models", [])
        except Exception:
            models = []
        big = max(models, key=lambda m: m.get("size", 0)) if models else None
        self.app.call_from_thread(self._found, big)

    def _found(self, big):
        self.big = big
        if not big:
            self.query_one("#right", Static).update(Text(self.app.tr("cmp_none"), style="#f5c2e7"))

    def on_input_submitted(self, event):
        self.ask(event.value)

    @work(thread=True, exclusive=True, group="ask")
    def ask(self, q):
        gb = self.app.gb
        if gb is None:
            return
        rr = self.app.roman if self.app.state.romanize else (lambda s: s)
        self.app.call_from_thread(self.query_one("#left", Static).update, self.app.tr("loading"))
        # MONA: chat model if it exists, otherwise the base model completing a Q/A template
        t = time.perf_counter()
        stop = {gb.tok.token_to_id(T.EOT), gb.tok.token_to_id(T.END)}
        torch.manual_seed(0)
        if CHAT_WEIGHTS.exists():
            from ...engine.lessons import load_model
            model, ids, label = load_model(CHAT_WEIGHTS), T.chat_prompt(gb.tok, [{"role": "user", "content": q}]), "MONA-Chat"
        else:
            model, ids, label = gb.model, gb.encode(f"Q: {q}\nA:"), "MONA (base)"
        out_ids = list(model.generate(torch.tensor([ids]), 80, temperature=0.7, top_p=0.9, stop_ids=stop))
        mona_text = gb.tok.decode(out_ids).strip()
        mona_s = time.perf_counter() - t
        left = Text(f"{label}  ·  110M parameters  ·  2.5B training tokens\n", style="bold #f9e2af")
        left.append(f"{len(out_ids) / mona_s:.1f} tokens/s on CPU\n\n", style="#6c7086")
        left.append(rr(mona_text), style="#cdd6f4")
        self.app.call_from_thread(self.query_one("#left", Static).update, left)
        if not self.big:
            return
        name = self.big["name"]
        cpu = training_running()
        waiting = Text(f"{name} …\n", style="bold #89dceb")
        if cpu:
            waiting.append(self.app.tr("cmp_cpu"), style="italic #9399b2")
        self.app.call_from_thread(self.query_one("#right", Static).update, waiting)
        options = {"temperature": 0.7, "num_predict": 200}
        if cpu:
            options["num_gpu"] = 0
        try:
            t = time.perf_counter()
            r = ollama("/api/generate", {"model": name, "prompt": q, "stream": False, "think": False, "options": options})
            big_s = time.perf_counter() - t
            answer = re.sub(r"<think>.*?</think>", "", r.get("response", ""), flags=re.S).strip()
            raw = ollama("/api/generate", {"model": name, "prompt": q, "raw": True, "stream": False,
                                           "options": {**options, "num_predict": 1}})
            big_tokens = raw.get("prompt_eval_count")
        except Exception as e:
            self.app.call_from_thread(self.query_one("#right", Static).update, Text(f"{name}: {e}", style="#f5c2e7"))
            return
        params = self.big.get("details", {}).get("parameter_size", "?")
        tps = r.get("eval_count", 0) / max(r.get("eval_duration", 1) / 1e9, 1e-6)
        right = Text(f"{name}  ·  {params} parameters  ·  {'CPU' if cpu else 'GPU'}\n", style="bold #89dceb")
        right.append(f"{tps:.1f} tokens/s · {big_s:.0f} s\n\n", style="#6c7086")
        right.append(rr(answer[:900]), style="#cdd6f4")
        self.app.call_from_thread(self.query_one("#right", Static).update, right)
        mona_tokens = len(gb.encode(q))
        tok = Text(self.app.tr("cmp_tokens", a=mona_tokens, name=name, b=big_tokens), style="bold #a6e3a1")
        self.app.call_from_thread(self.query_one("#tokens", Static).update, tok)
