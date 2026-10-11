"""Stage 3 — Embeddings: every token is a list of 768 numbers; similar words get similar numbers."""
import random

import regex
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

from ..text import register
from ..widgets import CHIP_COLOURS, Avatar, show_piece

register({
    "emb_title": {"en": "Embeddings: words as numbers", "hi": "एम्बेडिंग: शब्द संख्याओं के रूप में", "hinglish": "Embeddings: words numbers ke roop mein"},
    "emb_tab_nb": {"en": "Neighbours", "hi": "पड़ोसी", "hinglish": "Padosi"},
    "emb_tab_map": {"en": "Word map", "hi": "शब्द नक्शा", "hinglish": "Word map"},
    "emb_tab_odd": {"en": "Odd one out", "hi": "अलग कौन?", "hinglish": "Odd one out"},
    "emb_explain": {
        "en": {"simple": "MONA turns every token into a list of 768 numbers. Words used in similar ways end up with similar "
                         "numbers, so they sit close together, like neighbours on a map.",
               "student": "An embedding is the row of 768 numbers MONA keeps for each of its 32,768 tokens (MONA's first "
                          "layer). Nobody told MONA what words mean: tokens that appear in similar contexts drift close to each "
                          "other during training. Closeness here = cosine similarity.",
               "engineer": "Rows of the 32,768 × 768 token-embedding matrix (tied with the output layer). Neighbours by cosine "
                           "similarity; multi-token words use the mean of their pieces' vectors (marked *). Map = 2D PCA."},
        "hi": {"simple": "MONA हर टोकन को 768 संख्याओं की सूची में बदलती है। एक जैसे इस्तेमाल होने वाले शब्दों की संख्याएँ भी एक "
                         "जैसी होती हैं, इसलिए वे पास-पास रहते हैं, जैसे नक्शे पर पड़ोसी।",
               "student": "एम्बेडिंग 768 संख्याओं की वह पंक्ति है जो MONA अपने 32,768 टोकनों में से हर एक के लिए रखती है (MONA की "
                          "पहली लेयर)। MONA को किसी ने अर्थ नहीं बताया: जो टोकन एक जैसे संदर्भ में आते हैं, वे ट्रेनिंग के दौरान पास "
                          "आ जाते हैं। यहाँ निकटता = cosine similarity।",
               "engineer": "32,768 × 768 token-embedding मैट्रिक्स की पंक्तियाँ (output layer के साथ tied)। पड़ोसी cosine "
                           "similarity से; कई-टोकन शब्दों के लिए टुकड़ों का औसत (* चिह्न)। नक्शा = 2D PCA।"},
        "hinglish": {"simple": "MONA har token ko 768 numbers ki list mein badalti hai. Ek jaise use hone wale words ke numbers "
                               "bhi ek jaise hote hain, isliye woh paas-paas rehte hain, jaise map par padosi.",
                     "student": "Embedding woh 768 numbers ki row hai jo MONA apne 32,768 tokens mein se har ek ke liye rakhti "
                                "hai (MONA ki pehli layer). MONA ko kisi ne meaning nahi bataya: jo tokens ek jaise context mein "
                                "aate hain, woh training mein paas aa jaate hain. Yahan nazdeeki = cosine similarity.",
                     "engineer": "32,768 × 768 token-embedding matrix ki rows (output layer ke saath tied). Neighbours cosine "
                                 "similarity se; multi-token words ke liye pieces ka mean (* mark). Map = 2D PCA."},
    },
    "emb_prompt": {"en": "A word (Enter)…", "hi": "एक शब्द (Enter)…", "hinglish": "Ek word (Enter)…"},
    "emb_nb_title": {"en": "Tokens closest to “{w}”{star}", "hi": "“{w}”{star} के सबसे पास वाले टोकन",
                     "hinglish": "“{w}”{star} ke sabse paas wale tokens"},
    "emb_star": {"en": " (* made of {n} tokens: their average)", "hi": " (* {n} टोकन से बना: उनका औसत)",
                 "hinglish": " (* {n} tokens se bana: unka average)"},
    "emb_map_title": {"en": "Word map: {name}  (X: next set)", "hi": "शब्द नक्शा: {name}  (X: अगला समूह)",
                      "hinglish": "Word map: {name}  (X: agla set)"},
    "emb_map_note": {"en": "768 numbers squeezed into 2 so they fit on screen; close on the map ≈ close for MONA.",
                     "hi": "768 संख्याएँ 2 में दबाई गईं ताकि स्क्रीन पर आ सकें; नक्शे पर पास ≈ MONA के लिए पास।",
                     "hinglish": "768 numbers ko 2 mein dabaya taaki screen par aa sakein; map par paas ≈ MONA ke liye paas."},
    "emb_map_mixed": {"en": "Look: Hindi words sit together and English words sit together. MONA first groups words by "
                            "LANGUAGE, then by meaning; “dog” and “कुत्ता” are not neighbours (yet).",
                      "hi": "देखिए: हिंदी शब्द एक साथ हैं और अंग्रेज़ी शब्द एक साथ। MONA पहले शब्दों को भाषा से, फिर अर्थ से "
                            "समूहित करती है; “dog” और “कुत्ता” (अभी) पड़ोसी नहीं हैं।",
                      "hinglish": "Dekho: Hindi words saath hain aur English words saath. MONA pehle words ko BHASHA se, phir "
                                  "meaning se group karti hai; “dog” aur “कुत्ता” (abhi) padosi nahi hain."},
    "emb_odd_q": {"en": "Which one doesn't belong? Press 1-4.", "hi": "इनमें से कौन अलग है? 1-4 दबाइए।",
                  "hinglish": "Inmein se kaun alag hai? 1-4 dabao."},
    "emb_odd_res": {"en": "Answer: “{a}”.  You: {y}   MONA's numbers say: “{m}” {mm}", "hi": "जवाब: “{a}”।  आप: {y}   MONA की संख्याएँ कहती हैं: “{m}” {mm}",
                    "hinglish": "Jawab: “{a}”.  Tum: {y}   MONA ke numbers kehte hain: “{m}” {mm}"},
    "emb_odd_score": {"en": "MONA agreed with the answer {k} of {n} times.   N: next puzzle",
                      "hi": "MONA {n} में से {k} बार सही रही।   N: अगली पहेली", "hinglish": "MONA {n} mein se {k} baar sahi rahi.   N: agli paheli"},
    "emb_badge": {"en": "🏅 Badge: Word Mapper", "hi": "🏅 बैज: Word Mapper", "hinglish": "🏅 Badge: Word Mapper"},
    "emb_keys": {"en": "Esc back   F5 Neighbours  F6 Word map  F7 Odd one out   X next set   1-4 answer   N next",
                 "hi": "Esc वापस   F5 पड़ोसी  F6 नक्शा  F7 अलग कौन   X अगला समूह   1-4 जवाब   N अगला",
                 "hinglish": "Esc wapas   F5 Padosi  F6 Map  F7 Odd one out   X agla set   1-4 jawab   N agla"},
})

