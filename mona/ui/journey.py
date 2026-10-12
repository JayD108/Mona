"""MONA's training journey, start to end: the real story, told from its logs.

Each chapter has a date, what happened, and (where it fits) live numbers from the run: the loss at
that moment and what MONA actually wrote then. Chapters that haven't happened yet show progress.
"""
import csv

from rich.text import Text
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, VerticalScroll
from textual.screen import Screen
from textual.widgets import OptionList, Static
from textual.widgets.option_list import Option

from .. import paths
from .text import register
from .widgets import Avatar

register({
    "jr_title": {"en": "MONA's journey: from nothing to a released model", "hi": "MONA का सफ़र: शून्य से रिलीज़ तक",
                 "hinglish": "MONA ka safar: zero se release tak"},
    "jr_explain": {
        "en": "{addr}, this is the real diary of your lab's first model. Every date, number and sentence below comes from "
              "MONA's own logs. Walk through it chapter by chapter.",
        "hi": "{addr}, यह आपकी लैब के पहले मॉडल की असली डायरी है। नीचे की हर तारीख़, संख्या और वाक्य MONA के अपने लॉग से है। "
              "अध्याय दर अध्याय चलिए।",
        "hinglish": "{addr}, yeh aapki lab ke pehle model ki asli diary hai. Neeche ki har date, number aur sentence MONA ke apne logs "
                    "se hai. Chapter by chapter chalo.",
    },
    "jr_loss": {"en": "Loss at this moment: {l}  (10.4 = random guessing; lower is better)",
                "hi": "इस समय लॉस: {l}  (10.4 = अंधा अंदाज़ा; कम बेहतर है)",
                "hinglish": "Is waqt loss: {l}  (10.4 = andha guess; kam behtar hai)"},
    "jr_wrote": {"en": "What MONA wrote then (prompt + MONA's words):", "hi": "तब MONA ने क्या लिखा (शुरुआत + MONA के शब्द):",
                 "hinglish": "Tab MONA ne kya likha (prompt + MONA ke words):"},
    "jr_curve": {"en": "The whole run (▲ = this chapter):", "hi": "पूरी ट्रेनिंग (▲ = यह अध्याय):",
                 "hinglish": "Poori training (▲ = yeh chapter):"},
    "jr_wait": {"en": "⏳ Not yet: this chapter is still ahead. Training is at {p}.",
                "hi": "⏳ अभी नहीं: यह अध्याय अभी आगे है। ट्रेनिंग {p} पर है।",
                "hinglish": "⏳ Abhi nahi: yeh chapter abhi aage hai. Training {p} par hai."},
    "jr_wait2": {"en": "⏳ Not yet: this chapter is still ahead.", "hi": "⏳ अभी नहीं: यह अध्याय अभी आगे है।",
                 "hinglish": "⏳ Abhi nahi: yeh chapter abhi aage hai."},
    "jr_keys": {"en": "↑↓ chapters   Esc back   F1 explain a word", "hi": "↑↓ अध्याय   Esc वापस   F1 शब्द का मतलब",
                "hinglish": "↑↓ chapters   Esc wapas   F1 word ka matlab"},
})

