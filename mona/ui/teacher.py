"""Teacher mode: a 45-minute lesson plan, discussion questions and a printable quiz for every stage.

Teacher text is in English and Hindi (Hinglish users see English). Quizzes add live questions computed
from MONA itself, so every worksheet uses real numbers.
"""
import datetime as dt
import random
from pathlib import Path

from rich.text import Text
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, VerticalScroll
from textual.screen import Screen
from textual.widgets import OptionList, Static
from textual.widgets.option_list import Option

from .text import STAGES, register, stage_name
from .widgets import Avatar

register({
    "te_title": {"en": "Teacher mode: lesson plans and quizzes", "hi": "शिक्षक मोड: पाठ योजना और प्रश्नोत्तरी"},
    "te_plan": {"en": "45-minute lesson plan", "hi": "45 मिनट की पाठ योजना"},
    "te_obj": {"en": "Goal", "hi": "लक्ष्य"},
    "te_disc": {"en": "Discussion questions", "hi": "चर्चा के प्रश्न"},
    "te_quiz": {"en": "Quiz preview (Q saves a printable worksheet with answer key)",
                "hi": "प्रश्नोत्तरी (Q दबाकर उत्तर-कुंजी सहित छापने योग्य वर्कशीट सहेजें)"},
    "te_saved": {"en": "Worksheet saved: {p}", "hi": "वर्कशीट सहेजी गई: {p}"},
    "te_keys": {"en": "↑↓ stage   Q save worksheet (.md)   Esc back", "hi": "↑↓ चरण   Q वर्कशीट सहेजें (.md)   Esc वापस"},
})

TIMELINE = {"en": ["0-5 min · Hook: run the lab on the projector, ask the class to guess first",
                   "5-20 min · Explore: students do the lab in pairs ({activity})",
                   "20-30 min · Discuss: the questions below",
                   "30-40 min · Quiz: the worksheet (Q)",
                   "40-45 min · Wrap-up: one sentence each, \"today I learned that an LLM…\""],
            "hi": ["0-5 मिनट · शुरुआत: प्रोजेक्टर पर लैब चलाइए, कक्षा से पहले अंदाज़ा लगवाइए",
                   "5-20 मिनट · खोज: छात्र जोड़ियों में लैब करें ({activity})",
                   "20-30 मिनट · चर्चा: नीचे दिए प्रश्न",
                   "30-40 मिनट · प्रश्नोत्तरी: वर्कशीट (Q)",
                   "40-45 मिनट · समापन: हर छात्र एक वाक्य, \"आज मैंने सीखा कि LLM…\""]}

