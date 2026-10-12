"""Model mysteries: debug a language model the way practitioners do.

Each case starts with a strange behaviour of MONA. The learner runs small experiments on the REAL model
(keys 1-3) to collect evidence, then picks the cause (A, B or C). The answer explains the mechanism and
points to the exact code behind it (F8 opens that code).
"""
import re

from rich.text import Text
from textual import work
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, VerticalScroll
from textual.screen import Screen
from textual.widgets import OptionList, Static
from textual.widgets.option_list import Option

from .. import config
from .text import register
from .widgets import Avatar

register({
    "my_title": {"en": "Model mysteries: debug MONA", "hi": "मॉडल की पहेलियाँ: MONA को डीबग कीजिए", "hinglish": "Model mysteries: MONA ko debug karo"},
    "my_explain": {
        "en": "{addr}, every case starts with something strange MONA does. Don't guess yet: run the experiments (1, 2, 3) "
              "on the real model, look at the evidence, then name the cause (A, B or C).",
        "hi": "{addr}, हर केस MONA के किसी अजीब व्यवहार से शुरू होता है। अभी अंदाज़ा मत लगाइए: असली मॉडल पर प्रयोग (1, 2, 3) चलाइए, "
              "सबूत देखिए, फिर वजह बताइए (A, B या C)।",
        "hinglish": "{addr}, har case MONA ke kisi ajeeb behaviour se shuru hota hai. Abhi guess mat karo: asli model par experiments "
                    "(1, 2, 3) chalao, evidence dekho, phir cause batao (A, B ya C).",
    },
    "my_symptom": {"en": "🩺 Symptom", "hi": "🩺 लक्षण", "hinglish": "🩺 Symptom"},
    "my_experiments": {"en": "🧪 Experiments (press 1, 2, 3)", "hi": "🧪 प्रयोग (1, 2, 3 दबाइए)", "hinglish": "🧪 Experiments (1, 2, 3 dabao)"},
    "my_evidence": {"en": "📋 Evidence", "hi": "📋 सबूत", "hinglish": "📋 Evidence"},
    "my_causes": {"en": "🔍 What's the cause? (press A, B or C)", "hi": "🔍 वजह क्या है? (A, B या C दबाइए)",
                  "hinglish": "🔍 Cause kya hai? (A, B ya C dabao)"},
    "my_need": {"en": "Run at least one experiment first: real investigators look before they conclude.",
                "hi": "पहले कम से कम एक प्रयोग चलाइए: असली जाँचकर्ता नतीजे से पहले देखते हैं।",
                "hinglish": "Pehle kam se kam ek experiment chalao: asli investigators conclude karne se pehle dekhte hain."},
    "my_right": {"en": "✅ Solved, {addr}!", "hi": "✅ सुलझ गया, {addr}!", "hinglish": "✅ Solve ho gaya, {addr}!"},
    "my_wrong": {"en": "❌ Not quite. Look at the evidence again; the right cause is highlighted.",
                 "hi": "❌ पूरी तरह नहीं। सबूत फिर देखिए; सही वजह हाइलाइट है।",
                 "hinglish": "❌ Poori tarah nahi. Evidence phir dekho; sahi cause highlight hai."},
    "my_why": {"en": "Why it happens", "hi": "ऐसा क्यों होता है", "hinglish": "Aisa kyun hota hai"},
    "my_code": {"en": "Where it lives in MONA's code (F8 to open):", "hi": "MONA के कोड में कहाँ है (खोलने के लिए F8):",
                "hinglish": "MONA ke code mein kahan hai (kholne ke liye F8):"},
    "my_running": {"en": "⏳ running on the real model…", "hi": "⏳ असली मॉडल पर चल रहा है…", "hinglish": "⏳ asli model par chal raha hai…"},
    "my_loading": {"en": "⏳ MONA is still waking up…", "hi": "⏳ MONA अभी जाग रही है…", "hinglish": "⏳ MONA abhi jaag rahi hai…"},
    "my_badge": {"en": "🏅 Badge: Model Detective. All five cases solved, {addr}.",
                 "hi": "🏅 बैज: Model Detective। पाँचों केस सुलझ गए, {addr}।",
                 "hinglish": "🏅 Badge: Model Detective. Paanchon cases solve ho gaye, {addr}."},
    "my_keys": {"en": "↑↓ case   1 2 3 run experiment   A B C name the cause   F8 the code   Esc back",
                "hi": "↑↓ केस   1 2 3 प्रयोग   A B C वजह   F8 कोड   Esc वापस",
                "hinglish": "↑↓ case   1 2 3 experiment   A B C cause   F8 code   Esc wapas"},
})

CHAT_WEIGHTS = config.RUNS_DIR / "mona_m_chat" / "model.pt"


# ── experiments: each takes the GlassBox and returns a Text of evidence ──────────────────────────
def flat(text):
    """One line, keeping the leading space that separates the prompt from MONA's first word."""
    return re.sub(r"\s+", " ", text)