# (id, when, icon, {lang: (title, story)}, tokens in billions for live numbers or None, done-check or None)
CHAPTERS = [
    ("seed", "before", "🌱", {
        "en": ("The seed: MANAS v1",
               "It started with MANAS: a 10.8-million-parameter model that read Tulsidas letter by letter. It could imitate "
               "the rhythm of the verse, but it was tiny and knew only one style. The question became: how are the big "
               "models really made? The only way to truly understand was to build one, every step, from scratch."),
        "hi": ("बीज: MANAS v1",
               "शुरुआत MANAS से हुई: 1.08 करोड़ पैरामीटर का मॉडल जो तुलसीदास को अक्षर-अक्षर पढ़ता था। वह चौपाई की लय की नकल कर लेता था, पर "
               "बहुत छोटा था और एक ही शैली जानता था। सवाल उठा: बड़े मॉडल असल में कैसे बनते हैं? सच में समझने का एक ही तरीक़ा था: "
               "एक मॉडल ख़ुद बनाना, हर कदम, शुरू से।"),
        "hinglish": ("Beej: MANAS v1",
                     "Shuruaat MANAS se hui: 10.8 million parameters ka model jo Tulsidas ko letter-by-letter padhta tha. Woh chaupai ki lay "
                     "copy kar leta tha, par bahut chhota tha aur ek hi style jaanta tha. Sawaal utha: bade models asal mein kaise bante hain? "
                     "Sach mein samajhne ka ek hi tareeka tha: ek model khud banana, har step, scratch se.")}, None, None),
    ("plan", "11 Oct", "📐", {
        "en": ("The plan: how big?",
               "Like a real research team, we measured before spending: three model sizes (42M, 72M, 110M parameters) were "
               "timed on this laptop. With two nights of training, the Chinchilla rule (~20 tokens per parameter) pointed to "
               "110 million parameters and 2.5 billion tokens. Four languages: English, Hindi, Hinglish and Awadhi."),
        "hi": ("योजना: कितना बड़ा?",
               "असली रिसर्च टीम की तरह, ख़र्च से पहले मापा: तीन आकार (4.2, 7.2, 11 करोड़ पैरामीटर) इस लैपटॉप पर आज़माए। दो रातों की ट्रेनिंग "
               "के लिए Chinchilla नियम (~20 टोकन प्रति पैरामीटर) ने 11 करोड़ पैरामीटर और 2.5 अरब टोकन सुझाए। चार भाषाएँ: अंग्रेज़ी, हिंदी, "
               "हिंग्लिश और अवधी।"),
        "hinglish": ("Plan: kitna bada?",
                     "Asli research team ki tarah, kharch se pehle measure kiya: teen sizes (42M, 72M, 110M parameters) is laptop par test kiye. "
                     "Do raaton ki training ke liye Chinchilla rule (~20 tokens per parameter) ne 110M parameters aur 2.5 billion tokens suggest "
                     "kiye. Chaar languages: English, Hindi, Hinglish aur Awadhi.")}, None, None),
    ("data", "11 Oct", "📚", {
        "en": ("Gathering the library",
               "Downloaded from Hugging Face: FineWeb-Edu (English, 1.60 billion tokens), AI4Bharat Sangraha (Hindi 0.97 billion, "
               "Hinglish 0.13 billion) and Tulsidas's verse. Cleaning threw out short pages and wrong-script text, and fixed "
               "~70 strange machine-made Hinglish spellings."),
        "hi": ("लाइब्रेरी जुटाना",
               "Hugging Face से डाउनलोड: FineWeb-Edu (अंग्रेज़ी, 1.60 अरब टोकन), AI4Bharat Sangraha (हिंदी 0.97 अरब, हिंग्लिश 0.13 अरब) और "
               "तुलसीदास की चौपाइयाँ। सफ़ाई में छोटे पन्ने और ग़लत लिपि वाला पाठ हटाया, और मशीन से बनी ~70 अजीब हिंग्लिश वर्तनियाँ सुधारीं।"),
        "hinglish": ("Library jutana",
                     "Hugging Face se download: FineWeb-Edu (English, 1.60 billion tokens), AI4Bharat Sangraha (Hindi 0.97 billion, Hinglish "
                     "0.13 billion) aur Tulsidas ki chaupaiyan. Safai mein chhote pages aur galat script wala text hataya, aur machine se bani "
                     "~70 ajeeb Hinglish spellings theek ki.")}, None, None),
    ("tok", "11 Oct, 19:29", "🧩", {
        "en": ("Teaching MONA to read",
               "A 32,768-piece byte-level BPE tokenizer was trained on all four languages. It costs 1.33 tokens per Hindi word "
               "and 1.48 per English word: fair to Hindi, unlike many English-first models that spend 4 or more."),
        "hi": ("MONA को पढ़ना सिखाना",
               "चारों भाषाओं पर 32,768 टुकड़ों वाला byte-level BPE टोकनाइज़र ट्रेन हुआ। हिंदी के एक शब्द में 1.33 और अंग्रेज़ी में 1.48 टोकन: हिंदी "
               "के साथ न्याय, उन कई अंग्रेज़ी-केंद्रित मॉडलों के उलट जो 4 या ज़्यादा लगाते हैं।"),
        "hinglish": ("MONA ko padhna sikhana",
                     "Chaaron languages par 32,768 pieces wala byte-level BPE tokenizer train hua. Hindi ke ek word mein 1.33 aur English mein "
                     "1.48 tokens: Hindi ke saath insaaf, un kai English-first models ke ulat jo 4 ya zyada lagate hain.")}, None, None),
    ("pilot", "11 Oct", "🧪", {
        "en": ("The pilot run",
               "Before the big run, a tiny pilot model was trained, stopped and resumed on purpose. It caught a real bug: "
               "after a restart, the random-number state was restored on the wrong device. Fixed before it could ruin the "
               "real run. Real labs do the same: small rehearsals before the expensive show."),
        "hi": ("पायलट रन",
               "बड़ी ट्रेनिंग से पहले एक छोटा पायलट मॉडल जानबूझकर रोका और फिर चलाया गया। इससे एक असली बग पकड़ा गया: दोबारा शुरू होने पर "
               "रैंडम-नंबर की स्थिति ग़लत डिवाइस पर लौट रही थी। असली ट्रेनिंग बिगाड़ने से पहले ठीक हुआ। असली लैब भी यही करती हैं: महँगे शो "
               "से पहले छोटा रिहर्सल।"),
        "hinglish": ("Pilot run",
                     "Badi training se pehle ek chhota pilot model jaan-boojhkar roka aur phir chalaya gaya. Isse ek asli bug pakda gaya: restart "
                     "par random-number state galat device par wapas aa rahi thi. Asli training bigadne se pehle theek hua. Asli labs bhi yahi "
                     "karti hain: mehenge show se pehle chhota rehearsal.")}, None, None),
    ("launch", "11 Oct, 20:10", "🚀", {
        "en": ("Night 1: the big run begins",
               "Step 1: loss 10.55, which means MONA was guessing completely at random among 32,768 tokens. Ten steps later: 9.32. "
               "The first scare came within minutes: the watchdog couldn't see the hidden training process, thought it had "
               "died, and 'restarted' it three times. It was a false alarm; the watchdog was fixed to recognise it."),
        "hi": ("रात 1: बड़ी ट्रेनिंग शुरू",
               "कदम 1: लॉस 10.55, यानी MONA 32,768 टोकन में से बिल्कुल अंधा अंदाज़ा लगा रही थी। दस कदम बाद: 9.32। पहला डर कुछ ही मिनटों में "
               "आया: वॉचडॉग छिपी ट्रेनिंग प्रक्रिया को देख नहीं पाया, उसे लगा ट्रेनिंग रुक गई, और उसने तीन बार 'दोबारा शुरू' किया। यह झूठा "
               "अलार्म था; वॉचडॉग को ठीक किया गया।"),
        "hinglish": ("Raat 1: badi training shuru",
                     "Step 1: loss 10.55, yaani MONA 32,768 tokens mein se bilkul andha guess laga rahi thi. Das steps baad: 9.32. Pehla dar kuch "
                     "hi minutes mein aaya: watchdog chhupi training process ko dekh nahi paaya, use laga training ruk gayi, aur usne teen baar "
                     "'restart' kiya. Yeh false alarm tha; watchdog theek kiya gaya.")}, 0.005, None),
    ("words", "11 Oct, ~21:00", "👶", {
        "en": ("First words",
               "After 131 million tokens, MONA could already write grammatical-looking sentences, but with no sense. Like a "
               "toddler copying the sound of adult talk."),
        "hi": ("पहले शब्द",
               "13.1 करोड़ टोकन के बाद MONA व्याकरण जैसे दिखने वाले वाक्य लिखने लगी, पर बिना मतलब के। जैसे छोटा बच्चा बड़ों की बातों की आवाज़ "
               "की नकल करे।"),
        "hinglish": ("Pehle words",
                     "131 million tokens ke baad MONA grammar jaise dikhne wale sentences likhne lagi, par bina matlab ke. Jaise chhota bachcha "
                     "badon ki baaton ki awaaz copy kare.")}, 0.131, None),
    ("half", "11 Oct, 23:15", "📸", {
        "en": ("Half a billion tokens",
               "The first snapshot of MONA's brain was saved. Sentences now stay on one topic for longer. You can talk to this "
               "exact version in the Time machine (stage 7)."),
        "hi": ("आधा अरब टोकन",
               "MONA के दिमाग़ की पहली तस्वीर सहेजी गई। अब वाक्य ज़्यादा देर तक एक विषय पर टिके रहते हैं। इसी संस्करण से आप टाइम मशीन (चरण 7) "
               "में बात कर सकते हैं।"),
        "hinglish": ("Aadha billion tokens",
                     "MONA ke dimaag ka pehla snapshot save hua. Ab sentences zyada der tak ek topic par tike rehte hain. Isi version se aap "
                     "Time machine (stage 7) mein baat kar sakte ho.")}, 0.5, None),
    ("copyright", "12 Oct, 01:09", "⚖️", {
        "en": ("The copyright decision",
               "At 0.80 billion tokens, training was stopped on purpose. The Awadhi data contained a modern Hindi commentary "
               "on Tulsidas that is probably still under copyright. Decision: remove it completely and keep only the "
               "public-domain verse (245,710 tokens). It cost an hour; it was the right call. Real labs face this question "
               "with every dataset."),
        "hi": ("कॉपीराइट का फ़ैसला",
               "0.80 अरब टोकन पर ट्रेनिंग जानबूझकर रोकी गई। अवधी डेटा में तुलसीदास पर एक आधुनिक हिंदी टीका थी जो शायद अभी भी कॉपीराइट में है। "
               "फ़ैसला: उसे पूरी तरह हटाओ और सिर्फ़ सार्वजनिक चौपाइयाँ (2,45,710 टोकन) रखो। एक घंटा लगा; फ़ैसला सही था। असली लैब हर डेटासेट "
               "के साथ यह सवाल झेलती हैं।"),
        "hinglish": ("Copyright ka faisla",
                     "0.80 billion tokens par training jaan-boojhkar roki gayi. Awadhi data mein Tulsidas par ek modern Hindi commentary thi jo "
                     "shayad abhi bhi copyright mein hai. Faisla: use poori tarah hatao aur sirf public-domain chaupaiyan (2,45,710 tokens) rakho. "
                     "Ek ghanta laga; faisla sahi tha. Asli labs har dataset ke saath yeh sawaal face karti hain.")}, 0.80, None),
    ("heat", "12 Oct, 01:11–01:58", "🌡️", {
        "en": ("Heat and a cooling break",
               "After 6 hours of running, the power guard took its planned 20-minute break. Back at work, the GPU hit 83°C "
               "and the exhaust was blowing very hot air. A 5-minute freeze, then a heat limiter: above 77°C, MONA pauses "
               "for 0.03 seconds after each 0.18 seconds of work. At most 15% slower, much kinder to the laptop."),
        "hi": ("गर्मी और ठंडक का ब्रेक",
               "6 घंटे चलने के बाद पावर गार्ड ने तय 20 मिनट का ब्रेक लिया। वापस काम पर GPU 83°C पर पहुँचा और वेंट से बहुत गर्म हवा निकल रही थी। "
               "5 मिनट का ठहराव, फिर हीट लिमिटर: 77°C से ऊपर, MONA हर 0.18 सेकंड काम के बाद 0.03 सेकंड रुकती है। ज़्यादा से ज़्यादा 15% धीमा, "
               "लैपटॉप के लिए बहुत बेहतर।"),
        "hinglish": ("Garmi aur cooling break",
                     "6 ghante chalne ke baad power guard ne planned 20 minute ka break liya. Wapas kaam par GPU 83°C par pahuncha aur vent se "
                     "bahut garam hawa nikal rahi thi. 5 minute ka freeze, phir heat limiter: 77°C se upar, MONA har 0.18 second kaam ke baad "
                     "0.03 second rukti hai. Zyada se zyada 15% slow, laptop ke liye bahut behtar.")}, 0.823, None),
    ("billion", "12 Oct, 03:15", "🧠", {
        "en": ("One billion tokens",
               "The second snapshot. MONA now knows a lot of common facts and phrases in all three main languages, though it "
               "still mixes them up and invents things."),
        "hi": ("एक अरब टोकन",
               "दूसरी तस्वीर। MONA अब तीनों मुख्य भाषाओं के बहुत से आम तथ्य और वाक्यांश जानती है, हालाँकि अभी भी उन्हें मिला देती है और बातें गढ़ "
               "लेती है।"),
        "hinglish": ("Ek billion tokens",
                     "Doosra snapshot. MONA ab teeno main languages ke bahut se common facts aur phrases jaanti hai, haalaanki abhi bhi unhe mix "
                     "kar deti hai aur baatein bana leti hai.")}, 1.0, None),
    ("charger", "12 Oct, 07:10 & 07:29", "🔌", {
        "en": ("A loose charger",
               "Twice in the morning the laptop briefly lost power. Each time the power guard froze training in place within "
               "seconds and resumed it when power came back. No progress was lost. 1.5 billion tokens were reached at 06:54."),
        "hi": ("ढीला चार्जर",
               "सुबह दो बार लैपटॉप की बिजली कुछ पल के लिए गई। हर बार पावर गार्ड ने कुछ सेकंड में ट्रेनिंग को वहीं रोक दिया और बिजली लौटने पर "
               "फिर चालू कर दिया। कोई प्रगति नहीं खोई। 1.5 अरब टोकन 06:54 पर पूरे हुए।"),
        "hinglish": ("Dheela charger",
                     "Subah do baar laptop ki power kuch pal ke liye gayi. Har baar power guard ne kuch seconds mein training ko wahin freeze kiya "
                     "aur power lautne par phir chalu kar diya. Koi progress nahi khoyi. 1.5 billion tokens 06:54 par poore hue.")}, 1.5, None),
    ("decay", "12 Oct, afternoon", "🎯", {
        "en": ("The final stretch: cooling down",
               "For the last 15% of training (from 2.125 billion tokens), the learning rate slowly drops to 5%, and the mix gets "
               "4× more Awadhi verse. This 'annealing' is where loss falls fastest: like polishing after carving."),
        "hi": ("आख़िरी हिस्सा: धीमे होना",
               "ट्रेनिंग के आख़िरी 15% में (2.125 अरब टोकन से), लर्निंग रेट धीरे-धीरे 5% तक गिरता है, और मिश्रण में 4 गुना ज़्यादा अवधी चौपाइयाँ "
               "आती हैं। इसी 'एनीलिंग' में लॉस सबसे तेज़ गिरता है: जैसे तराशने के बाद चमकाना।"),
        "hinglish": ("Aakhri hissa: cooling down",
                     "Training ke aakhri 15% mein (2.125 billion tokens se), learning rate dheere-dheere 5% tak girta hai, aur mix mein 4 guna "
                     "zyada Awadhi chaupaiyan aati hain. Isi 'annealing' mein loss sabse tez girta hai: jaise taraashne ke baad chamkana.")}, 2.2, None),
    ("final", "12 Oct", "🏁", {
        "en": ("Pretraining complete",
               "2.5 billion tokens, 4,769 steps. MONA, the base model, is finished: it can continue any text in English, Hindi, "
               "Hinglish or Awadhi style, but it doesn't yet know how to have a conversation."),
        "hi": ("प्रीट्रेनिंग पूरी",
               "2.5 अरब टोकन, 4,769 कदम। बेस मॉडल MONA तैयार है: वह अंग्रेज़ी, हिंदी, हिंग्लिश या अवधी शैली में कोई भी पाठ आगे बढ़ा सकती है, पर "
               "अभी बातचीत करना नहीं जानती।"),
        "hinglish": ("Pretraining complete",
                     "2.5 billion tokens, 4,769 steps. Base model MONA ready hai: woh English, Hindi, Hinglish ya Awadhi style mein koi bhi text "
                     "aage badha sakti hai, par abhi baatcheet karna nahi jaanti.")}, 2.5, "final"),
    ("chat", "12 Oct", "💬", {
        "en": ("Chat tuning: MONA learns to answer",
               "127,025 example conversations (English, Hindi Q&A, Hinglish, Tulsidas verse completion, and 160 'who are you?' "
               "examples), 2 passes, graded only on MONA's own answers. The result: MONA-Chat."),
        "hi": ("चैट ट्यूनिंग: MONA जवाब देना सीखती है",
               "1,27,025 उदाहरण बातचीत (अंग्रेज़ी, हिंदी सवाल-जवाब, हिंग्लिश, तुलसीदास की चौपाई पूरी करना, और 160 'तुम कौन हो?' उदाहरण), 2 बार, "
               "अंक सिर्फ़ MONA के अपने जवाबों पर। नतीजा: MONA-Chat।"),
        "hinglish": ("Chat tuning: MONA jawab dena seekhti hai",
                     "1,27,025 example chats (English, Hindi Q&A, Hinglish, Tulsidas chaupai completion, aur 160 'tum kaun ho?' examples), 2 baar, "
                     "marks sirf MONA ke apne answers par. Result: MONA-Chat.")}, None, "chat"),
    ("eval", "12 Oct", "📝", {
        "en": ("The report card",
               "MONA was tested on text it never saw: bits per byte for every language, multiple-choice questions, and chat "
               "checks. Open stage 9 to read the results."),
        "hi": ("रिपोर्ट कार्ड",
               "MONA को उस पाठ पर जाँचा गया जो उसने कभी नहीं देखा: हर भाषा के लिए bits per byte, बहुविकल्पीय सवाल, और चैट जाँच। नतीजे पढ़ने के "
               "लिए चरण 9 खोलिए।"),
        "hinglish": ("Report card",
                     "MONA ko us text par test kiya gaya jo usne kabhi nahi dekha: har language ke liye bits per byte, multiple-choice sawaal, aur "
                     "chat checks. Results padhne ke liye stage 9 kholo.")}, None, "eval"),
    ("release", "12 Oct", "🌍", {
        "en": ("Release to the world",
               "Four checks passed (models exist, scores sensible, chat replies real, copyright scan clean), then MONA and "
               "MONA-Chat went public on Hugging Face under MIT, with a model card and data credits. And this app became "
               "the way anyone can open MONA up and see how an LLM works."),
        "hi": ("दुनिया के लिए रिलीज़",
               "चार जाँच पास हुईं (मॉडल मौजूद, अंक समझदार, चैट जवाब असली, कॉपीराइट स्कैन साफ़), फिर MONA और MONA-Chat, MIT लाइसेंस के तहत "
               "Hugging Face पर सार्वजनिक हुईं, मॉडल कार्ड और डेटा-श्रेय के साथ। और यह ऐप वह रास्ता बना जिससे कोई भी MONA को खोलकर देख सके "
               "कि LLM कैसे काम करता है।"),
        "hinglish": ("Duniya ke liye release",
                     "Chaar checks pass hue (models maujood, scores sensible, chat replies asli, copyright scan saaf), phir MONA aur MONA-Chat MIT "
                     "licence ke saath Hugging Face par public hui, model card aur data credits ke saath. Aur yeh app woh raasta bana jisse koi "
                     "bhi MONA ko kholkar dekh sake ki LLM kaise kaam karta hai.")}, None, "release"),
]

