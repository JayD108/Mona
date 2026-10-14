"""Story mode (follow YOUR sentence through MONA, with the real build diary) and the badges screen."""
from rich.text import Text
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.screen import Screen
from textual.widgets import Input, Static

from .text import STAGES, register, stage_name
from .widgets import Avatar

register({
    "st_title": {"en": "Story mode: the journey of your sentence", "hi": "कहानी: आपके वाक्य का सफ़र", "hinglish": "Story mode: tumhare sentence ka safar"},
    "st_ask": {"en": "Type ONE sentence (any language). It will travel through MONA with you, chapter by chapter. Enter to start.",
               "hi": "एक वाक्य लिखिए (किसी भी भाषा में)। यह अध्याय-दर-अध्याय आपके साथ MONA के अंदर सफ़र करेगा। शुरू करने के लिए Enter।",
               "hinglish": "Ek sentence likho (kisi bhi bhasha mein). Yeh chapter-by-chapter tumhare saath MONA ke andar safar karega. Shuru karne ke liye Enter."},
    "st_chapter": {"en": "Chapter {i} of {n}", "hi": "अध्याय {i} / {n}", "hinglish": "Chapter {i} / {n}"},
    "st_diary": {"en": "📓 From MONA's real build diary", "hi": "📓 MONA की असली निर्माण डायरी से", "hinglish": "📓 MONA ki asli build diary se"},
    "st_go": {"en": "Enter: open this chapter's lab (with your sentence)   ·   Esc there: come back here for the next chapter",
              "hi": "Enter: इस अध्याय की लैब खोलें (आपके वाक्य के साथ)   ·   वहाँ Esc: अगले अध्याय के लिए यहाँ लौटें",
              "hinglish": "Enter: is chapter ki lab kholo (tumhare sentence ke saath)   ·   wahan Esc: agle chapter ke liye yahan lauto"},
    "st_end": {"en": "🎉 You followed one sentence all the way through a real language model: data, tokens, numbers, attention, "
                     "layers, a guess, training, chat tuning and evaluation. That's how every LLM works, from MONA to the "
                     "biggest ones. Press Esc to return home.",
               "hi": "🎉 आपने एक वाक्य को असली भाषा मॉडल के अंदर पूरे रास्ते देखा: डेटा, टोकन, संख्याएँ, अटेंशन, लेयर, अंदाज़ा, "
                     "ट्रेनिंग, चैट ट्यूनिंग और परीक्षा। हर LLM ऐसे ही काम करता है, MONA से लेकर सबसे बड़े तक। घर लौटने के लिए Esc।",
               "hinglish": "🎉 Tumne ek sentence ko asli language model ke andar poore raaste dekha: data, tokens, numbers, attention, "
                           "layers, guess, training, chat tuning aur evaluation. Har LLM aise hi kaam karta hai, MONA se lekar sabse "
                           "bade tak. Ghar lautne ke liye Esc."},
    "st_keys": {"en": "Enter open lab   ←/→ previous / next chapter   Esc home", "hi": "Enter लैब खोलें   ←/→ पिछला / अगला अध्याय   Esc घर",
                "hinglish": "Enter lab kholo   ←/→ pichhla / agla chapter   Esc ghar"},
    "bd_title": {"en": "Progress, badges & certificate", "hi": "प्रगति, बैज और प्रमाणपत्र", "hinglish": "Progress, badges aur certificate"},
    "bd_keys": {"en": "Esc back   F9 save the certificate", "hi": "Esc वापस   F9 प्रमाणपत्र सहेजें", "hinglish": "Esc wapas   F9 certificate save karo"},
    "cert_left": {"en": "🎓 Your certificate of completion unlocks after all 12 stages. {n} to go, {addr}!",
                  "hi": "🎓 आपका पूर्णता प्रमाणपत्र सभी 12 चरणों के बाद खुलेगा। {n} बाकी, {addr}!",
                  "hinglish": "🎓 Aapka completion certificate saare 12 stages ke baad khulega. {n} baaki, {addr}!"},
    "cert_head": {"en": "CERTIFICATE OF COMPLETION", "hi": "पूर्णता प्रमाणपत्र", "hinglish": "CERTIFICATE OF COMPLETION"},
    "cert_body": {"en": "This certifies that\n\n{who}\n\ntook a real language model apart and looked inside, stage by stage:\n"
                        "data, tokens, embeddings, attention, layers, sampling,\ntraining, chat tuning, evals, RAG and beyond.",
                  "hi": "प्रमाणित किया जाता है कि\n\n{who}\n\nने एक असली भाषा मॉडल को चरण-दर-चरण खोलकर अंदर से समझा:\n"
                        "डेटा, टोकन, एम्बेडिंग, अटेंशन, लेयर, सैंपलिंग,\nट्रेनिंग, चैट ट्यूनिंग, परीक्षा, RAG और आगे।",
                  "hinglish": "Yeh pramaanit kiya jaata hai ki\n\n{who}\n\nne ek asli language model ko andar se\n"
                              "stage-by-stage kholkar samjha: data, tokens, embeddings, attention, layers,\nsampling, training, chat tuning, "
                              "evals, RAG aur aage."},
    "cert_sign": {"en": "Signed: MONA (110,100,000 parameters)", "hi": "हस्ताक्षर: MONA (11,01,00,000 पैरामीटर)",
                  "hinglish": "Signed: MONA (110,100,000 parameters)"},
})