def _gen(gb, prompt, n=40, temperature=0.8, seed=0):
    return "".join(step.token.text for step in gb.generate(prompt, n=n, temperature=temperature, top_p=0.95, seed=seed))


def _repeats(text):
    """How much of the text is repeated 4-word chunks (0 = none, 1 = all)."""
    w = text.split()
    grams = [" ".join(w[i:i + 4]) for i in range(len(w) - 3)]
    return 1 - len(set(grams)) / len(grams) if grams else 0.0


def exp_greedy(gb, lang):
    out = Text()
    p = {"en": "The history of India", "hi": "भारत का इतिहास", "hinglish": "Bharat ka itihaas"}[lang]
    for t in (0.0, 0.8):
        txt = _gen(gb, p, 60, temperature=t)
        out.append(f"temperature {t}:  ", style="bold #ffd166")
        out.append(f"“{p}{flat(txt)}”\n", style="italic #e8e8f0")
        out.append(f"   repeated 4-word chunks: {_repeats(txt):.0%}\n\n", style="#8ecae6")
    return out


def exp_topchoice(gb, lang):
    p = {"en": "The history of India", "hi": "भारत का इतिहास", "hinglish": "Bharat ka itihaas"}[lang]
    txt = _gen(gb, p, 40, temperature=0.0)
    ids = gb.encode(p + txt)
    out = Text("Once a phrase appears, how sure is MONA that it comes again? (greedy run)\n", style="#c9cce0")
    probs = gb.probs(ids)
    for g in gb.next_word(ids, top=5):
        out.append(f"  {g.token.text!r:>16}  ", style="bold")
        out.append("█" * max(1, round(30 * g.prob)), style="#06d6a0")
        out.append(f" {g.prob:.0%}\n")
    out.append(f"\nGreedy decoding always takes the top bar. The top choice here has {probs.max().item():.0%}: "
               "a loop that feeds itself.", style="#8ecae6")
    return out


def exp_seeds(gb, lang):
    p = {"en": "My favourite food is", "hi": "मेरा पसंदीदा खाना", "hinglish": "Mera favourite khaana"}[lang]
    out = Text()
    for label, t in (("greedy (temperature 0)", 0.0), ("sampled (temperature 0.8)", 0.8)):
        out.append(label + ", three runs:\n", style="bold #ffd166")
        for seed in (1, 2, 3):
            out.append(f"  “{p}{flat(_gen(gb, p, 14, temperature=t, seed=seed))}”\n", style="italic #e8e8f0")
        out.append("\n")
    return out


def exp_question(gb, lang):
    q = {"en": "What is the capital of India?", "hi": "भारत की राजधानी क्या है?", "hinglish": "Bharat ki rajdhani kya hai?"}[lang]
    out = Text("Base MONA, asked a plain question:\n", style="bold #ffd166")
    out.append(f"  “{q}{flat(_gen(gb, q, 40, temperature=0.7))}”\n", style="italic #e8e8f0")
    return out


def exp_qa_format(gb, lang):
    q = {"en": "What is the capital of India?", "hi": "भारत की राजधानी क्या है?", "hinglish": "Bharat ki rajdhani kya hai?"}[lang]
    a = {"en": "Answer:", "hi": "उत्तर:", "hinglish": "Jawab:"}[lang]
    prompt = f"{q}\n{a}"
    out = Text("Same model, but the text now LOOKS like an answer comes next:\n", style="bold #ffd166")
    out.append(f"  “{prompt}{flat(_gen(gb, prompt, 20, temperature=0.3))}”\n", style="italic #e8e8f0")
    out.append("\nThe model didn't get smarter. The pattern of the text changed what 'the likely next words' are.",
               style="#8ecae6")
    return out


def exp_chat_model(gb, lang):
    q = {"en": "What is the capital of India?", "hi": "भारत की राजधानी क्या है?", "hinglish": "Bharat ki rajdhani kya hai?"}[lang]
    if not CHAT_WEIGHTS.exists():
        return Text("MONA-Chat isn't trained yet on this computer (it's made after pretraining). Chat tuning shows the model "
                    "thousands of examples written as  <|user|> question <|end|> <|assistant|> answer <|end|>, "
                    "so it learns that an answer follows a question.", style="#e8e8f0")
    import torch
    from .. import tokenizer as T
    from ..engine.lessons import load_model
    m = load_model(CHAT_WEIGHTS)
    ids = torch.tensor([T.chat_prompt(gb.tok, [{"role": "user", "content": q}])])
    end = {gb.tok.token_to_id(T.END), gb.tok.token_to_id(T.EOT)}
    torch.manual_seed(0)
    reply = gb.tok.decode(list(m.generate(ids, 50, temperature=0.5, top_p=0.9, stop_ids=end)))
    out = Text("MONA-Chat (same base model + chat tuning), same question:\n", style="bold #ffd166")
    out.append(f"  “{flat(reply).strip()}”\n", style="italic #e8e8f0")
    return out


