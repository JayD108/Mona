"""Stage 8 — Chat tuning (SFT): how a text-continuer becomes an assistant."""
import json
import random

import torch
from rich.text import Text
from textual import work
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, VerticalScroll
from textual.screen import Screen
from textual.widgets import Input, Static, TabbedContent, TabPane

from ... import config
from ... import tokenizer as T
from ..text import register
from ..widgets import Avatar, show_piece

register({
    "ct_title": {"en": "Chat tuning: from text-continuer to assistant", "hi": "चैट ट्यूनिंग: पाठ आगे बढ़ाने वाले से सहायक तक",
                 "hinglish": "Chat tuning: text aage badhane wale se assistant tak"},
    "ct_tab_tpl": {"en": "Chat template", "hi": "चैट ढाँचा", "hinglish": "Chat template"},
    "ct_tab_cmp": {"en": "Base vs Chat", "hi": "Base बनाम Chat", "hinglish": "Base vs Chat"},
    "ct_tab_data": {"en": "Training examples", "hi": "प्रशिक्षण उदाहरण", "hinglish": "Training examples"},
    "ct_explain": {
        "en": {"simple": "After reading billions of words, MONA can continue any text, but it doesn't know it should ANSWER "
                         "you. So we show it thousands of example chats, and only grade it on the answers.",
               "student": "A pretrained (base) model only continues text. Supervised fine-tuning (SFT) teaches a format: "
                          "conversations written with special role tokens, and the loss counted only on the assistant's "
                          "tokens (loss masking). After a few passes over ~100K chats, the model 'becomes' an assistant.",
               "engineer": "SFT: chat template <|system|>/<|user|>/<|assistant|> … <|end|>, packed into 1,024-token rows, "
                           "cross-entropy masked to assistant tokens, LR 1e-4 cosine, ~2 epochs (scripts/mona_sft.py)."},
        "hi": {"simple": "अरबों शब्द पढ़ने के बाद MONA कोई भी पाठ आगे बढ़ा सकती है, पर उसे पता नहीं कि उसे आपको जवाब देना है। "
                         "इसलिए हम उसे हज़ारों उदाहरण-बातचीत दिखाते हैं, और केवल जवाबों पर अंक देते हैं।",
               "student": "पहले से प्रशिक्षित (base) मॉडल केवल पाठ आगे बढ़ाता है। Supervised fine-tuning (SFT) एक ढाँचा सिखाता है: "
                          "विशेष भूमिका-टोकन वाली बातचीत, और loss केवल सहायक के टोकनों पर (loss masking)। ~1 लाख बातचीत पर कुछ "
                          "बार चलाने के बाद मॉडल 'सहायक' बन जाता है।",
               "engineer": "SFT: chat template <|system|>/<|user|>/<|assistant|> … <|end|>, 1,024-टोकन पंक्तियों में packed, "
                           "cross-entropy केवल सहायक टोकनों पर, LR 1e-4 cosine, ~2 epochs (scripts/mona_sft.py)।"},
        "hinglish": {"simple": "Arabon words padhne ke baad MONA koi bhi text aage badha sakti hai, par use pata nahi ki use "
                               "tumhe JAWAB dena hai. Isliye hum use hazaron example chats dikhate hain, aur sirf jawabon par marks dete hain.",
                     "student": "Pretrained (base) model sirf text aage badhata hai. Supervised fine-tuning (SFT) ek format sikhata "
                                "hai: special role tokens wali conversations, aur loss sirf assistant ke tokens par (loss masking). "
                                "~1 lakh chats par kuch passes ke baad model 'assistant' ban jaata hai.",
                     "engineer": "SFT: chat template <|system|>/<|user|>/<|assistant|> … <|end|>, 1,024-token rows mein packed, "
                                 "cross-entropy sirf assistant tokens par, LR 1e-4 cosine, ~2 epochs (scripts/mona_sft.py)."},
    },
    "ct_q": {"en": "Question (Enter)…", "hi": "प्रश्न (Enter)…", "hinglish": "Sawaal (Enter)…"},
    "ct_a": {"en": "Answer (Enter)…", "hi": "उत्तर (Enter)…", "hinglish": "Jawab (Enter)…"},
    "ct_learn": {"en": "LEARN = MONA is graded on predicting this token", "hi": "LEARN = इस टोकन के अनुमान पर अंक मिलते हैं",
                 "hinglish": "LEARN = is token ke guess par marks milte hain"},
    "ct_count": {"en": "{a} of {n} tokens count toward the loss: only the answer.", "hi": "{n} में से {a} टोकन loss में गिने जाते हैं: केवल उत्तर।",
                 "hinglish": "{n} mein se {a} tokens loss mein gine jaate hain: sirf jawab."},
    "ct_base": {"en": "BASE MONA (pretrained only) sees the chat prompt and writes:", "hi": "BASE MONA (केवल pretrained) चैट प्रॉम्प्ट देखकर लिखती है:",
                "hinglish": "BASE MONA (sirf pretrained) chat prompt dekhkar likhti hai:"},
    "ct_chat": {"en": "MONA-CHAT (after chat tuning) answers:", "hi": "MONA-CHAT (चैट ट्यूनिंग के बाद) जवाब देती है:",
                "hinglish": "MONA-CHAT (chat tuning ke baad) jawab deti hai:"},
    "ct_nochat": {"en": "MONA-Chat doesn't exist yet: it is trained automatically right after pretraining finishes. "
                        "Notice how base MONA doesn't really answer; that's exactly what chat tuning fixes.",
                  "hi": "MONA-Chat अभी नहीं है: pretraining ख़त्म होते ही यह अपने-आप प्रशिक्षित होगी। ध्यान दीजिए कि base MONA "
                        "सचमुच जवाब नहीं देती; चैट ट्यूनिंग यही ठीक करती है।",
                  "hinglish": "MONA-Chat abhi nahi hai: pretraining khatam hote hi yeh apne-aap train hogi. Dekho base MONA "
                              "sach mein jawab nahi deti; chat tuning yahi theek karti hai."},
    "ct_nodata": {"en": "The chat dataset is built automatically after pretraining. It will mix: ~80K English chats "
                        "(smol-smoltalk), Hindi chats (Aya), Hindi and Hinglish Wikipedia Q&A, 7,747 Tulsidas verse→meaning "
                        "pairs, and \"who are you?\" examples so MONA knows its own name.",
                  "hi": "चैट डेटा pretraining के बाद अपने-आप बनेगा। इसमें होंगे: ~80K अंग्रेज़ी बातचीत (smol-smoltalk), हिंदी बातचीत "
                        "(Aya), हिंदी और हिंग्लिश विकिपीडिया प्रश्नोत्तर, 7,747 तुलसीदास चौपाई→अर्थ जोड़े, और \"तुम कौन हो?\" उदाहरण।",
                  "hinglish": "Chat data pretraining ke baad apne-aap banega. Isme honge: ~80K English chats (smol-smoltalk), "
                              "Hindi chats (Aya), Hindi aur Hinglish Wikipedia Q&A, 7,747 Tulsidas chaupai→arth pairs, aur "
                              "\"tum kaun ho?\" examples."},
    "ct_keys": {"en": "Esc back   F5 Template  F6 Base vs Chat  F7 Examples   N next example   F2 language  F3 depth  F4 romanize",
                "hi": "Esc वापस   F5 ढाँचा  F6 Base बनाम Chat  F7 उदाहरण   N अगला उदाहरण   F2 भाषा  F3 गहराई  F4 रोमन",
                "hinglish": "Esc wapas   F5 Template  F6 Base vs Chat  F7 Examples   N agla example   F2 bhasha  F3 depth  F4 roman"},
})