# chapter: (stage id, {lang: story}, {lang: diary fact})
CHAPTERS = [
    ("lm", {"en": "Before anything else: what IS a language model? It plays one game, forever: guess the next word.",
            "hi": "सबसे पहले: भाषा मॉडल है क्या? वह हमेशा एक ही खेल खेलता है: अगला शब्द अंदाज़ा लगाना।",
            "hinglish": "Sabse pehle: language model hai kya? Woh hamesha ek hi game khelta hai: agla word guess karna."},
     {"en": "MONA started at loss 10.55: pure guessing among 32,768 tokens. Hours later it was under 4.",
      "hi": "MONA 10.55 loss से शुरू हुई: 32,768 टोकनों में से बस तुक्का। कुछ घंटों में यह 4 से नीचे आ गया।",
      "hinglish": "MONA loss 10.55 se shuru hui: 32,768 tokens mein bas tukka. Kuch ghanton mein yeh 4 se neeche aa gaya."}),
    ("data", {"en": "Your sentence is new to MONA. Everything MONA knows came from what it read. Let's look at that reading pile.",
              "hi": "आपका वाक्य MONA के लिए नया है। MONA जो कुछ जानती है, वह उसके पढ़े हुए से आया। चलिए वह ढेर देखें।",
              "hinglish": "Tumhara sentence MONA ke liye naya hai. MONA jo kuch jaanti hai, woh uske padhe hue se aaya. Chalo woh dher dekhein."},
     {"en": "Our Hinglish data said \"ack prajaati haye\" instead of \"ek prajati hai\". We counted the words and fixed 70 of them.",
      "hi": "हमारे हिंग्लिश डेटा में \"ek prajati hai\" की जगह \"ack prajaati haye\" लिखा था। हमने शब्द गिने और 70 सुधारे।",
      "hinglish": "Hamare Hinglish data mein \"ek prajati hai\" ki jagah \"ack prajaati haye\" likha tha. Humne words gine aur 70 theek kiye."}),
    ("tokens", {"en": "Step one inside MONA: your sentence is cut into tokens, and each token becomes a number.",
                "hi": "MONA के अंदर पहला कदम: आपका वाक्य टोकनों में कटता है, और हर टोकन एक नंबर बनता है।",
                "hinglish": "MONA ke andar pehla step: tumhara sentence tokens mein katta hai, aur har token ek number banta hai."},
     {"en": "We trained the tokenizer on a balanced mix, so Hindi needs 1.33 tokens per word: even fewer than English (1.48).",
      "hi": "हमने tokenizer को संतुलित मिश्रण पर सिखाया, इसलिए हिंदी को प्रति शब्द 1.33 टोकन लगते हैं: अंग्रेज़ी (1.48) से भी कम।",
      "hinglish": "Humne tokenizer ko balanced mix par sikhaya, isliye Hindi ko har word par 1.33 tokens lagte hain: English (1.48) se bhi kam."}),
    ("embeddings", {"en": "Each token number picks a row of 768 numbers: MONA's idea of that word.",
                    "hi": "हर टोकन नंबर 768 संख्याओं की एक पंक्ति चुनता है: उस शब्द के बारे में MONA की समझ।",
                    "hinglish": "Har token number 768 numbers ki ek row chunta hai: us word ke baare mein MONA ki samajh."},
     {"en": "Nobody taught MONA meanings, yet \"king\" ended up next to prince, emperor and queen.",
      "hi": "MONA को किसी ने अर्थ नहीं सिखाए, फिर भी \"king\" prince, emperor और queen के पास पहुँच गया।",
      "hinglish": "MONA ko kisi ne meanings nahi sikhaye, phir bhi \"king\" prince, emperor aur queen ke paas pahunch gaya."}),
    ("attention", {"en": "Now the words talk to each other: every word looks back at the words before it.",
                   "hi": "अब शब्द एक-दूसरे से बात करते हैं: हर शब्द पीछे के शब्दों को देखता है।",
                   "hinglish": "Ab words ek-doosre se baat karte hain: har word peeche ke words ko dekhta hai."},
     {"en": "Within the first 0.1B tokens MONA grew a \"previous-word\" head all by itself.",
      "hi": "पहले 0.1 अरब टोकनों में ही MONA ने अपने-आप एक \"पिछला-शब्द\" हेड बना लिया।",
      "hinglish": "Pehle 0.1B tokens mein hi MONA ne apne-aap ek \"previous-word\" head bana liya."}),
    ("layers", {"en": "This happens 12 times, in 12 layers. Watch MONA's guess sharpen as your sentence climbs.",
                "hi": "यह 12 बार होता है, 12 लेयरों में। देखिए आपका वाक्य ऊपर चढ़ते हुए MONA का अंदाज़ा कैसे पैना होता है।",
                "hinglish": "Yeh 12 baar hota hai, 12 layers mein. Dekho tumhara sentence upar chadhte hue MONA ka guess kaise tez hota hai."},
     {"en": "Early in training, MONA's last layer changed its mind twice on the same sentence.",
      "hi": "ट्रेनिंग की शुरुआत में MONA की आख़िरी लेयर ने एक ही वाक्य पर दो बार राय बदली।",
      "hinglish": "Training ki shuruaat mein MONA ki last layer ne ek hi sentence par do baar mind badla."}),
    ("next", {"en": "Out comes a probability for every possible next token. Then MONA rolls the dice.",
              "hi": "निकलती है हर संभव अगले टोकन की संभावना। फिर MONA पासा फेंकती है।",
              "hinglish": "Nikalti hai har possible agle token ki probability. Phir MONA dice phenkti hai."},
     {"en": "At temperature 2.0 MONA wrote \"विलय का दूल mandatory empower teeth\": mixing languages mid-sentence.",
      "hi": "temperature 2.0 पर MONA ने लिखा \"विलय का दूल mandatory empower teeth\": वाक्य के बीच भाषाएँ मिलाती हुई।",
      "hinglish": "Temperature 2.0 par MONA ne likha \"विलय का दूल mandatory empower teeth\": sentence ke beech bhashayein milate hue."}),
    ("training", {"en": "How did MONA get its numbers right? By guessing billions of times, and learning from every mistake.",
                  "hi": "MONA की संख्याएँ सही कैसे हुईं? अरबों बार अंदाज़ा लगाकर, और हर गलती से सीखकर।",
                  "hinglish": "MONA ke numbers sahi kaise hue? Arabon baar guess karke, aur har galti se seekhkar."},
     {"en": "A 2-minute pilot run caught a bug that would have made a 3 AM crash unrecoverable. Always run a pilot.",
      "hi": "2 मिनट के pilot run ने एक बग पकड़ा जिससे रात 3 बजे का crash ठीक नहीं हो पाता। हमेशा pilot चलाइए।",
      "hinglish": "2 minute ke pilot run ne ek bug pakda jisse raat 3 baje ka crash theek nahi ho paata. Hamesha pilot chalao."}),
    ("chat", {"en": "A trained MONA still only continues text. To make it answer you, it needs chat tuning.",
              "hi": "प्रशिक्षित MONA भी केवल पाठ आगे बढ़ाती है। आपको जवाब देने के लिए उसे चैट ट्यूनिंग चाहिए।",
              "hinglish": "Trained MONA bhi sirf text aage badhati hai. Tumhe jawab dene ke liye use chat tuning chahiye."},
     {"en": "Asked \"What is photosynthesis?\", base MONA wrote \"…, cubs, videographers, etc.\" Chat tuning fixes that.",
      "hi": "\"What is photosynthesis?\" पूछने पर base MONA ने लिखा \"…, cubs, videographers, etc.\" चैट ट्यूनिंग इसे ठीक करती है।",
      "hinglish": "\"What is photosynthesis?\" poochhne par base MONA ne likha \"…, cubs, videographers, etc.\" Chat tuning ise theek karti hai."}),
    ("evals", {"en": "Last question: is MONA any good? Let's test it, and measure how surprised it is by your sentence.",
               "hi": "आख़िरी सवाल: क्या MONA अच्छी है? परीक्षा लेते हैं, और नापते हैं कि आपके वाक्य से वह कितनी हैरान है।",
               "hinglish": "Aakhri sawaal: kya MONA achhi hai? Test lete hain, aur naapte hain ki tumhare sentence se woh kitni hairaan hai."},
     {"en": "Early MONA scored 64% on our mini exam, where random guessing gets 25%.",
      "hi": "शुरुआती MONA ने हमारी छोटी परीक्षा में 64% पाए, जहाँ तुक्के से 25% आते।",
      "hinglish": "Shuruaati MONA ne hamare mini exam mein 64% laaye, jahan tukke se 25% aate."}),
]