def exp_confident(gb, lang):
    p = {"en": "The capital of Australia is", "hi": "ऑस्ट्रेलिया की राजधानी", "hinglish": "Australia ki rajdhani"}[lang]
    out = Text(f"“{p} …”  MONA's top guesses for the next token:\n", style="bold #ffd166")
    for g in gb.next_word(p, top=6):
        out.append(f"  {g.token.text!r:>14}  ", style="bold")
        out.append("█" * max(1, round(40 * g.prob)), style="#f4a3c0")
        out.append(f" {g.prob:.1%}\n")
    out.append("\n(The true answer is Canberra. Is it on top? Is it even on the list?)", style="#8ecae6")
    return out


def exp_confidence_trace(gb, lang):
    p = {"en": "The first person to walk on the Moon was", "hi": "चाँद पर चलने वाले पहले इंसान थे", "hinglish": "Chaand par chalne wale pehle insaan the"}[lang]
    out = Text("A sentence MONA writes, each token coloured by how sure she was:\n  ", style="bold #ffd166")
    out.append(p, style="italic #e8e8f0")
    for step in gb.generate(p, n=20, temperature=0.7, top_p=0.9, seed=4):
        colour = "#06d6a0" if step.prob > 0.5 else "#ffd166" if step.prob > 0.15 else "#f4a3c0"
        out.append(step.token.text, style=f"bold {colour}")
    out.append("\n\n  green = sure (>50%)   yellow = unsure   pink = a guess (<15%)\n", style="#8a8fb0")
    out.append("Facts and fluent filler are produced by exactly the same mechanism.", style="#8ecae6")
    return out


def exp_rag_hint(gb, lang):
    p = "Australia's capital city, Canberra, was chosen as a compromise. The capital of Australia is"
    out = Text("Now put the fact in the text first (what RAG does), then ask again:\n", style="bold #ffd166")
    for g in gb.next_word(p, top=4):
        out.append(f"  {g.token.text!r:>14}  ", style="bold")
        out.append("█" * max(1, round(40 * g.prob)), style="#06d6a0")
        out.append(f" {g.prob:.1%}\n")
    out.append("\nWith the answer in its context, MONA can simply copy it. Without it, she can only guess what sounds likely.",
               style="#8ecae6")
    return out


def exp_eval_losses(gb, lang):
    from ..engine.lessons import training_curves
    _, evals = training_curves()
    out = Text()
    if not evals:
        return Text("No evaluation log found.", style="#f4a3c0")
    last = evals[-1]
    out.append(f"Held-out loss per language at {int(last['tokens']) / 1e9:.2f}B tokens (lower = better):\n", style="bold #ffd166")
    for k in ("english", "hindi", "hinglish", "awadhi"):
        if k in last:
            v = float(last[k])
            out.append(f"  {k:<9} ", style="bold")
            out.append("█" * round(v * 6), style="#f4a3c0" if k == "awadhi" else "#06d6a0")
            out.append(f" {v:.2f}\n")
    return out


def exp_data_share(gb, lang):
    import json
    try:
        manifest = json.loads((config.TOKENS_DIR / "manifest.json").read_text())
    except OSError:
        return Text("No data manifest found.", style="#f4a3c0")
    share = {"english": 0.55, "hindi": 0.40, "hinglish": 0.0497, "awadhi": 0.0003}
    out = Text("What MONA could read, per language (and its share of each batch since the copyright fix):\n",
               style="bold #ffd166")
    for k in ("english", "hindi", "hinglish", "awadhi"):
        n = manifest.get(k, {}).get("train_tokens", 0)
        out.append(f"  {k:<9} {n:>15,} tokens   {share[k]:7.2%} of every batch\n",
                   style="bold #f4a3c0" if k == "awadhi" else "#e8e8f0")
    eng, awa = manifest.get("english", {}).get("train_tokens", 0), manifest.get("awadhi", {}).get("train_tokens", 1)
    out.append(f"\nThere is {eng / max(awa, 1):,.0f}× more English than Awadhi verse. Repeating the verse more often would make "
               "MONA memorise it instead of learning the language.", style="#8ecae6")
    return out


def exp_awadhi_tokens(gb, lang):
    samples = {"English": "The king walked into the forest with his brother.",
               "Hindi": "राजा अपने भाई के साथ जंगल में गया।",
               "Awadhi": "राम लखन सिय बन गवने तहाँ।"}
    out = Text("Tokens per word (fewer = the tokenizer knows these words well):\n", style="bold #ffd166")
    for name, s in samples.items():
        n = len(gb.encode(s))
        out.append(f"  {name:<8} {n / len(s.split()):.2f}   ", style="bold")
        out.append(" ".join(t.text for t in gb.tokens(s)) + "\n", style="#c9cce0")
    out.append("\nRare words are cut into more, smaller pieces: harder to learn from very little data.", style="#8ecae6")
    return out