CHAT_WEIGHTS = config.RUNS_DIR / "mona_m_chat" / "model.pt"


class Examples(Static, can_focus=True):
    BINDINGS = [Binding("n", "screen.next_example")]


class ChatTuningLab(Screen):
    BINDINGS = [Binding("escape", "app.pop_screen", "back"), Binding("f5", "tab('tpl')"), Binding("f6", "tab('cmp')"),
                Binding("f7", "tab('data')")]

    def compose(self) -> ComposeResult:
        with Horizontal(classes="lab-head"):
            yield Avatar(id="avatar", classes="lab-avatar")
            yield Static(id="title", classes="lab-title")
        yield Static(id="explain", classes="explain")
        with TabbedContent(id="tabs"):
            with TabPane("Chat template", id="tpl"):
                yield Input(id="q")
                yield Input(id="a")
                with VerticalScroll():
                    yield Static(id="tpl-view", classes="panel")
            with TabPane("Base vs Chat", id="cmp"):
                yield Input(id="cmp-q")
                with VerticalScroll():
                    yield Static(id="cmp-view", classes="panel")
            with TabPane("Training examples", id="data"):
                with VerticalScroll():
                    yield Examples(id="data-view", classes="panel")
        yield Static(id="keys", classes="keys")

    def on_mount(self):
        self.examples, self.ex_i, self.cmp = None, 0, None
        self.query_one("#q", Input).value = "भारत की राजधानी क्या है?"
        self.query_one("#a", Input).value = "भारत की राजधानी नई दिल्ली है।"
        self.query_one("#cmp-q", Input).value = getattr(self, "seed", None) or "What is photosynthesis?"
        self.refresh_texts()
        self.load_examples()
        self.app.state.complete("chat")

    def refresh_texts(self):
        tr = self.app.tr
        self.query_one("#title", Static).update(tr("ct_title"))
        self.query_one("#explain", Static).update(tr("ct_explain"))
        self.query_one("#q", Input).placeholder = tr("ct_q")
        self.query_one("#a", Input).placeholder = tr("ct_a")
        self.query_one("#cmp-q", Input).placeholder = tr("ct_q")
        self.query_one("#keys", Static).update(tr("ct_keys"))
        tabs = self.query_one("#tabs", TabbedContent)
        for pane, key in (("tpl", "ct_tab_tpl"), ("cmp", "ct_tab_cmp"), ("data", "ct_tab_data")):
            tabs.get_tab(pane).label = tr(key)
        self.draw_template()
        self.draw_cmp()
        self.draw_example()

    def action_tab(self, pane):
        self.query_one("#tabs", TabbedContent).active = pane
        self.query_one({"tpl": "#q", "cmp": "#cmp-q", "data": "#data-view"}[pane]).focus()
        if pane == "cmp" and self.cmp is None:
            self.compare()

    @property
    def rr(self):
        return self.app.roman if self.app.state.romanize else (lambda s: s)

    def on_input_changed(self, event):
        if event.input.id in ("q", "a"):
            self.draw_template()

    def on_input_submitted(self, event):
        if event.input.id == "cmp-q":
            self.compare()

    # ── template + loss mask ────────────────────────────────────────────────
    def draw_template(self):
        tok, tr = self.app.tokenizer, self.app.tr
        msgs = [{"role": "user", "content": self.query_one("#q", Input).value},
                {"role": "assistant", "content": self.query_one("#a", Input).value}]
        ids, mask = T.encode_chat(tok, msgs)
        out = Text()
        for tid, m in zip(ids, mask):
            name = tok.id_to_token(tid)
            if name in T.SPECIAL_TOKENS:
                out.append(f" {name} ", style="bold #14172b on #cdb4db")
            else:
                piece = self.rr(show_piece(tok.decode([tid])))
                out.append(f"{piece}", style="bold #14172b on #06d6a0" if m else "#8a8fb0 on #2b2f55")
            out.append(" ")
        out.append("\n\n")
        out.append(" LEARN ", style="bold #14172b on #06d6a0")
        out.append("  " + tr("ct_learn") + "\n", style="#c9cce0")
        out.append(tr("ct_count", a=sum(mask), n=len(mask)), style="bold #8ecae6")
        self.query_one("#tpl-view", Static).update(out)

    # ── base vs chat ─────────────────────────────────────────────────────────
    @work(thread=True, exclusive=True, group="cmp")
    def compare(self):
        gb = self.app.gb
        if gb is None:
            return
        q = self.query_one("#cmp-q", Input).value
        prompt = T.chat_prompt(gb.tok, [{"role": "user", "content": q}])
        stop = {gb.tok.token_to_id(T.END), gb.tok.token_to_id(T.EOT)}
        torch.manual_seed(0)
        base = gb.tok.decode(list(gb.model.generate(torch.tensor([prompt]), 80, temperature=0.7, top_p=0.9, stop_ids=stop)))
        chat = None
        if CHAT_WEIGHTS.exists():
            from ...engine.lessons import load_model
            m = load_model(CHAT_WEIGHTS)
            torch.manual_seed(0)
            chat = gb.tok.decode(list(m.generate(torch.tensor([prompt]), 120, temperature=0.7, top_p=0.9, stop_ids=stop)))
        self.app.call_from_thread(self._compared, base, chat)

    def _compared(self, base, chat):
        self.cmp = (base, chat)
        self.draw_cmp()

    def draw_cmp(self):
        tr, view = self.app.tr, self.query_one("#cmp-view", Static)
        if not self.cmp:
            view.update(tr("loading"))
            return
        base, chat = self.cmp
        out = Text(tr("ct_base") + "\n", style="bold #f78c6b")
        out.append(self.rr(base.strip()) + "\n\n", style="#e8e8f0")
        out.append(tr("ct_chat") + "\n", style="bold #06d6a0")
        if chat is None:
            out.append(tr("ct_nochat"), style="italic #8a8fb0")
        else:
            out.append(self.rr(chat.strip()), style="#e8e8f0")
        view.update(out)

    # ── real SFT examples ────────────────────────────────────────────────────
    @work(thread=True, exclusive=True, group="data")
    def load_examples(self):
        path = config.SFT_DIR / "train.jsonl"
        if not path.exists():
            self.app.call_from_thread(self._examples, [])
            return
        by_source = {}
        with open(path, encoding="utf-8") as f:
            for i, line in enumerate(f):
                if i > 20000:
                    break
                ex = json.loads(line)
                by_source.setdefault(ex["source"], []).append(ex)
        picks = [random.choice(v) for v in by_source.values()]
        self.app.call_from_thread(self._examples, picks)

    def _examples(self, picks):
        self.examples = picks
        self.draw_example()

    def action_next_example(self):
        if self.examples:
            self.ex_i = (self.ex_i + 1) % len(self.examples)
            self.draw_example()

    def draw_example(self):
        tr, view = self.app.tr, self.query_one("#data-view", Static)
        if self.examples is None:
            view.update(tr("loading"))
            return
        if not self.examples:
            view.update(Text(tr("ct_nodata"), style="#c9cce0"))
            return
        ex = self.examples[self.ex_i]
        out = Text(f"[{ex['source']}]  {self.ex_i + 1}/{len(self.examples)}\n\n", style="bold #8ecae6")
        colours = {"system": "#cdb4db", "user": "#8ecae6", "assistant": "#06d6a0"}
        for m in ex["messages"]:
            out.append(f"{m['role']}: ", style=f"bold {colours[m['role']]}")
            out.append(self.rr(m["content"][:500]) + "\n\n", style="#e8e8f0")
        view.update(out)
