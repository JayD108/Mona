"""The screens of the MONA app: display check, and home (a 4-track learning path + "Explore further")."""
import datetime as dt

from rich.text import Text
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual import work
from textual.screen import Screen
from textual.widgets import Button, OptionList, Static
from textual.widgets.option_list import Option

from . import brain
from .text import READY, STAGES, register, stage_name
from .welcome import greeting_key
from .widgets import Avatar

# The learning path: the 12 stages in four tracks.  (track title en, hi, hinglish, [stage ids])
TRACKS = [
    (("① FOUNDATIONS · how text becomes numbers", "① नींव · पाठ संख्या कैसे बनता है", "① FOUNDATIONS · text numbers kaise banta hai"),
     ["lm", "data", "tokens", "embeddings"]),
    (("② INSIDE THE MODEL · how it thinks", "② मॉडल के अंदर · यह कैसे सोचता है", "② MODEL KE ANDAR · yeh kaise sochta hai"),
     ["attention", "layers", "next"]),
    (("③ LEARNING · how it got good", "③ सीखना · यह अच्छा कैसे बना", "③ LEARNING · yeh achha kaise bana"),
     ["training", "chat", "evals"]),
    (("④ BEYOND · using and shrinking models", "④ आगे · मॉडल का इस्तेमाल और छोटा करना", "④ AAGE · models use karna aur chhota karna"),
     ["rag", "beyond"]),
]

# Explore further: hands-on work beyond the 12 stages.  (id or None for a heading, key, en, hi, hinglish)
EXPLORE = [
    (None, "", "💬 TALK AND WATCH", "💬 TALK AND WATCH", "💬 TALK AND WATCH"),
    ("talk", "K", "Talk with MONA", "Talk with MONA", "Talk with MONA"),
    ("zoom", "Z", "Inside MONA: model to neuron", "Inside MONA: model to neuron", "Inside MONA: model to neuron"),
    ("words", "W", "Your words, step by step", "Your words, step by step", "Your words, step by step"),
    (None, "", "🔍 INVESTIGATE", "🔍 जाँच", "🔍 INVESTIGATE"),
    ("mysteries", "M", "Model mysteries: debug MONA", "मॉडल की पहेलियाँ: MONA को डीबग कीजिए", "Model mysteries: MONA ko debug karo"),
    ("incidents", "I", "Training failures: what goes wrong", "ट्रेनिंग की गड़बड़ियाँ: क्या बिगड़ता है", "Training failures: kya bigadta hai"),
    (None, "", "🛠  BUILD", "🛠  बनाइए", "🛠  BUILD"),
    ("course", "G", "Train a model yourself", "ख़ुद एक मॉडल ट्रेन कीजिए", "Khud ek model train karo"),
    ("journey", "J", "How MONA was trained (real logs)", "MONA कैसे ट्रेन हुई (असली लॉग)", "MONA kaise train hui (asli logs)"),
    (None, "", "📈 SCALE", "📈 पैमाना", "📈 SCALE"),
    ("budget", "P", "Scaling laws explorer", "स्केलिंग नियम: खोजिए", "Scaling laws explorer"),
    ("tour", "O", "How AI labs build models", "AI लैब मॉडल कैसे बनाती हैं", "AI labs models kaise banati hain"),
    ("compare", "C", "MONA vs a big model", "MONA बनाम बड़ा मॉडल", "MONA vs bada model"),
    (None, "", "🎒 MORE", "🎒 और", "🎒 MORE"),
    ("story", "S", "Follow one sentence through MONA", "एक वाक्य का MONA में सफ़र", "Ek sentence ka MONA mein safar"),
    ("teacher", "T", "Teacher mode: lessons & quizzes", "शिक्षक मोड: पाठ और क्विज़", "Teacher mode: lessons aur quiz"),
    ("badges", "B", "Progress & certificate", "प्रगति और प्रमाणपत्र", "Progress aur certificate"),
]

# The suggested order for "Next up": stages interleaved with hands-on work at the right moments.
PATH = ["zoom", "lm", "data", "tokens", "embeddings", "attention", "layers", "next", "course", "training", "chat", "evals",
        "mysteries", "rag", "beyond", "budget"]
PATH_NAMES = {item[0]: item[2:] for item in EXPLORE if item[0]}