def exp_word_costs(gb, lang):
    words = ["the", "India", "information", "unbelievably", "photosynthesis", "नमस्ते", "विद्यालय", "Ramcharitmanas"]
    out = Text("How many tokens each word costs MONA:\n", style="bold #ffd166")
    for w in words:
        toks = gb.tokens(" " + w)
        out.append(f"  {w:<16} {len(toks)}  ", style="bold")
        out.append(" | ".join(t.text.strip() or "▁" for t in toks) + "\n", style="#c9cce0")
    return out


def exp_merge_order(gb, lang):
    from ..engine.lessons import bpe_replay
    out = Text("Replay the tokenizer on “unbelievably”: merges learned EARLY (low rank) are common pairs.\n",
               style="bold #ffd166")
    for step in bpe_replay(gb.tok, " unbelievably")[1:]:
        out.append(f"  rank {step.rank:>6,}  merge “{step.merged}”  → ", style="#e8e8f0")
        out.append(" ".join(step.pieces) + "\n", style="#c9cce0")
    return out


def exp_frequency(gb, lang):
    out = Text("Token id ≈ how early the piece was learned (lower id = more frequent in the training data):\n",
               style="bold #ffd166")
    for w in (" the", " and", " India", " believe", " photos", " synthesis"):
        ids = gb.encode(w)
        out.append(f"  {w!r:<12} ids {ids}\n", style="#e8e8f0")
    out.append("\nBPE gives one token to pieces it saw very often. Rare words are spelled out from smaller, common pieces.",
               style="#8ecae6")
    return out


