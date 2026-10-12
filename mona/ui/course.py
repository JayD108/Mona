"""Train a model yourself: a guided course. The learner really trains a tiny language model, on this computer.

Every step is the same as MONA's, only smaller, and shows the real command used for the full-size MONA.
The work runs in a background thread, so the screen stays alive while the model learns.
"""
import re

from rich.text import Text
from textual import work
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, VerticalScroll
from textual.screen import Screen
from textual.widgets import Input, OptionList, Static
from textual.widgets.option_list import Option

from .text import register
from .widgets import Avatar, token_chips

register({
    "co_title": {"en": "Train your own model, step by step", "hi": "अपना मॉडल ट्रेन कीजिए, कदम दर कदम",
                 "hinglish": "Apna model train karo, step by step"},
    "co_explain": {
        "en": "{addr}, today you train a real language model yourself, on this computer, in about 2 minutes. It's built exactly "
              "like MONA, just 100× smaller. Choose a step and press Enter to run it. Go in order: 1 → 7.",
        "hi": "{addr}, आज आप ख़ुद एक असली भाषा मॉडल ट्रेन करेंगे, इसी कंप्यूटर पर, लगभग 2 मिनट में। यह बिल्कुल MONA जैसा बना है, बस 100 गुना "
              "छोटा। कोई कदम चुनिए और चलाने के लिए Enter दबाइए। क्रम से चलिए: 1 → 7।",
        "hinglish": "{addr}, aaj aap khud ek asli language model train karoge, isi computer par, lagbhag 2 minute mein. Yeh bilkul MONA "
                    "jaisa bana hai, bas 100 guna chhota. Koi step chuno aur chalane ke liye Enter dabao. Order mein chalo: 1 → 7.",
    },
    "co_run": {"en": "▶ Press Enter to run this step", "hi": "▶ यह कदम चलाने के लिए Enter दबाइए", "hinglish": "▶ Yeh step chalane ke liye Enter dabao"},
    "co_busy": {"en": "⏳ Working…", "hi": "⏳ काम चल रहा है…", "hinglish": "⏳ Kaam chal raha hai…"},
    "co_first": {"en": "{addr}, please finish step {n} first.", "hi": "{addr}, पहले कदम {n} पूरा कीजिए।", "hinglish": "{addr}, pehle step {n} poora karo."},
    "co_cmd": {"en": "How the full-size MONA did this step:", "hi": "पूरे आकार की MONA ने यह कदम कैसे किया:",
               "hinglish": "Full-size MONA ne yeh step kaise kiya:"},
    "co_device": {"en": "Running on: {d}", "hi": "यहाँ चल रहा है: {d}", "hinglish": "Yahan chal raha hai: {d}"},
    "co_cpu_note": {"en": "(CPU, because MONA's own training is using the GPU right now)",
                    "hi": "(CPU, क्योंकि अभी MONA की अपनी ट्रेनिंग GPU इस्तेमाल कर रही है)",
                    "hinglish": "(CPU, kyunki abhi MONA ki apni training GPU use kar rahi hai)"},
    "co_prompt": {"en": "Type a beginning for your model and press Enter", "hi": "अपने मॉडल के लिए शुरुआत लिखिए और Enter दबाइए",
                  "hinglish": "Apne model ke liye shuruaat likho aur Enter dabao"},
    "co_keys": {"en": "↑↓ step   Enter run   Esc back   F1 explain a word", "hi": "↑↓ कदम   Enter चलाएँ   Esc वापस   F1 शब्द का मतलब",
                "hinglish": "↑↓ step   Enter chalao   Esc wapas   F1 word ka matlab"},
    # results
    "co_r1": {"en": "Collected {c:,} characters (~{w:,} words) of real {l} text. 90% to learn from, 10% kept hidden for the final test.\n\nA peek:",
              "hi": "असली {l} पाठ के {c:,} अक्षर (~{w:,} शब्द) जुटाए। 90% सीखने के लिए, 10% आख़िरी परीक्षा के लिए छिपाकर रखा।\n\nएक झलक:",
              "hinglish": "Asli {l} text ke {c:,} characters (~{w:,} words) jutaaye. 90% seekhne ke liye, 10% final test ke liye chhupa kar rakha.\n\nEk jhalak:"},
    "co_r2": {"en": "Your tokenizer learned {v:,} pieces in {s:.1f} s. The same sentence, cut by your tokenizer and by MONA's (32,768 pieces):",
              "hi": "आपके टोकनाइज़र ने {s:.1f} सेकंड में {v:,} टुकड़े सीखे। वही वाक्य, आपके और MONA के (32,768 टुकड़े) टोकनाइज़र से कटा हुआ:",
              "hinglish": "Aapke tokenizer ne {s:.1f} second mein {v:,} pieces seekhe. Wahi sentence, aapke aur MONA ke (32,768 pieces) tokenizer se kata hua:"},
    "co_yours": {"en": "Yours ({n} tokens):", "hi": "आपका ({n} टोकन):", "hinglish": "Aapka ({n} tokens):"},
    "co_monas": {"en": "MONA's ({n} tokens):", "hi": "MONA का ({n} टोकन):", "hinglish": "MONA ka ({n} tokens):"},
    "co_r2b": {"en": "Fewer pieces = cheaper and faster. A bigger vocabulary learns longer pieces.",
               "hi": "कम टुकड़े = सस्ता और तेज़। बड़ी शब्दावली लंबे टुकड़े सीखती है।",
               "hinglish": "Kam pieces = sasta aur fast. Badi vocabulary lambe pieces seekhti hai."},
    "co_r3": {"en": "Your model has {p:,} parameters (MONA: 110,100,000, about {x}× more). Where they live:",
              "hi": "आपके मॉडल में {p:,} पैरामीटर हैं (MONA: 11,01,00,000, लगभग {x} गुना ज़्यादा)। वे कहाँ हैं:",
              "hinglish": "Aapke model mein {p:,} parameters hain (MONA: 110,100,000, lagbhag {x} guna zyada). Woh kahan hain:"},
    "co_r3b": {"en": "Right now every number is random. Ask it anything and you get gibberish:",
               "hi": "अभी हर संख्या बेतरतीब है। कुछ भी पूछिए, अनाप-शनाप मिलेगा:",
               "hinglish": "Abhi har number random hai. Kuch bhi poochho, bakwaas milega:"},
    "co_r4": {"en": "Step {s}/{n} · loss {l:.2f} · {t:.0f} s", "hi": "कदम {s}/{n} · लॉस {l:.2f} · {t:.0f} से.", "hinglish": "Step {s}/{n} · loss {l:.2f} · {t:.0f} s"},
    "co_r4_sample": {"en": "At step {s} it writes:", "hi": "कदम {s} पर यह लिखता है:", "hinglish": "Step {s} par yeh likhta hai:"},
    "co_r4_done": {"en": "Done! Loss fell from {a:.2f} to {b:.2f}. Your model learned real patterns from text, {addr}.",
                   "hi": "हो गया! लॉस {a:.2f} से {b:.2f} पर आया। आपके मॉडल ने पाठ से असली पैटर्न सीखे, {addr}।",
                   "hinglish": "Ho gaya! Loss {a:.2f} se {b:.2f} par aaya. Aapke model ne text se asli patterns seekhe, {addr}."},
    "co_r5": {"en": "Your model continues “{p}”:", "hi": "आपका मॉडल “{p}” को आगे बढ़ाता है:", "hinglish": "Aapka model “{p}” ko aage badhata hai:"},
    "co_r5b": {"en": "Try other beginnings below. It sounds like the language but makes little sense: it learned spelling and "
                     "rhythm, not meaning. That needs far more parameters and data, which is exactly what MONA has.",
               "hi": "नीचे और शुरुआत आज़माइए। भाषा जैसा लगता है पर मतलब कम है: इसने वर्तनी और लय सीखी, अर्थ नहीं। उसके लिए कहीं ज़्यादा पैरामीटर "
                     "और डेटा चाहिए, जो MONA के पास है।",
               "hinglish": "Neeche aur shuruaat try karo. Bhasha jaisa lagta hai par matlab kam hai: isne spelling aur lay seekhi, meaning nahi. "
                           "Uske liye kahin zyada parameters aur data chahiye, jo MONA ke paas hai."},
    "co_r6": {"en": "Final exam on the hidden 10% (bits per byte, lower = better):", "hi": "छिपे 10% पर आख़िरी परीक्षा (bits per byte, कम = बेहतर):",
              "hinglish": "Chhupe 10% par final exam (bits per byte, kam = behtar):"},
    "co_untrained": {"en": "Your model before training", "hi": "ट्रेनिंग से पहले आपका मॉडल", "hinglish": "Training se pehle aapka model"},
    "co_trained": {"en": "Your model after training", "hi": "ट्रेनिंग के बाद आपका मॉडल", "hinglish": "Training ke baad aapka model"},
    "co_mona": {"en": "MONA (110M, 2.5B tokens)", "hi": "MONA (11 करोड़, 2.5 अरब टोकन)", "hinglish": "MONA (110M, 2.5B tokens)"},
    "co_r6b": {"en": "🏅 Badge: Model Maker. You did data → tokenizer → model → training → generation → evaluation, {addr}: the "
                     "same pipeline as every frontier lab. Your model is saved in {p}",
               "hi": "🏅 बैज: Model Maker। आपने डेटा → टोकनाइज़र → मॉडल → ट्रेनिंग → लेखन → परीक्षा किया, {addr}: वही पाइपलाइन जो हर बड़ी लैब "
                     "चलाती है। आपका मॉडल यहाँ सहेजा गया: {p}",
               "hinglish": "🏅 Badge: Model Maker. Aapne data → tokenizer → model → training → generation → evaluation kiya, {addr}: wahi "
                           "pipeline jo har badi lab chalati hai. Aapka model yahan save hua: {p}"},
    "co_r7": {"en": "Same model, same data, same seed. Only the learning rate changes ({n} steps each):",
              "hi": "वही मॉडल, वही डेटा, वही seed। सिर्फ़ लर्निंग रेट बदला ({n} कदम हर बार):",
              "hinglish": "Wahi model, wahi data, wahi seed. Sirf learning rate badla ({n} steps har baar):"},
    "co_r7_run": {"en": "training with learning rate {lr}…", "hi": "लर्निंग रेट {lr} से ट्रेनिंग…", "hinglish": "learning rate {lr} se training…"},
    "co_r7_end": {"en": "Final test loss (lower = better):", "hi": "आख़िरी टेस्ट लॉस (कम = बेहतर):", "hinglish": "Final test loss (kam = behtar):"},
    "co_r7_why": {"en": "Too small: every step is timid, so it learns slowly. Too big: steps overshoot, the loss jumps around or "
                        "gets stuck. Somewhere in between is best, and finding it is a real part of every lab's work. MONA "
                        "uses 6e-4, a value known to work at this size (GPT-3's 125M-parameter model used it too).",
                  "hi": "बहुत छोटा: हर कदम डरपोक, इसलिए धीमी सीख। बहुत बड़ा: कदम आगे निकल जाते हैं, लॉस उछलता है या अटक जाता है। बीच में कहीं "
                        "सबसे अच्छा होता है, और उसे खोजना हर लैब के काम का असली हिस्सा है। MONA 6e-4 इस्तेमाल करती है, जो इस आकार पर काम करने वाला जाना-माना मान है (GPT-3 के 12.5 करोड़ पैरामीटर वाले मॉडल ने भी यही लिया)।",
                  "hinglish": "Bahut chhota: har step darpok, isliye slow learning. Bahut bada: steps aage nikal jaate hain, loss uchhalta hai "
                              "ya atak jaata hai. Beech mein kahin best hota hai, aur use dhoondhna har lab ke kaam ka asli hissa hai. MONA "
                              "6e-4 use karti hai, jo is size par kaam karne wali jaani-maani value hai (GPT-3 ke 125M model ne bhi yahi li)."},
    "co_r6c": {"en": "Next: a base model only continues text. To make it answer questions, labs do chat tuning: see stage 8.",
               "hi": "आगे: बेस मॉडल सिर्फ़ पाठ आगे बढ़ाता है। सवालों के जवाब दिलवाने के लिए लैब चैट ट्यूनिंग करती हैं: चरण 8 देखिए।",
               "hinglish": "Aage: base model sirf text aage badhata hai. Sawaalon ke jawab dilwane ke liye labs chat tuning karti hain: stage 8 dekho."},
})

