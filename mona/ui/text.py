"""Every word the app shows, in English / हिंदी / Hinglish, and per depth where it matters.

An entry is either {lang: text} or {lang: {depth: text}}. The app shows English only, at two depths
(simple / engineer); the older "hi" / "hinglish" / "student" wording is kept in the dictionaries but never shown.

Plain-language rule: a technical word is always explained in plain words the first time.
"""
import re

from indic_transliteration import sanscript
from indic_transliteration.sanscript import transliterate

STAGES = [  # id, English, हिंदी, Hinglish
    ("lm", "What is a language model?", "भाषा मॉडल क्या है?", "Language model kya hai?"),
    ("data", "Data", "डेटा", "Data"),
    ("tokens", "Tokens", "टोकन", "Tokens"),
    ("embeddings", "Embeddings", "एम्बेडिंग", "Embeddings"),
    ("attention", "Attention", "अटेंशन", "Attention"),
    ("layers", "Layers", "लेयर", "Layers"),
    ("next", "Next word", "अगला शब्द", "Agla shabd"),
    ("training", "Training", "ट्रेनिंग", "Training"),
    ("chat", "Chat tuning", "चैट ट्यूनिंग", "Chat tuning"),
    ("evals", "Evals", "परीक्षा (Evals)", "Evals"),
    ("rag", "RAG", "RAG", "RAG"),
    ("beyond", "Beyond", "आगे", "Aage"),
]
READY = {"lm", "data", "tokens", "embeddings", "next", "attention", "training", "layers", "evals", "chat", "rag", "beyond"}          # stages that open in this version; the rest show "coming soon"

S = {
    "tagline": {
        "en": "Understand AI from the inside: look, experiment, build.",
        "hi": "AI को अंदर से समझिए: देखिए, प्रयोग कीजिए, बनाइए।",
        "hinglish": "AI ko andar se samjho: dekho, experiment karo, banao.",
    },
    "hello": {
        "en": {"simple": "I guess the next word, one piece at a time. Follow the path on the left to see how, step by step.",
               "student": "I'm a 110-million-number language model, trained from scratch and fully open. Follow the path, "
                          "or jump to an experiment on the right.",
               "engineer": "MONA: 110M-param Llama-style decoder, 32K BPE, trained from scratch. Every view uses my real weights; "
                           "F8 shows the code behind it."},
        "hi": {"simple": "मैं अगला शब्द, एक-एक टुकड़ा करके, अंदाज़ा लगाती हूँ। कैसे, यह बाईं ओर के रास्ते पर कदम-दर-कदम देखिए।",
               "student": "मैं 11 करोड़ संख्याओं वाला भाषा मॉडल हूँ, शुरू से ट्रेन किया हुआ और पूरी तरह खुला। रास्ते पर चलिए, "
                          "या दाईं ओर किसी प्रयोग पर जाइए।",
               "engineer": "MONA: 11 करोड़ पैरामीटर वाला Llama-शैली डिकोडर, 32K BPE, शुरू से प्रशिक्षित। हर दृश्य मेरे असली वज़न से बनता है; "
                           "F8 उसके पीछे का कोड दिखाता है।"},
        "hinglish": {"simple": "Main agla shabd guess karti hoon, ek-ek tukda karke. Kaise, yeh left wale path par step-by-step dekho.",
                     "student": "Main 11 crore numbers wala language model hoon, scratch se trained aur poori tarah open. Path par chalo, "
                                "ya right mein kisi experiment par jao.",
                     "engineer": "MONA: 110M params ka Llama-style decoder, 32K BPE, scratch se trained. Har view mere asli weights se banta "
                                 "hai; F8 uske peeche ka code dikhata hai."},
    },
    "journey": {"en": "THE LEARNING PATH", "hi": "सीखने का रास्ता", "hinglish": "LEARNING PATH"},
    "progress": {"en": "your progress", "hi": "आपकी प्रगति", "hinglish": "aapki progress"},
    "keys_home": {
        "en": "↑↓ choose  Enter open  N next up  Tab path ⇄ explore  F1 explain a word  F8 show the code  F7 your name  D depth  Q quit",
        "hi": "↑↓ चुनें  Enter खोलें  N अगला  Tab रास्ता ⇄ और  F1 शब्द का मतलब  F8 कोड देखें  F7 आपका नाम  L/D/R भाषा/गहराई/रोमन  Q बंद",
        "hinglish": "↑↓ chuno  Enter kholo  N agla  Tab path ⇄ explore  F1 word ka matlab  F8 code dekho  F7 aapka naam  L/D/R bhasha/depth/roman  Q band",
    },
    "soon": {"en": "Coming soon: this stage is being built.", "hi": "जल्द आ रहा है: यह चरण बन रहा है।",
             "hinglish": "Jaldi aa raha hai: yeh stage ban raha hai."},
    "loading": {"en": "Waking MONA up…", "hi": "MONA को जगा रहे हैं…", "hinglish": "MONA ko jaga rahe hain…"},
    "depth_name": {"en": {"simple": "Simple", "engineer": "Engineer"},
                   "hi": {"simple": "सरल", "student": "विद्यार्थी", "engineer": "इंजीनियर"},
                   "hinglish": {"simple": "Simple", "student": "Student", "engineer": "Engineer"}},

    # ── display check (first run) ────────────────────────────────────────────
    "check_title": {"en": "Quick check: can your terminal draw Hindi?", "hi": "छोटी जाँच: क्या आपका टर्मिनल हिंदी ठीक दिखाता है?",
                    "hinglish": "Chhoti check: kya aapka terminal Hindi theek dikhata hai?"},
    "check_q": {"en": "Do these words look right: no boxes, no floating marks?",
                "hi": "क्या ये शब्द सही दिख रहे हैं: कोई डिब्बा या अलग तैरती मात्रा नहीं?",
                "hinglish": "Kya yeh shabd sahi dikh rahe hain: koi box ya alag tairti matra nahi?"},
    "check_fix": {
        "en": "No problem. To fix it: Windows Terminal → Settings → your profile → Appearance → Font face: "
              "Nirmala UI (or Mangal). macOS Terminal and most Linux terminals work as they are.\n"
              "Until then, MONA will show Hindi in Latin letters (romanized). Press R anytime to switch.",
        "hi": "कोई बात नहीं। ठीक करने के लिए: Windows Terminal → Settings → आपकी प्रोफ़ाइल → Appearance → Font face: "
              "Nirmala UI (या Mangal)।\nतब तक MONA हिंदी को रोमन अक्षरों में दिखाएगी। कभी भी R दबाकर बदल सकते हैं।",
        "hinglish": "Koi baat nahi. Theek karne ke liye: Windows Terminal → Settings → aapki profile → Appearance → "
                    "Font face: Nirmala UI (ya Mangal).\nTab tak MONA Hindi ko roman letters mein dikhayegi. R dabakar kabhi bhi badlo.",
    },
    "yes": {"en": "Yes, looks right", "hi": "हाँ, सही है", "hinglish": "Haan, sahi hai"},
    "no": {"en": "No, it's broken", "hi": "नहीं, टूटा हुआ है", "hinglish": "Nahi, toota hua hai"},

    "back": {"en": "Esc back", "hi": "Esc वापस", "hinglish": "Esc wapas"},
}