# ── the cases ─────────────────────────────────────────────────────────────────────────────────────
# (id, icon, {lang: (title, symptom, [exp labels ×3], [causes ×3], why, code)}, [experiment fns ×3], correct cause, stage)
CASES = [
    ("loop", "🔁", {
        "en": ("MONA repeats herself forever",
               "A user set MONA to 'always pick the most likely word' to make her more accurate. Now she writes the same "
               "phrase again and again.",
               ["Generate with temperature 0 vs 0.8", "Look at the probabilities inside the loop", "Same prompt, three runs each"],
               ["The model is broken and needs retraining", "Always taking the top word (greedy decoding) lets a phrase feed itself",
                "The text is longer than MONA's context window"],
               "Repeating a phrase makes that phrase even more likely next time, so 'always take the top word' falls into a "
               "loop. Sampling (temperature, top-p) adds controlled randomness that breaks loops. That's why chat apps "
               "rarely use temperature 0 for long text.",
               "mona/model.py → MONA.generate (temperature / top-p)   ·   see it live: stage 6, Next word"),
        "hi": ("MONA एक ही बात बार-बार दोहराती है",
               "किसी ने MONA को 'हमेशा सबसे संभावित शब्द चुनो' पर सेट किया ताकि वह ज़्यादा सटीक हो। अब वह एक ही वाक्यांश बार-बार लिखती है।",
               ["temperature 0 बनाम 0.8 पर लिखवाइए", "लूप के अंदर की संभावनाएँ देखिए", "एक ही शुरुआत, तीन-तीन बार"],
               ["मॉडल टूट गया है, दोबारा ट्रेन करना होगा", "हमेशा सबसे ऊपर वाला शब्द (greedy) लेने से वाक्यांश ख़ुद को दोहराता है",
                "पाठ MONA की context window से लंबा है"],
               "किसी वाक्यांश को दोहराने से वह अगली बार और भी संभावित हो जाता है, इसलिए 'हमेशा सबसे ऊपर वाला' एक लूप में फँस जाता है। "
               "सैंपलिंग (temperature, top-p) नियंत्रित अनियमितता जोड़कर लूप तोड़ती है।",
               "mona/model.py → MONA.generate (temperature / top-p)   ·   असली में: चरण 6, अगला शब्द"),
        "hinglish": ("MONA ek hi baat baar-baar repeat karti hai",
                     "Kisi ne MONA ko 'hamesha sabse likely word chuno' par set kiya taaki woh zyada accurate ho. Ab woh ek hi phrase "
                     "baar-baar likhti hai.",
                     ["Temperature 0 vs 0.8 par likhwao", "Loop ke andar ki probabilities dekho", "Same prompt, teen-teen baar"],
                     ["Model toot gaya hai, dobara train karna padega", "Hamesha top word (greedy) lene se phrase khud ko repeat karta hai",
                      "Text MONA ki context window se lamba hai"],
                     "Kisi phrase ko repeat karne se woh agli baar aur bhi likely ho jaata hai, isliye 'hamesha top word' loop mein "
                     "phas jaata hai. Sampling (temperature, top-p) controlled randomness jodkar loop todti hai.",
                     "mona/model.py → MONA.generate (temperature / top-p)   ·   live: stage 6, Next word")},
     [exp_greedy, exp_topchoice, exp_seeds], 1, "next"),
    ("question", "❓", {
        "en": ("Ask a question, get more questions",
               "Asked “What is the capital of India?”, base MONA doesn't answer. She writes more questions, or wanders off.",
               ["Ask the plain question", "Make the text look like a Q&A", "Ask MONA-Chat (after chat tuning)"],
               ["MONA doesn't know any facts", "A pretrained model continues text; it was never taught that questions get answers",
                "The question needs more tokens"],
               "Pretraining teaches 'what text usually comes next'. On the web, a question is often followed by more questions "
               "(FAQ pages, exams). Chat tuning (SFT) shows thousands of question → answer conversations so the model learns "
               "the assistant pattern. Same knowledge, different behaviour.",
               "mona/tokenizer.py → encode_chat (the chat template)   ·   scripts/mona_sft.py   ·   stage 8, Chat tuning"),
        "hi": ("सवाल पूछो, और सवाल मिलते हैं",
               "“भारत की राजधानी क्या है?” पूछने पर बेस MONA जवाब नहीं देती। वह और सवाल लिखती है, या भटक जाती है।",
               ["सीधा सवाल पूछिए", "पाठ को सवाल-जवाब जैसा बनाइए", "MONA-Chat से पूछिए (चैट ट्यूनिंग के बाद)"],
               ["MONA कोई तथ्य नहीं जानती", "प्रीट्रेन मॉडल पाठ आगे बढ़ाता है; उसे कभी नहीं सिखाया गया कि सवाल के बाद जवाब आता है",
                "सवाल को ज़्यादा टोकन चाहिए"],
               "प्रीट्रेनिंग सिखाती है 'आम तौर पर आगे क्या लिखा होता है'। वेब पर सवाल के बाद अक्सर और सवाल होते हैं (FAQ, परीक्षा)। "
               "चैट ट्यूनिंग (SFT) हज़ारों सवाल → जवाब बातचीत दिखाकर सहायक का ढंग सिखाती है। वही ज्ञान, अलग व्यवहार।",
               "mona/tokenizer.py → encode_chat (चैट टेम्पलेट)   ·   scripts/mona_sft.py   ·   चरण 8, चैट ट्यूनिंग"),
        "hinglish": ("Sawaal poocho, aur sawaal milte hain",
                     "“Bharat ki rajdhani kya hai?” poochne par base MONA jawab nahi deti. Woh aur sawaal likhti hai, ya bhatak jaati hai.",
                     ["Seedha sawaal poocho", "Text ko Q&A jaisa banao", "MONA-Chat se poocho (chat tuning ke baad)"],
                     ["MONA koi facts nahi jaanti", "Pretrained model text aage badhata hai; use kabhi nahi sikhaya gaya ki sawaal ke baad jawab aata hai",
                      "Sawaal ko zyada tokens chahiye"],
                     "Pretraining sikhati hai 'aam taur par aage kya likha hota hai'. Web par sawaal ke baad aksar aur sawaal hote hain "
                     "(FAQ, exams). Chat tuning (SFT) hazaron sawaal → jawab chats dikhakar assistant ka pattern sikhati hai.",
                     "mona/tokenizer.py → encode_chat (chat template)   ·   scripts/mona_sft.py   ·   stage 8, Chat tuning")},
     [exp_question, exp_qa_format, exp_chat_model], 1, "chat"),
    ("confident", "🎭", {
        "en": ("Confident, fluent, and wrong",
               "MONA writes facts in a calm, confident tone. Some are simply false. How can a model be so sure and so wrong?",
               ["Look at the next-token probabilities for a fact", "Colour a sentence by confidence", "Put the fact in the context first"],
               ["MONA is lying on purpose", "The training data was full of wrong facts",
                "MONA predicts likely-sounding words; truth only matters if the right fact is likely, or is in front of her"],
               "A language model has no separate 'fact checker'. It produces the most plausible continuation. Fluency is easy "
               "to learn; rare facts need far more data and parameters. Retrieval (RAG) helps because copying a fact from the "
               "context is easy. This is called hallucination.",
               "mona/engine/glassbox.py → GlassBox.next_word   ·   mona/engine/rag.py   ·   stage 10, RAG"),
        "hi": ("भरोसेमंद, धाराप्रवाह, और ग़लत",
               "MONA शांत, पक्के लहजे में तथ्य लिखती है। कुछ बिल्कुल ग़लत होते हैं। कोई मॉडल इतना पक्का और इतना ग़लत कैसे हो सकता है?",
               ["किसी तथ्य के लिए अगले टोकन की संभावनाएँ देखिए", "वाक्य को भरोसे के हिसाब से रंगिए", "तथ्य पहले संदर्भ में रखिए"],
               ["MONA जानबूझकर झूठ बोलती है", "ट्रेनिंग डेटा ग़लत तथ्यों से भरा था",
                "MONA संभावित लगने वाले शब्द बताती है; सच तभी आता है जब सही तथ्य संभावित हो, या सामने लिखा हो"],
               "भाषा मॉडल में अलग 'तथ्य जाँचने वाला' नहीं होता। वह सबसे विश्वसनीय लगने वाला आगे का पाठ बनाता है। धाराप्रवाह होना आसान है; "
               "दुर्लभ तथ्यों के लिए बहुत ज़्यादा डेटा और पैरामीटर चाहिए। RAG मदद करता है क्योंकि संदर्भ से तथ्य कॉपी करना आसान है।",
               "mona/engine/glassbox.py → GlassBox.next_word   ·   mona/engine/rag.py   ·   चरण 10, RAG"),
        "hinglish": ("Confident, fluent, aur galat",
                     "MONA shaant, pakke tone mein facts likhti hai. Kuch bilkul galat hote hain. Koi model itna sure aur itna galat kaise ho sakta hai?",
                     ["Kisi fact ke liye next-token probabilities dekho", "Sentence ko confidence ke hisaab se rango", "Fact pehle context mein rakho"],
                     ["MONA jaan-boojhkar jhooth bolti hai", "Training data galat facts se bhara tha",
                      "MONA likely lagne wale words batati hai; sach tabhi aata hai jab sahi fact likely ho, ya saamne likha ho"],
                     "Language model mein alag 'fact checker' nahi hota. Woh sabse plausible continuation banata hai. Fluent hona aasaan hai; "
                     "rare facts ke liye bahut zyada data aur parameters chahiye. RAG madad karta hai kyunki context se fact copy karna aasaan hai.",
                     "mona/engine/glassbox.py → GlassBox.next_word   ·   mona/engine/rag.py   ·   stage 10, RAG")},
     [exp_confident, exp_confidence_trace, exp_rag_hint], 2, "rag"),
    ("awadhi", "📜", {
        "en": ("Great at Hindi, weak at Awadhi",
               "MONA writes decent Hindi, but her Awadhi (Tulsidas's language) is poor, even though Awadhi is close to Hindi.",
               ["Compare held-out loss per language", "Check how much of each language MONA read", "Count tokens per word"],
               ["Awadhi is too difficult for any model", "The tokenizer can't read Awadhi letters",
                "Awadhi was a tiny share of the data: only ~246,000 tokens of verse exist, 6,500× less than English"],
               "Models learn in proportion to what they see. Awadhi was kept tiny on purpose: only public-domain verse was "
               "allowed (copyright), and repeating it too often would make MONA memorise instead of learn. Data quantity "
               "per language matters more than how 'hard' a language is.",
               "scripts/mona_pretrain.py → MIX_STABLE / MIX_DECAY   ·   mona/data.py → PretrainBatches   ·   stage 1, Data"),
        "hi": ("हिंदी में अच्छी, अवधी में कमज़ोर",
               "MONA ठीक-ठाक हिंदी लिखती है, पर उसकी अवधी (तुलसीदास की भाषा) कमज़ोर है, जबकि अवधी हिंदी के क़रीब है।",
               ["हर भाषा का अनदेखे पाठ पर लॉस मिलाइए", "देखिए MONA ने हर भाषा कितनी पढ़ी", "प्रति शब्द टोकन गिनिए"],
               ["अवधी किसी भी मॉडल के लिए बहुत कठिन है", "टोकनाइज़र अवधी अक्षर नहीं पढ़ सकता",
                "डेटा में अवधी का हिस्सा बहुत छोटा था: चौपाइयों के सिर्फ़ ~2,46,000 टोकन हैं, अंग्रेज़ी से 6,500 गुना कम"],
               "मॉडल उतना सीखते हैं जितना देखते हैं। अवधी जानबूझकर छोटी रखी गई: सिर्फ़ सार्वजनिक चौपाइयाँ (कॉपीराइट), और बहुत दोहराने से MONA "
               "रट लेती। हर भाषा का डेटा उसकी 'कठिनाई' से ज़्यादा मायने रखता है।",
               "scripts/mona_pretrain.py → MIX_STABLE / MIX_DECAY   ·   mona/data.py → PretrainBatches   ·   चरण 1, डेटा"),
        "hinglish": ("Hindi mein achhi, Awadhi mein kamzor",
                     "MONA theek-thaak Hindi likhti hai, par uski Awadhi (Tulsidas ki bhasha) kamzor hai, jabki Awadhi Hindi ke kareeb hai.",
                     ["Har language ka held-out loss compare karo", "Dekho MONA ne har language kitni padhi", "Tokens per word gino"],
                     ["Awadhi kisi bhi model ke liye bahut mushkil hai", "Tokenizer Awadhi letters nahi padh sakta",
                      "Data mein Awadhi ka hissa bahut chhota tha: chaupaiyon ke sirf ~2,46,000 tokens hain, English se 6,500 guna kam"],
                     "Models utna seekhte hain jitna dekhte hain. Awadhi jaan-boojhkar chhoti rakhi gayi: sirf public-domain chaupaiyan "
                     "(copyright), aur bahut repeat karne se MONA ratt leti. Har language ka data uski 'difficulty' se zyada matter karta hai.",
                     "scripts/mona_pretrain.py → MIX_STABLE / MIX_DECAY   ·   mona/data.py → PretrainBatches   ·   stage 1, Data")},
     [exp_eval_losses, exp_data_share, exp_awadhi_tokens], 2, "data"),
    ("tokens", "🧩", {
        "en": ("Why does “unbelievably” cost 5 tokens but “the” only 1?",
               "Some words are one token, others are split into many pieces. Long prompts with rare words fill MONA's "
               "1,024-token memory faster.",
               ["Count tokens for common and rare words", "Replay the tokenizer's merges", "Compare token ids"],
               ["Long words always need more tokens", "BPE gives single tokens to pieces that were frequent in the training data",
                "The tokenizer splits words at random"],
               "BPE starts from bytes and repeatedly glues together the most frequent neighbouring pair. Frequent words end up "
               "as one token; rare words are built from smaller common pieces. Length matters less than frequency: a long "
               "common word can be 1 token, a short rare one several.",
               "mona/tokenizer.py → train / _empty   ·   mona/engine/lessons.py → bpe_replay   ·   stage 2, Tokens"),
        "hi": ("“unbelievably” के 5 टोकन पर “the” का सिर्फ़ 1 क्यों?",
               "कुछ शब्द एक टोकन होते हैं, कुछ कई टुकड़ों में कटते हैं। दुर्लभ शब्दों वाले लंबे पाठ MONA की 1,024-टोकन याददाश्त जल्दी भर देते हैं।",
               ["आम और दुर्लभ शब्दों के टोकन गिनिए", "टोकनाइज़र के जोड़ दोबारा चलाइए", "टोकन id मिलाइए"],
               ["लंबे शब्द हमेशा ज़्यादा टोकन लेते हैं", "BPE उन टुकड़ों को एक टोकन देता है जो ट्रेनिंग डेटा में बार-बार आए",
                "टोकनाइज़र शब्दों को बेतरतीब काटता है"],
               "BPE बाइट्स से शुरू करके सबसे आम पड़ोसी जोड़े को बार-बार जोड़ता है। आम शब्द एक टोकन बन जाते हैं; दुर्लभ शब्द छोटे आम टुकड़ों "
               "से बनते हैं। लंबाई से ज़्यादा मायने रखता है कि शब्द कितना आम है।",
               "mona/tokenizer.py → train / _empty   ·   mona/engine/lessons.py → bpe_replay   ·   चरण 2, टोकन"),
        "hinglish": ("“unbelievably” ke 5 tokens par “the” ka sirf 1 kyun?",
                     "Kuch words ek token hote hain, kuch kai pieces mein katte hain. Rare words wale lambe prompts MONA ki 1,024-token "
                     "memory jaldi bhar dete hain.",
                     ["Common aur rare words ke tokens gino", "Tokenizer ke merges replay karo", "Token ids compare karo"],
                     ["Lambe words hamesha zyada tokens lete hain", "BPE un pieces ko ek token deta hai jo training data mein baar-baar aaye",
                      "Tokenizer words ko random kaat-ta hai"],
                     "BPE bytes se shuru karke sabse common padosi pair ko baar-baar jodta hai. Common words ek token ban jaate hain; rare "
                     "words chhote common pieces se bante hain. Length se zyada matter karta hai ki word kitna common hai.",
                     "mona/tokenizer.py → train / _empty   ·   mona/engine/lessons.py → bpe_replay   ·   stage 2, Tokens")},
     [exp_word_costs, exp_merge_order, exp_frequency], 1, "tokens"),
]