# stage: {goal, activity, discussion[2], quiz[(question, options, answer index)]} in en / hi
LESSONS = {
    "lm": {"en": {"goal": "Understand that a language model only predicts the next token, again and again.",
                  "activity": "Human vs MONA, 5 rounds",
                  "disc": ["If an LLM only guesses the next word, how can it write a whole essay?",
                           "Why is guessing the next word hard even for humans?"],
                  "quiz": [("A language model's one job is to…", ["predict the next token", "search the internet", "store facts in a table", "translate only"], 0),
                           ("Writing a long answer is done by…", ["repeating next-token prediction", "copying a document", "a separate grammar module", "magic"], 0)]},
           "hi": {"goal": "समझना कि भाषा मॉडल बस बार-बार अगला टोकन बताता है।", "activity": "इंसान बनाम MONA, 5 राउंड",
                  "disc": ["अगर LLM बस अगला शब्द बताता है, तो पूरा निबंध कैसे लिख लेता है?", "अगला शब्द बताना इंसानों के लिए भी मुश्किल क्यों है?"],
                  "quiz": [("भाषा मॉडल का एकमात्र काम है…", ["अगला टोकन बताना", "इंटरनेट खोजना", "तालिका में तथ्य रखना", "केवल अनुवाद"], 0),
                           ("लंबा जवाब कैसे लिखा जाता है?", ["अगले टोकन के अनुमान को दोहराकर", "कोई दस्तावेज़ कॉपी करके", "अलग व्याकरण मॉड्यूल से", "जादू से"], 0)]}},
    "data": {"en": {"goal": "See that a model is only as good as the text it learns from.", "activity": "Be the curator: 10 documents",
                    "disc": ["What could go wrong if a model learns from messy or biased text?", "Why did we repeat Awadhi only ~4 times?"],
                    "quiz": [("Why remove very short documents?", ["too little to learn from", "they are always wrong", "they are in English", "to save electricity"], 0),
                             ("Showing the same small text too many times makes a model…", ["memorise instead of learn", "faster", "multilingual", "smaller"], 0)]},
             "hi": {"goal": "देखना कि मॉडल उतना ही अच्छा है जितना उसका पढ़ा पाठ।", "activity": "छँटाई कीजिए: 10 दस्तावेज़",
                    "disc": ["गंदे या पक्षपाती पाठ से सीखने पर क्या गड़बड़ हो सकती है?", "अवधी को केवल ~4 बार ही क्यों दोहराया?"],
                    "quiz": [("बहुत छोटे दस्तावेज़ क्यों हटाते हैं?", ["सीखने लायक कम है", "वे हमेशा गलत होते हैं", "वे अंग्रेज़ी में हैं", "बिजली बचाने को"], 0),
                             ("एक ही छोटा पाठ बहुत बार दिखाने से मॉडल…", ["सीखने के बजाय रटता है", "तेज़ होता है", "बहुभाषी बनता है", "छोटा होता है"], 0)]}},
    "tokens": {"en": {"goal": "Understand tokens, and why some languages cost more tokens than others.", "activity": "Peek + Language race",
                      "disc": ["Why does a tokenizer cut rare words into more pieces?", "Is it fair if Hindi needs more tokens than English? Why does it matter?"],
                      "quiz": [("A token is…", ["a piece of text the model knows", "always one whole word", "always one letter", "a punctuation mark"], 0),
                               ("BPE builds its vocabulary by…", ["merging the most frequent pairs", "using a dictionary", "random choice", "counting sentences"], 0)]},
               "hi": {"goal": "टोकन समझना, और कुछ भाषाओं में ज़्यादा टोकन क्यों लगते हैं।", "activity": "झाँकें + भाषा दौड़",
                      "disc": ["tokenizer दुर्लभ शब्दों को ज़्यादा टुकड़ों में क्यों काटता है?", "अगर हिंदी में अंग्रेज़ी से ज़्यादा टोकन लगें तो क्या यह उचित है? क्यों ज़रूरी है?"],
                      "quiz": [("टोकन है…", ["पाठ का टुकड़ा जो मॉडल जानता है", "हमेशा पूरा शब्द", "हमेशा एक अक्षर", "विराम चिह्न"], 0),
                               ("BPE अपनी शब्दावली कैसे बनाता है?", ["सबसे आम जोड़ों को मिलाकर", "शब्दकोश से", "यादृच्छिक", "वाक्य गिनकर"], 0)]}},
    "embeddings": {"en": {"goal": "See words as lists of numbers, where similar words are close.", "activity": "Neighbours + Word map",
                          "disc": ["Nobody told MONA what words mean. How did similar words end up close?", "Why might Hindi and English words sit apart?"],
                          "quiz": [("An embedding is…", ["a list of numbers for a token", "a picture", "a dictionary entry", "a grammar rule"], 0),
                                   ("Words that appear in similar contexts get…", ["similar embeddings", "deleted", "longer", "capital letters"], 0)]},
                   "hi": {"goal": "शब्दों को संख्याओं की सूची के रूप में देखना, जहाँ मिलते-जुलते शब्द पास हों।", "activity": "पड़ोसी + शब्द नक्शा",
                          "disc": ["MONA को किसी ने अर्थ नहीं बताए। मिलते-जुलते शब्द पास कैसे आ गए?", "हिंदी और अंग्रेज़ी शब्द अलग क्यों बैठ सकते हैं?"],
                          "quiz": [("एम्बेडिंग है…", ["टोकन के लिए संख्याओं की सूची", "एक चित्र", "शब्दकोश प्रविष्टि", "व्याकरण नियम"], 0),
                                   ("एक जैसे संदर्भ में आने वाले शब्दों को मिलता है…", ["मिलती-जुलती एम्बेडिंग", "हटा दिया जाता है", "लंबा रूप", "बड़े अक्षर"], 0)]}},
    "attention": {"en": {"goal": "See how each word gathers information from earlier words.", "activity": "Heatmaps + Attention detective",
                         "disc": ["Why can a word only look at EARLIER words?", "What might a 'previous-word head' be useful for?"],
                         "quiz": [("Attention lets a token…", ["use information from earlier tokens", "see future tokens", "change its spelling", "skip layers"], 0),
                                  ("MONA has 12 layers × 12 heads = …", ["144 attention patterns", "24", "12", "1"], 0)]},
                  "hi": {"goal": "देखना कि हर शब्द पिछले शब्दों से जानकारी कैसे लेता है।", "activity": "हीटमैप + अटेंशन जासूस",
                         "disc": ["एक शब्द केवल पिछले शब्दों को ही क्यों देख सकता है?", "'पिछला-शब्द हेड' किस काम का हो सकता है?"],
                         "quiz": [("Attention से टोकन…", ["पिछले टोकनों की जानकारी लेता है", "आगे के टोकन देखता है", "वर्तनी बदलता है", "लेयर छोड़ता है"], 0),
                                  ("MONA में 12 लेयर × 12 हेड = …", ["144 पैटर्न", "24", "12", "1"], 0)]}},
    "layers": {"en": {"goal": "See a prediction sharpen as it passes through the layers.", "activity": "Logit lens on two sentences",
                      "disc": ["Why do early layers guess common words like 'the'?", "What changes between layer 1 and layer 12?"],
                      "quiz": [("The logit lens shows…", ["the guess after each layer", "the training data", "the tokenizer", "the GPU temperature"], 0)]},
               "hi": {"goal": "देखना कि अनुमान लेयर दर लेयर कैसे पैना होता है।", "activity": "दो वाक्यों पर logit lens",
                      "disc": ["शुरुआती लेयर 'the' जैसे आम शब्द क्यों बताती हैं?", "लेयर 1 और 12 के बीच क्या बदलता है?"],
                      "quiz": [("Logit lens दिखाता है…", ["हर लेयर के बाद का अनुमान", "ट्रेनिंग डेटा", "tokenizer", "GPU तापमान"], 0)]}},
    "next": {"en": {"goal": "Understand probabilities and how temperature, top-k and top-p shape the output.", "activity": "Both temperature challenges",
                    "disc": ["When would you want low temperature? When high?", "Why does very high temperature mix languages?"],
                    "quiz": [("Lower temperature makes output…", ["safer and more repetitive", "more random", "longer", "multilingual"], 0),
                             ("Top-p keeps…", ["the smallest set of tokens adding up to p", "exactly p tokens", "the least likely tokens", "only punctuation"], 0)]},
             "hi": {"goal": "संभावनाएँ समझना, और temperature, top-k, top-p आउटपुट कैसे बदलते हैं।", "activity": "दोनों temperature चुनौतियाँ",
                    "disc": ["कम temperature कब चाहिए? ज़्यादा कब?", "बहुत ज़्यादा temperature भाषाएँ क्यों मिला देता है?"],
                    "quiz": [("कम temperature से आउटपुट…", ["सुरक्षित और दोहराव वाला", "ज़्यादा यादृच्छिक", "लंबा", "बहुभाषी"], 0),
                             ("Top-p रखता है…", ["सबसे छोटा समूह जिसका जोड़ p हो", "ठीक p टोकन", "सबसे कम संभावित टोकन", "केवल विराम चिह्न"], 0)]}},
    "training": {"en": {"goal": "Understand training as guessing, measuring the error (loss) and adjusting, billions of times.", "activity": "Time machine",
                        "disc": ["Why does the loss fall fast at first, then slowly?", "What is the difference between training loss and held-out loss?"],
                        "quiz": [("Loss measures…", ["how wrong the guesses are", "model size", "the number of layers", "speed"], 0),
                                 ("Held-out text is…", ["text the model never trained on", "the training data", "the tokenizer", "a GPU setting"], 0)]},
                 "hi": {"goal": "ट्रेनिंग को समझना: अंदाज़ा, गलती नापना (loss) और सुधारना, अरबों बार।", "activity": "टाइम मशीन",
                        "disc": ["loss शुरू में तेज़ी से, फिर धीरे क्यों घटता है?", "ट्रेनिंग loss और held-out loss में क्या फ़र्क़ है?"],
                        "quiz": [("Loss नापता है…", ["अनुमान कितने गलत हैं", "मॉडल का आकार", "लेयरों की संख्या", "रफ़्तार"], 0),
                                 ("Held-out पाठ है…", ["जिस पर मॉडल ने ट्रेनिंग नहीं की", "ट्रेनिंग डेटा", "tokenizer", "GPU सेटिंग"], 0)]}},
    "chat": {"en": {"goal": "Understand how chat tuning turns a text-continuer into an assistant.", "activity": "Template + Base vs Chat",
                    "disc": ["Why grade the model only on the answer, not the question?", "What does a base model do with a question?"],
                    "quiz": [("Loss masking means…", ["only the answer tokens count", "the model can't see the question", "hiding the loss", "removing tokens"], 0)]},
             "hi": {"goal": "समझना कि चैट ट्यूनिंग पाठ आगे बढ़ाने वाले को सहायक कैसे बनाती है।", "activity": "ढाँचा + Base बनाम Chat",
                    "disc": ["मॉडल को केवल उत्तर पर ही अंक क्यों, प्रश्न पर क्यों नहीं?", "base मॉडल किसी प्रश्न के साथ क्या करता है?"],
                    "quiz": [("Loss masking का अर्थ है…", ["केवल उत्तर के टोकन गिने जाते हैं", "मॉडल प्रश्न नहीं देख सकता", "loss छिपाना", "टोकन हटाना"], 0)]}},
    "evals": {"en": {"goal": "Learn how language models are tested, and the limits of tests.", "activity": "Mini exam + make your own",
                     "disc": ["Why compare with random guessing?", "Can a model pass a test without understanding?"],
                     "quiz": [("With 4 options, random guessing scores about…", ["25%", "50%", "4%", "100%"], 0),
                              ("Bits per byte: lower means…", ["the model finds the text more natural", "the text is shorter", "more bytes", "a bigger model"], 0)]},
              "hi": {"goal": "सीखना कि भाषा मॉडल की परीक्षा कैसे होती है, और परीक्षा की सीमाएँ।", "activity": "छोटी परीक्षा + अपनी परीक्षा",
                     "disc": ["तुक्के से तुलना क्यों?", "क्या कोई मॉडल बिना समझे परीक्षा पास कर सकता है?"],
                     "quiz": [("4 विकल्पों में तुक्के से लगभग…", ["25%", "50%", "4%", "100%"], 0),
                              ("Bits per byte कम होने का अर्थ…", ["मॉडल को पाठ ज़्यादा स्वाभाविक लगा", "पाठ छोटा है", "ज़्यादा बाइट", "बड़ा मॉडल"], 0)]}},
    "rag": {"en": {"goal": "Understand retrieval: answering from a library instead of memory.", "activity": "With vs without the library; add your own text",
                   "disc": ["Why does RAG reduce made-up answers?", "What happens if the library doesn't have the answer?"],
                   "quiz": [("RAG stands for…", ["Retrieval-Augmented Generation", "Random Answer Generator", "Rapid AI Graph", "Read And Guess"], 0)]},
            "hi": {"goal": "Retrieval समझना: याददाश्त के बजाय पुस्तकालय से जवाब।", "activity": "पुस्तकालय के साथ और बिना; अपना पाठ जोड़ें",
                   "disc": ["RAG से गढ़े हुए जवाब कम क्यों होते हैं?", "अगर पुस्तकालय में जवाब न हो तो क्या होगा?"],
                   "quiz": [("RAG का पूरा नाम…", ["Retrieval-Augmented Generation", "Random Answer Generator", "Rapid AI Graph", "Read And Guess"], 0)]}},
    "beyond": {"en": {"goal": "See practical tricks: smaller models (quantization), tools, and speed (KV-cache).", "activity": "All three modes",
                      "disc": ["Why can a 4-bit model be almost as good as a 32-bit one?", "Why should a language model use a calculator?"],
                      "quiz": [("Quantization makes a model…", ["smaller", "smarter", "multilingual", "slower to download"], 0),
                               ("The KV-cache makes generation faster by…", ["remembering earlier keys and values", "skipping layers", "using fewer tokens", "a faster GPU"], 0)]},
               "hi": {"goal": "व्यावहारिक तरकीबें: छोटे मॉडल (quantization), औज़ार, और रफ़्तार (KV-cache)।", "activity": "तीनों मोड",
                      "disc": ["4-bit मॉडल लगभग 32-bit जितना अच्छा कैसे हो सकता है?", "भाषा मॉडल को कैलकुलेटर क्यों इस्तेमाल करना चाहिए?"],
                      "quiz": [("Quantization से मॉडल…", ["छोटा होता है", "ज़्यादा समझदार", "बहुभाषी", "धीमे डाउनलोड"], 0),
                               ("KV-cache से generation तेज़ होता है क्योंकि…", ["पिछले keys और values याद रहते हैं", "लेयर छूटती हैं", "कम टोकन", "तेज़ GPU"], 0)]}},
}