CATEGORIES = {
    "animals":   (["cat", "dog", "horse", "cow", "lion"], ["बिल्ली", "कुत्ता", "घोड़ा", "गाय", "शेर"]),
    "numbers":   (["one", "two", "three", "four", "five"], ["एक", "दो", "तीन", "चार", "पांच"]),
    "family":    (["mother", "father", "brother", "sister", "son"], ["माँ", "पिता", "भाई", "बहन", "बेटा"]),
    "countries": (["India", "China", "France", "Japan", "Brazil"], ["भारत", "चीन", "फ्रांस", "जापान", "ब्राज़ील"]),
    "colours":   (["red", "blue", "green", "yellow", "black"], ["लाल", "नीला", "हरा", "पीला", "काला"]),
    "food":      (["rice", "bread", "milk", "tea", "sugar"], ["चावल", "रोटी", "दूध", "चाय", "चीनी"]),
}
MAP_SETS = [("English", 0), ("हिंदी", 1), ("English + हिंदी", 2)]
HAS_LETTER = regex.compile(r"\p{L}\p{M}*\p{L}")       # at least two letters: skip one-letter fragments


class MapView(Static, can_focus=True):
    BINDINGS = [Binding("x", "screen.next_set")]


class OddView(Static, can_focus=True):
    BINDINGS = [Binding("n", "screen.new_odd")] + [Binding(str(i), f"screen.answer({i})") for i in range(1, 5)]