class MysteryScreen(Screen):
    BINDINGS = [Binding("escape", "app.pop_screen", "back"),
                Binding("1", "experiment(0)", show=False), Binding("2", "experiment(1)", show=False),
                Binding("3", "experiment(2)", show=False), Binding("a", "cause(0)", show=False),
                Binding("b", "cause(1)", show=False), Binding("c", "cause(2)", show=False)]

    def compose(self) -> ComposeResult:
        with Horizontal(classes="lab-head"):
            yield Avatar(id="avatar", classes="lab-avatar")
            yield Static(id="title", classes="lab-title")
        yield Static(id="explain", classes="explain")
        with Horizontal(id="tour-cols"):
            yield OptionList(id="cases")
            with VerticalScroll(id="tour-right"):
                yield Static(id="case", classes="panel")
                yield Static(id="evidence", classes="panel")
                yield Static(id="verdict", classes="panel")
        yield Static(id="keys", classes="keys")

    def on_mount(self):
        self.evidence = {}          # (case id, experiment index) -> Text
        self.answers = {}           # case id -> chosen cause
        self.running = None
        self.refresh_texts()
        box = self.query_one("#cases", OptionList)
        box.highlighted = 0
        box.focus()

    def refresh_texts(self):
        app, tr = self.app, self.app.tr
        self.query_one("#title", Static).update(tr("my_title"))
        self.query_one("#explain", Static).update(tr("my_explain"))
        self.query_one("#keys", Static).update(tr("my_keys"))
        box = self.query_one("#cases", OptionList)
        keep = box.highlighted
        box.clear_options()
        for cid, icon, d, _, correct, _ in CASES:
            title = d[app.state.lang][0]
            mark = "" if cid not in self.answers else (" ✅" if self.answers[cid] == correct else " ❌")
            box.add_option(Option(f" {icon} {app.roman(title) if app.state.romanize else title}{mark}", id=cid))
        box.highlighted = keep if keep is not None else 0
        self.show()

    def on_option_list_option_highlighted(self, event):
        self.show()

    def current(self):
        return CASES[self.query_one("#cases", OptionList).highlighted or 0]

    def code_targets(self):
        """For F8: the code behind the case that's open."""
        return {"loop": ["generate"], "question": ["encode_chat"], "confident": ["next_word", "rag_search"],
                "awadhi": ["batches"], "tokens": ["bpe_replay", "tokenizer"]}[self.current()[0]]

    def show(self):
        app, tr = self.app, self.app.tr
        cid, icon, d, fns, correct, stage = self.current()
        title, symptom, labels, causes, why, code = d[app.state.lang]
        out = Text(f"{icon} {title}\n\n", style="bold #ffd166")
        out.append(tr("my_symptom") + "\n", style="bold #f4a3c0")
        out.append(symptom + "\n\n", style="#e8e8f0")
        out.append(tr("my_experiments") + "\n", style="bold #8ecae6")
        for i, label in enumerate(labels):
            done = (cid, i) in self.evidence
            out.append(f"  {i + 1}. {label}{'  ✓' if done else ''}\n", style="#06d6a0" if done else "#e8e8f0")
        out.append("\n" + tr("my_causes") + "\n", style="bold #8ecae6")
        chosen = self.answers.get(cid)
        for i, cause in enumerate(causes):
            style = "#e8e8f0"
            if chosen is not None:
                style = "bold #06d6a0" if i == correct else ("bold #f4a3c0" if i == chosen else "#8a8fb0")
            out.append(f"  {'ABC'[i]}. {cause}\n", style=style)
        self.query_one("#case", Static).update(app.roman(out.plain) if app.state.romanize else out)

        ev = Text(tr("my_evidence") + "\n\n", style="bold #8ecae6")
        if self.running and self.running[0] == cid:
            ev.append(tr("my_running"), style="bold #ffd166")
        for i in range(3):
            if (cid, i) in self.evidence:
                ev.append(f"[{i + 1}] {labels[i]}\n", style="bold #e8e8f0")
                ev.append_text(self.evidence[(cid, i)])
                ev.append("\n\n")
        self.query_one("#evidence", Static).update(ev)
        self.query_one("#evidence").display = any((cid, i) in self.evidence for i in range(3)) or bool(self.running)

        verdict = self.query_one("#verdict", Static)
        verdict.display = chosen is not None
        if chosen is not None:
            v = Text(tr("my_right") if chosen == correct else tr("my_wrong"), style="bold #06d6a0" if chosen == correct else "bold #f4a3c0")
            v.append("\n\n" + tr("my_why") + "\n", style="bold #8ecae6")
            v.append(why + "\n\n", style="#e8e8f0")
            v.append(tr("my_code") + "\n", style="bold #cdb4db")
            v.append(code, style="#c9cce0")
            if len([k for k, a in self.answers.items() if a == next(c for c in CASES if c[0] == k)[4]]) == len(CASES):
                v.append("\n\n" + tr("my_badge"), style="bold #ffd166")
            verdict.update(app.roman(v.plain) if app.state.romanize else v)

    def action_experiment(self, i: int):
        if self.app.gb is None:
            self.app.notify(self.app.tr("my_loading"), timeout=3)
            return
        if self.running:
            return
        cid = self.current()[0]
        self.running = (cid, i)
        self.show()
        self.run_experiment(cid, i)

    @work(thread=True, exclusive=True)
    def run_experiment(self, cid, i):
        case = next(c for c in CASES if c[0] == cid)
        try:
            result = case[3][i](self.app.gb, self.app.state.lang)
        except Exception as e:                              # an experiment must never crash the app
            result = Text(f"⚠ {type(e).__name__}: {e}", style="bold #f4a3c0")
        self.app.call_from_thread(self._done, cid, i, result)

    def _done(self, cid, i, result):
        self.evidence[(cid, i)] = result
        self.running = None
        self.show()

    def action_cause(self, i: int):
        cid, _, _, _, correct, _ = self.current()
        if cid in self.answers:
            return
        if not any((cid, k) in self.evidence for k in range(3)):
            self.app.notify(self.app.tr("my_need"), timeout=4)
            return
        self.answers[cid] = i
        solved = [k for k, a in self.answers.items() if a == next(c for c in CASES if c[0] == k)[4]]
        if len(self.answers) == len(CASES):
            self.app.state.complete("mysteries", badge="Model Detective" if len(solved) == len(CASES) else None)
        self.refresh_texts()