RUN = paths.RUNS_DIR / "mona_m"
CHAT = paths.RUNS_DIR / "mona_m_chat"
SAMPLE_LANG = {"en": "english", "hi": "hindi", "hinglish": "hinglish"}


def is_done(check):
    released = (paths.MODEL_DIR / "mona.pt").exists()          # installed copy = everything already happened
    if check == "final":
        return (RUN / "final.pt").exists() or released
    if check == "chat":
        return (CHAT / "DONE").exists() or (CHAT / "model.pt").exists() and released
    if check == "eval":
        return (RUN / "eval.txt").exists()
    if check == "release":
        return (RUN / "RELEASED").exists() or (released and not paths.DEV)
    return True


def train_rows():
    try:
        with open(RUN / "train_log.csv") as f:
            return [(int(r["tokens"]) / 1e9, float(r["loss"])) for r in csv.DictReader(f)]
    except (OSError, KeyError, ValueError):
        return []


def samples_at(billions):
    from ..engine.lessons import recorded_samples
    recs = recorded_samples()
    if not recs:
        return None
    best = min(recs, key=lambda r: abs(r[0] - billions))
    return best if abs(best[0] - billions) < 0.06 else None


def loss_curve(rows, mark, width=60, height=5):
    """The whole planned run (0 → 2.5B tokens) as a block chart; ▲ marks a chapter's moment."""
    cols = [[] for _ in range(width)]
    for b, loss in rows:
        cols[min(int(b / 2.5 * width), width - 1)].append(loss)
    vals = [sum(c) / len(c) if c else None for c in cols]
    known = [v for v in vals if v is not None]
    if not known:
        return Text("")
    lo, hi = min(known), max(known)
    span = (hi - lo) or 1
    blocks = " ▁▂▃▄▅▆▇█"
    out = Text()
    for row in range(height - 1, -1, -1):
        out.append(f"{hi:5.1f} " if row == height - 1 else (f"{lo:5.1f} " if row == 0 else "      "), style="#5a5f7c")
        for v in vals:
            if v is None:
                out.append("·" if row == 0 else " ", style="#3a3f5c")
            else:
                lv = round((v - lo) / span * height * 8)
                out.append(blocks[min(max(lv - row * 8, 0), 8)], style="#06d6a0")
        out.append("\n")
    if mark is not None:
        out.append("      " + " " * min(int(mark / 2.5 * width), width - 1) + "▲", style="bold #ffd166")
    out.append("\n      0" + " " * (width - 6) + "2.5B tokens", style="#5a5f7c")
    return out


