"""Stage 1 — Data: what MONA learned from, and how it was cleaned. Be the data curator."""
import json
import random

import pyarrow.parquet as pq
from rich.text import Text
from textual import work
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, VerticalScroll
from textual.screen import Screen
from textual.widgets import Static, TabbedContent, TabPane

from ... import config
from ..text import register
from ..widgets import CHIP_COLOURS, Avatar

register({
    "dat_title": {"en": "Data: what MONA read", "hi": "डेटा: MONA ने क्या पढ़ा", "hinglish": "Data: MONA ne kya padha"},
    "dat_tab_cur": {"en": "Be the curator", "hi": "छँटाई कीजिए", "hinglish": "Curator bano"},
    "dat_tab_mix": {"en": "The mix", "hi": "मिश्रण", "hinglish": "Mix"},
    "dat_tab_fix": {"en": "Fixing Hinglish", "hi": "हिंग्लिश सुधार", "hinglish": "Hinglish fix"},
    "dat_explain": {
        "en": {"simple": "MONA learned only from what it read. Bad text in = bad MONA out. Before training, every document "
                         "was checked: keep it or throw it away? You decide first, then see what MONA's cleaner decided.",
               "student": "A model is only as good as its data. MONA's 2.5B training tokens came from web text (FineWeb-Edu, "
                          "AI4Bharat Sangraha) plus Tulsidas. A cleaner removed junk: too-short pages, text in the wrong "
                          "script, broken characters, duplicates. Decide keep (K) or drop (D), then compare.",
               "engineer": "pipeline/mona_clean.py: NFC, strip category-C chars (keep ZWNJ/ZWJ), collapse whitespace, "
                           "drop < 200 chars, Hindi needs ≥ 60% Devanagari letters, Hinglish ≥ 80% Latin, exact dedup by "
                           "blake2b hash. The game mixes kept and dropped documents ~50/50; real drop rates are shown."},
        "hi": {"simple": "MONA ने केवल वही सीखा जो उसने पढ़ा। खराब पाठ = खराब MONA। ट्रेनिंग से पहले हर दस्तावेज़ जाँचा गया: "
                         "रखें या फेंकें? पहले आप तय कीजिए, फिर देखिए MONA के cleaner ने क्या किया।",
               "student": "मॉडल उतना ही अच्छा होता है जितना उसका डेटा। MONA के 2.5 अरब टोकन वेब पाठ (FineWeb-Edu, AI4Bharat "
                          "Sangraha) और तुलसीदास से आए। Cleaner ने कचरा हटाया: बहुत छोटे पन्ने, गलत लिपि, टूटे अक्षर, दोहराव। "
                          "रखें (K) या हटाएँ (D) तय कीजिए, फिर तुलना कीजिए।",
               "engineer": "pipeline/mona_clean.py: NFC, category-C अक्षर हटाना (ZWNJ/ZWJ रखकर), स्पेस समेटना, < 200 अक्षर हटाना, "
                           "हिंदी में ≥ 60% देवनागरी, हिंग्लिश में ≥ 80% लैटिन, blake2b hash से सटीक dedup। खेल में रखे/हटाए "
                           "दस्तावेज़ ~50/50 मिलाए गए हैं; असली हटाने की दर दिखाई गई है।"},
        "hinglish": {"simple": "MONA ne sirf wahi seekha jo usne padha. Kharab text = kharab MONA. Training se pehle har document "
                               "check hua: rakhein ya phenkein? Pehle tum decide karo, phir dekho MONA ke cleaner ne kya kiya.",
                     "student": "Model utna hi achha hota hai jitna uska data. MONA ke 2.5B tokens web text (FineWeb-Edu, "
                                "AI4Bharat Sangraha) aur Tulsidas se aaye. Cleaner ne kachra hataya: bahut chhote pages, galat "
                                "script, toote characters, duplicates. Rakho (K) ya hatao (D), phir compare karo.",
                     "engineer": "pipeline/mona_clean.py: NFC, category-C chars hatana (ZWNJ/ZWJ rakhkar), whitespace collapse, "
                                 "< 200 chars drop, Hindi ≥ 60% Devanagari, Hinglish ≥ 80% Latin, blake2b hash se exact dedup. "
                                 "Game mein kept/dropped ~50/50; asli drop rate dikhaya gaya hai."},
    },
    "dat_doc": {"en": "Document {i} · from the {src} web data · {n:,} characters", "hi": "दस्तावेज़ {i} · {src} वेब डेटा से · {n:,} अक्षर",
                "hinglish": "Document {i} · {src} web data se · {n:,} characters"},
    "dat_q": {"en": "Keep it for training (K) or drop it (D)?", "hi": "ट्रेनिंग के लिए रखें (K) या हटाएँ (D)?",
              "hinglish": "Training ke liye rakho (K) ya hatao (D)?"},
    "dat_kept": {"en": "MONA's cleaner KEPT it", "hi": "MONA के cleaner ने इसे रखा", "hinglish": "MONA ke cleaner ne ise RAKHA"},
    "dat_dropped": {"en": "MONA's cleaner DROPPED it: {why}", "hi": "MONA के cleaner ने इसे हटाया: {why}",
                    "hinglish": "MONA ke cleaner ne ise HATAYA: {why}"},
    "why_short": {"en": "too short (under 200 characters): not enough to learn from",
                  "hi": "बहुत छोटा (200 अक्षर से कम): सीखने लायक नहीं", "hinglish": "bahut chhota (200 se kam): seekhne layak nahi"},
    "why_script": {"en": "wrong script: only {p:.0%} of its letters are {s}", "hi": "गलत लिपि: केवल {p:.0%} अक्षर {s} हैं",
                   "hinglish": "galat script: sirf {p:.0%} letters {s} hain"},
    "dat_you": {"en": "You: {y} {m}", "hi": "आप: {y} {m}", "hinglish": "Tum: {y} {m}"},
    "dat_score": {"en": "You agreed with the cleaner {k} of {n} times.   N: next document",
                  "hi": "आप {n} में से {k} बार cleaner से सहमत रहे।   N: अगला दस्तावेज़",
                  "hinglish": "Tum {n} mein se {k} baar cleaner se sahmat rahe.   N: agla document"},
    "dat_rates": {"en": "Real drop rates: English {e:.1%} · Hindi {h:.1%} · Hinglish {g:.1%}  (most web text was already good)",
                  "hi": "असली हटाने की दर: अंग्रेज़ी {e:.1%} · हिंदी {h:.1%} · हिंग्लिश {g:.1%}  (ज़्यादातर पाठ पहले से अच्छा था)",
                  "hinglish": "Asli drop rate: English {e:.1%} · Hindi {h:.1%} · Hinglish {g:.1%}  (zyada text pehle se achha tha)"},
    "dat_badge": {"en": "🏅 Badge: Data Curator", "hi": "🏅 बैज: Data Curator", "hinglish": "🏅 Badge: Data Curator"},
    "dat_mix_title": {"en": "What MONA trains on (real token counts)", "hi": "MONA किस पर सीखती है (असली टोकन संख्या)",
                      "hinglish": "MONA kis par seekhti hai (asli token counts)"},
    "dat_mix_note": {
        "en": "Awadhi is tiny (under 1M tokens), so it is shown ~4 times during training; more repeats and MONA would start "
              "memorising Tulsidas instead of learning from him. English and Hindi are seen about once each.",
        "hi": "अवधी बहुत कम है (10 लाख से कम टोकन), इसलिए ट्रेनिंग में ~4 बार दिखाई जाती है; इससे ज़्यादा दोहराने पर MONA "
              "तुलसीदास को रटने लगती, सीखती नहीं। अंग्रेज़ी और हिंदी लगभग एक-एक बार दिखती हैं।",
        "hinglish": "Awadhi bahut kam hai (10 lakh se kam tokens), isliye training mein ~4 baar dikhayi jaati hai; isse zyada "
                    "repeat karne par MONA Tulsidas ko ratne lagti, seekhti nahi. English aur Hindi lagbhag ek-ek baar dikhti hain.",
    },
    "dat_fix_title": {"en": "A real data bug we found: machine-made Hinglish", "hi": "एक असली डेटा बग जो हमें मिला: मशीन से बनी हिंग्लिश",
                      "hinglish": "Ek asli data bug jo humein mila: machine se bani Hinglish"},
    "dat_fix_note": {
        "en": "Our Hinglish came from a computer that turned Hindi letters into English letters, with spellings no person "
              "types (\"ack\" for ek, \"haye\" for hai). We counted the most common words, and fixed the ~70 worst before "
              "training, so MONA learns how people actually write.",
        "hi": "हमारी हिंग्लिश एक कंप्यूटर से बनी थी जिसने हिंदी अक्षरों को अंग्रेज़ी अक्षरों में बदला, ऐसी वर्तनी के साथ जो कोई नहीं "
              "लिखता (एक के लिए \"ack\", है के लिए \"haye\")। हमने सबसे आम शब्द गिने और ट्रेनिंग से पहले ~70 सबसे बुरे ठीक किए।",
        "hinglish": "Hamari Hinglish ek computer se bani thi jisne Hindi letters ko English letters mein badla, aisi spelling ke "
                    "saath jo koi nahi likhta (ek ke liye \"ack\", hai ke liye \"haye\"). Humne sabse common words gine aur "
                    "training se pehle ~70 sabse bure theek kiye.",
    },
    "dat_before": {"en": "before", "hi": "पहले", "hinglish": "pehle"},
    "dat_after": {"en": "after", "hi": "बाद", "hinglish": "baad"},
    "dat_keys": {"en": "Esc back   F5 Curator  F6 Mix  F7 Hinglish fix   K keep  D drop  N next",
                 "hi": "Esc वापस   F5 छँटाई  F6 मिश्रण  F7 हिंग्लिश सुधार   K रखें  D हटाएँ  N अगला",
                 "hinglish": "Esc wapas   F5 Curator  F6 Mix  F7 Hinglish fix   K rakho  D hatao  N agla"},
})

