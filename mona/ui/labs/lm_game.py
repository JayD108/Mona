"""Stage 0 — What is a language model? Human vs MONA: who guesses the next word better?"""
import random

import numpy as np
import regex
from rich.text import Text
from textual import work
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, VerticalScroll
from textual.screen import Screen
from textual.widgets import Input, Static

from ... import config
from ..text import register
from ..widgets import Avatar, prob_bars

register({
    "lm_title": {"en": "What is a language model? Human vs MONA", "hi": "भाषा मॉडल क्या है? इंसान बनाम MONA",
                 "hinglish": "Language model kya hai? Insaan vs MONA"},
    "lm_explain": {
        "en": {"simple": "A language model has ONE job: guess the next word. That's all MONA ever does, over and over. "
                         "Can you guess better than MONA? 5 rounds. Type your guess and press Enter.",
               "student": "A language model estimates P(next token | everything before it). Writing a story, answering a "
                          "question, translating: all of it is just this one guess, repeated. These sentences are real "
                          "text MONA has never seen. Type the next word; 5 rounds.",
               "engineer": "Autoregressive LM: maximise Σ log P(x_t | x_<t). Prompts are drawn from the held-out validation "
                           "shards (never trained on); MONA's guess = argmax of the next-token distribution."},
        "hi": {"simple": "भाषा मॉडल का एक ही काम है: अगला शब्द अंदाज़ा लगाना। MONA बस यही बार-बार करती है। क्या आप MONA से "
                         "बेहतर अंदाज़ा लगा सकते हैं? 5 राउंड। अपना अंदाज़ा लिखकर Enter दबाइए।",
               "student": "भाषा मॉडल P(अगला टोकन | उससे पहले का सब कुछ) का अनुमान लगाता है। कहानी लिखना, सवाल का जवाब, अनुवाद: सब "
                          "इसी एक अंदाज़े को दोहराना है। ये असली वाक्य हैं जिन्हें MONA ने कभी नहीं देखा। अगला शब्द लिखिए; 5 राउंड।",
               "engineer": "Autoregressive LM: Σ log P(x_t | x_<t) को अधिकतम करना। वाक्य held-out validation shards से हैं (ट्रेनिंग "
                           "में नहीं); MONA का अंदाज़ा = अगले-टोकन वितरण का argmax।"},
        "hinglish": {"simple": "Language model ka ek hi kaam hai: agla word guess karna. MONA bas yahi baar-baar karti hai. Kya "
                               "tum MONA se behtar guess kar sakte ho? 5 rounds. Apna guess likho aur Enter dabao.",
                     "student": "Language model P(agla token | usse pehle ka sab kuch) ka andaaza lagata hai. Kahani likhna, "
                                "sawaal ka jawab, translation: sab isi ek guess ko repeat karna hai. Yeh asli sentences hain jo "
                                "MONA ne kabhi nahi dekhe. Agla word likho; 5 rounds.",
                     "engineer": "Autoregressive LM: Σ log P(x_t | x_<t) maximise karna. Prompts held-out validation shards se "
                                 "(training mein nahi); MONA ka guess = next-token distribution ka argmax."},
    },
    "lm_round": {"en": "Round {r}/5", "hi": "राउंड {r}/5", "hinglish": "Round {r}/5"},
    "lm_prompt": {"en": "Your guess for the next word…", "hi": "अगले शब्द का आपका अंदाज़ा…", "hinglish": "Agle word ka tumhara guess…"},
    "lm_real": {"en": "The real next word: “{w}”", "hi": "असली अगला शब्द: “{w}”", "hinglish": "Asli agla word: “{w}”"},
    "lm_you": {"en": "You: {g}  {m}", "hi": "आप: {g}  {m}", "hinglish": "Tum: {g}  {m}"},
    "lm_mona": {"en": "MONA: {g}  {m}   (it gave the real word {p} chance, rank #{k})",
                "hi": "MONA: {g}  {m}   (असली शब्द को {p} संभावना दी, क्रम #{k})",
                "hinglish": "MONA: {g}  {m}   (asli word ko {p} chance diya, rank #{k})"},
    "lm_score": {"en": "Score — You {a} : {b} MONA", "hi": "स्कोर — आप {a} : {b} MONA", "hinglish": "Score — Tum {a} : {b} MONA"},
    "lm_next": {"en": "Press Enter for the next round.", "hi": "अगले राउंड के लिए Enter दबाइए।", "hinglish": "Agle round ke liye Enter dabao."},
    "lm_end_win": {"en": "🏅 You beat MONA! Badge: Mind Reader. (Press Enter to play again.)",
                   "hi": "🏅 आपने MONA को हरा दिया! बैज: Mind Reader। (फिर खेलने के लिए Enter)",
                   "hinglish": "🏅 Tumne MONA ko hara diya! Badge: Mind Reader. (Phir khelne ke liye Enter)"},
    "lm_end": {"en": "Game over. Guessing the next word is hard, and it's the ONLY thing MONA learned to do. (Enter: play again)",
               "hi": "खेल ख़त्म। अगला शब्द अंदाज़ा लगाना मुश्किल है, और MONA ने बस यही सीखा है। (Enter: फिर खेलें)",
               "hinglish": "Game over. Agla word guess karna mushkil hai, aur MONA ne bas yahi seekha hai. (Enter: phir khelo)"},
    "lm_keys": {"en": "Enter submit / next   Esc back   F2 language (changes the sentences)   F3 depth   F4 romanize",
                "hi": "Enter जमा / अगला   Esc वापस   F2 भाषा (वाक्य बदलते हैं)   F3 गहराई   F4 रोमन",
                "hinglish": "Enter submit / agla   Esc wapas   F2 bhasha (sentences badlenge)   F3 depth   F4 roman"},
})