def live_questions(app, stage, lang):
    """Questions computed from MONA itself, so worksheets contain real numbers."""
    tok = app.tokenizer
    if stage == "tokens":
        word = random.choice(["भारत", "unbelievable", "तुलसीदास", "computer", "mujhe"])
        n = len(tok.encode(" " + word).ids)
        q = (f"How many tokens does MONA use for “{word}” (mid-sentence)?" if lang == "en"
             else f"MONA “{word}” (वाक्य के बीच) के लिए कितने टोकन लेती है?")
        opts = sorted({n, n + 1, max(1, n - 1), n + 2})
        return [(q, [str(o) for o in opts], opts.index(n))]
    if stage == "training":
        from ..engine.lessons import training_curves
        _, evals = training_curves()
        if evals:
            first, last = float(evals[0]["english"]), float(evals[-1]["english"])
            q = (f"MONA's English held-out loss went from {first:.2f} to …" if lang == "en"
                 else f"MONA का अंग्रेज़ी held-out loss {first:.2f} से घटकर हुआ…")
            opts = [f"{last:.2f}", f"{first + 1:.2f}", f"{first:.2f}", "0.00"]
            return [(q, opts, 0)]
    return []


class TeacherScreen(Screen):
    BINDINGS = [Binding("escape", "app.pop_screen", "back"), Binding("q", "save", "worksheet")]

    def compose(self) -> ComposeResult:
        with Horizontal(classes="lab-head"):
            yield Avatar(id="avatar", classes="lab-avatar")
            yield Static(id="title", classes="lab-title")
        with Horizontal(id="te-cols"):
            yield OptionList(id="te-stages")
            with VerticalScroll(id="te-right"):
                yield Static(id="te-plan", classes="panel")
        yield Static(id="keys", classes="keys")

    def on_mount(self):
        self.stage = "tokens"
        self.refresh_texts()
        self.query_one("#te-stages").focus()

    @property
    def lang(self):
        return "hi" if self.app.state.lang == "hi" else "en"

    def refresh_texts(self):
        tr = self.app.tr
        self.query_one("#title", Static).update(tr("te_title"))
        self.query_one("#keys", Static).update(tr("te_keys"))
        ol = self.query_one("#te-stages", OptionList)
        ol.clear_options()
        for i, s in enumerate(STAGES):
            ol.add_option(Option(f"{i:>2}  {stage_name(s, self.app.state.lang)}", id=s[0]))
        ol.highlighted = [s[0] for s in STAGES].index(self.stage)
        self.draw()

    def on_option_list_option_highlighted(self, event):
        self.stage = event.option.id
        self.draw()

    def lesson(self):
        return LESSONS[self.stage][self.lang]

    def draw(self):
        tr, L = self.app.tr, self.lesson()
        out = Text(f"{tr('te_obj')}: ", style="bold #ffd166")
        out.append(L["goal"] + "\n\n", style="#e8e8f0")
        out.append(tr("te_plan") + "\n", style="bold #8ecae6")
        for line in TIMELINE[self.lang]:
            out.append("  • " + line.format(activity=L["activity"]) + "\n", style="#c9cce0")
        out.append("\n" + tr("te_disc") + "\n", style="bold #8ecae6")
        for q in L["disc"]:
            out.append(f"  ? {q}\n", style="#c9cce0")
        out.append("\n" + tr("te_quiz") + "\n", style="bold #8ecae6")
        for n, (q, opts, ans) in enumerate(L["quiz"] + live_questions(self.app, self.stage, self.lang), 1):
            out.append(f"  {n}. {q}\n", style="#e8e8f0")
            out.append("     " + "   ".join(f"{'abcd'[i]}) {o}" for i, o in enumerate(opts)) + "\n", style="#8a8fb0")
        self.query_one("#te-plan", Static).update(out)

    def action_save(self):
        L = self.lesson()
        name = next(stage_name(s, self.app.state.lang) for s in STAGES if s[0] == self.stage)
        questions = []
        for q, opts, ans in L["quiz"] + live_questions(self.app, self.stage, self.lang):
            order = list(range(len(opts)))
            random.shuffle(order)                                   # shuffle options so the answer isn't always (a)
            questions.append((q, [opts[i] for i in order], order.index(ans)))
        md = [f"# MONA worksheet: {name}", "", f"**{self.app.tr('te_obj')}:** {L['goal']}", "",
              "Name: ______________________   Date: ____________", ""]
        for n, (q, opts, _) in enumerate(questions, 1):
            md += [f"{n}. {q}", ""] + [f"   {'abcd'[i]}) {o}" for i, o in enumerate(opts)] + [""]
        md += ["## " + self.app.tr("te_disc"), ""] + [f"- {q}" for q in L["disc"]] + ["", "---", "", "## Answer key", ""]
        md += [f"{n}. {'abcd'[ans]}) {opts[ans]}" for n, (q, opts, ans) in enumerate(questions, 1)]
        out_dir = Path.home() / "mona_exports"
        out_dir.mkdir(exist_ok=True)
        path = out_dir / f"worksheet_{self.stage}_{dt.datetime.now():%Y%m%d_%H%M%S}.md"
        path.write_text("\n".join(md) + "\n", encoding="utf-8")
        self.app.notify(self.app.tr("te_saved", p=str(path)), timeout=6)