BADGES = [  # name, stage, {lang: how to earn}
    ("Mind Reader", "lm", {"en": "Beat MONA at Human vs MONA", "hi": "इंसान बनाम MONA में MONA को हराइए", "hinglish": "Insaan vs MONA mein MONA ko harao"}),
    ("Data Curator", "data", {"en": "Agree with the cleaner on 75% of 8+ documents", "hi": "8+ दस्तावेज़ों में 75% पर cleaner से सहमत रहें",
                              "hinglish": "8+ documents mein 75% par cleaner se sahmat raho"}),
    ("Token Tamer", "tokens", {"en": "Make MONA cut one word into 6+ tokens", "hi": "MONA से एक शब्द के 6+ टोकन करवाइए",
                               "hinglish": "MONA se ek word ke 6+ tokens karwao"}),
    ("Word Mapper", "embeddings", {"en": "Odd one out: MONA agrees 3 times", "hi": "अलग कौन: MONA 3 बार सही", "hinglish": "Odd one out: MONA 3 baar sahi"}),
    ("Attention Detective", "attention", {"en": "Solve 3 attention mysteries", "hi": "अटेंशन की 3 पहेलियाँ सुलझाइए", "hinglish": "Attention ki 3 paheliyan suljhao"}),
    ("Temperature Tamer", "next", {"en": "Make MONA repeat itself AND go wild", "hi": "MONA से दोहराव भी और बेकाबूपन भी करवाइए",
                                   "hinglish": "MONA se repeat bhi aur wild bhi karwao"}),
    ("Exam Maker", "evals", {"en": "Write 3 exam questions for MONA", "hi": "MONA के लिए 3 प्रश्न लिखिए", "hinglish": "MONA ke liye 3 sawaal likho"}),
]