# One "did you know?" per day on the home screen: small true facts that make people curious.
MEMOS = [
    ("MONA has 110 million numbers inside. GPT-3 has 175 billion: 1,600 times more.",
     "MONA के अंदर 11 करोड़ संख्याएँ हैं। GPT-3 में 17,500 करोड़: 1,600 गुना ज़्यादा।",
     "MONA ke andar 11 crore numbers hain. GPT-3 mein 17,500 crore: 1,600 guna zyada."),
    ("MONA read 2.5 billion tokens. Reading one book a day, a person would need about 30,000 years.",
     "MONA ने 2.5 अरब टोकन पढ़े। रोज़ एक किताब पढ़ें तो इंसान को लगभग 30,000 साल लगेंगे।",
     "MONA ne 2.5 billion tokens padhe. Roz ek kitaab padho to insaan ko lagbhag 30,000 saal lagenge."),
    ("A model never sees letters, only numbers. 'नमस्ते' is just a few token numbers to MONA.",
     "मॉडल अक्षर कभी नहीं देखता, सिर्फ़ संख्याएँ। MONA के लिए 'नमस्ते' बस कुछ टोकन नंबर है।",
     "Model letters kabhi nahi dekhta, sirf numbers. MONA ke liye 'नमस्ते' bas kuch token numbers hai."),
    ("Training MONA took about 19 hours on one laptop. Frontier models use thousands of GPUs for months.",
     "MONA की ट्रेनिंग एक लैपटॉप पर लगभग 30 घंटे चली। बड़े मॉडल हज़ारों GPU पर महीनों चलते हैं।",
     "MONA ki training ek laptop par lagbhag 30 ghante chali. Bade models hazaron GPUs par mahino chalte hain."),
    ("Chat models are first trained to continue text. Only then are they taught to answer like an assistant.",
     "चैट मॉडल पहले सिर्फ़ पाठ आगे बढ़ाना सीखते हैं। उसके बाद ही उन्हें सहायक की तरह जवाब देना सिखाया जाता है।",
     "Chat models pehle sirf text aage badhana seekhte hain. Uske baad hi unhe assistant ki tarah jawab dena sikhaya jaata hai."),
    ("During training, a laptop GPU reached 83°C. Real labs plan cooling as carefully as the model itself.",
     "ट्रेनिंग के दौरान लैपटॉप का GPU 83°C तक पहुँचा। असली लैब ठंडक की योजना मॉडल जितनी ही ध्यान से बनाती हैं।",
     "Training ke dauran laptop ka GPU 83°C tak pahuncha. Asli labs cooling ka plan model jitna hi dhyaan se banati hain."),
    ("Copyright matters: MONA's team removed a modern commentary from training and kept only 450-year-old verse.",
     "कॉपीराइट ज़रूरी है: MONA की टीम ने आधुनिक टीका हटाकर सिर्फ़ 450 साल पुरानी चौपाइयाँ रखीं।",
     "Copyright zaroori hai: MONA ki team ne modern commentary hata kar sirf 450 saal purani chaupaiyan rakhin."),
    ("'Temperature' decides how adventurous the model is. Low = safe and boring, high = creative and wild.",
     "'टेम्परेचर' तय करता है कि मॉडल कितना साहसी हो। कम = सुरक्षित और नीरस, ज़्यादा = रचनात्मक और बेलगाम।",
     "'Temperature' decide karta hai model kitna adventurous ho. Kam = safe aur boring, zyada = creative aur wild."),
    ("Hindi costs MONA 1.33 tokens per word. Many English-first models spend 4 or more.",
     "MONA को हिंदी के एक शब्द के लिए 1.33 टोकन लगते हैं। कई अंग्रेज़ी-केंद्रित मॉडल 4 या ज़्यादा लगाते हैं।",
     "MONA ko Hindi ke ek word ke liye 1.33 tokens lagte hain. Kai English-first models 4 ya zyada lagate hain."),
    ("Most of a lab's work is not the model code (MONA's is 170 lines) but data, testing and keeping training alive.",
     "लैब का ज़्यादातर काम मॉडल का कोड नहीं (MONA का 170 लाइन है), बल्कि डेटा, जाँच और ट्रेनिंग को चालू रखना है।",
     "Lab ka zyadatar kaam model ka code nahi (MONA ka 170 lines hai), balki data, testing aur training ko chaalu rakhna hai."),
    ("A model that 'sounds sure' can still be wrong. That's why labs spend so much on evaluation.",
     "जो मॉडल 'पक्का लगे' वह भी ग़लत हो सकता है। इसीलिए लैब जाँच (evaluation) पर इतना ख़र्च करती हैं।",
     "Jo model 'pakka lage' woh bhi galat ho sakta hai. Isiliye labs evaluation par itna kharcha karti hain."),
    ("RAG lets a small model look things up instead of remembering everything, like an open-book exam.",
     "RAG से छोटा मॉडल सब याद रखने के बजाय चीज़ें खोज सकता है, जैसे खुली किताब वाली परीक्षा।",
     "RAG se chhota model sab yaad rakhne ke bajaye cheezein dhoondh sakta hai, jaise open-book exam."),
]