RAW = config.DATA_DIR / "raw"
SOURCES = [("english", RAW / "english_fineweb/sample/10BT/000_00000.parquet"),
           ("hindi", RAW / "hindi_sangraha/verified/hin/data-3.parquet"),
           ("hinglish", RAW / "hinglish_sangraha/synthetic/hin_Latn/wiki_hin_Latn_0000_of_0063.parquet")]


class Curate(Static, can_focus=True):
    BINDINGS = [Binding("k", "screen.decide(True)"), Binding("d", "screen.decide(False)"), Binding("n", "screen.next_doc")]


class DataLab(Screen):
    BINDINGS = [Binding("escape", "app.pop_screen", "back"), Binding("f5", "tab('cur')"), Binding("f6", "tab('mix')"),
                Binding("f7", "tab('fix')")]

    def compose(self) -> ComposeResult:
        with Horizontal(classes="lab-head"):
            yield Avatar(id="avatar", classes="lab-avatar")
            yield Static(id="title", classes="lab-title")
        yield Static(id="explain", classes="explain")
        with TabbedContent(id="tabs"):
            with TabPane("Be the curator", id="cur"):
                with VerticalScroll():
                    yield Curate(id="cur-view", classes="panel")
            with TabPane("The mix", id="mix"):
                with VerticalScroll():
                    yield Static(id="mix-view", classes="panel")
            with TabPane("Fixing Hinglish", id="fix"):
                with VerticalScroll():
                    yield Static(id="fix-view", classes="panel")
        yield Static(id="keys", classes="keys")

    def on_mount(self):
        self.pool, self.i, self.answered, self.k, self.n, self.rates, self.fix = [], 0, None, 0, 0, None, None
        self.refresh_texts()
        self.load_pool()
        self.query_one("#cur-view").focus()

    def refresh_texts(self):
        tr = self.app.tr
        self.query_one("#title", Static).update(tr("dat_title"))
        self.query_one("#explain", Static).update(tr("dat_explain"))
        self.query_one("#keys", Static).update(tr("dat_keys"))
        tabs = self.query_one("#tabs", TabbedContent)
        for pane, key in (("cur", "dat_tab_cur"), ("mix", "dat_tab_mix"), ("fix", "dat_tab_fix")):
            tabs.get_tab(pane).label = tr(key)
        self.draw_doc()
        self.draw_mix()
        self.draw_fix()

    def action_tab(self, pane):
        self.query_one("#tabs", TabbedContent).active = pane
        self.query_one({"cur": "#cur-view", "mix": "#mix-view", "fix": "#fix-view"}[pane]).focus()

    @property
    def rr(self):
        return self.app.roman if self.app.state.romanize else (lambda s: s)

    # ── load real raw documents and run MONA's real cleaner on them ─────────
    @work(thread=True, exclusive=True)
    def load_pool(self):
        from ...textclean import DEVA, LATIN, LETTER, fix_hinglish, keep, normalise
        kept, dropped, rates, fix = [], [], {}, None
        for lang, path in SOURCES:
            if not path.exists():
                continue
            docs = next(pq.ParquetFile(path).iter_batches(batch_size=3000, columns=["text"])).column("text").to_pylist()
            n_drop = 0
            for raw in docs:
                text = normalise(raw)
                if lang == "hinglish":
                    if fix is None and " haye" in text:
                        fix = (raw[:420], fix_hinglish(text)[:420])
                    text = fix_hinglish(text)
                letters = len(LETTER.findall(text)) or 1
                stats = {"deva": len(DEVA.findall(text)) / letters, "latin": len(LATIN.findall(text)) / letters}
                if len(text) < 200:
                    why = ("why_short", {})
                elif not keep(lang, text):
                    why = ("why_script", {"p": stats["deva" if lang == "hindi" else "latin"],
                                          "s": "Devanagari" if lang == "hindi" else "Latin"})
                else:
                    why = None
                item = {"lang": lang, "raw": raw, "why": why}
                (dropped if why else kept).append(item)
                n_drop += why is not None
            rates[lang] = n_drop / max(len(docs), 1)
        rnd = random.Random()
        pool = rnd.sample(dropped, min(10, len(dropped))) + rnd.sample(kept, min(10, len(kept)))
        rnd.shuffle(pool)
        self.app.call_from_thread(self._pooled, pool, rates, fix)

    def _pooled(self, pool, rates, fix):
        self.pool, self.rates, self.fix, self.i, self.answered = pool, rates, fix, 0, None
        self.draw_doc()
        self.draw_fix()

    def action_decide(self, keep_it: bool):
        if not self.pool or self.answered is not None:
            return
        doc = self.pool[self.i]
        cleaner_keeps = doc["why"] is None
        self.answered = keep_it
        self.n += 1
        self.k += keep_it == cleaner_keeps
        if self.n >= 8 and self.k / self.n >= 0.75:
            self.app.state.complete("data", badge="Data Curator")
        else:
            self.app.state.complete("data")
        self.draw_doc()

    def action_next_doc(self):
        if self.pool:
            self.i = (self.i + 1) % len(self.pool)
            self.answered = None
            self.draw_doc()

    def draw_doc(self):
        tr, view = self.app.tr, self.query_one("#cur-view", Static)
        if not self.pool:
            view.update(tr("loading"))
            return
        doc = self.pool[self.i]
        raw = doc["raw"].strip()
        out = Text(tr("dat_doc", i=self.n + (self.answered is None), src=doc["lang"], n=len(raw)) + "\n\n", style="bold #89dceb")
        out.append(self.rr(raw[:600]) + ("…" if len(raw) > 600 else "") + "\n\n", style="#cdd6f4")
        if self.answered is None:
            out.append(tr("dat_q"), style="bold #f9e2af")
        else:
            keeps = doc["why"] is None
            if keeps:
                out.append(tr("dat_kept") + "\n", style="bold #a6e3a1")
            else:
                key, fmt = doc["why"]
                out.append(tr("dat_dropped", why=tr(key, **fmt)) + "\n", style="bold #ef476f")
            right = self.answered == keeps
            out.append(tr("dat_you", y="K" if self.answered else "D", m="✓" if right else "✗") + "\n",
                       style="#a6e3a1" if right else "#f5c2e7")
            out.append(tr("dat_score", k=self.k, n=self.n) + "\n", style="#bac2de")
            if self.rates:
                out.append(tr("dat_rates", e=self.rates.get("english", 0), h=self.rates.get("hindi", 0),
                              g=self.rates.get("hinglish", 0)), style="#9399b2")
            if self.n >= 8 and self.k / self.n >= 0.75:
                out.append("\n" + tr("dat_badge"), style="bold #f9e2af")
            self.query_one("#avatar", Avatar).set_mood("wow" if right else "thinking")
        view.update(out)

    def draw_mix(self):
        tr = self.app.tr
        try:
            manifest = json.loads((config.TOKENS_DIR / "manifest.json").read_text())
        except OSError:
            return
        # (stable-phase share, decay-phase share) from scripts/mona_pretrain.py; decay = last 15% of training
        shares = {"english": (0.55, 0.55), "hindi": (0.40, 0.40), "hinglish": (0.0497, 0.049), "awadhi": (0.00026, 0.00104)}
        total = sum(v["train_tokens"] for v in manifest.values())
        out = Text(tr("dat_mix_title") + "\n\n", style="bold #89dceb")
        for c, (lang, v) in enumerate(sorted(manifest.items(), key=lambda kv: -kv[1]["train_tokens"])):
            n = v["train_tokens"]
            out.append(f"{lang:9s} ", style=f"bold {CHIP_COLOURS[c]}")
            out.append("█" * max(1, round(50 * n / total)), style=CHIP_COLOURS[c])
            s_stable, s_decay = shares.get(lang, (0, 0))
            seen = 2.5e9 * (0.85 * s_stable + 0.15 * s_decay) / n
            out.append(f"  {n / 1e6:8,.1f}M tokens · {s_stable:.1%} of training · seen ~{seen:.1f}×\n", style="#bac2de")
        out.append(f"\n{'total':9s} {total / 1e9:.2f}B tokens available · 2.5B used for training\n\n", style="bold")
        out.append(tr("dat_mix_note"), style="italic #bac2de")
        self.query_one("#mix-view", Static).update(out)

    def draw_fix(self):
        tr = self.app.tr
        out = Text(tr("dat_fix_title") + "\n\n", style="bold #89dceb")
        out.append(tr("dat_fix_note") + "\n\n", style="#bac2de")
        if self.fix:
            before, after = self.fix
            out.append(f"{tr('dat_before')}:\n", style="bold #ef476f")
            out.append(before + "…\n\n", style="#cdd6f4")
            out.append(f"{tr('dat_after')}:\n", style="bold #a6e3a1")
            out.append(after + "…", style="#cdd6f4")
        self.query_one("#fix-view", Static).update(out)
