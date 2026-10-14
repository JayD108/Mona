"""F8 anywhere: show the real MONA code behind the current screen, with a plain-language walkthrough.

The code is read live with `inspect`, so what you see is always exactly what runs.
"""
import importlib
import inspect
from pathlib import Path

from rich.console import Group
from rich.syntax import Syntax
from rich.text import Text
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.screen import ModalScreen
from textual.widgets import OptionList, Static
from textual.widgets.option_list import Option

from .text import register

register({
    "cv_title": {"en": "🔧 The code behind this screen", "hi": "🔧 इस स्क्रीन के पीछे का कोड", "hinglish": "🔧 Is screen ke peeche ka code"},
    "cv_keys": {"en": "↑↓ choose   Esc / F8 close   (this is the real code MONA runs, read live)",
                "hi": "↑↓ चुनें   Esc / F8 बंद   (यह वही असली कोड है जो MONA चलाती है)",
                "hinglish": "↑↓ chuno   Esc / F8 band   (yeh wahi asli code hai jo MONA chalati hai)"},
})

# key: (module, qualified name, title, {lang: walkthrough})
SNIPPETS = {
    "forward": ("mona.model", "MONA.forward", "The whole model, start to end", {
        "en": "Token ids → embedding vectors → 12 blocks → final norm → scores for all 32,768 possible next tokens. With "
              "targets, it also computes the loss: how surprised the model was by the real next token (cross-entropy).",
        "hi": "टोकन id → एम्बेडिंग → 12 ब्लॉक → आख़िरी नॉर्म → सभी 32,768 संभावित अगले टोकन के अंक। सही जवाब दिए हों तो लॉस भी "
              "निकालता है: असली अगले टोकन से मॉडल कितना हैरान हुआ।",
        "hinglish": "Token ids → embedding → 12 blocks → final norm → saare 32,768 possible next tokens ke scores. Targets diye hon "
                    "to loss bhi nikalta hai: asli next token se model kitna surprised hua."}),
    "block": ("mona.model", "Block.forward", "One layer: look around, then think", {
        "en": "Two lines are the whole idea: attention mixes in information from earlier tokens, then the feed-forward network "
              "processes each token. Each result is ADDED to x (the residual stream), so layers refine instead of replace.",
        "hi": "दो लाइनें ही पूरा विचार हैं: अटेंशन पहले के टोकन से जानकारी मिलाता है, फिर फ़ीड-फ़ॉरवर्ड हर टोकन को प्रोसेस करता है। हर नतीजा "
              "x में जोड़ा जाता है (residual), इसलिए लेयर बदलती नहीं, सुधारती हैं।",
        "hinglish": "Do lines hi poora idea hain: attention pehle ke tokens se info milata hai, phir feed-forward har token ko process "
                    "karta hai. Har result x mein ADD hota hai (residual), isliye layers replace nahi, refine karti hain."}),
    "attention": ("mona.model", "Attention.forward", "Attention", {
        "en": "One matrix makes a query, key and value for every token. RoPE rotates queries and keys by position. "
              "scaled_dot_product_attention computes softmax(q·k / √64) · v, with a causal mask so no token can see the future.",
        "hi": "एक मैट्रिक्स हर टोकन के लिए query, key और value बनाता है। RoPE स्थिति के हिसाब से q और k घुमाता है। "
              "scaled_dot_product_attention softmax(q·k / √64) · v निकालता है, causal mask के साथ ताकि कोई टोकन भविष्य न देखे।",
        "hinglish": "Ek matrix har token ke liye query, key aur value banata hai. RoPE position ke hisaab se q aur k ghumata hai. "
                    "scaled_dot_product_attention softmax(q·k / √64) · v nikalta hai, causal mask ke saath taaki koi token future na dekhe."}),
    "rope": ("mona.model", "apply_rope", "RoPE: how MONA knows word order", {
        "en": "Each pair of numbers in q and k is rotated by an angle that grows with the position. Two tokens' dot product "
              "then depends on how far apart they are.",
        "hi": "q और k की हर संख्या-जोड़ी स्थिति के साथ बढ़ते कोण से घुमाई जाती है। फिर दो टोकन का dot product उनकी दूरी पर निर्भर करता है।",
        "hinglish": "q aur k ki har number-pair position ke saath badhte angle se ghumayi jaati hai. Phir do tokens ka dot product unki "
                    "doori par depend karta hai."}),
    "swiglu": ("mona.model", "SwiGLU.forward", "The feed-forward 'thinking' part", {
        "en": "Two projections up to 2,048 numbers; one passes through SiLU and acts as a gate on the other; then back down to 768.",
        "hi": "दो प्रोजेक्शन 2,048 संख्याओं तक; एक SiLU से गुज़रकर दूसरे पर गेट बनता है; फिर वापस 768।",
        "hinglish": "Do projections 2,048 numbers tak; ek SiLU se guzarkar doosre par gate banta hai; phir wapas 768."}),
    "embedding": ("mona.model", "MONA.__init__", "Building the model: embeddings and layers", {
        "en": "`self.embed` is the table of 32,768 × 768 numbers: one row per token. The output layer reuses the same table "
              "(weight tying), saving 25 million parameters.",
        "hi": "`self.embed` 32,768 × 768 संख्याओं की तालिका है: हर टोकन की एक पंक्ति। आउटपुट लेयर यही तालिका दोबारा इस्तेमाल करती है, "
              "2.5 करोड़ पैरामीटर बचाकर।",
        "hinglish": "`self.embed` 32,768 × 768 numbers ki table hai: har token ki ek row. Output layer yahi table reuse karti hai "
                    "(weight tying), 25 million parameters bachakar."}),
    "generate": ("mona.model", "MONA.generate", "Writing text, one token at a time", {
        "en": "Scores ÷ temperature → softmax → top-k / top-p cut away unlikely tokens → draw one at random → feed it back in. "
              "The KV-cache keeps earlier keys and values, so each new token costs one small step.",
        "hi": "अंक ÷ temperature → softmax → top-k / top-p असंभावित टोकन हटाते हैं → एक बेतरतीब चुनो → वापस डालो। KV-cache पुराने "
              "keys और values रखता है, इसलिए हर नया टोकन एक छोटा कदम है।",
        "hinglish": "Scores ÷ temperature → softmax → top-k / top-p unlikely tokens hatate hain → ek random chuno → wapas daalo. "
                    "KV-cache purane keys aur values rakhta hai, isliye har naya token ek chhota step hai."}),
    "next_word": ("mona.engine.glassbox", "GlassBox.next_word", "MONA's top guesses for the next token", {
        "en": "Runs the model once and returns the most probable next tokens. Every probability bar in the app comes from here.",
        "hi": "मॉडल एक बार चलाकर सबसे संभावित अगले टोकन लौटाता है। ऐप की हर संभावना-पट्टी यहीं से आती है।",
        "hinglish": "Model ek baar chalakar sabse likely next tokens return karta hai. App ki har probability bar yahin se aati hai."}),
    "trace": ("mona.engine.glassbox", "GlassBox.trace", "Recording attention and the logit lens", {
        "en": "Runs the model layer by layer, keeps every attention map, and applies the final norm + output layer after "
              "each layer to see what MONA would guess at that depth (the logit lens).",
        "hi": "मॉडल को लेयर-दर-लेयर चलाता है, हर अटेंशन मैप रखता है, और हर लेयर के बाद आख़िरी नॉर्म + आउटपुट लेयर लगाकर देखता है कि उस "
              "गहराई पर MONA क्या अंदाज़ा लगाती (logit lens)।",
        "hinglish": "Model ko layer-by-layer chalata hai, har attention map rakhta hai, aur har layer ke baad final norm + output layer "
                    "lagakar dekhta hai ki us depth par MONA kya guess karti (logit lens)."}),
    "shape": ("mona.engine.lessons", "shape", "The sampling knobs", {
        "en": "Temperature reshapes the probabilities; top-k keeps the k best tokens; top-p keeps the smallest group that adds up to p.",
        "hi": "Temperature संभावनाओं का आकार बदलता है; top-k सबसे अच्छे k टोकन रखता है; top-p वह सबसे छोटा समूह रखता है जिसका जोड़ p हो।",
        "hinglish": "Temperature probabilities ka shape badalta hai; top-k best k tokens rakhta hai; top-p woh sabse chhota group rakhta "
                    "hai jiska total p ho."}),
    "tokenizer": ("mona.tokenizer", "_empty", "The tokenizer's recipe", {
        "en": "Normalise Unicode, split text into words (keeping Hindi vowel signs on their letters), then byte-level BPE.",
        "hi": "Unicode सामान्य करो, पाठ को शब्दों में बाँटो (हिंदी मात्राएँ अपने अक्षर के साथ), फिर byte-level BPE।",
        "hinglish": "Unicode normalise karo, text ko words mein baanto (Hindi matras apne letter ke saath), phir byte-level BPE."}),
    "bpe_replay": ("mona.engine.lessons", "bpe_replay", "Replaying BPE merges", {
        "en": "Start from single bytes; repeatedly merge the neighbouring pair that was learned earliest (lowest rank). "
              "This is exactly what the tokenizer does, slowed down so you can watch.",
        "hi": "एक-एक बाइट से शुरू; बार-बार वह पड़ोसी जोड़ा जोड़ो जो सबसे पहले सीखा गया (सबसे कम rank)। टोकनाइज़र यही करता है, बस धीमा करके दिखाया।",
        "hinglish": "Single bytes se shuru; baar-baar woh padosi pair jodo jo sabse pehle seekha gaya (lowest rank). Tokenizer yahi karta "
                    "hai, bas slow karke dikhaya."}),
    "encode_chat": ("mona.tokenizer", "encode_chat", "The chat template and loss mask", {
        "en": "A conversation becomes one token sequence with <|user|> / <|assistant|> markers. The mask is 1 only on the "
              "assistant's tokens, so chat tuning grades MONA only on her answers.",
        "hi": "बातचीत <|user|> / <|assistant|> निशानों के साथ एक टोकन क्रम बनती है। मास्क सिर्फ़ सहायक के टोकन पर 1 है, इसलिए चैट ट्यूनिंग "
              "MONA को सिर्फ़ उसके जवाबों पर अंक देती है।",
        "hinglish": "Conversation <|user|> / <|assistant|> markers ke saath ek token sequence banti hai. Mask sirf assistant ke tokens par 1 "
                    "hai, isliye chat tuning MONA ko sirf uske answers par marks deti hai."}),
    "train": ("mona.engine.minitrain", "train", "The training loop", {
        "en": "Take a batch, compute the loss, backward() finds how each weight should change, clip extreme gradients, "
              "AdamW takes a step. Warmup then cosine decay for the learning rate. MONA's real loop does the same at scale.",
        "hi": "एक बैच लो, लॉस निकालो, backward() बताता है हर वज़न कैसे बदले, बहुत बड़े gradient काटो, AdamW कदम लेता है। लर्निंग रेट पहले "
              "warmup फिर cosine से घटता है। MONA की असली ट्रेनिंग बड़े पैमाने पर यही करती है।",
        "hinglish": "Ek batch lo, loss nikalo, backward() batata hai har weight kaise badle, extreme gradients clip karo, AdamW step leta "
                    "hai. Learning rate pehle warmup phir cosine decay. MONA ki asli training bade scale par yahi karti hai."}),
    "bits_per_byte": ("mona.engine.minitrain", "bits_per_byte", "A fair score: bits per byte", {
        "en": "Total surprise in bits divided by the text's size in bytes. Unlike loss per token, it doesn't depend on the "
              "tokenizer, so different models can be compared fairly.",
        "hi": "कुल हैरानी (बिट) ÷ पाठ का आकार (बाइट)। प्रति-टोकन लॉस के उलट यह टोकनाइज़र पर निर्भर नहीं, इसलिए अलग मॉडलों की निष्पक्ष तुलना होती है।",
        "hinglish": "Total surprise (bits) ÷ text ka size (bytes). Per-token loss ke ulat yeh tokenizer par depend nahi karta, isliye "
                    "alag models ka fair comparison hota hai."}),
    "rag_search": ("mona.engine.rag", "Library.search", "RAG: finding the right passage (BM25)", {
        "en": "Scores every chunk by how many question words it contains, weighting rare words more (idf) and not "
              "over-rewarding long chunks. The best chunks are pasted into MONA's prompt.",
        "hi": "हर टुकड़े को अंक देता है कि उसमें सवाल के कितने शब्द हैं, दुर्लभ शब्दों को ज़्यादा वज़न (idf), लंबे टुकड़ों को ज़्यादा इनाम नहीं। "
              "सबसे अच्छे टुकड़े MONA के प्रॉम्प्ट में डाले जाते हैं।",
        "hinglish": "Har chunk ko score deta hai ki usmein sawaal ke kitne words hain, rare words ko zyada weight (idf), lambe chunks ko "
                    "zyada reward nahi. Best chunks MONA ke prompt mein daale jaate hain."}),
    "keep": ("mona.textclean", "keep", "The data cleaner's rules", {
        "en": "A document is kept only if it's long enough and mostly letters of the right script. Simple rules like these "
              "decide what a model ever gets to learn.",
        "hi": "दस्तावेज़ तभी रखा जाता है जब वह काफ़ी लंबा हो और ज़्यादातर सही लिपि के अक्षर हों। ऐसे सीधे नियम तय करते हैं कि मॉडल क्या सीखेगा।",
        "hinglish": "Document tabhi rakha jaata hai jab woh kaafi lamba ho aur zyadatar sahi script ke letters hon. Aise simple rules "
                    "decide karte hain ki model kya seekhega."}),
    "batches": ("mona.data", "PretrainBatches", "How the language mix is drawn", {
        "en": "For every training row, a language is chosen with the mix weights, then a random window is read from that "
              "language's token file. Change the weights and you change what MONA becomes.",
        "hi": "हर ट्रेनिंग पंक्ति के लिए मिश्रण के वज़न से एक भाषा चुनी जाती है, फिर उस भाषा की टोकन फ़ाइल से एक बेतरतीब हिस्सा पढ़ा जाता है। "
              "वज़न बदलो, MONA बदल जाती है।",
        "hinglish": "Har training row ke liye mix weights se ek language chuni jaati hai, phir us language ki token file se random window "
                    "padhi jaati hai. Weights badlo, MONA badal jaati hai."}),
    "fake_quant": ("mona.ui.labs.beyond", "fake_quant", "Quantization: fewer bits per weight", {
        "en": "Each group of 64 weights is scaled to fit into a few bits, rounded, and scaled back. The rounding error is "
              "exactly the quality you lose.",
        "hi": "64 वज़न के हर समूह को कुछ बिट में फ़िट करने के लिए स्केल किया जाता है, गोल किया जाता है, और वापस स्केल। गोलाई की ग़लती ही "
              "खोई हुई गुणवत्ता है।",
        "hinglish": "64 weights ke har group ko kuch bits mein fit karne ke liye scale kiya jaata hai, round kiya jaata hai, aur wapas scale. "
                    "Rounding error hi khoyi hui quality hai."}),
    "scaling": ("mona.ui.budget", "loss", "The scaling-law formula", {
        "en": "L(N, D) = E + A/N^α + B/D^β: an irreducible floor E, plus a penalty for too few parameters N and one for too "
              "little data D. Fixed compute C ≈ 6·N·D forces a trade-off between the two.",
        "hi": "L(N, D) = E + A/N^α + B/D^β: एक न घटने वाला तल E, कम पैरामीटर N का दंड, और कम डेटा D का दंड। तय कंप्यूट C ≈ 6·N·D दोनों "
              "के बीच चुनाव करवाता है।",
        "hinglish": "L(N, D) = E + A/N^α + B/D^β: ek irreducible floor E, kam parameters N ki penalty, aur kam data D ki penalty. Fixed "
                    "compute C ≈ 6·N·D dono ke beech trade-off karwata hai."}),
}

