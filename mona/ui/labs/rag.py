"""Stage 10 — RAG: give MONA a library to look things up in, instead of guessing from memory."""
import random

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
from ...engine.rag import build_library, words

CHAT_WEIGHTS = config.RUNS_DIR / "mona_m_chat" / "model.pt"
from ..text import register
from ..widgets import Avatar

register({
    "rag_title": {"en": "RAG: an open-book exam for MONA", "hi": "RAG: MONA के लिए खुली किताब वाली परीक्षा",
                  "hinglish": "RAG: MONA ke liye open-book exam"},
    "rag_explain": {
        "en": {"simple": "MONA can't remember every fact, so it sometimes makes things up. With RAG, we first SEARCH a "
                         "library for your question, paste what we found into MONA's prompt, then let it answer: an open-book exam.",
               "student": "Retrieval-Augmented Generation: 1) search a library for text related to the question, 2) insert the "
                          "best passages into the prompt, 3) the model answers using them. Facts come from the library, not "
                          "the model's memory, so they can be updated, checked and cited. RAG only finds what's IN the library.",
               "engineer": "BM25 retrieval (k1=1.5, b=0.75) over ~12K chunks (Tulsidas verses, Hindi/Hinglish "
                           "Wikipedia openings) → top-k passages templated into the prompt → MONA generates (T=0.7). Real "
                           "systems use embedding search + rerankers; the pipeline is the same."},
        "hi": {"simple": "MONA हर तथ्य याद नहीं रख सकती, इसलिए कभी-कभी बातें गढ़ लेती है। RAG में हम पहले आपके सवाल के लिए एक "
                         "पुस्तकालय में खोजते हैं, मिली जानकारी MONA के प्रॉम्प्ट में डालते हैं, फिर उसे जवाब देने देते हैं: खुली किताब परीक्षा।",
               "student": "Retrieval-Augmented Generation: 1) सवाल से जुड़ा पाठ पुस्तकालय में खोजो, 2) सबसे अच्छे अंश प्रॉम्प्ट में डालो, "
                          "3) मॉडल उन्हीं से जवाब देता है। तथ्य पुस्तकालय से आते हैं, मॉडल की याददाश्त से नहीं, इसलिए उन्हें बदला, "
                          "जाँचा और उद्धृत किया जा सकता है। RAG वही ढूँढ सकता है जो पुस्तकालय में है।",
               "engineer": "~12K अंशों (तुलसीदास की चौपाइयाँ, हिंदी/हिंग्लिश विकिपीडिया) पर BM25 खोज (k1=1.5, b=0.75) → शीर्ष-k अंश "
                           "प्रॉम्प्ट में → MONA जवाब बनाती है (T=0.7)। असली सिस्टम embedding खोज + reranker इस्तेमाल करते हैं; ढाँचा वही है।"},
        "hinglish": {"simple": "MONA har fact yaad nahi rakh sakti, isliye kabhi-kabhi baatein bana leti hai. RAG mein hum pehle "
                               "tumhare sawaal ke liye ek library mein dhoondte hain, jo mila use MONA ke prompt mein daalte hain, "
                               "phir use jawab dene dete hain: open-book exam.",
                     "student": "Retrieval-Augmented Generation: 1) sawaal se juda text library mein dhoondo, 2) sabse achhe passages "
                                "prompt mein daalo, 3) model unhi se jawab deta hai. Facts library se aate hain, model ki memory se "
                                "nahi, isliye update, check aur cite ho sakte hain. RAG wahi dhoondh sakta hai jo library mein hai.",
                     "engineer": "~12K chunks (Tulsidas chaupaiyan, Hindi/Hinglish Wikipedia) par BM25 search (k1=1.5, b=0.75) → "
                                 "top-k passages prompt mein → MONA generate karti hai (T=0.7). Asli systems embedding search + "
                                 "rerankers use karte hain; pipeline wahi hai."},
    },
    "rag_prompt": {"en": "Ask a question (Enter)…   F5: an example from the library   F6: add your own text to the library",
                   "hi": "सवाल पूछिए (Enter)…   F5: पुस्तकालय से उदाहरण   F6: अपना पाठ जोड़िए",
                   "hinglish": "Sawaal poochho (Enter)…   F5: library se example   F6: apna text jodo"},
    "rag_lib": {"en": "📚 Library: {n:,} passages ({detail})", "hi": "📚 पुस्तकालय: {n:,} अंश ({detail})",
                "hinglish": "📚 Library: {n:,} passages ({detail})"},
    "rag_step1": {"en": "① Search the library for your question", "hi": "① पुस्तकालय में आपका सवाल खोजें",
                  "hinglish": "① Library mein tumhara sawaal dhoondo"},
    "rag_none": {"en": "Nothing found: RAG can only find what's IN the library. Add your own text with F6.",
                 "hi": "कुछ नहीं मिला: RAG वही ढूँढ सकता है जो पुस्तकालय में है। F6 से अपना पाठ जोड़िए।",
                 "hinglish": "Kuch nahi mila: RAG wahi dhoondh sakta hai jo library mein hai. F6 se apna text jodo."},
    "rag_step2": {"en": "② The prompt MONA actually sees (the found passage is pasted in)", "hi": "② वह प्रॉम्प्ट जो MONA सच में देखती है (मिला अंश चिपकाया गया)",
                  "hinglish": "② Woh prompt jo MONA sach mein dekhti hai (mila hua passage chipkaya gaya)"},
    "rag_step3": {"en": "③ MONA's answers", "hi": "③ MONA के जवाब", "hinglish": "③ MONA ke jawab"},
    "rag_without": {"en": "WITHOUT the library (memory only):", "hi": "पुस्तकालय के बिना (केवल याददाश्त):", "hinglish": "Library ke BINA (sirf memory):"},
    "rag_with": {"en": "WITH the library (open book):", "hi": "पुस्तकालय के साथ (खुली किताब):", "hinglish": "Library ke SAATH (open book):"},
    "rag_grounded": {"en": "{p:.0%} of the answer's words also appear in the passage (green): that's grounding.",
                     "hi": "जवाब के {p:.0%} शब्द अंश में भी हैं (हरे): यही grounding है।",
                     "hinglish": "Jawab ke {p:.0%} words passage mein bhi hain (hare): yahi grounding hai."},
    "rag_added": {"en": "Added to the library. Now ask about it!", "hi": "पुस्तकालय में जोड़ दिया। अब इसके बारे में पूछिए!",
                  "hinglish": "Library mein jod diya. Ab iske baare mein poochho!"},
    "rag_add_prompt": {"en": "Paste a paragraph to add to the library (Enter)…", "hi": "पुस्तकालय में जोड़ने के लिए एक अनुच्छेद (Enter)…",
                       "hinglish": "Library mein jodne ke liye ek paragraph (Enter)…"},
    "rag_keys": {"en": "Enter ask   F5 example   F6 add your text   Esc back   F2 language  F3 depth  F4 romanize",
                 "hi": "Enter पूछें   F5 उदाहरण   F6 अपना पाठ   Esc वापस   F2 भाषा  F3 गहराई  F4 रोमन",
                 "hinglish": "Enter poochho   F5 example   F6 apna text   Esc wapas   F2 bhasha  F3 depth  F4 roman"},
})