def register(entries):
    """Each lab adds its own text when it is first opened."""
    S.update(entries)


def t(key, lang="en", depth="simple", **fmt):
    entry = S[key]
    val = entry["en"]                          # the app is English-only; hi / hinglish entries are legacy
    if isinstance(val, dict):
        val = val.get(depth) or val.get("simple") or val.get("student")
    return val.format(**fmt) if fmt else val


def stage_name(stage, lang):
    _, en, hi, hinglish = stage
    return {"en": en, "hi": hi, "hinglish": hinglish}[lang]


# ── romanized display for terminals that can't draw Devanagari ──────────────
_DEVANAGARI = re.compile(r"[ऀ-ॿ]+")
_ITRANS_FIX = [("||", "."), ("|", "."), ("j~n", "gy"), (".DH", "dh"), (".D", "d"), (".N", "n"), ("~N", "n"),
               ("~n", "n"), ("RRi", "ri"), ("R^i", "ri"), ("x", "ksh"), ("Sh", "sh"), ("A", "a"), ("I", "i"), ("U", "u"), ("M", "n"), ("T", "t"),
               ("D", "d"), ("N", "n"), ("L", "l"), (".h", ""), ("H", "h"), ("^", "")]


def _roman_word(word):
    word = word.replace("ॉ", "ो").replace("ॅ", "े")          # English loan vowels (डॉक्टर, सेंटर): no ITRANS letter
    s = transliterate(word, sanscript.DEVANAGARI, sanscript.ITRANS)
    if len(s) > 2:
        s = re.sub(r"(?<=[^aeiouAEIOU])a$", "", s)       # drop the silent final 'a' (भारत -> bhaarat -> bharat)
    for a, b in _ITRANS_FIX:
        s = s.replace(a, b)
    return s.lower()


def romanize(text):
    return _DEVANAGARI.sub(lambda m: _roman_word(m.group(0)), text)