class StoryScreen(Screen):
    # Enter opens the chapter (when the sentence box has focus, Enter submits it instead)
    BINDINGS = [Binding("escape", "app.pop_screen", "home"), Binding("left", "move(-1)"), Binding("right", "move(1)"),
                Binding("enter", "open_chapter", "open")]

    def compose(self) -> ComposeResult:
        with Horizontal(classes="lab-head"):
            yield Avatar(id="avatar", classes="lab-avatar")
            yield Static(id="title", classes="lab-title")
        with Vertical():                           # not a scroll container: it would swallow ←/→ and Enter
            yield Static(id="ask", classes="explain")
            yield Input(id="sentence")
            yield Static(id="card", classes="panel")
        yield Static(id="keys", classes="keys")

    def on_mount(self):
        self.sentence = self.app.state.records.get("story_sentence", "")
        self.chapter = self.app.state.records.get("story_chapter", 0) if self.sentence else -1
        self.query_one("#sentence", Input).value = self.sentence
        self.refresh_texts()
        if self.chapter < 0:
            self.query_one("#sentence").focus()

    def refresh_texts(self):
        tr = self.app.tr
        self.query_one("#title", Static).update(tr("st_title"))
        self.query_one("#ask", Static).update(tr("st_ask"))
        self.query_one("#keys", Static).update(tr("st_keys"))
        self.draw()

    def on_input_submitted(self, event):
        if self.chapter < 0 or event.value != self.sentence:
            self.sentence, self.chapter = event.value.strip(), 0
            self.save()
            self.draw()
            self.focus_card()
        else:
            self.open_chapter()

    def focus_card(self):
        # keys (Enter/←/→) now drive the story; run after Textual restores focus on screen resume
        self.call_after_refresh(self.set_focus, None)

    def action_open_chapter(self):
        if 0 <= self.chapter < len(CHAPTERS):
            self.open_chapter()

    def action_move(self, d: int):
        if self.chapter >= 0:
            self.chapter = min(max(self.chapter + d, 0), len(CHAPTERS))
            self.save()
            self.draw()

    def save(self):
        self.app.state.records["story_sentence"] = self.sentence
        self.app.state.records["story_chapter"] = self.chapter
        self.app.state.save()

    def open_chapter(self):
        from .screens import open_lab
        stage = CHAPTERS[self.chapter][0]
        lab = open_lab(stage)
        if lab:
            lab.seed = self.sentence             # the lab starts with YOUR sentence
            self.waiting = True
            self.app.push_screen(lab)

    def on_screen_resume(self):
        """Coming back from this chapter's lab moves the story on to the next chapter."""
        if getattr(self, "waiting", False):
            self.waiting = False
            self.chapter += 1
            self.save()
        self.draw()
        self.focus_card()

    def draw(self):
        tr, lang = self.app.tr, self.app.state.lang
        roman = self.app.roman if self.app.state.romanize else (lambda s: s)
        card = self.query_one("#card", Static)
        if self.chapter < 0:
            card.update("")
            return
        out = Text()
        if self.chapter >= len(CHAPTERS):
            out.append(tr("st_end"), style="bold #f9e2af")
            card.update(out)
            self.app.state.complete("story", badge="Storyteller")
            return
        stage, story, diary = CHAPTERS[self.chapter]
        name = next(stage_name(s, lang) for s in STAGES if s[0] == stage)
        out.append(tr("st_chapter", i=self.chapter + 1, n=len(CHAPTERS)) + "  ·  ", style="#6c7086")
        out.append(roman(name) + "\n\n", style="bold #f9e2af")
        out.append("“" + roman(self.sentence) + "”\n\n", style="italic #89dceb")
        out.append(roman(story.get(lang, story["en"])) + "\n\n", style="#cdd6f4")
        out.append(tr("st_diary") + "\n", style="bold #cba6f7")
        out.append(roman(diary.get(lang, diary["en"])) + "\n\n", style="#bac2de")
        out.append("▶ " + tr("st_go"), style="bold #a6e3a1")
        bar = "".join("●" if i < self.chapter else ("◉" if i == self.chapter else "○") for i in range(len(CHAPTERS)))
        out.append("\n\n" + bar, style="#f9e2af")
        card.update(out)