class EmbeddingsLab(Screen):
    BINDINGS = [Binding("escape", "app.pop_screen", "back"), Binding("f5", "tab('nb')"), Binding("f6", "tab('map')"),
                Binding("f7", "tab('odd')")]

    def compose(self) -> ComposeResult:
        with Horizontal(classes="lab-head"):
            yield Avatar(id="avatar", classes="lab-avatar")
            yield Static(id="title", classes="lab-title")
        yield Static(id="explain", classes="explain")
        with TabbedContent(id="tabs"):
            with TabPane("Neighbours", id="nb"):
                yield Input(id="word")
                with VerticalScroll():
                    yield Static(id="nb-view", classes="panel")
            with TabPane("Word map", id="map"):
                yield MapView(id="map-view", classes="panel")
            with TabPane("Odd one out", id="odd"):
                yield OddView(id="odd-view", classes="panel")
        yield Static(id="keys", classes="keys")

    def on_mount(self):
        self.E = None
        self.set_i, self.odd, self.odd_answered, self.odd_n, self.odd_k = 0, None, False, 0, 0
        self.query_one("#word", Input).value = "king"
        self.refresh_texts()
        self.prepare()

    def refresh_texts(self):
        tr = self.app.tr
        self.query_one("#title", Static).update(tr("emb_title"))
        self.query_one("#explain", Static).update(tr("emb_explain"))
        self.query_one("#word", Input).placeholder = tr("emb_prompt")
        self.query_one("#keys", Static).update(tr("emb_keys"))
        tabs = self.query_one("#tabs", TabbedContent)
        for pane, key in (("nb", "emb_tab_nb"), ("map", "emb_tab_map"), ("odd", "emb_tab_odd")):
            tabs.get_tab(pane).label = tr(key)
        if self.E is not None:
            self.neighbours()
            self.draw_map()
            self.draw_odd()

    def on_engine_ready(self):
        self.prepare()

    def prepare(self):
        gb = self.app.gb
        if gb is None:
            self.query_one("#nb-view", Static).update(self.app.tr("loading"))
            return
        W = gb.model.embed.weight.detach().float()
        self.E = F.normalize(W, dim=-1)                           # unit vectors: dot product = cosine similarity
        self.allowed = torch.tensor([bool(HAS_LETTER.search(gb.tok.decode([i]))) and i not in gb.special_ids
                                     for i in range(W.shape[0])])
        self.app.state.complete("embeddings")
        self.neighbours()
        self.draw_map()
        self.new_odd(draw=True)

    def action_tab(self, pane):
        self.query_one("#tabs", TabbedContent).active = pane
        self.query_one({"nb": "#word", "map": "#map-view", "odd": "#odd-view"}[pane]).focus()

    @property
    def rr(self):
        return self.app.roman if self.app.state.romanize else (lambda s: s)

    def vec(self, word):
        ids = self.app.gb.encode(" " + word.strip())
        return F.normalize(self.E[ids].mean(0), dim=-1), len(ids)

    # ── neighbours ───────────────────────────────────────────────────────────
    def on_input_submitted(self, event):
        self.neighbours()

    def neighbours(self):
        word = self.query_one("#word", Input).value.strip()
        if self.E is None or not word:
            return
        v, n = self.vec(word)
        sims = self.E @ v
        sims[~self.allowed] = -1
        own = set(self.app.gb.encode(" " + word))
        vals, idx = torch.topk(sims, 14)
        rows = [(self.app.gb.tok.decode([i]), s) for s, i in zip(vals.tolist(), idx.tolist()) if i not in own][:12]
        tr = self.app.tr
        star = tr("emb_star", n=n) if n > 1 else ""
        out = Text(tr("emb_nb_title", w=self.rr(word), star=star) + "\n\n", style="bold #8ecae6")
        label_w = max(cell_len(self.rr(show_piece(t))) for t, _ in rows) + 2
        for k, (t, s) in enumerate(rows):
            piece = self.rr(show_piece(t))
            out.append(piece + " " * (label_w - cell_len(piece)), style=f"bold {CHIP_COLOURS[k % len(CHIP_COLOURS)]}")
            out.append("█" * max(1, round(36 * max(s, 0))), style=CHIP_COLOURS[k % len(CHIP_COLOURS)])
            out.append(f" {s:.2f}\n", style="#c9cce0")
        self.query_one("#nb-view", Static).update(out)

    # ── 2D word map ──────────────────────────────────────────────────────────
    def action_next_set(self):
        self.set_i = (self.set_i + 1) % len(MAP_SETS)
        self.draw_map()

    def draw_map(self, width=76, height=18):
        if self.E is None:
            return
        name, which = MAP_SETS[self.set_i]
        words, cats = [], []
        for c, (en, hi) in enumerate(CATEGORIES.values()):
            chosen = en if which == 0 else hi if which == 1 else en[:3] + hi[:3]
            words += chosen
            cats += [c] * len(chosen)
        X = torch.stack([self.vec(w)[0] for w in words])
        X = X - X.mean(0)
        U, S, V = torch.pca_lowrank(X, q=2, center=False)
        P = X @ V[:, :2]
        P = (P - P.min(0).values) / (P.max(0).values - P.min(0).values + 1e-9)
        rows = {}
        for w, c, (x, y) in zip(words, cats, P.tolist()):
            rows.setdefault(int(y * (height - 1)), []).append((int(x * (width - 12)), self.rr(w), c))
        out = Text(self.app.tr("emb_map_title", name=name) + "\n\n", style="bold #8ecae6")
        for r in range(height - 1, -1, -1):
            line, pos = Text("│ ", style="#3a3f5c"), 0
            for x, w, c in sorted(rows.get(r, [])):
                x = max(x, pos)
                line.append(" " * (x - pos))
                line.append(f"• {w}", style=f"bold {CHIP_COLOURS[c]}")
                pos = x + 2 + cell_len(w) + 1
                line.append(" ")
            out.append_text(line)
            out.append("\n")
        out.append("└" + "─" * width + "\n", style="#3a3f5c")
        legend = Text()
        for c, cat in enumerate(CATEGORIES):
            legend.append(f"● {cat}   ", style=CHIP_COLOURS[c])
        out.append_text(legend)
        out.append("\n" + self.app.tr("emb_map_note"), style="italic #8a8fb0")
        if which == 2:
            out.append("\n" + self.app.tr("emb_map_mixed"), style="italic #ffd166")
        self.query_one("#map-view", Static).update(out)

    # ── odd one out ──────────────────────────────────────────────────────────
    def action_new_odd(self):
        self.new_odd(draw=True)

    def new_odd(self, draw=False):
        lang = 1 if self.app.state.lang == "hi" else 0
        cats = list(CATEGORIES)
        a, b = random.sample(cats, 2)
        group = random.sample(CATEGORIES[a][lang], 3)
        odd = random.choice(CATEGORIES[b][lang])
        words = group + [odd]
        random.shuffle(words)
        self.odd, self.odd_answered = (words, words.index(odd)), False
        if draw:
            self.draw_odd()

    def mona_odd(self, words):
        V = torch.stack([self.vec(w)[0] for w in words])
        sims = V @ V.T
        mean_sim = (sims.sum(1) - 1) / (len(words) - 1)          # how close each word is to the others
        return int(mean_sim.argmin())

    def action_answer(self, n: int):
        if not self.odd or self.odd_answered:
            return
        words, ans = self.odd
        mona = self.mona_odd(words)
        self.odd_answered = True
        self.odd_n += 1
        self.odd_k += mona == ans
        self.odd_result = (n - 1, mona)
        if self.odd_k >= 3:
            self.app.state.complete("embeddings", badge="Word Mapper")
        self.draw_odd()

    def draw_odd(self):
        if not self.odd:
            return
        tr = self.app.tr
        words, ans = self.odd
        out = Text(tr("emb_odd_q") + "\n\n", style="bold #8ecae6")
        for i, w in enumerate(words, 1):
            out.append(f"  {i}  ", style="bold #ffd166")
            out.append(self.rr(w) + "\n", style="bold #e8e8f0")
        if self.odd_answered:
            you, mona = self.odd_result
            out.append("\n" + tr("emb_odd_res", a=self.rr(words[ans]), y="✓" if you == ans else "✗",
                                 m=self.rr(words[mona]), mm="✓" if mona == ans else "✗") + "\n", style="bold #06d6a0")
            out.append(tr("emb_odd_score", k=self.odd_k, n=self.odd_n), style="#c9cce0")
            if self.odd_k >= 3:
                out.append("\n" + tr("emb_badge"), style="bold #ffd166")
        self.query_one("#odd-view", Static).update(out)
        self.query_one("#avatar", Avatar).set_mood("wow" if self.odd_answered else "thinking")