# The mission briefing under the lists: (objective, experiment, what you unlock) for the highlighted item.
MISSIONS = {
    "words": ("Follow the text YOU type through MONA, from letters to the next word she picks.",
              "Type a sentence, then watch 12 animated pages: cleaning, splitting, bytes, merges, token ids, embeddings, position, blocks, attention, scores.",
              "Understand exactly what happens to every word you type."),
    "talk": ("Have a real conversation with MONA.",
             "Ask her anything and watch her write, token by token, on your own computer.", "See what a small model can and cannot do."),
    "zoom": ("See how a language model is built, from the whole thing down to a single neuron.",
             "Watch an animated dive through MONA with her real numbers at every step.", "Understand what is inside every model."),
    "lm": ("Discover that guessing the next word is the only thing a language model does.",
           "Play 5 rounds against MONA and compare your guesses with hers.", "Understand next-token prediction."),
    "data": ("See what MONA read, and why cleaning data is most of the work.",
             "Keep or drop real documents using MONA's own cleaning rules.", "Understand training data and filtering."),
    "tokens": ("Learn how text becomes the numbers a model reads.",
               "Cut your own sentence into tokens, replay BPE merges, race languages by token cost.", "Understand tokenization."),
    "embeddings": ("See how words become points, with similar words close together.",
                   "Find a word's neighbours and play odd-one-out.", "Understand embeddings."),
    "attention": ("Discover how tokens exchange information.",
                  "Change the input and inspect an attention head.", "Understand self-attention."),
    "layers": ("Watch a guess form as it passes through the layers.",
               "Move along a sentence and read MONA's guess after every layer (the logit lens).", "Understand how depth builds an answer."),
    "next": ("Learn how the next token is chosen from the probabilities.",
             "Turn temperature, top-k and top-p and watch the writing change.", "Understand sampling."),
    "training": ("See how MONA went from random noise to sentences.",
                 "Ask MONA's saved checkpoints the same prompt and study the real loss curve.", "Understand pretraining."),
    "chat": ("See how a text-continuer becomes an assistant.",
             "Compare base MONA and MONA-Chat on one question; inspect the chat template and loss mask.", "Understand fine-tuning."),
    "evals": ("Learn how to tell whether a model is any good.",
              "Take a mini exam, make your own, and read the surprise meter.", "Understand evaluation, and why benchmarks mislead."),
    "rag": ("Let MONA look things up instead of guessing.",
            "Ask one question with and without the library and compare the answers.", "Understand retrieval-augmented generation."),
    "beyond": ("Learn how models are shrunk, given tools and made fast.",
               "Quantize MONA, call a tool, and time the KV-cache.", "Understand quantization, tool use and caching."),
    "mysteries": ("Investigate a model that misbehaves.",
                  "Run up to three experiments, name the cause, then read the code.", "Learn to debug a model."),
    "incidents": ("Learn what really goes wrong in a training run.",
                  "Choose what you would do in six real incidents from MONA's own run.", "Understand running training in practice."),
    "course": ("Train your own small model.",
               "Train it, test it against MONA, then compare three learning rates.", "Understand training by changing one variable."),
    "journey": ("Follow MONA's real training diary.",
                "Step through the chapters with the real loss and the real samples.", "Understand the whole build, start to finish."),
    "budget": ("See how compute and model size trade off.",
               "Pick a budget and a model size and read the loss curve.", "Understand scaling laws."),
    "tour": ("See how frontier labs are organised.",
             "Walk through the seven teams and compare with MONA's own build.", "Understand how models are built at scale."),
    "compare": ("Compare MONA with a much bigger model.",
                "Ask both the same question and compare answers, speed and token counts.", "Understand what scale buys."),
    "story": ("Follow one sentence through the model.",
              "Type a sentence and watch it pass through every stage.", "See the whole pipeline in one view."),
    "teacher": ("Teach this to a class.",
                "Open a 45-minute lesson plan and a printable quiz.", "Run a lesson."),
    "badges": ("Review your progress.", "Check your badges and your certificate.", "See what you have completed."),
}