LANG_NAME = {"en": {"en": "English", "hi": "Hindi", "hinglish": "Hinglish"},
             "hi": {"en": "अंग्रेज़ी", "hi": "हिंदी", "hinglish": "हिंग्लिश"},
             "hinglish": {"en": "English", "hi": "Hindi", "hinglish": "Hinglish"}}
PROMPT = {"en": "The history of", "hi": "भारत की", "hinglish": "aaj mausam"}
EXAMPLE = {"en": "The rivers of India are very long.", "hi": "भारत की नदियाँ बहुत लंबी हैं।", "hinglish": "Bharat ki nadiyan bahut lambi hain."}

# (title, what & why, the full-size command) per language
STEPS = {
    "en": [
        ("1 · Collect data", "Every model starts with text to learn from. Big labs gather trillions of words; you'll take about "
         "half a million characters of real text that MONA never trained on. Like a library: no books, no learning.",
         "python -m pipeline.mona_download english hindi hinglish   (2.7 billion tokens)\npython -m pipeline.mona_clean"),
        ("2 · Make a tokenizer", "The model can't read letters, only numbers. A tokenizer learns which pieces of words appear "
         "most often and gives each one a number. You'll learn 2,048 pieces from your text (MONA has 32,768).",
         "python -m pipeline.mona_tokenizer   (32,768 pieces, ~15 min)\npython -m pipeline.mona_tokenize"),
        ("3 · Build the model", "Now the brain: the same Llama-style transformer as MONA, with 4 layers instead of 12 and lists of "
         "128 numbers instead of 768. It starts with random numbers: it knows nothing yet.",
         "mona/model.py with MONA_M = 12 layers, d_model 768, 12 heads  →  110M parameters"),
        ("4 · Train it", "Show it text, let it guess the next token, measure how wrong it was (the loss), and nudge every number "
         "to do better. 300 times. Watch the loss fall and the writing improve.",
         "python -m scripts.mona_pretrain --name mona_m   (4,769 steps, 2.5B tokens, ~30 hours on a laptop GPU)"),
        ("5 · Let it write", "Give your model a beginning and let it continue, one token at a time: exactly how ChatGPT writes, "
         "too.", "python -m scripts.mona_chat --weights runs/mona_m_chat/model.pt"),
        ("6 · Test it", "A fair exam on the hidden 10% it never saw: bits per byte. It works across tokenizers, so you can "
         "compare your model with MONA directly.", "python -m scripts.mona_eval runs/mona_m/final.pt"),
        ("7 · Experiment: learning rate", "Science means changing ONE thing and measuring. Train the same tiny model three "
         "times, identical except for the learning rate (how big each correction step is), and compare the loss curves.",
         "python -m scripts.mona_pretrain --name test --lr 3e-4   (MONA used 6e-4, the usual value at this size)"),
    ],
    "hi": [
        ("1 · डेटा जुटाइए", "हर मॉडल सीखने के लिए पाठ से शुरू होता है। बड़ी लैब खरबों शब्द जुटाती हैं; आप लगभग पाँच लाख अक्षर असली पाठ लेंगे "
         "जिस पर MONA ने कभी ट्रेनिंग नहीं की। लाइब्रेरी की तरह: किताबें नहीं, तो सीखना नहीं।",
         "python -m pipeline.mona_download english hindi hinglish   (2.7 अरब टोकन)\npython -m pipeline.mona_clean"),
        ("2 · टोकनाइज़र बनाइए", "मॉडल अक्षर नहीं पढ़ सकता, सिर्फ़ संख्याएँ। टोकनाइज़र सीखता है कि शब्दों के कौन से टुकड़े सबसे ज़्यादा आते हैं और हर एक "
         "को एक संख्या देता है। आप अपने पाठ से 2,048 टुकड़े सीखेंगे (MONA के पास 32,768 हैं)।",
         "python -m pipeline.mona_tokenizer   (32,768 टुकड़े, ~15 मिनट)\npython -m pipeline.mona_tokenize"),
        ("3 · मॉडल बनाइए", "अब दिमाग़: MONA जैसा ही Llama-शैली का ट्रांसफ़ॉर्मर, 12 की जगह 4 लेयर और 768 की जगह 128 संख्याओं की सूचियाँ। यह "
         "बेतरतीब संख्याओं से शुरू होता है: अभी कुछ नहीं जानता।",
         "mona/model.py में MONA_M = 12 लेयर, d_model 768, 12 हेड  →  11 करोड़ पैरामीटर"),
        ("4 · ट्रेन कीजिए", "इसे पाठ दिखाइए, अगला टोकन अंदाज़ा लगाने दीजिए, नापिए कितना ग़लत था (लॉस), और हर संख्या को थोड़ा सुधारिए। 300 बार। "
         "लॉस गिरता और लिखावट सुधरती देखिए।",
         "python -m scripts.mona_pretrain --name mona_m   (4,769 कदम, 2.5 अरब टोकन, लैपटॉप GPU पर ~30 घंटे)"),
        ("5 · लिखवाइए", "अपने मॉडल को शुरुआत दीजिए और उसे आगे लिखने दीजिए, एक-एक टोकन: ChatGPT भी बिल्कुल ऐसे ही लिखता है।",
         "python -m scripts.mona_chat --weights runs/mona_m_chat/model.pt"),
        ("6 · परीक्षा लीजिए", "छिपे 10% पर निष्पक्ष परीक्षा जो इसने कभी नहीं देखा: bits per byte। यह हर टोकनाइज़र पर काम करता है, इसलिए आप अपने "
         "मॉडल की MONA से सीधी तुलना कर सकते हैं।", "python -m scripts.mona_eval runs/mona_m/final.pt"),
        ("7 · प्रयोग: लर्निंग रेट", "विज्ञान यानी एक चीज़ बदलकर नापना। वही छोटा मॉडल तीन बार ट्रेन कीजिए, सिर्फ़ लर्निंग रेट (हर सुधार कदम "
         "कितना बड़ा हो) अलग रखकर, और लॉस कर्व की तुलना कीजिए।",
         "python -m scripts.mona_pretrain --name test --lr 3e-4   (MONA ने 6e-4 इस्तेमाल किया, इस आकार का आम मान)"),
    ],
    "hinglish": [
        ("1 · Data jutao", "Har model seekhne ke liye text se shuru hota hai. Badi labs trillions words jutaati hain; aap lagbhag paanch "
         "lakh characters asli text loge jis par MONA ne kabhi training nahi ki. Library ki tarah: kitaabein nahi, to seekhna nahi.",
         "python -m pipeline.mona_download english hindi hinglish   (2.7 billion tokens)\npython -m pipeline.mona_clean"),
        ("2 · Tokenizer banao", "Model letters nahi padh sakta, sirf numbers. Tokenizer seekhta hai ki words ke kaun se pieces sabse zyada "
         "aate hain aur har ek ko ek number deta hai. Aap apne text se 2,048 pieces seekhoge (MONA ke paas 32,768 hain).",
         "python -m pipeline.mona_tokenizer   (32,768 pieces, ~15 min)\npython -m pipeline.mona_tokenize"),
        ("3 · Model banao", "Ab dimaag: MONA jaisa hi Llama-style transformer, 12 ki jagah 4 layers aur 768 ki jagah 128 numbers ki lists. "
         "Yeh random numbers se shuru hota hai: abhi kuch nahi jaanta.",
         "mona/model.py mein MONA_M = 12 layers, d_model 768, 12 heads  →  110M parameters"),
        ("4 · Train karo", "Ise text dikhao, agla token guess karne do, naapo kitna galat tha (loss), aur har number ko thoda sudhaaro. "
         "300 baar. Loss girte aur likhaai sudharte dekho.",
         "python -m scripts.mona_pretrain --name mona_m   (4,769 steps, 2.5B tokens, laptop GPU par ~30 ghante)"),
        ("5 · Likhwao", "Apne model ko shuruaat do aur use aage likhne do, ek-ek token: ChatGPT bhi bilkul aise hi likhta hai.",
         "python -m scripts.mona_chat --weights runs/mona_m_chat/model.pt"),
        ("6 · Test lo", "Chhupe 10% par fair exam jo isne kabhi nahi dekha: bits per byte. Yeh har tokenizer par kaam karta hai, isliye aap "
         "apne model ki MONA se seedhi comparison kar sakte ho.", "python -m scripts.mona_eval runs/mona_m/final.pt"),
        ("7 · Experiment: learning rate", "Science matlab EK cheez badlo aur naapo. Wahi chhota model teen baar train karo, "
         "sirf learning rate (har correction step kitna bada ho) alag rakhkar, aur loss curves compare karo.",
         "python -m scripts.mona_pretrain --name test --lr 3e-4   (MONA ne 6e-4 use kiya, is size ki common value)"),
    ],
}
TRAIN_STEPS = 300


