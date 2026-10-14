"""How AI labs build models: the life of a model, team by team, next to what MONA did at each step.

Each team is explained in plain words: what big labs do, what MONA's build did (real numbers), and the key
question that team has to answer. Enter opens the matching stage to see it for real.
"""
from rich.text import Text
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, VerticalScroll
from textual.screen import Screen
from textual.widgets import OptionList, Static
from textual.widgets.option_list import Option

from .text import register
from .widgets import Avatar

register({
    "tour_title": {"en": "How AI labs build models", "hi": "AI लैब मॉडल कैसे बनाती हैं", "hinglish": "AI labs models kaise banati hain"},
    "tour_explain": {
        "en": "{addr}, every big AI lab (OpenAI, Google DeepMind, Anthropic, Meta…) is organised around the life of a model. "
              "Pick a team to see what it does. MONA was built on one laptop, but every one of these jobs still had to be done.",
        "hi": "{addr}, हर बड़ी AI लैब (OpenAI, Google DeepMind, Anthropic, Meta…) एक मॉडल के जीवन के इर्द-गिर्द बनी होती है। "
              "कोई टीम चुनकर देखिए वह क्या करती है। MONA एक लैपटॉप पर बनी, पर ये सारे काम फिर भी करने पड़े।",
        "hinglish": "{addr}, har badi AI lab (OpenAI, Google DeepMind, Anthropic, Meta…) ek model ki life ke around bani hoti hai. "
                    "Koi team chuno aur dekho woh kya karti hai. MONA ek laptop par bani, par yeh saare kaam phir bhi karne pade.",
    },
    "tour_big": {"en": "🏢 In a frontier lab", "hi": "🏢 बड़ी लैब में", "hinglish": "🏢 Badi lab mein"},
    "tour_ours": {"en": "🧪 How MONA did it", "hi": "🧪 MONA में कैसे हुआ", "hinglish": "🧪 MONA mein kaise hua"},
    "tour_q": {"en": "🤔 The key question", "hi": "🤔 मुख्य सवाल", "hinglish": "🤔 Main sawaal"},
    "tour_open": {"en": "Enter: see it live in stage “{s}”", "hi": "Enter: चरण “{s}” में असली में देखिए",
                  "hinglish": "Enter: stage “{s}” mein live dekho"},
    "tour_keys": {"en": "↑↓ choose a team   Enter open its stage   Esc back   F1 explain a word",
                  "hi": "↑↓ टीम चुनें   Enter उसका चरण खोलें   Esc वापस   F1 शब्द का मतलब",
                  "hinglish": "↑↓ team chuno   Enter uska stage kholo   Esc wapas   F1 word ka matlab"},
})

