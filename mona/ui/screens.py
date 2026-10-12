"""The screens of the MONA app: display check, and home (a 4-track learning path + "Explore further")."""
import datetime as dt

from rich.text import Text
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.screen import Screen
from textual.widgets import Button, OptionList, Static
from textual.widgets.option_list import Option

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
PATH = ["lm", "data", "tokens", "embeddings", "attention", "layers", "next", "course", "training", "chat", "evals",
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
    ("Training MONA took about 30 hours on one laptop. Frontier models use thousands of GPUs for months.",
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
    BINDINGS = [Binding("l", "app.cycle_lang", "language"), Binding("d", "app.cycle_depth", "depth"),
                Binding("r", "app.toggle_roman", "romanize"), Binding("q", "app.quit", "quit"),
                Binding("s", "story", "story"), Binding("b", "badges", "badges"), Binding("c", "compare", "compare"),
                Binding("t", "teacher", "teacher"), Binding("o", "tour", "tour"), Binding("j", "journey", "journey"),
                Binding("g", "course", "course"), Binding("i", "incidents", "incidents"), Binding("p", "budget", "budget"),
                Binding("m", "mysteries", "mysteries"), Binding("n", "next_up", "next")]

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
        yield Static(id="topbar")
        with Horizontal(id="hello-row"):
            yield Avatar(id="avatar")
            yield Static(id="hello")
        with Horizontal(id="home-cols"):
            with Vertical(id="stage-col"):
                yield Static(id="journey-title", classes="title")
                yield OptionList(id="stages")
            with Vertical(id="desk-col"):
                yield Static(id="desk-title", classes="title")
                yield OptionList(id="desk")
        yield Static(id="progress")
        yield Static(id="keys", classes="keys")

    def on_mount(self):
        self.refresh_texts()
        self.query_one("#stages").focus()

    def refresh_texts(self):
        app, s = self.app, self.app.state
        tr = app.tr
        langs = Text()
        for code, name in (("en", "EN"), ("hi", "हिं"), ("hinglish", "Hinglish")):
            langs.append(f" {name} ", style="bold #1b1f3b on #ffd166" if s.lang == code else "#8a8fb0")
        top = Text.assemble((" MONA ", "bold #1b1f3b on #8ecae6"), "  ", (app.tr("tagline"), "italic #c9cce0"))
        top.append("\n")
        top.append_text(langs)
        top.append(f"   ◆ {tr('depth_name')}", style="bold #06d6a0")
        if s.romanize:
            top.append("   abc→अ", style="#f4a3c0")
        self.query_one("#topbar", Static).update(top)
        who = app.addr()
        hello = Text(tr(greeting_key()) + (f", {who}" if who else "") + "! ", style="bold #ffd166")
        hello.append(tr("hello"), style="#e8e8f0")
        li = {"en": 0, "hi": 1, "hinglish": 2}[s.lang]
        nxt = self.next_up()
        if nxt:
            stage = next((st for st in STAGES if st[0] == nxt), None)
            name = f"{STAGES.index(stage)} · {stage_name(stage, s.lang)}" if stage else PATH_NAMES[nxt][li]
            hello.append("\n" + tr("next_up", n=app.roman(name) if s.romanize else name), style="bold #06d6a0")
        else:
            hello.append("\n" + tr("all_done"), style="bold #06d6a0")
        memo = MEMOS[dt.date.today().toordinal() % len(MEMOS)][li]
        hello.append("\n" + tr("memo", m=app.roman(memo) if s.romanize else memo), style="#8ecae6")
        self.query_one("#hello", Static).update(hello)
        self.query_one("#journey-title", Static).update(tr("journey"))
        self.query_one("#desk-title", Static).update(tr("desk_title"))
        desk = self.query_one("#desk", OptionList)
        keep = desk.highlighted
        desk.clear_options()
        for item in EXPLORE:
            name = item[2 + li]
            name = app.roman(name) if s.romanize else name
            if item[0] is None:                                      # a section heading
                desk.add_option(Option(Text(name, style="bold #8ecae6"), disabled=True))
            else:
                mark = "✓" if item[0] in s.completed else " "
                desk.add_option(Option(Text.assemble((f" {item[1]} ", "bold #ffd166"), (f"{mark} ", "#06d6a0"),
                                                     (name, "bold")), id=item[0]))
        desk.highlighted = keep if keep is not None else 1
        stages = self.query_one("#stages", OptionList)
        highlighted = stages.highlighted
        stages.clear_options()
        target = None
        for title, ids in TRACKS:
            stages.add_option(Option(Text(app.roman(title[li]) if s.romanize else title[li], style="bold #8ecae6"),
                                     disabled=True))
            for sid in ids:
                stage = next(st for st in STAGES if st[0] == sid)
                i = STAGES.index(stage)
                mark = "✓" if sid in s.completed else ("●" if sid in READY else "○")
                name = stage_name(stage, s.lang)
                if s.romanize:
                    name = app.roman(name)
                label = Text.assemble((f"  {i:>2}  {mark}  ", "#ffd166" if sid in READY else "#5a5f7c"),
                                      (name, "bold" if sid in READY else "#8a8fb0"))
                stages.add_option(Option(label, id=sid))
                if sid == nxt:
                    target = stages.option_count - 1
        stages.highlighted = highlighted if highlighted is not None else (target if target is not None else 1)
        done = len([c for c in s.completed if c in {st[0] for st in STAGES}])   # stages only, not story
        bar = "█" * done + "░" * (len(STAGES) - done)
        badges = "   " + "  ".join(f"🏅 {b}" for b in s.badges) if s.badges else ""
        self.query_one("#progress", Static).update(
            Text.assemble((f"{tr('progress')}  ", "#8a8fb0"), (bar, "#06d6a0"), (f"  {done}/{len(STAGES)}", "#8a8fb0"),
                          (badges, "#ffd166")))
        self.query_one("#keys", Static).update(tr("keys_home"))

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