class BadgesScreen(Screen):
    BINDINGS = [Binding("escape", "app.pop_screen", "back")]

    def compose(self) -> ComposeResult:
        with Horizontal(classes="lab-head"):
            yield Avatar(id="avatar", classes="lab-avatar")
            yield Static(id="title", classes="lab-title")
        with VerticalScroll():
            yield Static(id="list", classes="panel")
        yield Static(id="keys", classes="keys")

    def on_mount(self):
        self.refresh_texts()

    def refresh_texts(self):
        tr, st, lang = self.app.tr, self.app.state, self.app.state.lang
        roman = self.app.roman if st.romanize else (lambda s: s)
        self.query_one("#title", Static).update(tr("bd_title"))
        self.query_one("#keys", Static).update(tr("bd_keys"))
        out = Text()
        all_badges = BADGES + [
            ("Storyteller", "story", {"en": "Finish Story mode", "hi": "कहानी पूरी कीजिए", "hinglish": "Story mode poora karo"}),
            ("Run Rescuer", "incidents", {"en": "Handle 5 training failures like an ML engineer", "hi": "5 ट्रेनिंग गड़बड़ियाँ ML इंजीनियर की तरह सँभालिए",
                                          "hinglish": "5 training failures ML engineer ki tarah sambhalo"}),
            ("Model Detective", "mysteries", {"en": "Solve all 5 Model mysteries", "hi": "मॉडल की सभी 5 पहेलियाँ सुलझाइए",
                                              "hinglish": "Saari 5 Model mysteries suljhao"}),
            ("Model Maker", "course", {"en": "Train your own model (all 6 steps)", "hi": "अपना मॉडल ट्रेन कीजिए (सभी 6 कदम)",
                                       "hinglish": "Apna model train karo (saare 6 steps)"})]
        for name, stage, how in all_badges:
            have = name in st.badges
            out.append("🏅 " if have else "🔒 ", style="")
            out.append(f"{name:22s}", style="bold #f9e2af" if have else "#6c7086")
            out.append(roman(how.get(lang, how["en"])) + "\n", style="#cdd6f4" if have else "#9399b2")
        out.append(f"\n{len(st.badges)}/{len(all_badges)}\n\n", style="bold #a6e3a1")
        left = len([s for s in STAGES if s[0] not in st.completed])
        if left:
            out.append(tr("cert_left", n=left), style="bold #89dceb")
        else:
            out.append_text(self.certificate())
        self.query_one("#list", Static).update(out)

    def certificate(self):
        """A framed certificate with the learner's name; F9 saves it."""
        import datetime as dt
        from rich.cells import cell_len
        tr = self.app.tr
        who = self.app.state.user_name or self.app.addr() or "MONA learner"      # a certificate carries the real name if known
        lines = ["", tr("cert_head"), ""] + tr("cert_body", who=who).split("\n") + ["", tr("cert_sign"),
                                                                                   f"{dt.date.today():%d %B %Y}", ""]
        width = max(cell_len(line) for line in lines) + 6
        out = Text()
        out.append("╔" + "═" * width + "╗\n", style="#f9e2af")
        for line in lines:
            pad = width - cell_len(line)
            out.append("║", style="#f9e2af")
            out.append(" " * (pad // 2) + line + " " * (pad - pad // 2),
                       style="bold #f9e2af" if line in (tr("cert_head"), who) else "#cdd6f4")
            out.append("║\n", style="#f9e2af")
        out.append("╚" + "═" * width + "╝", style="#f9e2af")
        return out

    def export(self):
        left = len([s for s in STAGES if s[0] not in self.app.state.completed])
        text = self.app.tr("cert_left", n=left) if left else self.certificate().plain
        return ("MONA certificate of completion", "```\n" + text + "\n```",
                "# Your MONA certificate: open the .md or .svg saved next to this file.\n"
                "print(open(__file__[:-3] + '.md', encoding='utf-8').read())\n")