# (id, icon, {lang: (team name, big labs, MONA, key question)}, stage to open)
TEAMS = [
    ("cycle", "🔁", {
        "en": ("The life of a model (overview)",
               "1 Research picks the recipe → 2 Data gathers and cleans text → 3 Infrastructure readies thousands of GPUs → "
               "4 Pretraining runs for weeks or months → 5 Post-training turns it into an assistant (SFT, then RLHF) → "
               "6 Evals & Safety test it and try to break it → 7 Launch publishes it with a model card, then watches how people use it. "
               "Then the cycle starts again for the next model.",
               "MONA went through all 7 steps in a few days on one laptop: 1 size chosen with scaling laws → 2 4 languages cleaned → "
               "3 one RTX 5080 laptop GPU with guards → 4 2.5 billion tokens in ~30 hours → 5 127,000 chat examples → "
               "6 bits-per-byte tests and copyright scan → 7 release on Hugging Face.",
               "Pick a team on the left. Each one faces a hard trade-off; see how it was handled for MONA."),
        "hi": ("एक मॉडल का जीवन (झलक)",
               "1 रिसर्च नुस्ख़ा चुनती है → 2 डेटा टीम पाठ जुटाती और साफ़ करती है → 3 इंफ़्रास्ट्रक्चर हज़ारों GPU तैयार करता है → "
               "4 प्रीट्रेनिंग हफ़्तों या महीनों चलती है → 5 पोस्ट-ट्रेनिंग इसे सहायक बनाती है (SFT, फिर RLHF) → "
               "6 Evals और सेफ़्टी इसे जाँचते और तोड़ने की कोशिश करते हैं → 7 लॉन्च मॉडल कार्ड के साथ इसे जारी करता है और फिर इस्तेमाल पर नज़र रखता है। "
               "फिर अगले मॉडल के लिए चक्र दोबारा शुरू होता है।",
               "MONA कुछ ही दिनों में एक लैपटॉप पर सातों कदमों से गुज़री: 1 स्केलिंग नियमों से आकार चुना → 2 4 भाषाएँ साफ़ कीं → "
               "3 एक RTX 5080 लैपटॉप GPU, सुरक्षा गार्ड के साथ → 4 ~30 घंटे में 2.5 अरब टोकन → 5 1,27,000 चैट उदाहरण → "
               "6 bits-per-byte जाँच और कॉपीराइट स्कैन → 7 Hugging Face पर रिलीज़।",
               "बाईं ओर कोई टीम चुनिए। हर टीम के सामने एक कठिन चुनाव होता है; देखिए MONA में वह कैसे सुलझा।"),
        "hinglish": ("Ek model ki life (overview)",
                     "1 Research recipe chunti hai → 2 Data team text jutati aur saaf karti hai → 3 Infrastructure hazaron GPUs ready karta hai → "
                     "4 Pretraining hafton ya mahino chalti hai → 5 Post-training ise assistant banati hai (SFT, phir RLHF) → "
                     "6 Evals aur Safety ise test karte aur todne ki koshish karte hain → 7 Launch model card ke saath release karta hai, phir usage par nazar rakhta hai. "
                     "Phir agle model ke liye cycle dobara shuru hota hai.",
                     "MONA kuch hi dinon mein ek laptop par saaton steps se guzri: 1 scaling laws se size chuna → 2 4 languages saaf ki → "
                     "3 ek RTX 5080 laptop GPU, guards ke saath → 4 ~30 ghante mein 2.5 billion tokens → 5 1,27,000 chat examples → "
                     "6 bits-per-byte tests aur copyright scan → 7 Hugging Face par release.",
                     "Left mein koi team chuno. Har team ke saamne ek mushkil trade-off hota hai; dekho MONA mein woh kaise suljha.")}, "lm"),
    ("research", "🔬", {
        "en": ("1 · Research",
               "Scientists run hundreds of small 'pilot' models to find the best recipe: how big, how much data, which architecture. "
               "Scaling laws let them predict how good a huge model will be before paying for it. A single big run can cost "
               "tens of millions of dollars, so guessing wrong is very expensive.",
               "We measured three sizes on this laptop (42M, 72M, 110M parameters) and used the Chinchilla rule (~20 tokens per parameter) "
               "to pick 110M parameters and 2.5 billion tokens: the best model that fits two nights of training. "
               "Design: Llama-style (RMSNorm, RoPE, SwiGLU), the same family as today's open models.",
               "How big should a model be for a given amount of compute? Try the Scaling laws explorer (P)."),
        "hi": ("1 · रिसर्च",
               "वैज्ञानिक सैकड़ों छोटे 'पायलट' मॉडल चलाकर सबसे अच्छा नुस्ख़ा खोजते हैं: कितना बड़ा, कितना डेटा, कौन सा डिज़ाइन। "
               "स्केलिंग नियम पैसे ख़र्च करने से पहले ही बता देते हैं कि बड़ा मॉडल कितना अच्छा होगा। एक बड़ी ट्रेनिंग करोड़ों डॉलर की "
               "हो सकती है, इसलिए ग़लत अंदाज़ा बहुत महँगा पड़ता है।",
               "हमने इस लैपटॉप पर तीन आकार मापे (4.2, 7.2 और 11 करोड़ पैरामीटर) और Chinchilla नियम (~20 टोकन प्रति पैरामीटर) से "
               "11 करोड़ पैरामीटर और 2.5 अरब टोकन चुने: दो रातों की ट्रेनिंग में सबसे अच्छा मॉडल। "
               "डिज़ाइन: Llama-शैली (RMSNorm, RoPE, SwiGLU), आज के खुले मॉडलों का ही परिवार।",
               "तय कंप्यूट में मॉडल कितना बड़ा हो? स्केलिंग नियम (P) आज़माइए।"),
        "hinglish": ("1 · Research",
                     "Scientists sainkdon chhote 'pilot' models chalakar sabse achhi recipe dhoondhte hain: kitna bada, kitna data, kaunsa design. "
                     "Scaling laws paisa kharch karne se pehle hi bata dete hain ki bada model kitna achha hoga. Ek badi training crore-on dollars "
                     "ki ho sakti hai, isliye galat guess bahut mehenga padta hai.",
                     "Humne is laptop par teen sizes measure kiye (42M, 72M, 110M parameters) aur Chinchilla rule (~20 tokens per parameter) se "
                     "110M parameters aur 2.5 billion tokens chune: do raaton ki training mein sabse achha model. "
                     "Design: Llama-style (RMSNorm, RoPE, SwiGLU), aaj ke open models ki hi family.",
                     "Fixed compute mein model kitna bada ho? Scaling laws explorer (P) try karo.")}, "layers"),
    ("data", "📚", {
        "en": ("2 · Data",
               "Often the biggest team. They collect trillions of tokens (web pages, books, code), remove spam, duplicates, "
               "personal information and toxic text, check licences, and choose the mix of languages and topics. "
               "Better data beats a bigger model surprisingly often.",
               "English (FineWeb-Edu), Hindi and Hinglish (AI4Bharat Sangraha), Awadhi (Tulsidas's verse). We dropped short and "
               "wrong-script documents, fixed ~70 badly spelled Hinglish words, and removed a copyrighted Hindi commentary "
               "at 0.8 billion tokens, keeping only the public-domain verse.",
               "What goes in, what stays out? Be the data curator in stage 1."),
        "hi": ("2 · डेटा",
               "अक्सर सबसे बड़ी टीम। ये खरबों टोकन जुटाते हैं (वेब पेज, किताबें, कोड), स्पैम, दोहराव, निजी जानकारी और ज़हरीला पाठ हटाते हैं, "
               "लाइसेंस जाँचते हैं, और भाषाओं व विषयों का मिश्रण तय करते हैं। अच्छा डेटा अक्सर बड़े मॉडल से भी ज़्यादा काम आता है।",
               "अंग्रेज़ी (FineWeb-Edu), हिंदी और हिंग्लिश (AI4Bharat Sangraha), अवधी (तुलसीदास की चौपाइयाँ)। हमने छोटे और ग़लत लिपि वाले "
               "दस्तावेज़ हटाए, ~70 ग़लत वर्तनी वाले हिंग्लिश शब्द सुधारे, और 0.8 अरब टोकन पर एक कॉपीराइट वाली हिंदी टीका हटाई, "
               "सिर्फ़ सार्वजनिक चौपाइयाँ रखीं।",
               "क्या अंदर जाए, क्या बाहर रहे? चरण 1 में डेटा क्यूरेटर बनिए।"),
        "hinglish": ("2 · Data",
                     "Aksar sabse badi team. Yeh trillions tokens jutaate hain (web pages, books, code), spam, duplicates, personal info aur "
                     "toxic text hatate hain, licences check karte hain, aur languages aur topics ka mix decide karte hain. "
                     "Achha data aksar bade model se bhi zyada kaam aata hai.",
                     "English (FineWeb-Edu), Hindi aur Hinglish (AI4Bharat Sangraha), Awadhi (Tulsidas ki chaupaiyan). Humne chhote aur galat "
                     "script wale documents hataye, ~70 galat spelling wale Hinglish words theek kiye, aur 0.8 billion tokens par ek copyrighted "
                     "Hindi commentary hatayi, sirf public-domain chaupaiyan rakhin.",
                     "Kya andar jaaye, kya bahar rahe? Stage 1 mein data curator bano.")}, "data"),
    ("infra", "🖥️", {
        "en": ("3 · Infrastructure",
               "Engineers wire together thousands of GPUs, keep them cool and fed with data, and make sure a crash on one machine "
               "doesn't lose weeks of work. Failures are normal at that scale: GPUs break every day, so everything is checkpointed "
               "and restarted automatically.",
               "One laptop GPU, guarded like a data centre: checkpoints every 30 minutes, a watchdog that restarts dead or "
               "hung training, a power guard that freezes training when the charger is unplugged, a heat limiter at 77°C, "
               "and automatic start after a reboot. All of these were needed for real (see Training failures, I).",
               "Speed or safety? How hot is too hot? Work through the real failures in Training failures (I)."),
        "hi": ("3 · इंफ़्रास्ट्रक्चर",
               "इंजीनियर हज़ारों GPU जोड़ते हैं, उन्हें ठंडा रखते हैं और डेटा पहुँचाते हैं, और ध्यान रखते हैं कि एक मशीन का क्रैश हफ़्तों का काम न "
               "खो दे। इतने बड़े पैमाने पर ख़राबी आम है: रोज़ GPU टूटते हैं, इसलिए सब कुछ चेकपॉइंट होता है और अपने-आप दोबारा शुरू होता है।",
               "एक लैपटॉप GPU, डेटा सेंटर की तरह सुरक्षित: हर 30 मिनट चेकपॉइंट, रुकी या अटकी ट्रेनिंग दोबारा चलाने वाला वॉचडॉग, चार्जर हटने पर "
               "ट्रेनिंग रोकने वाला पावर गार्ड, 77°C पर हीट लिमिटर, और रीबूट के बाद अपने-आप शुरू। ये सब सच में काम आए (ट्रेनिंग की गड़बड़ियाँ, I देखिए)।",
               "रफ़्तार या सुरक्षा? कितनी गर्मी ज़्यादा है? ट्रेनिंग की गड़बड़ियाँ (I) में असली समस्याएँ सुलझाइए।"),
        "hinglish": ("3 · Infrastructure",
                     "Engineers hazaron GPUs jodte hain, unhe thanda rakhte hain aur data pahunchaate hain, aur dhyaan rakhte hain ki ek machine ka "
                     "crash hafton ka kaam na kho de. Itne bade scale par failure normal hai: roz GPUs toot-te hain, isliye sab kuch checkpoint "
                     "hota hai aur apne-aap restart hota hai.",
                     "Ek laptop GPU, data centre ki tarah guarded: har 30 minute checkpoint, ruki ya atki training restart karne wala watchdog, "
                     "charger hatne par training freeze karne wala power guard, 77°C par heat limiter, aur reboot ke baad auto-start. "
                     "Yeh sab sach mein kaam aaye (Training failures, I dekho).",
                     "Speed ya safety? Kitni garmi zyada hai? Training failures (I) mein asli problems suljhao.")}, "training"),
    ("pretrain", "🏋️", {
        "en": ("4 · Pretraining",
               "The big run: the model reads trillions of tokens and learns to guess the next one. It runs for weeks to months "
               "on thousands of GPUs. A small team watches the loss curve day and night, ready to roll back if it spikes.",
               "2.5 billion tokens, 4,769 steps of 524,288 tokens each, about 30 hours over two nights. The loss fell from "
               "10.4 (random guessing) to about 3.2. Every half-billion tokens we saved a snapshot of MONA's brain, so you "
               "can watch it grow up in the Time machine.",
               "When is the model 'done'? Watch MONA's real training in stage 7, then its full story in the Journey (J)."),
        "hi": ("4 · प्रीट्रेनिंग",
               "बड़ी ट्रेनिंग: मॉडल खरबों टोकन पढ़कर अगला टोकन अंदाज़ा लगाना सीखता है। यह हज़ारों GPU पर हफ़्तों से महीनों तक चलती है। "
               "एक छोटी टीम दिन-रात लॉस कर्व पर नज़र रखती है, ताकि उछाल आए तो पीछे लौट सके।",
               "2.5 अरब टोकन, 5,24,288 टोकन वाले 4,769 कदम, दो रातों में लगभग 30 घंटे। लॉस 10.4 (अंधा अंदाज़ा) से लगभग 3.2 तक गिरा। "
               "हर आधे अरब टोकन पर हमने MONA के दिमाग़ की तस्वीर सहेजी, ताकि आप टाइम मशीन में उसे बड़ा होते देख सकें।",
               "मॉडल कब 'तैयार' है? चरण 7 में MONA की असली ट्रेनिंग देखिए, फिर सफ़र (J) में पूरी कहानी।"),
        "hinglish": ("4 · Pretraining",
                     "Badi training: model trillions tokens padhkar agla token guess karna seekhta hai. Yeh hazaron GPUs par hafton se mahino tak "
                     "chalti hai. Ek chhoti team din-raat loss curve par nazar rakhti hai, taaki spike aaye to rollback kar sake.",
                     "2.5 billion tokens, 524,288 tokens wale 4,769 steps, do raaton mein lagbhag 30 ghante. Loss 10.4 (andha guess) se lagbhag "
                     "3.2 tak gira. Har aadhe billion tokens par humne MONA ke dimaag ka snapshot save kiya, taaki aap Time machine mein use "
                     "bada hote dekh sako.",
                     "Model kab 'ready' hai? Stage 7 mein MONA ki asli training dekho, phir Journey (J) mein poori kahani.")}, "training"),
    ("post", "🎓", {
        "en": ("5 · Post-training",
               "A pretrained model only continues text. Post-training teams turn it into an assistant: first SFT (thousands of "
               "example conversations written by people), then RLHF or similar methods, where people compare answers and the "
               "model learns which ones humans prefer: helpful, honest, harmless.",
               "SFT on 127,000 conversations in English, Hindi, Hinglish and Tulsidas verse, with loss masking (MONA is graded "
               "only on its own answers). That made MONA-Chat. We did not do RLHF: it needs many human ratings.",
               "What should your assistant say, and refuse? Compare base MONA and MONA-Chat in stage 8."),
        "hi": ("5 · पोस्ट-ट्रेनिंग",
               "प्रीट्रेन मॉडल सिर्फ़ पाठ आगे बढ़ाता है। पोस्ट-ट्रेनिंग टीमें उसे सहायक बनाती हैं: पहले SFT (लोगों की लिखी हज़ारों उदाहरण बातचीत), "
               "फिर RLHF जैसे तरीक़े, जहाँ लोग जवाबों की तुलना करते हैं और मॉडल सीखता है कि इंसान कौन से जवाब पसंद करते हैं: मददगार, ईमानदार, सुरक्षित।",
               "अंग्रेज़ी, हिंदी, हिंग्लिश और तुलसीदास की चौपाइयों की 1,27,000 बातचीत पर SFT, लॉस मास्किंग के साथ (MONA को सिर्फ़ अपने जवाबों पर "
               "अंक मिलते हैं)। इससे MONA-Chat बनी। हमने RLHF नहीं किया: उसके लिए बहुत सारी इंसानी रेटिंग चाहिए।",
               "आपका सहायक क्या कहे, और किससे मना करे? चरण 8 में बेस MONA और MONA-Chat की तुलना कीजिए।"),
        "hinglish": ("5 · Post-training",
                     "Pretrained model sirf text aage badhata hai. Post-training teams use assistant banati hain: pehle SFT (logon ki likhi hazaron "
                     "example chats), phir RLHF jaise methods, jahan log answers compare karte hain aur model seekhta hai ki insaan kaunse answers "
                     "pasand karte hain: helpful, honest, harmless.",
                     "English, Hindi, Hinglish aur Tulsidas ki chaupaiyon ki 1,27,000 chats par SFT, loss masking ke saath (MONA ko sirf apne answers "
                     "par marks milte hain). Isse MONA-Chat bani. Humne RLHF nahi kiya: uske liye bahut saari human ratings chahiye.",
                     "Aapka assistant kya bole, aur kis baat se mana kare? Stage 8 mein base MONA aur MONA-Chat compare karo.")}, "chat"),
    ("evals", "🧪", {
        "en": ("6 · Evals & Safety",
               "Before launch, the model takes hundreds of tests: knowledge, reasoning, coding, languages. Safety teams "
               "'red-team' it: they try hard to make it say harmful or false things, then fix what they find. A launch can "
               "be delayed or cancelled because of these results.",
               "Bits per byte on held-out text for every language, multiple-choice tests, chat checks, and a copyright scan "
               "that blocks the release if any commentary text is found. MONA is honest about its limits: it's small and "
               "often makes things up.",
               "Is it good enough to release? Read MONA's report card in stage 9."),
        "hi": ("6 · Evals और सेफ़्टी",
               "लॉन्च से पहले मॉडल सैकड़ों परीक्षाएँ देता है: ज्ञान, तर्क, कोडिंग, भाषाएँ। सेफ़्टी टीमें उसे 'रेड-टीम' करती हैं: पूरी कोशिश करती हैं "
               "कि वह हानिकारक या ग़लत बात कहे, फिर मिली कमियाँ ठीक करती हैं। इन नतीजों की वजह से लॉन्च टल या रद्द भी हो सकता है।",
               "हर भाषा के अनदेखे पाठ पर bits per byte, बहुविकल्पीय परीक्षा, चैट जाँच, और कॉपीराइट स्कैन जो टीका का कोई भी हिस्सा मिलने पर रिलीज़ "
               "रोक देता है। MONA अपनी सीमाओं के बारे में ईमानदार है: वह छोटी है और अक्सर बातें गढ़ लेती है।",
               "क्या यह रिलीज़ लायक है? चरण 9 में MONA का रिपोर्ट कार्ड पढ़िए।"),
        "hinglish": ("6 · Evals aur Safety",
                     "Launch se pehle model sainkdon tests deta hai: knowledge, reasoning, coding, languages. Safety teams use 'red-team' karti hain: "
                     "poori koshish karti hain ki woh harmful ya galat baat bole, phir mili kamiyan theek karti hain. In results ki wajah se launch "
                     "tal ya cancel bhi ho sakta hai.",
                     "Har language ke unseen text par bits per byte, multiple-choice tests, chat checks, aur copyright scan jo commentary ka koi bhi "
                     "hissa milne par release rok deta hai. MONA apni limits ke baare mein honest hai: woh chhoti hai aur aksar baatein bana leti hai.",
                     "Kya yeh release layak hai? Stage 9 mein MONA ka report card padho.")}, "evals"),
    ("launch", "🚀", {
        "en": ("7 · Launch",
               "Product and policy teams decide who gets the model and how (app, API, open weights), write the model card "
               "(what it is, what data, what limits), handle licences, and then watch real-world use to find problems "
               "the tests missed. What they learn feeds the next model.",
               "MONA is released openly under MIT on Hugging Face (JayF14/MONA) with a model card and a data-credits notice, "
               "only after every check passed. This app, the thing you're using, is the product: `pip install`, then `mona`.",
               "Open or closed? Who should be able to use your model? Read the model card on Hugging Face."),
        "hi": ("7 · लॉन्च",
               "प्रोडक्ट और नीति टीमें तय करती हैं कि मॉडल किसे और कैसे मिले (ऐप, API, खुले वज़न), मॉडल कार्ड लिखती हैं (क्या है, कौन सा डेटा, "
               "क्या सीमाएँ), लाइसेंस सँभालती हैं, और फिर असली इस्तेमाल पर नज़र रखती हैं ताकि वे कमियाँ मिलें जो परीक्षा में छूट गईं। "
               "जो सीखते हैं वह अगले मॉडल में जाता है।",
               "MONA, MIT लाइसेंस के तहत Hugging Face (JayF14/MONA) पर खुले रूप में जारी है, मॉडल कार्ड और डेटा-श्रेय के साथ, और सिर्फ़ तब जब हर "
               "जाँच पास हुई। यह ऐप, जो आप चला रहे हैं, वही प्रोडक्ट है: `pip install`, फिर `mona`।",
               "खुला या बंद? आपका मॉडल कौन इस्तेमाल कर सके? Hugging Face पर मॉडल कार्ड पढ़िए।"),
        "hinglish": ("7 · Launch",
                     "Product aur policy teams decide karti hain ki model kise aur kaise mile (app, API, open weights), model card likhti hain (kya hai, "
                     "kaunsa data, kya limits), licences sambhalti hain, aur phir real usage par nazar rakhti hain taaki woh kamiyan milein jo tests "
                     "mein chhoot gayin. Jo seekhte hain woh agle model mein jaata hai.",
                     "MONA, MIT licence ke saath Hugging Face (JayF14/MONA) par open release hai, model card aur data-credits ke saath, aur sirf tab "
                     "jab har check pass hua. Yeh app, jo aap chala rahe ho, wahi product hai: `pip install`, phir `mona`.",
                     "Open ya closed? Aapka model kaun use kar sake? Hugging Face par model card padho.")}, "beyond"),
]