SCREEN_CODE = {
    "LMGameLab": ["next_word", "forward"], "DataLab": ["keep", "batches"], "TokensLab": ["tokenizer", "bpe_replay"],
    "EmbeddingsLab": ["embedding", "forward"], "AttentionLab": ["attention", "rope"], "LayersLab": ["trace", "block"],
    "SamplingLab": ["shape", "generate"], "TimeMachineLab": ["train", "forward"], "ChatTuningLab": ["encode_chat"],
    "EvalsLab": ["bits_per_byte"], "RagLab": ["rag_search"], "BeyondLab": ["fake_quant", "generate"],
    "CourseScreen": ["train", "bits_per_byte", "tokenizer"], "BudgetScreen": ["scaling"], "IncidentScreen": ["train"],
    "JourneyScreen": ["train", "batches"], "CompareLab": ["generate"],
    "ChatScreen": ["generate", "encode_chat"], "ZoomScreen": ["forward", "block", "attention", "swiglu"],
}
DEFAULT = ["forward", "block", "attention", "swiglu", "generate"]


def source_of(key):
    """(relative path, first line number, code) for a snippet, read from the installed package."""
    module, qual, _, _ = SNIPPETS[key]
    obj = importlib.import_module(module)
    for part in qual.split("."):
        obj = getattr(obj, part)
    lines, start = inspect.getsourcelines(obj)
    path = Path(inspect.getsourcefile(obj))
    try:
        rel = path.relative_to(Path(importlib.import_module("mona").__file__).parent.parent)
    except ValueError:
        rel = path.name
    return str(rel).replace("\\", "/"), start, "".join(lines)