WORD = regex.compile(r"^ [\p{L}\p{M}]{3,}$")
LANG_SHARD = {"en": "english", "hi": "hindi", "hinglish": "hinglish"}


def norm(w):
    return w.strip().lower().strip(".,!?।\"'")


class LMGameLab(Screen):
    BINDINGS = [Binding("escape", "app.pop_screen", "back")]

    def compose(self) -> ComposeResult:
        with Horizontal(classes="lab-head"):
            yield Avatar(id="avatar", classes="lab-avatar")
            yield Static(id="title", classes="lab-title")
        yield Static(id="explain", classes="explain")
        with VerticalScroll():
            yield Static(id="context", classes="panel")
            yield Input(id="guess")
            yield Static(id="reveal", classes="panel")
        yield Static(id="keys", classes="keys")

    def on_mount(self):
        self.round, self.you, self.mona, self.answered, self.item = 0, 0, 0, False, None
        self.rng = random.Random()
        self.refresh_texts()
        self.new_game()

    def refresh_texts(self):
        tr = self.app.tr
        self.query_one("#title", Static).update(tr("lm_title"))
        self.query_one("#explain", Static).update(tr("lm_explain"))
        self.query_one("#guess", Input).placeholder = tr("lm_prompt")
        self.query_one("#keys", Static).update(tr("lm_keys"))
        self.draw_context()

    def on_engine_ready(self):
        if self.item is None:
            self.next_round()

    def new_game(self):
        self.round, self.you, self.mona = 0, 0, 0
        self.next_round()

    # ── pick a real held-out sentence, cut just before a whole word ─────────
    def sample(self):
        tok = self.app.tokenizer
        eot = tok.token_to_id("<|endoftext|>")
        data = np.memmap(config.TOKENS_DIR / f"{LANG_SHARD[self.app.state.lang]}_val.bin", dtype=np.uint16, mode="r")
        for _ in range(500):
            i = self.rng.randrange(40, len(data) - 1)
            nxt = tok.decode([int(data[i])])
            after = tok.decode([int(data[i + 1])]) if i + 1 < len(data) else " "
            window = [int(t) for t in data[i - 28:i]]
            # a whole word: this token starts with a space AND the next one starts a new word / punctuation
            # (otherwise " turt" + "les" would ask the player to guess half a word)
            if WORD.match(nxt) and after[:1] in " \n.,;:!?।\"')" and eot not in window:
                ctx = tok.decode(window)
                ctx = ctx[ctx.find(" ") + 1:]                    # drop the cut-off first word
                return ctx, nxt.strip(), int(data[i])
        return None

    def next_round(self):
        if self.app.gb is None:
            self.query_one("#context", Static).update(self.app.tr("loading"))
            return
        if self.round >= 5:
            self.new_game()
            return
        self.round += 1
        self.item, self.answered = self.sample(), False
        self.query_one("#reveal", Static).update("")
        inp = self.query_one("#guess", Input)
        inp.value = ""
        inp.disabled = False
        inp.focus()
        self.draw_context()
        self.query_one("#avatar", Avatar).set_mood("thinking")

    def draw_context(self):
        if not getattr(self, "item", None):
            return
        roman = self.app.roman if self.app.state.romanize else (lambda s: s)
        ctx = self.item[0]
        out = Text(self.app.tr("lm_round", r=self.round) + "\n\n", style="bold #8ecae6")
        out.append("…" + roman(ctx), style="#e8e8f0")
        out.append(" ____", style="bold #ffd166")
        self.query_one("#context", Static).update(out)

    def on_input_submitted(self, event: Input.Submitted):
        if self.answered or not self.item:
            self.next_round()
            return
        self.judge(event.value)

    @work(thread=True, exclusive=True)
    def judge(self, guess):
        gb = self.app.gb
        ctx, real, real_id = self.item
        p = gb.probs(gb.encode(ctx))
        top = gb.next_word(gb.encode(ctx), top=5)
        rank = int((p > p[real_id]).sum().item()) + 1
        self.app.call_from_thread(self._judged, guess, top, p[real_id].item(), rank)

    def _judged(self, guess, top, p_real, rank):
        tr = self.app.tr
        roman = self.app.roman if self.app.state.romanize else (lambda s: s)
        ctx, real, _ = self.item
        you_ok = norm(guess) == norm(real)
        mona_guess = top[0].token.text.strip()
        mona_ok = norm(mona_guess) == norm(real)
        self.you += you_ok
        self.mona += mona_ok
        self.answered = True
        out = Text()
        out.append(tr("lm_real", w=roman(real)) + "\n\n", style="bold #ffd166")
        out.append(tr("lm_you", g=roman(guess) or "—", m="✓" if you_ok else "✗") + "\n",
                   style="bold #06d6a0" if you_ok else "#f4a3c0")
        out.append(tr("lm_mona", g=roman(mona_guess), m="✓" if mona_ok else "✗", p=f"{p_real:.1%}", k=rank) + "\n\n",
                   style="bold #06d6a0" if mona_ok else "#f4a3c0")
        out.append_text(prob_bars(top, self.app.roman if self.app.state.romanize else None))
        out.append("\n" + tr("lm_score", a=self.you, b=self.mona) + "\n", style="bold #8ecae6")
        if self.round >= 5:
            if self.you > self.mona:
                self.app.state.complete("lm", badge="Mind Reader")
                out.append(tr("lm_end_win"), style="bold #ffd166")
            else:
                self.app.state.complete("lm")
                out.append(tr("lm_end"), style="#c9cce0")
        else:
            out.append(tr("lm_next"), style="#5a5f7c")
        self.query_one("#reveal", Static).update(out)
        self.query_one("#guess", Input).focus()
        self.query_one("#avatar", Avatar).set_mood("wow" if mona_ok else ("happy" if you_ok else "thinking"))