register({
    "memo": {"en": "💡 Did you know? {m}", "hi": "💡 क्या आप जानते हैं? {m}", "hinglish": "💡 Kya aap jaante ho? {m}"},
    "next_up": {"en": "➜ Next up: {n}   (press N)", "hi": "➜ अगला: {n}   (N दबाइए)", "hinglish": "➜ Agla: {n}   (N dabao)"},
    "all_done": {"en": "🎓 You've completed the whole path. Try the Model mysteries again, or train with new settings!",
                 "hi": "🎓 आपने पूरा रास्ता तय कर लिया। मॉडल की पहेलियाँ फिर से आज़माइए, या नई सेटिंग से ट्रेन कीजिए!",
                 "hinglish": "🎓 Aapne poora path complete kar liya. Model mysteries phir try karo, ya nayi settings se train karo!"},
    "desk_title": {"en": "EXPLORE FURTHER", "hi": "और गहराई में", "hinglish": "AUR GEHRAI MEIN"},
})


class DisplayCheckScreen(Screen):
    """First run: make sure Hindi is drawn correctly, or switch to romanized Hindi."""

    def compose(self) -> ComposeResult:
        with Vertical(id="check-box"):
            yield Static(id="check-title", classes="title")
            yield Static("हिंदी   ·   भारत   ·   राम ने धनुष तोड़ा   ·   क्षत्रिय", id="check-sample")
            yield Static(id="check-q")
            with Horizontal(id="check-buttons"):
                yield Button(id="yes", variant="success")
                yield Button(id="no", variant="warning")
            yield Static(id="check-fix")
            yield Button(id="continue", variant="primary")

    def on_mount(self):
        self.query_one("#continue").display = False
        self.refresh_texts()

    def refresh_texts(self):
        tr = self.app.tr
        self.query_one("#check-title", Static).update(tr("check_title"))
        self.query_one("#check-q", Static).update(tr("check_q"))
        self.query_one("#yes", Button).label = tr("yes")
        self.query_one("#no", Button).label = tr("no")
        self.query_one("#continue", Button).label = "→"

    def on_button_pressed(self, event: Button.Pressed):
        state = self.app.state
        if event.button.id == "yes":
            state.romanize, state.display_checked = False, True
            state.save()
            self.app.pop_screen()
        elif event.button.id == "no":
            state.romanize, state.display_checked = True, True
            state.save()
            self.query_one("#check-fix", Static).update(self.app.tr("check_fix"))
            self.query_one("#check-buttons").display = False
            self.query_one("#continue").display = True
        else:
            self.app.pop_screen()