TEMPLATES = {"hi": "जानकारी:\n{ctx}\n\nप्रश्न: {q}\nउत्तर:", "en": "Information:\n{ctx}\n\nQuestion: {q}\nAnswer:"}


class RagLab(Screen):
    BINDINGS = [Binding("escape", "app.pop_screen", "back"), Binding("f5", "example"), Binding("f6", "add_mode")]

    def compose(self) -> ComposeResult:
        with Horizontal(classes="lab-head"):
            yield Avatar(id="avatar", classes="lab-avatar")
            yield Static(id="title", classes="lab-title")
        yield Static(id="explain", classes="explain")
        yield Static(id="lib", classes="dim")
        yield Input(id="question")
        with VerticalScroll():
            yield Static(id="search", classes="panel")
            yield Static(id="prompt", classes="panel")
            yield Static(id="answers", classes="panel")
        yield Static(id="keys", classes="keys")

    def on_mount(self):
        self.lib, self.adding, self.result = None, False, None
        self.refresh_texts()
        self.load()
        self.app.state.complete("rag")

    def refresh_texts(self):
        tr = self.app.tr
        self.query_one("#title", Static).update(tr("rag_title"))
        self.query_one("#explain", Static).update(tr("rag_explain"))
        self.query_one("#question", Input).placeholder = tr("rag_add_prompt") if self.adding else tr("rag_prompt")
        self.query_one("#keys", Static).update(tr("rag_keys"))
        self.draw_lib()
        self.draw()

    @property
    def rr(self):
        return self.app.roman if self.app.state.romanize else (lambda s: s)

    @work(thread=True, exclusive=True, group="lib")
    def load(self):
        lib = build_library()
        self.app.call_from_thread(self._loaded, lib)

    def _loaded(self, lib):
        self.lib = lib
        self.draw_lib()
        seed = getattr(self, "seed", None)
        self.query_one("#question", Input).value = seed or "मंगल भवन अमंगल हारी द्रवउ सो दसरथ अजिर बिहारी"
        self.ask()

    def draw_lib(self):
        if not self.lib:
            self.query_one("#lib", Static).update(self.app.tr("loading"))
            return
        from collections import Counter
        c = Counter(ch.source for ch in self.lib.chunks)
        detail = " · ".join(f"{k} {v:,}" for k, v in c.items())
        self.query_one("#lib", Static).update(self.app.tr("rag_lib", n=len(self.lib.chunks), detail=detail))

    # ── actions ──────────────────────────────────────────────────────────────
    def action_example(self):
        if not self.lib:
            return
        wiki = [c for c in self.lib.chunks if c.source != "tulsidas"]
        c = random.choice(wiki)
        q = f"{c.title} क्या है?" if c.source == "hindi-wiki" else f"{c.title} kya hai?"
        self.query_one("#question", Input).value = q
        self.ask()

    def action_add_mode(self):
        self.adding = True
        inp = self.query_one("#question", Input)
        inp.value = ""
        inp.focus()
        self.refresh_texts()

    def on_input_submitted(self, event):
        if self.adding:
            text = event.value.strip()
            if len(text) > 20:
                self.lib.add("yours", text[:40], text)
                self.app.notify(self.app.tr("rag_added"), timeout=3)
                self.draw_lib()
            self.adding = False
            event.input.value = ""
            self.refresh_texts()
            return
        self.ask()

    def ask(self):
        if not self.lib or self.app.gb is None:
            return
        self.query_one("#avatar", Avatar).set_mood("thinking")
        self.query_one("#answers", Static).update(self.app.tr("loading"))
        self._ask(self.query_one("#question", Input).value)

    @work(thread=True, exclusive=True, group="ask")
    def _ask(self, q):
        gb = self.app.gb
        hits = self.lib.search(q, k=3)
        lang = "en" if q.isascii() else "hi"
        ctx = hits[0].chunk.text[:600] if hits else ""
        with_prompt = TEMPLATES[lang].format(ctx=ctx, q=q) if ctx else None
        without_prompt = TEMPLATES[lang].split("\n\n", 1)[1].format(q=q)
        stop = {gb.tok.token_to_id(T.EOT), gb.tok.token_to_id(T.END)}
        chat = self.chat_model()
        if chat is not None:      # MONA-Chat: the passage goes inside the user's turn, like real RAG systems
            with_prompt = f"{ctx}\n\n{q}" if ctx else None
            without_prompt = q
            model, ids_of = chat, (lambda p: T.chat_prompt(gb.tok, [{"role": "user", "content": p}]))
        else:                     # base MONA: plain text template
            model, ids_of = gb.model, gb.encode

        def answer(prompt):
            torch.manual_seed(0)
            out = gb.tok.decode(list(model.generate(torch.tensor([ids_of(prompt)]), 80, temperature=0.7,
                                                    top_p=0.9, stop_ids=stop)))
            return out.strip() if chat is not None else (out.split("\n")[0].strip() or out.strip())

        without = answer(without_prompt)
        with_ = answer(with_prompt) if with_prompt else None
        self.which = "MONA-Chat" if chat is not None else "base MONA: MONA-Chat takes over after chat training"
        self.app.call_from_thread(self._answered, q, hits, with_prompt, without, with_)

    def chat_model(self):
        """MONA-Chat (after SFT) answers far better with a passage; use it as soon as it exists."""
        if not CHAT_WEIGHTS.exists():
            return None
        if getattr(self, "_chat", None) is None:
            from ...engine.lessons import load_model
            self._chat = load_model(CHAT_WEIGHTS)
        return self._chat

    def _answered(self, q, hits, with_prompt, without, with_):
        self.result = (q, hits, with_prompt, without, with_)
        self.draw()

    # ── drawing ──────────────────────────────────────────────────────────────
    def draw(self):
        if not self.result:
            return
        tr, rr = self.app.tr, self.rr
        q, hits, with_prompt, without, with_ = self.result
        qwords = set(words(q))
        s = Text(tr("rag_step1") + "\n\n", style="bold #8ecae6")
        if not hits:
            s.append(tr("rag_none"), style="#f4a3c0")
        for h in hits:
            s.append(f"{h.score:5.1f}  ", style="bold #ffd166")
            s.append(f"[{h.chunk.source}] ", style="#8a8fb0")
            s.append(rr(h.chunk.title) + "\n", style="bold #e8e8f0")
            snippet = h.chunk.text[:220].replace("\n", " ")
            line = Text("       ")
            for w in snippet.split(" "):
                line.append(rr(w) + " ", style="bold #14172b on #ffd166" if w.lower().strip(".,।?!") in qwords else "#c9cce0")
            s.append_text(line)
            s.append("\n")
        self.query_one("#search", Static).update(s)

        p = Text(tr("rag_step2") + "\n\n", style="bold #8ecae6")
        p.append(rr(with_prompt[:700]) if with_prompt else "—", style="#c9cce0")
        self.query_one("#prompt", Static).update(p)

        a = Text(tr("rag_step3") + f"   ({getattr(self, 'which', '')})\n\n", style="bold #8ecae6")
        a.append(tr("rag_without") + "\n", style="bold #f78c6b")
        a.append(rr(without) + "\n\n", style="#e8e8f0")
        if with_ is not None:
            a.append(tr("rag_with") + "\n", style="bold #06d6a0")
            ctx_words = set(words(hits[0].chunk.text))
            ans = with_.split(" ")
            grounded = 0
            for w in ans:
                inside = w.lower().strip(".,।?!") in ctx_words
                grounded += inside
                a.append(rr(w) + " ", style="bold #06d6a0" if inside else "#e8e8f0")
            a.append("\n\n" + tr("rag_grounded", p=grounded / max(len(ans), 1)), style="italic #8ecae6")
        self.query_one("#answers", Static).update(a)
        self.query_one("#avatar", Avatar).set_mood("wow" if with_ else "thinking")