class JourneyScreen(Screen):
    BINDINGS = [Binding("escape", "app.pop_screen", "back")]

    def compose(self) -> ComposeResult:
        with Horizontal(classes="lab-head"):
            yield Avatar(id="avatar", classes="lab-avatar")
            yield Static(id="title", classes="lab-title")
        yield Static(id="explain", classes="explain")
        with Horizontal(id="tour-cols"):
            yield OptionList(id="chapters")
            with VerticalScroll(id="tour-right"):
                yield Static(id="chapter", classes="panel")
        yield Static(id="keys", classes="keys")

    def on_mount(self):
        self.rows = train_rows()
        self.refresh_texts()
        box = self.query_one("#chapters", OptionList)
        box.highlighted = 0
        box.focus()

    def refresh_texts(self):
        app, tr = self.app, self.app.tr
        self.query_one("#title", Static).update(tr("jr_title"))
        self.query_one("#explain", Static).update(tr("jr_explain"))
        self.query_one("#keys", Static).update(tr("jr_keys"))
        box = self.query_one("#chapters", OptionList)
        keep = box.highlighted
        box.clear_options()
        for cid, when, icon, d, billions, check in CHAPTERS:
            title = d[app.state.lang][0]
            ahead = self.ahead(billions, check)
            label = Text.assemble((f" {icon} ", ""), (app.roman(title) if app.state.romanize else title,
                                                      "#5a5f7c" if ahead else "bold"))
            box.add_option(Option(label, id=cid))
        box.highlighted = keep if keep is not None else 0
        self.show()

    def ahead(self, billions, check):
        if check:
            return not is_done(check)
        if billions is None:
            return False
        if (RUN / "final.pt").exists() or (paths.MODEL_DIR / "mona.pt").exists():
            return False
        return bool(self.rows) and self.rows[-1][0] < billions

    def on_option_list_option_highlighted(self, event):
        self.show()

    def show(self):
        app, tr = self.app, self.app.tr
        idx = self.query_one("#chapters", OptionList).highlighted or 0
        cid, when, icon, d, billions, check = CHAPTERS[idx]
        title, story = d[app.state.lang]
        out = Text(f"{icon} {title}", style="bold #ffd166")
        out.append(f"    {when}\n\n", style="#8a8fb0")
        out.append(story + "\n\n", style="#e8e8f0")
        if self.ahead(billions, check):
            seen = self.rows[-1][0] if self.rows else 0
            out.append((tr("jr_wait", p=f"{seen:.2f}B / 2.5B tokens") if self.rows else tr("jr_wait2")) + "\n\n",
                       style="bold #f4a3c0")
        elif billions is not None and self.rows:
            near = min(self.rows, key=lambda r: abs(r[0] - billions))
            out.append(tr("jr_loss", l=f"{near[1]:.2f}") + "\n\n", style="bold #8ecae6")
            rec = samples_at(billions)
            lang = SAMPLE_LANG[app.state.lang]
            if rec and lang in rec[1]:
                out.append(tr("jr_wrote") + "\n", style="bold #06d6a0")
                out.append(f"“{rec[1][lang][:260]}…”\n\n", style="italic #c9cce0")
        if self.rows:
            out.append(tr("jr_curve") + "\n", style="#8a8fb0")
            out.append_text(loss_curve(self.rows, billions))
        self.query_one("#chapter", Static).update(app.roman(out.plain) if app.state.romanize else out)
        if idx == len(CHAPTERS) - 1:
            app.state.complete("journey")