class TourScreen(Screen):
    BINDINGS = [Binding("escape", "app.pop_screen", "back")]

    def compose(self) -> ComposeResult:
        with Horizontal(classes="lab-head"):
            yield Avatar(id="avatar", classes="lab-avatar")
            yield Static(id="title", classes="lab-title")
        yield Static(id="explain", classes="explain")
        with Horizontal(id="tour-cols"):
            yield OptionList(id="teams")
            with VerticalScroll(id="tour-right"):
                yield Static(id="brief", classes="panel")
        yield Static(id="keys", classes="keys")

    def on_mount(self):
        self.refresh_texts()
        teams = self.query_one("#teams", OptionList)
        teams.highlighted = 0
        teams.focus()

    def refresh_texts(self):
        app, tr = self.app, self.app.tr
        self.query_one("#title", Static).update(tr("tour_title"))
        self.query_one("#explain", Static).update(tr("tour_explain"))
        self.query_one("#keys", Static).update(tr("tour_keys"))
        teams = self.query_one("#teams", OptionList)
        keep = teams.highlighted
        teams.clear_options()
        for tid, icon, d, _ in TEAMS:
            name = d[app.state.lang][0]
            teams.add_option(Option(f" {icon} {app.roman(name) if app.state.romanize else name}", id=tid))
        teams.highlighted = keep if keep is not None else 0
        self.show()

    def on_option_list_option_highlighted(self, event):
        self.show()

    def current(self):
        teams = self.query_one("#teams", OptionList)
        return TEAMS[teams.highlighted or 0]

    def show(self):
        app, tr = self.app, self.app.tr
        _, icon, d, stage = self.current()
        name, big, ours, question = d[app.state.lang]
        out = Text(f"{icon} {name}\n\n", style="bold #f9e2af")
        for head, body, colour in ((tr("tour_big"), big, "#89dceb"), (tr("tour_ours"), ours, "#a6e3a1"),
                                   (tr("tour_q"), question, "#f5c2e7")):
            out.append(head + "\n", style=f"bold {colour}")
            out.append(body + "\n\n", style="#cdd6f4")
        from .text import STAGES, stage_name
        st = next(s for s in STAGES if s[0] == stage)
        out.append(tr("tour_open", s=stage_name(st, app.state.lang)), style="bold #f9e2af")
        self.query_one("#brief", Static).update(app.roman(out.plain) if app.state.romanize else out)
        if self.query_one("#teams", OptionList).highlighted == len(TEAMS) - 1:      # walked the whole floor
            app.state.complete("tour")

    def on_option_list_option_selected(self, event: OptionList.OptionSelected):
        from .screens import open_lab
        lab = open_lab(self.current()[3])
        if lab:
            self.app.push_screen(lab)