class CodeScreen(ModalScreen):
    BINDINGS = [Binding("escape", "app.pop_screen", "close"), Binding("f8", "app.pop_screen", "close", show=False)]

    def __init__(self, keys):
        super().__init__()
        self.keys = [k for k in keys if k in SNIPPETS] or DEFAULT

    def compose(self) -> ComposeResult:
        with Vertical(id="cv-box"):
            yield Static(id="cv-title", classes="title")
            with Horizontal(id="cv-cols"):
                yield OptionList(id="cv-list")
                with VerticalScroll(id="cv-right"):
                    yield Static(id="cv-code")
            yield Static(id="cv-keys", classes="dim")

    def on_mount(self):
        self.query_one("#cv-title", Static).update(self.app.tr("cv_title"))
        self.query_one("#cv-keys", Static).update(self.app.tr("cv_keys"))
        box = self.query_one("#cv-list", OptionList)
        for k in self.keys:
            box.add_option(Option(SNIPPETS[k][2], id=k))
        box.highlighted = 0
        box.focus()
        self.show()

    def on_option_list_option_highlighted(self, event):
        self.show()

    def show(self):
        box = self.query_one("#cv-list", OptionList)
        key = self.keys[box.highlighted or 0]
        _, _, title, walk = SNIPPETS[key]
        try:
            rel, start, code = source_of(key)
        except Exception as e:                                  # e.g. source not shipped
            self.query_one("#cv-code", Static).update(Text(f"(source not available: {e})", style="#f5c2e7"))
            return
        lang = self.app.state.lang
        head = Text(f"{title}\n", style="bold #f9e2af")
        head.append(f"{rel}:{start}\n\n", style="#89dceb")
        head.append(walk.get(lang, walk["en"]) + "\n", style="#cdd6f4")
        syntax = Syntax(code, "python", theme="monokai", line_numbers=True, start_line=start, word_wrap=False,
                        background_color="#1e1e2e")
        self.query_one("#cv-code", Static).update(Group(head, syntax))