class HomeScreen(Screen):
    BINDINGS = [Binding("d", "app.cycle_depth", "depth"), Binding("q", "app.quit", "quit"), Binding("escape", "root_hint", "back", show=False),
                Binding("s", "story", "story"), Binding("b", "badges", "badges"), Binding("c", "compare", "compare"),
                Binding("t", "teacher", "teacher"), Binding("o", "tour", "tour"), Binding("j", "journey", "journey"),
                Binding("g", "course", "course"), Binding("i", "incidents", "incidents"), Binding("p", "budget", "budget"),
                Binding("m", "mysteries", "mysteries"), Binding("n", "next_up", "next"),
                Binding("e", "brain_next", "next example"),
                Binding("k", "talk", "talk with MONA"), Binding("z", "zoom", "inside MONA"),
                Binding("w", "words", "your words")]

    def action_root_hint(self):
        self.app.notify("This is the home screen, the first stop. Press Q to quit, or pick something to explore.", timeout=3)

    def action_talk(self):
        from .chat import ChatScreen
        self.app.push_screen(ChatScreen())

    def action_words(self):
        from .path import PathScreen
        self.app.push_screen(PathScreen())

    def action_zoom(self):
        from .zoom import ZoomScreen
        self.app.push_screen(ZoomScreen())

    def action_mysteries(self):
        from .mysteries import MysteryScreen
        self.app.push_screen(MysteryScreen())

    def next_up(self):
        return next((sid for sid in PATH if sid not in self.app.state.completed), None)

    def action_next_up(self):
        sid = self.next_up()
        if sid in PATH_NAMES:
            getattr(self, f"action_{sid}")()
        elif sid:
            self.app.push_screen(open_lab(sid))

    def action_tour(self):
        from .tour import TourScreen
        self.app.push_screen(TourScreen())

    def action_journey(self):
        from .journey import JourneyScreen
        self.app.push_screen(JourneyScreen())

    def action_course(self):
        from .course import CourseScreen
        self.app.push_screen(CourseScreen())

    def action_incidents(self):
        from .incidents import IncidentScreen
        self.app.push_screen(IncidentScreen())

    def action_budget(self):
        from .budget import BudgetScreen
        self.app.push_screen(BudgetScreen())

    def action_teacher(self):
        from .teacher import TeacherScreen
        self.app.push_screen(TeacherScreen())

    def action_compare(self):
        from .labs.compare import CompareLab
        self.app.push_screen(CompareLab())

    def action_story(self):
        from .story import StoryScreen
        self.app.push_screen(StoryScreen())

    def action_badges(self):
        from .story import BadgesScreen
        self.app.push_screen(BadgesScreen())

    def compose(self) -> ComposeResult:
        with Vertical(id="main"):
            with Horizontal(id="top-row"):
                yield Static(id="hello")
                yield Static(id="brain")
            with Horizontal(id="home-cols"):
                with Vertical(id="stage-col"):
                    yield OptionList(id="stages")
                with Vertical(id="desk-col"):
                    yield OptionList(id="desk")
            yield Static(id="mission")
            yield Static(id="telemetry")
        yield Static(id="keys", classes="keys")

    def on_mount(self):
        self.reading, self.example_i = None, 0
        self.query_one("#main").border_title = "MONA  ·  understand AI from the inside"
        self.query_one("#stages").border_title = "Learning path"
        self.query_one("#desk").border_title = "Explore further"
        self.query_one("#mission").border_title = "Mission"
        self.query_one("#brain").border_title = "Model activity"
        self.query_one("#telemetry").border_title = "Telemetry"
        self.refresh_texts()
        self.query_one("#stages").focus()
        if self.app.gb is not None:
            self.run_brain()

    # ── MONA's Brain: one real forward pass, shown compactly ──────────────────
    def on_engine_ready(self):
        self.run_brain()

    def action_brain_next(self):
        self.example_i = (self.example_i + 1) % len(brain.EXAMPLES)
        self.run_brain()

    @work(thread=True, exclusive=True, group="brain")
    def run_brain(self):
        gb = self.app.gb
        if gb is None:
            return
        reading = brain.read(gb, brain.EXAMPLES[self.example_i])
        self.app.call_from_thread(self._brain_ready, reading)

    def _brain_ready(self, reading):
        self.reading = reading
        self.refresh_texts()

    def refresh_texts(self):
        app, s = self.app, self.app.state
        tr = app.tr
        who = app.addr()
        hello = Text(tr(greeting_key()) + (f", {who}" if who else "") + "! ", style="bold #f9e2af")
        hello.append(tr("hello"), style="#cdd6f4")
        hello.append("\n\n" + tr("memo", m=MEMOS[dt.date.today().toordinal() % len(MEMOS)][0]), style="#89dceb")
        box = self.query_one("#hello", Static)
        box.update(hello)
        box.border_title = f"Hello  ·  {tr('depth_name')} mode"
        self.query_one("#brain", Static).update(brain.render(getattr(self, "reading", None)))
        nxt = self.next_up()
        desk = self.query_one("#desk", OptionList)
        keep = desk.highlighted
        desk.clear_options()
        for item in EXPLORE:
            name = item[2]
            if item[0] is None:                                      # a section heading
                desk.add_option(Option(Text(name, style="bold underline #f9e2af"), disabled=True))
            else:
                mark = "✓" if item[0] in s.completed else " "
                desk.add_option(Option(Text.assemble((f" {item[1]} ", "bold #f9e2af"), (f"{mark} ", "#a6e3a1"),
                                                     (name, "bold")), id=item[0]))
        desk.highlighted = keep if keep is not None else 1
        stages = self.query_one("#stages", OptionList)
        highlighted = stages.highlighted
        stages.clear_options()
        target = None
        for title, ids in TRACKS:
            stages.add_option(Option(Text(title[0], style="bold underline #f9e2af"), disabled=True))
            for sid in ids:
                stage = next(st for st in STAGES if st[0] == sid)
                i = STAGES.index(stage)
                mark = "✓" if sid in s.completed else ("●" if sid in READY else "○")
                label = Text.assemble((f"  {i:>2}  {mark}  ", "#a6e3a1" if sid in s.completed else "#f9e2af" if sid in READY else "#6c7086"),
                                      (stage_name(stage, "en"), "bold" if sid in READY else "#9399b2"))
                stages.add_option(Option(label, id=sid))
                if sid == nxt:
                    target = stages.option_count - 1
        stages.highlighted = highlighted if highlighted is not None else (target if target is not None else 1)
        done = len([c for c in s.completed if c in {st[0] for st in STAGES}])   # stages only, not story
        self.query_one("#telemetry", Static).update(
            brain.telemetry(app.gb, getattr(self, "reading", None), done, len(STAGES), s.badges))
        self.query_one("#keys", Static).update(tr("keys_home"))
        self.show_mission()

    def on_option_list_option_highlighted(self, event: OptionList.OptionHighlighted):
        self.show_mission(event.option.id)

    def show_mission(self, oid=None):
        """The mission briefing: objective, experiment and what you unlock, for whatever the cursor is on."""
        if oid is None:
            lst = self.query_one("#stages", OptionList)
            oid = lst.get_option_at_index(lst.highlighted).id if lst.highlighted is not None else None
        if oid not in MISSIONS:
            return
        objective, experiment, unlock = MISSIONS[oid]
        stage = next((st for st in STAGES if st[0] == oid), None)
        name = stage_name(stage, "en") if stage else PATH_NAMES[oid][0]
        head = "NEXT MISSION" if oid == self.next_up() else "MISSION"
        out = Text(f"{head}: {name.upper()}\n", style="bold #f9e2af")
        for label, body in (("OBJECTIVE", objective), ("EXPERIMENT", experiment), ("UNLOCK", unlock)):
            out.append(f"{label} ", style="bold #89dceb")
            out.append(f"— {body}\n", style="#cdd6f4")
        out.append("ENTER → BEGIN", style="bold #a6e3a1")
        out.append("     F8 source code     F1 explain a word     E next example sentence", style="#9399b2")
        self.query_one("#mission", Static).update(out)

    def on_option_list_option_selected(self, event: OptionList.OptionSelected):
        if event.option_list.id == "desk":
            getattr(self, f"action_{event.option.id}")()
            return
        lab = open_lab(event.option.id)
        if lab:
            self.app.push_screen(lab)
        else:
            self.app.notify(self.app.tr("soon"), timeout=3)

    def on_screen_resume(self):
        self.refresh_texts()            # progress / badges may have changed inside a lab


def open_lab(stage_id):
    """Labs are imported only when opened, so the app starts instantly."""
    if stage_id == "lm":
        from .labs.lm_game import LMGameLab
        return LMGameLab()
    if stage_id == "embeddings":
        from .labs.embeddings import EmbeddingsLab
        return EmbeddingsLab()
    if stage_id == "evals":
        from .labs.evals import EvalsLab
        return EvalsLab()
    if stage_id == "data":
        from .labs.data import DataLab
        return DataLab()
    if stage_id == "chat":
        from .labs.chat_tuning import ChatTuningLab
        return ChatTuningLab()
    if stage_id == "rag":
        from .labs.rag import RagLab
        return RagLab()
    if stage_id == "beyond":
        from .labs.beyond import BeyondLab
        return BeyondLab()
    if stage_id == "tokens":
        from .labs.tokens import TokensLab
        return TokensLab()
    if stage_id == "attention":
        from .labs.attention import AttentionLab
        return AttentionLab()
    if stage_id == "training":
        from .labs.timemachine import TimeMachineLab
        return TimeMachineLab()
    if stage_id == "layers":
        from .labs.layers import LayersLab
        return LayersLab()
    if stage_id == "next":
        from .labs.sampling import SamplingLab
        return SamplingLab()
    return None
