"""F1 anywhere: explain any word in plain language, with an everyday comparison.

Each entry: (term, {lang: (meaning, everyday comparison)}, stage to see it live or None).
"""
from rich.text import Text
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Input, OptionList, Static
from textual.widgets.option_list import Option

from .text import register

register({
    "gl_title": {"en": "📖 Explain a word", "hi": "📖 शब्द का मतलब", "hinglish": "📖 Word ka matlab"},
    "gl_search": {"en": "Type to search…", "hi": "खोजने के लिए लिखिए…", "hinglish": "Search karne ke liye likho…"},
    "gl_like": {"en": "Think of it like this:", "hi": "ऐसे समझिए:", "hinglish": "Aise samjho:"},
    "gl_see": {"en": "See it live: stage “{s}”", "hi": "असली में देखिए: चरण “{s}”", "hinglish": "Live dekho: stage “{s}”"},
    "gl_keys": {"en": "type to search  ↑↓ choose  Esc close", "hi": "खोजने के लिए लिखिए  ↑↓ चुनें  Esc बंद",
                "hinglish": "search ke liye likho  ↑↓ chuno  Esc band"},
})

G = [
    ("Language model", {
        "en": ("A program that guesses the next word (token) of a text, again and again.",
               "Your phone keyboard's word suggestions, made millions of times smarter."),
        "hi": ("ऐसा प्रोग्राम जो किसी पाठ का अगला शब्द (टोकन) बार-बार अंदाज़ा लगाता है।",
               "फ़ोन के कीबोर्ड के शब्द-सुझाव, बस लाखों गुना ज़्यादा समझदार।"),
        "hinglish": ("Aisa program jo text ka agla word (token) baar-baar guess karta hai.",
                     "Phone keyboard ke word suggestions, bas laakhon guna zyada smart.")}, "lm"),
    ("Token", {
        "en": ("A small piece of text (a word or part of a word) that the model reads as one number.",
               "Lego pieces: words are built by snapping pieces together."),
        "hi": ("पाठ का छोटा टुकड़ा (शब्द या शब्द का हिस्सा), जिसे मॉडल एक संख्या की तरह पढ़ता है।",
               "लेगो के टुकड़े: शब्द टुकड़ों को जोड़कर बनते हैं।"),
        "hinglish": ("Text ka chhota tukda (word ya word ka hissa) jise model ek number ki tarah padhta hai.",
                     "Lego pieces: words tukdon ko jodkar bante hain.")}, "tokens"),
    ("Tokenizer (BPE)", {
        "en": ("The tool that cuts text into tokens. BPE learns which letter-pairs appear together most often and glues them.",
               "Noticing 'th' is so common that you give it its own key on the keyboard."),
        "hi": ("वह औज़ार जो पाठ को टोकन में काटता है। BPE सीखता है कि कौन से अक्षर-जोड़े सबसे ज़्यादा साथ आते हैं और उन्हें जोड़ देता है।",
               "जैसे 'क्ष' इतना आम है कि उसका अपना अलग अक्षर बन गया।"),
        "hinglish": ("Woh tool jo text ko tokens mein kaatta hai. BPE seekhta hai kaun se letter-pairs sabse zyada saath aate hain aur unhe jod deta hai.",
                     "Jaise 'th' itna common hai ki keyboard par uski alag key bana do.")}, "tokens"),
    ("Parameter / weight", {
        "en": ("One number inside the model that training adjusts. MONA has 110 million of them.",
               "One tiny knob on a giant mixing desk; training turns all the knobs a little at a time."),
        "hi": ("मॉडल के अंदर की एक संख्या जिसे ट्रेनिंग बदलती है। MONA में ऐसी 11 करोड़ हैं।",
               "एक बहुत बड़े साउंड-मिक्सर का एक छोटा नॉब; ट्रेनिंग सारे नॉब थोड़ा-थोड़ा घुमाती है।"),
        "hinglish": ("Model ke andar ka ek number jise training badalti hai. MONA mein aise 11 crore hain.",
                     "Ek bahut bade sound-mixer ka ek chhota knob; training saare knobs thoda-thoda ghumaati hai.")}, "training"),
    ("Embedding", {
        "en": ("The list of numbers (768 for MONA) that stands for a token. Similar words get similar lists.",
               "GPS coordinates for words: words with close meanings live close together on the map."),
        "hi": ("संख्याओं की सूची (MONA में 768) जो एक टोकन को दर्शाती है। मिलते-जुलते शब्दों की सूची भी मिलती-जुलती होती है।",
               "शब्दों के GPS निर्देशांक: मिलते-जुलते अर्थ वाले शब्द नक्शे पर पास-पास रहते हैं।"),
        "hinglish": ("Numbers ki list (MONA mein 768) jo ek token ko represent karti hai. Milte-julte words ki list bhi milti-julti hoti hai.",
                     "Words ke GPS coordinates: milte-julte meaning wale words map par paas-paas rehte hain.")}, "embeddings"),
    ("Attention", {
        "en": ("Each word decides which earlier words matter most for understanding it.",
               "Reading 'it' and glancing back to find what 'it' refers to."),
        "hi": ("हर शब्द तय करता है कि उसे समझने के लिए पहले के कौन से शब्द सबसे ज़रूरी हैं।",
               "'वह' पढ़कर पीछे देखना कि 'वह' किसके बारे में है।"),
        "hinglish": ("Har word decide karta hai ki use samajhne ke liye pehle ke kaun se words sabse zaroori hain.",
                     "'woh' padhkar peeche dekhna ki 'woh' kiske baare mein hai.")}, "attention"),
    ("Layer", {
        "en": ("One round of 'look around (attention), then think (feed-forward)'. MONA has 12 rounds.",
               "A team passing a draft along; each person improves it a little."),
        "hi": ("'आसपास देखो (अटेंशन), फिर सोचो' का एक दौर। MONA में 12 दौर हैं।",
               "एक टीम जो मसौदा आगे बढ़ाती है; हर व्यक्ति उसे थोड़ा बेहतर करता है।"),
        "hinglish": ("'Aas-paas dekho (attention), phir socho' ka ek round. MONA mein 12 rounds hain.",
                     "Ek team jo draft aage badhaati hai; har insaan use thoda behtar karta hai.")}, "layers"),
    ("Transformer", {
        "en": ("The design almost every modern LLM uses: stacked layers of attention + feed-forward.",
               "The engine design; GPT, Llama, Gemma and MONA are different cars with the same kind of engine."),
        "hi": ("वह डिज़ाइन जो लगभग हर आधुनिक LLM इस्तेमाल करता है: अटेंशन + फ़ीड-फ़ॉरवर्ड की परतें।",
               "इंजन का डिज़ाइन; GPT, Llama, Gemma और MONA अलग गाड़ियाँ हैं, इंजन एक जैसा।"),
        "hinglish": ("Woh design jo lagbhag har modern LLM use karta hai: attention + feed-forward ki layers.",
                     "Engine ka design; GPT, Llama, Gemma aur MONA alag gaadiyan hain, engine ek jaisa.")}, "layers"),
    ("Training / pretraining", {
        "en": ("Showing the model huge amounts of text so it learns to guess the next token. MONA read 2.5 billion tokens.",
               "Learning a language by reading a whole library, checking your guess after every word."),
        "hi": ("मॉडल को ढेर सारा पाठ दिखाना ताकि वह अगला टोकन अंदाज़ा लगाना सीखे। MONA ने 2.5 अरब टोकन पढ़े।",
               "पूरी लाइब्रेरी पढ़कर भाषा सीखना, हर शब्द के बाद अपना अंदाज़ा जाँचते हुए।"),
        "hinglish": ("Model ko dher saara text dikhana taaki woh agla token guess karna seekhe. MONA ne 2.5 billion tokens padhe.",
                     "Poori library padhkar bhasha seekhna, har word ke baad apna guess check karte hue.")}, "training"),
    ("Loss", {
        "en": ("A score for how wrong the model's guesses are. Lower is better; training pushes it down.",
               "The number of wrong answers in a practice test."),
        "hi": ("मॉडल के अंदाज़े कितने ग़लत हैं, उसका अंक। कम बेहतर है; ट्रेनिंग इसे नीचे लाती है।",
               "अभ्यास परीक्षा में ग़लत जवाबों की गिनती।"),
        "hinglish": ("Model ke guesses kitne galat hain, uska score. Kam behtar hai; training ise neeche laati hai.",
                     "Practice test mein galat answers ki ginti.")}, "training"),
    ("Learning rate", {
        "en": ("How big each correction step is during training. Too big: chaos. Too small: very slow.",
               "How hard you turn the steering wheel when the car drifts."),
        "hi": ("ट्रेनिंग में हर सुधार का कदम कितना बड़ा हो। बहुत बड़ा: गड़बड़। बहुत छोटा: बहुत धीमा।",
               "गाड़ी भटकने पर स्टीयरिंग कितना घुमाते हैं।"),
        "hinglish": ("Training mein har sudhaar ka step kitna bada ho. Bahut bada: gadbad. Bahut chhota: bahut slow.",
                     "Gaadi bhatakne par steering kitna ghumaate ho.")}, "training"),
    ("Checkpoint", {
        "en": ("A saved copy of training so it can continue after a stop or crash. MONA saves one every 30 minutes.",
               "Saving your game before the boss fight."),
        "hi": ("ट्रेनिंग की सहेजी गई कॉपी, ताकि रुकने या क्रैश के बाद आगे चल सके। MONA हर 30 मिनट में सहेजती है।",
               "बॉस-फ़ाइट से पहले गेम सेव करना।"),
        "hinglish": ("Training ki saved copy, taaki rukne ya crash ke baad aage chal sake. MONA har 30 minute mein save karti hai.",
                     "Boss fight se pehle game save karna.")}, None),
    ("GPU", {
        "en": ("A chip that does thousands of multiplications at once. Training is mostly multiplications.",
               "A thousand cashiers working in parallel instead of one."),
        "hi": ("एक चिप जो एक साथ हज़ारों गुणा करती है। ट्रेनिंग ज़्यादातर गुणा ही है।",
               "एक कैशियर की जगह हज़ार कैशियर एक साथ काम करते हुए।"),
        "hinglish": ("Ek chip jo ek saath hazaron multiplications karti hai. Training zyadatar multiplication hi hai.",
                     "Ek cashier ki jagah hazaar cashiers ek saath kaam karte hue.")}, None),
    ("Scaling laws", {
        "en": ("Rules of thumb that predict quality from model size, data and compute, before spending money.",
               "A recipe that tells you how much flour for how many guests."),
        "hi": ("अनुभव के नियम जो पैसे ख़र्च करने से पहले ही मॉडल के आकार, डेटा और कंप्यूट से गुणवत्ता बताते हैं।",
               "रेसिपी जो बताती है कितने मेहमानों के लिए कितना आटा।"),
        "hinglish": ("Thumb rules jo paisa kharch karne se pehle hi model size, data aur compute se quality predict karte hain.",
                     "Recipe jo batati hai kitne mehmaanon ke liye kitna aata.")}, None),
    ("Chinchilla rule", {
        "en": ("A 2022 finding: for a fixed budget, train on about 20 tokens per parameter. MONA used about 23.",
               "Don't build a huge brain and starve it of books."),
        "hi": ("2022 की खोज: तय बजट में हर पैरामीटर पर लगभग 20 टोकन से ट्रेन करें। MONA ने लगभग 23 इस्तेमाल किए।",
               "बड़ा दिमाग़ बनाकर उसे किताबों से भूखा मत रखो।"),
        "hinglish": ("2022 ki khoj: fixed budget mein har parameter par lagbhag 20 tokens se train karo. MONA ne lagbhag 23 use kiye.",
                     "Bada dimaag banakar use kitaabon se bhookha mat rakho.")}, None),
    ("Temperature", {
        "en": ("A knob for randomness when the model writes. Low: safe, repetitive. High: creative, sometimes nonsense.",
               "How adventurous you are when ordering food."),
        "hi": ("लिखते समय अनियमितता का नॉब। कम: सुरक्षित, दोहराव। ज़्यादा: रचनात्मक, कभी-कभी बेतुका।",
               "खाना ऑर्डर करते समय आप कितने साहसी हैं।"),
        "hinglish": ("Likhte samay randomness ka knob. Kam: safe, repeat. Zyada: creative, kabhi-kabhi bekaar.",
                     "Khaana order karte samay aap kitne adventurous ho.")}, "next"),
    ("Top-k / top-p", {
        "en": ("Rules that throw away unlikely next words before picking one, so the model doesn't say something silly.",
               "Shortlisting candidates before the final interview."),
        "hi": ("नियम जो चुनने से पहले असंभावित अगले शब्द हटा देते हैं, ताकि मॉडल बेतुका न बोले।",
               "आख़िरी इंटरव्यू से पहले उम्मीदवारों की शॉर्टलिस्ट।"),
        "hinglish": ("Rules jo choose karne se pehle unlikely agle words hata dete hain, taaki model bekaar na bole.",
                     "Final interview se pehle candidates ki shortlist.")}, "next"),
    ("Context window", {
        "en": ("How much text the model can see at once. MONA: 1,024 tokens (about 700 words).",
               "How many pages of a book you can keep open on your desk."),
        "hi": ("मॉडल एक बार में कितना पाठ देख सकता है। MONA: 1,024 टोकन (लगभग 700 शब्द)।",
               "मेज़ पर किताब के कितने पन्ने एक साथ खुले रख सकते हैं।"),
        "hinglish": ("Model ek baar mein kitna text dekh sakta hai. MONA: 1,024 tokens (lagbhag 700 words).",
                     "Desk par kitaab ke kitne pages ek saath khule rakh sakte ho.")}, None),
    ("SFT (chat tuning)", {
        "en": ("Supervised fine-tuning: teaching a pretrained model the question → answer format with example chats.",
               "A well-read student being trained for a job interview."),
        "hi": ("सुपरवाइज़्ड फ़ाइन-ट्यूनिंग: उदाहरण बातचीत से मॉडल को सवाल → जवाब का ढंग सिखाना।",
               "पढ़े-लिखे विद्यार्थी को नौकरी के इंटरव्यू के लिए तैयार करना।"),
        "hinglish": ("Supervised fine-tuning: example chats se model ko sawaal → jawab ka tareeka sikhana.",
                     "Padhe-likhe student ko job interview ke liye taiyaar karna.")}, "chat"),
    ("RLHF", {
        "en": ("Reinforcement learning from human feedback: people rank answers, and the model learns to prefer the better ones.",
               "A cook improving from customer ratings."),
        "hi": ("इंसानी फ़ीडबैक से सीखना: लोग जवाबों को रैंक करते हैं, मॉडल बेहतर जवाब पसंद करना सीखता है।",
               "ग्राहकों की रेटिंग से सुधरता रसोइया।"),
        "hinglish": ("Insaani feedback se seekhna: log answers ko rank karte hain, model behtar answers pasand karna seekhta hai.",
                     "Customers ki rating se sudharta cook.")}, None),
    ("Evaluation (evals)", {
        "en": ("Tests that measure how good a model is, on text it never saw during training.",
               "A final exam with questions that were never in the textbook."),
        "hi": ("जाँच जो नापती है कि मॉडल कितना अच्छा है, उस पाठ पर जो उसने ट्रेनिंग में कभी नहीं देखा।",
               "ऐसी परीक्षा जिसके सवाल किताब में कभी नहीं थे।"),
        "hinglish": ("Tests jo naapte hain ki model kitna achha hai, us text par jo usne training mein kabhi nahi dekha.",
                     "Aisa exam jiske sawaal kitaab mein kabhi nahi the.")}, "evals"),
    ("Bits per byte", {
        "en": ("A fair score for how surprised a model is by new text, comparable across languages and tokenizers.",
               "Grading everyone on the same scale, whatever language they wrote in."),
        "hi": ("नए पाठ से मॉडल कितना हैरान है, उसका निष्पक्ष अंक, जो भाषाओं और टोकनाइज़र के बीच तुलना योग्य है।",
               "सबको एक ही पैमाने पर जाँचना, चाहे किसी भी भाषा में लिखा हो।"),
        "hinglish": ("Naye text se model kitna surprised hai, uska fair score, jo languages aur tokenizers ke beech compare ho sakta hai.",
                     "Sabko ek hi scale par check karna, chahe kisi bhi bhasha mein likha ho.")}, "evals"),
    ("Hallucination", {
        "en": ("When a model confidently says something false. It predicts likely words, not true facts.",
               "A student bluffing confidently in a viva."),
        "hi": ("जब मॉडल पूरे भरोसे से कुछ ग़लत कह दे। वह संभावित शब्द बताता है, सच्चे तथ्य नहीं।",
               "वाइवा में पूरे भरोसे से गप्प मारता विद्यार्थी।"),
        "hinglish": ("Jab model poore bharose se kuch galat keh de. Woh likely words batata hai, sacche facts nahi.",
                     "Viva mein poore confidence se bluff maarta student.")}, "rag"),
    ("RAG", {
        "en": ("Retrieval-augmented generation: search a library first, then answer using what was found.",
               "An open-book exam."),
        "hi": ("पहले लाइब्रेरी में खोजो, फिर मिली जानकारी से जवाब दो।", "खुली किताब वाली परीक्षा।"),
        "hinglish": ("Pehle library mein dhoondho, phir mili jaankari se jawab do.", "Open-book exam.")}, "rag"),
    ("Quantization", {
        "en": ("Storing each weight with fewer bits so the model gets smaller and faster, losing a little quality.",
               "Saving a photo as a smaller JPEG."),
        "hi": ("हर वज़न को कम बिट में रखना ताकि मॉडल छोटा और तेज़ हो, थोड़ी गुणवत्ता खोकर।",
               "फ़ोटो को छोटी JPEG में सेव करना।"),
        "hinglish": ("Har weight ko kam bits mein rakhna taaki model chhota aur fast ho, thodi quality khokar.",
                     "Photo ko chhoti JPEG mein save karna.")}, "beyond"),
    ("KV-cache", {
        "en": ("While writing, the model remembers its earlier work instead of recomputing it for every new word.",
               "Keeping your rough notes instead of re-solving the whole sum each time."),
        "hi": ("लिखते समय मॉडल हर नए शब्द के लिए पुराना काम दोबारा करने की जगह उसे याद रखता है।",
               "हर बार पूरा सवाल दोबारा हल करने की जगह कच्चे नोट्स रखना।"),
        "hinglish": ("Likhte samay model har naye word ke liye purana kaam dobara karne ki jagah use yaad rakhta hai.",
                     "Har baar poora sawaal dobara solve karne ki jagah rough notes rakhna.")}, "beyond"),
    ("Logit lens", {
        "en": ("Peeking at what the model would guess after each layer, not only the last one.",
               "Asking each person in the relay what answer they'd give so far."),
        "hi": ("हर लेयर के बाद मॉडल का अंदाज़ा देखना, सिर्फ़ आख़िरी के बाद नहीं।",
               "रिले के हर व्यक्ति से पूछना कि अभी तक उसका जवाब क्या होगा।"),
        "hinglish": ("Har layer ke baad model ka guess dekhna, sirf last ke baad nahi.",
                     "Relay ke har insaan se poochna ki abhi tak uska answer kya hoga.")}, "layers"),
    ("Overfitting / memorising", {
        "en": ("When a model repeats its training text instead of learning general patterns.",
               "Mugging up answers instead of understanding the chapter."),
        "hi": ("जब मॉडल सामान्य पैटर्न सीखने की जगह ट्रेनिंग का पाठ रट ले।", "अध्याय समझने की जगह जवाब रट लेना।"),
        "hinglish": ("Jab model general patterns seekhne ki jagah training ka text ratt le.",
                     "Chapter samajhne ki jagah answers ratt lena.")}, None),
    ("Frontier lab", {
        "en": ("A company building the most capable AI models (for example OpenAI, Google DeepMind, Anthropic, Meta).",
               "The Formula 1 teams of AI."),
        "hi": ("सबसे सक्षम AI मॉडल बनाने वाली कंपनी (जैसे OpenAI, Google DeepMind, Anthropic, Meta)।",
               "AI की फ़ॉर्मूला 1 टीमें।"),
        "hinglish": ("Sabse capable AI models banane wali company (jaise OpenAI, Google DeepMind, Anthropic, Meta).",
                     "AI ki Formula 1 teams.")}, None),
    ("Red-teaming", {
        "en": ("Trying hard to make a model misbehave before release, to find and fix problems.",
               "Hiring friendly thieves to test your locks."),
        "hi": ("रिलीज़ से पहले मॉडल से जानबूझकर ग़लत काम करवाने की कोशिश, ताकि कमियाँ मिलें और ठीक हों।",
               "अपने ताले जाँचने के लिए दोस्ताना चोर रखना।"),
        "hinglish": ("Release se pehle model se jaan-boojhkar galat kaam karwaane ki koshish, taaki kamiyan milein aur theek hon.",
                     "Apne taale check karne ke liye friendly chor rakhna.")}, None),
    ("Model card", {
        "en": ("A public page describing what a model is, how it was made, what data it used and its limits.",
               "The nutrition label on a food packet."),
        "hi": ("एक सार्वजनिक पन्ना जो बताता है कि मॉडल क्या है, कैसे बना, कौन सा डेटा लगा और उसकी सीमाएँ।",
               "खाने के पैकेट पर पोषण का लेबल।"),
        "hinglish": ("Ek public page jo batata hai model kya hai, kaise bana, kaunsa data laga aur uski limits.",
                     "Khaane ke packet par nutrition label.")}, None),
]