def flat(text):
    """One line, but keep the leading space (it separates the prompt from the model's first word)."""
    return re.sub(r"\s+", " ", text)


def chart(losses, width=50, height=5):
    if not losses:
        return Text("")
    lo, hi = min(losses), max(losses)
    span = (hi - lo) or 1
    vals = [losses[min(int(i * len(losses) / width), len(losses) - 1)] for i in range(width)] if len(losses) < width else \
        [losses[int(i * len(losses) / width)] for i in range(width)]
    blocks = " ▁▂▃▄▅▆▇█"
    out = Text()
    for row in range(height - 1, -1, -1):
        out.append(f"{hi:5.2f} " if row == height - 1 else (f"{lo:5.2f} " if row == 0 else "      "), style="#5a5f7c")
        for v in vals:
            out.append(blocks[min(max(round((v - lo) / span * height * 8) - row * 8, 0), 8)], style="#06d6a0")
        out.append("\n")
    return out


class CourseScreen(Screen):
    BINDINGS = [Binding("escape", "app.pop_screen", "back")]

    def compose(self) -> ComposeResult:
        with Horizontal(classes="lab-head"):
            yield Avatar(id="avatar", classes="lab-avatar")
            yield Static(id="title", classes="lab-title")
        yield Static(id="explain", classes="explain")
        with Horizontal(id="tour-cols"):
            yield OptionList(id="steps")
            with VerticalScroll(id="tour-right"):
                yield Static(id="step-info", classes="panel")
                yield Static(id="step-out", classes="panel")
                yield Input(id="co-prompt")
        yield Static(id="keys", classes="keys")

    def on_mount(self):
        self.done = set()           # finished step numbers (1-6)
        self.busy = False
        self.out = {}               # step -> Text shown in the results panel
        self.lang = self.app.state.lang
        self.query_one("#co-prompt").display = False
        self.refresh_texts()
        box = self.query_one("#steps", OptionList)
        box.highlighted = 0
        box.focus()

    # ── layout ───────────────────────────────────────────────────────────────
    def refresh_texts(self):
        app, tr = self.app, self.app.tr
        self.query_one("#title", Static).update(tr("co_title"))
        self.query_one("#explain", Static).update(tr("co_explain"))
        self.query_one("#keys", Static).update(tr("co_keys"))
        self.query_one("#co-prompt", Input).placeholder = tr("co_prompt")
        box = self.query_one("#steps", OptionList)
        keep = box.highlighted
        box.clear_options()
        for n, (title, _, _) in enumerate(STEPS[app.state.lang], 1):
            mark = "✓" if n in self.done else "○"
            box.add_option(Option(Text.assemble((f" {mark} ", "#06d6a0" if n in self.done else "#5a5f7c"),
                                                (app.roman(title) if app.state.romanize else title, "bold")), id=str(n)))
        box.highlighted = keep if keep is not None else 0
        self.show()

    def current(self):
        return (self.query_one("#steps", OptionList).highlighted or 0) + 1

    def on_option_list_option_highlighted(self, event):
        self.show()

    def show(self):
        app, tr = self.app, self.app.tr
        n = self.current()
        title, what, cmd = STEPS[app.state.lang][n - 1]
        info = Text(title + "\n\n", style="bold #ffd166")
        info.append(what + "\n\n", style="#e8e8f0")
        info.append(tr("co_cmd") + "\n", style="bold #8ecae6")
        info.append(cmd + "\n\n", style="#c9cce0")
        info.append(tr("co_busy") if self.busy else tr("co_run"), style="bold #f4a3c0" if self.busy else "bold #06d6a0")
        self.query_one("#step-info", Static).update(app.roman(info.plain) if app.state.romanize else info)
        self.query_one("#step-out", Static).update(self.out.get(n, ""))
        self.query_one("#step-out").display = n in self.out
        self.query_one("#co-prompt").display = n == 5 and 5 in self.done

    def set_out(self, n, text):
        self.out[n] = text
        self.show()

    # ── running steps ────────────────────────────────────────────────────────
    def on_option_list_option_selected(self, event: OptionList.OptionSelected):
        n = int(event.option.id)
        if self.busy:
            return
        missing = next((k for k in range(1, n) if k not in self.done), None)
        if missing:
            self.app.notify(self.app.tr("co_first", n=missing), timeout=3)
            return
        self.busy = True
        self.show()
        self.run_step(n)

    def on_input_submitted(self, event: Input.Submitted):
        if event.value.strip() and not self.busy and 4 in self.done:
            self.busy = True
            self.run_step(5, event.value.strip())

    def finish(self, n):
        self.busy = False
        self.done.add(n)
        self.refresh_texts()
        if n < 7:
            box = self.query_one("#steps", OptionList)
            if box.highlighted == n - 1:
                box.highlighted = n                        # move on (go back to step 5 to try more beginnings)

    @work(thread=True, exclusive=True)
    def run_step(self, n, prompt=None):
        from ..engine import minitrain as M
        tr = self.app.tr
        call = self.app.call_from_thread
        try:
            if n == 1:
                self.lang = self.app.state.lang
                self.train_text, self.test_text = M.corpus(self.lang)
                c = len(self.train_text) + len(self.test_text)
                out = Text(tr("co_r1", c=c, w=len((self.train_text + self.test_text).split()),
                              l=LANG_NAME[self.app.state.lang][self.lang]) + "\n", style="#e8e8f0")
                out.append("“" + " ".join(self.train_text[:300].split()) + "…”", style="italic #c9cce0")
            elif n == 2:
                import time
                t = time.time()
                self.tok = M.make_tokenizer(self.train_text)
                secs = time.time() - t
                out = Text(tr("co_r2", v=self.tok.get_vocab_size(), s=secs) + "\n\n", style="#e8e8f0")
                ex = EXAMPLE[self.lang]
                for key, tk in (("co_yours", self.tok), ("co_monas", self.app.tokenizer)):
                    pieces = self._pieces(tk, ex)
                    out.append(tr(key, n=len(pieces)) + "\n", style="bold #8ecae6")
                    out.append_text(token_chips(pieces))
                    out.append("\n\n")
                out.append(tr("co_r2b"), style="italic #c9cce0")
            elif n == 3:
                self.device = M.pick_device()
                self.model = M.make_model(self.device)
                p = sum(x.numel() for x in self.model.parameters())
                out = Text(tr("co_r3", p=p, x=round(110.1e6 / p)) + "\n", style="#e8e8f0")
                for part, cnt in M.count_parts(self.model).items():
                    bar = "█" * max(1, round(30 * cnt / p))
                    out.append(f"  {part:<13} {cnt:>9,}  ", style="#c9cce0")
                    out.append(bar + "\n", style="#ffd166")
                out.append("\n" + tr("co_r3b") + "\n", style="#e8e8f0")
                out.append("“" + PROMPT[self.lang] + M.to_text(M.sample(self.model, self.tok, PROMPT[self.lang], 30,
                                                                       device=self.device)) + "”", style="italic #f4a3c0")
                self.ids = M.encode(self.tok, self.train_text)
                self.test_ids = M.encode(self.tok, self.test_text)
                self.bpb_before = M.bits_per_byte(self.model, self.tok, self.test_text, device=self.device)
            elif n == 4:
                import time
                t, losses, samples = time.time(), [], []
                dev = self.device + ("  " + tr("co_cpu_note") if self.device == "cpu" and M.training_running() else "")
                for step, loss in M.train(self.model, self.ids, steps=TRAIN_STEPS, device=self.device, every=10):
                    losses.append(loss)
                    if step in (1, 100, 200, TRAIN_STEPS):
                        samples.append((step, M.to_text(M.sample(self.model, self.tok, PROMPT[self.lang], 30, device=self.device))))
                    out = Text(tr("co_device", d=dev) + "\n", style="#8a8fb0")
                    out.append(tr("co_r4", s=step, n=TRAIN_STEPS, l=loss, t=time.time() - t) + "\n", style="bold #ffd166")
                    out.append_text(chart(losses))
                    for s, txt in samples:
                        out.append("\n" + tr("co_r4_sample", s=s) + " ", style="bold #8ecae6")
                        out.append("“" + PROMPT[self.lang] + flat(txt) + "”", style="italic #c9cce0")
                    call(self.set_out, 4, out)
                out.append("\n\n" + tr("co_r4_done", a=losses[0], b=losses[-1]), style="bold #06d6a0")
            elif n == 5:
                p = prompt or PROMPT[self.lang]
                out = Text(tr("co_r5", p=p) + "\n", style="bold #8ecae6")
                for _ in range(3):
                    txt = M.to_text(M.sample(self.model, self.tok, p, 40, device=self.device))
                    out.append("  “" + p + flat(txt) + "”\n", style="italic #e8e8f0")
                out.append("\n" + tr("co_r5b"), style="#c9cce0")
            elif n == 7:
                out = self.lr_experiment(M, call)
            else:
                after = M.bits_per_byte(self.model, self.tok, self.test_text, device=self.device)
                rows = [(tr("co_untrained"), self.bpb_before, "#f4a3c0"), (tr("co_trained"), after, "#ffd166")]
                gb = self.app.gb
                if gb is not None:
                    rows.append((tr("co_mona"), M.bits_per_byte(gb.model, gb.tok, self.test_text, device=gb.device, chunks=2),
                                 "#06d6a0"))
                out = Text(tr("co_r6") + "\n\n", style="bold #8ecae6")
                top = max(r[1] for r in rows)
                for name, v, colour in rows:
                    out.append(f"  {name:<34}", style="#e8e8f0")
                    out.append("█" * max(1, round(36 * v / top)), style=colour)
                    out.append(f" {v:.2f}\n", style="bold")
                path = self._save()
                out.append("\n" + tr("co_r6b", p=path) + "\n\n", style="bold #ffd166")
                out.append(tr("co_r6c"), style="#c9cce0")
                call(self.app.state.complete, "course", "Model Maker")
            call(self.set_out, n, out)
            call(self.finish, n)
        except Exception as e:                                  # never crash the app: show what went wrong
            call(self.set_out, n, Text(f"⚠ {type(e).__name__}: {e}", style="bold #f4a3c0"))
            call(self._unbusy)

    def lr_experiment(self, M, call):
        """Train three fresh copies of the tiny model, differing only in learning rate, and overlay their curves."""
        import torch
        tr = self.app.tr
        steps, runs = 150, []
        colours = {3e-2: "#f4a3c0", 3e-3: "#06d6a0", 3e-4: "#8ecae6"}
        for lr in colours:
            model = M.make_model(self.device)                     # same seed every time: identical start
            torch.manual_seed(0)                                  # identical batches too
            losses = []
            for step, loss in M.train(model, self.ids, steps=steps, lr=lr, device=self.device, every=5):
                losses.append(loss)
                if step % 25 == 0:
                    call(self.set_out, 7, Text(tr("co_r7_run", lr=f"{lr:g}") + f"  {step}/{steps}", style="bold #ffd166"))
            runs.append((lr, losses, M.test_loss(model, self.test_ids, device=self.device)))
        out = Text(tr("co_r7", n=steps) + "\n\n", style="bold #8ecae6")
        hi = max(max(l) for _, l, _ in runs)
        lo = min(min(l) for _, l, _ in runs)
        width = 48
        for lr, losses, _ in runs:                                # one strip per run, all on the same scale
            vals = [losses[min(int(i * len(losses) / width), len(losses) - 1)] for i in range(width)]
            out.append(f"  lr {lr:<7g}", style=f"bold {colours[lr]}")
            for v in vals:
                out.append(" ▁▂▃▄▅▆▇█"[min(8, max(0, round((v - lo) / ((hi - lo) or 1) * 8)))], style=colours[lr])
            out.append(f"  {losses[0]:.2f} → {losses[-1]:.2f}\n")
        out.append("\n" + tr("co_r7_end") + "\n", style="bold #8ecae6")
        best = min(runs, key=lambda r: r[2])[0]
        for lr, _, test in runs:
            out.append(f"  lr {lr:<7g} {test:.3f}{'  ★' if lr == best else ''}\n", style=f"bold {colours[lr]}")
        out.append("\n" + tr("co_r7_why"), style="#c9cce0")
        return out

    def _unbusy(self):
        self.busy = False
        self.show()

    def _pieces(self, tok, text):
        from ..engine.lessons import piece_text

        class P:                                                # what token_chips expects: .text and .id
            def __init__(self, text, i):
                self.text, self.id = text, i
        enc = tok.encode(text)
        return [P(piece_text(t), i) for t, i in zip(enc.tokens, enc.ids)]

    def _save(self):
        import torch
        from pathlib import Path
        out = Path.home() / "mona_exports"
        out.mkdir(exist_ok=True)
        torch.save(self.model.state_dict(), out / "my_first_model.pt")
        self.tok.save(str(out / "my_first_tokenizer.json"))
        return str(out / "my_first_model.pt")