class GlossaryScreen(ModalScreen):
    BINDINGS = [Binding("escape", "app.pop_screen", "close"), Binding("f1", "app.pop_screen", "close", show=False)]

    def compose(self) -> ComposeResult:
        with Vertical(id="gl-box"):
            yield Static(id="gl-title", classes="title")
            yield Input(id="gl-search")
            with Horizontal(id="gl-cols"):
                yield OptionList(id="gl-list")
                yield Static(id="gl-detail")
            yield Static(id="gl-keys", classes="dim")

    def on_mount(self):
        self.refresh_texts()
        self.fill("")
        self.query_one("#gl-search").focus()

    def refresh_texts(self):
        tr = self.app.tr
        self.query_one("#gl-title", Static).update(tr("gl_title"))
        self.query_one("#gl-search", Input).placeholder = tr("gl_search")
        self.query_one("#gl-keys", Static).update(tr("gl_keys"))
        self.show()

    def fill(self, query):
        q = query.lower().strip()
        lang = self.app.state.lang
        box = self.query_one("#gl-list", OptionList)
        box.clear_options()
        for i, (term, d, _) in enumerate(G):
            if not q or q in term.lower() or q in d[lang][0].lower():
                box.add_option(Option(term, id=str(i)))
        if box.option_count:
            box.highlighted = 0
        self.show()

    def on_input_changed(self, event: Input.Changed):
        self.fill(event.value)

    def on_key(self, event):
        box = self.query_one("#gl-list", OptionList)
        if event.key in ("up", "down") and self.focused is self.query_one("#gl-search"):
            box.action_cursor_down() if event.key == "down" else box.action_cursor_up()
            event.stop()

    def on_option_list_option_highlighted(self, event):
        self.show()

    def show(self):
        box = self.query_one("#gl-list", OptionList)
        detail = self.query_one("#gl-detail", Static)
        if box.highlighted is None or not box.option_count:
            detail.update("")
            return
        term, d, stage = G[int(box.get_option_at_index(box.highlighted).id)]
        app, lang = self.app, self.app.state.lang
        meaning, like = d.get(lang, d["en"])
        out = Text(term + "\n\n", style="bold #f9e2af")
        out.append(meaning + "\n\n", style="#cdd6f4")
        out.append(app.tr("gl_like") + " ", style="bold #89dceb")
        out.append(like + "\n", style="italic #bac2de")
        if stage:
            from .text import STAGES, stage_name
            st = next(s for s in STAGES if s[0] == stage)
            out.append("\n" + app.tr("gl_see", s=stage_name(st, lang)), style="#a6e3a1")
        detail.update(app.roman(out.plain) if app.state.romanize else out)
