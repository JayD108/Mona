"""Step ⑥ — build the instruction-tuning (chat) dataset for MONA.

Run from C:\\LLM:   python -m pipeline.mona_build_sft

Output: data/mona_sft/train.jsonl, val.jsonl — one {"messages": [...], "source": ...} per line.

Sources (each optional: missing ones are skipped)
  english   smol-smoltalk (Apache-2.0): ~80K multi-turn chats
  hindi     Aya dataset Hindi rows (Apache-2.0), human-written
  hindi_qa  Hindi Wikipedia (Sangraha synthetic/hin_Deva): "X के बारे में बताइए" -> article opening
  hinglish  romanized Hindi Wikipedia (Sangraha synthetic/hin_Latn): "X ke baare mein batao"
  tulsidas  verse completion from public-domain Tulsidas verses (no copyrighted commentary)
  identity  "who are you?" in all three languages, so MONA knows its name and its limits

📘 Every conversation is checked against the 1,024-token context: long chats are cut at
a turn boundary so they always end with an assistant reply.
"""
import json
import random
import re

import pyarrow.parquet as pq

from mona import config
from mona import tokenizer as T
from mona.textclean import fix_hinglish, normalise

RAW = config.DATA_DIR / "raw"
random.seed(0)
tok = T.load()
CREATOR = "Mrittunjay Dubey"

SYSTEM_PROMPTS = [
    "You are MONA, a helpful assistant. Reply in the same language as the user.",
    "You are MONA. Answer clearly and briefly.",
    "आप MONA हैं, एक सहायक। उपयोगकर्ता की भाषा में उत्तर दें।",
]


def n_tokens(messages):
    return len(T.encode_chat(tok, messages)[0])


def fit(messages, limit=config.MONA_M.context):
    """Keep the longest prefix of turns that fits and ends with an assistant reply."""
    while messages and n_tokens(messages) > limit:
        messages = messages[:-1]
    while messages and messages[-1]["role"] != "assistant":
        messages = messages[:-1]
    return messages if any(m["role"] == "assistant" for m in messages) else None


def with_system(messages, p=0.3):
    if random.random() < p:
        return [{"role": "system", "content": random.choice(SYSTEM_PROMPTS)}] + messages
    return messages


def english(limit=80_000):
    files = sorted((RAW / "sft" / "smol-smoltalk" / "data").glob("train-*.parquet"))
    rows = [r for f in files for r in pq.read_table(f).to_pylist()]
    random.shuffle(rows)
    for r in rows[:limit]:
        msgs = [{"role": m["role"], "content": m["content"]} for m in r["messages"]
                if m["role"] in ("system", "user", "assistant")]
        yield "english", msgs


def aya_hindi():
    for f in sorted((RAW / "sft" / "aya_dataset").rglob("*.parquet")):
        for r in pq.read_table(f).to_pylist():
            if r.get("language") == "Hindi" and r.get("inputs") and r.get("targets"):
                yield "hindi_aya", [{"role": "user", "content": r["inputs"]},
                                    {"role": "assistant", "content": r["targets"]}]


def opening(body, max_chars=700, stop="।"):
    """First paragraph(s) of an article, cut at a sentence end."""
    text = body.strip()[:max_chars]
    cut = max(text.rfind(stop), text.rfind("."))
    return text[:cut + 1] if cut > 150 else None


QA_TEMPLATES = {
    "hindi_qa": ["{t} के बारे में बताइए।", "{t} क्या है?", "मुझे {t} के बारे में जानकारी दीजिए।",
                 "{t} पर एक छोटा परिचय लिखिए।"],
    "hinglish": ["{t} ke baare mein batao", "{t} kya hai?", "mujhe {t} ke baare mein bataiye",
                 "{t} par chhota sa intro likho"],
}


def wiki_qa(source, folder, limit, stop):
    files = sorted(folder.rglob("*.parquet"))
    count = 0
    for f in files:
        for r in pq.read_table(f, columns=["text"]).to_pylist():
            text = normalise(r["text"])
            if source == "hinglish":
                text = fix_hinglish(text)       # same spelling fixes as the pretraining data
            parts = text.split("\n", 1)
            if len(parts) < 2:
                continue
            title, body = parts[0].strip(), parts[1]
            if not (2 <= len(title) <= 60):
                continue
            # body starts with the title as the subject ("X is a ..."): keep it. Drop section
            # headings ("varnan." / "वर्णन।"), i.e. short lines, and join the rest as prose.
            body = " ".join(line.strip() for line in body.split("\n") if len(line.strip()) > 40)
            answer = opening(body, stop=stop)
            if not answer:
                continue
            q = random.choice(QA_TEMPLATES[source]).format(t=title)
            yield source, [{"role": "user", "content": q}, {"role": "assistant", "content": answer}]
            count += 1
            if count >= limit:
                return


# Copyright: only Tulsidas's own verses (16th century, public domain) are used. The Hindi commentary
# (Hanuman Prasad Poddar / Gita Press) is likely still under copyright, so no verse→meaning pairs.
COMPLETE_ASKS = [
    "इस चौपाई को पूरा कीजिए:\n{a} ।",
    "तुलसीदास जी की यह पंक्ति आगे बढ़ाइए:\n{a} ।",
    "Complete this chaupai by Tulsidas:\n{a} ।",
    "is chaupai ko poora karo:\n{a} ।",
]
NEXT_LINE_ASKS = [
    "इसके बाद की पंक्ति सुनाइए:\n{a}",
    "What is the next line of this verse by Tulsidas?\n{a}",
    "iske baad ki line sunao:\n{a}",
]


def tulsidas():
    """Verse-completion tasks built only from public-domain verse lines."""
    path = config.DATA_DIR / "processed" / "tulsidas_verse_strict.txt"
    lines = [l.strip() for l in open(path, encoding="utf-8") if l.strip()]
    for i, line in enumerate(lines):
        halves = [h.strip() for h in line.rstrip("॥।0123456789०१२३४५६७८९ ").split("।") if h.strip()]
        if len(halves) == 2 and all(len(h.split()) >= 3 for h in halves):          # a chaupai: half । half ॥
            yield "tulsidas", [{"role": "user", "content": random.choice(COMPLETE_ASKS).format(a=halves[0])},
                               {"role": "assistant", "content": f"{halves[0]} । {halves[1]} ॥"}]
        if i + 1 < len(lines) and random.random() < 0.3:
            yield "tulsidas", [{"role": "user", "content": random.choice(NEXT_LINE_ASKS).format(a=line)},
                               {"role": "assistant", "content": lines[i + 1]}]


IDENTITY = [
    (["Who are you?", "What is your name?", "Introduce yourself.", "What are you?"],
     f"I am MONA, a small multilingual language model. I understand English, Hindi and Hinglish, and I "
     f"have a special fondness for Awadhi poetry, especially Tulsidas. I was trained from scratch on a "
     f"single laptop GPU by {CREATOR} as a learning project, so I can make mistakes. Please double-check "
     f"anything important."),
    (["Who made you?", "Who created you?", "Who trained you?"],
     f"I was built and trained from scratch by {CREATOR}, as a project to learn how large language models "
     f"are made: from the tokenizer and the transformer architecture to pretraining and instruction tuning."),
    (["तुम कौन हो?", "आपका नाम क्या है?", "अपना परिचय दीजिए।"],
     f"मैं MONA हूँ, एक छोटा बहुभाषी भाषा मॉडल। मैं हिंदी, अंग्रेज़ी और हिंग्लिश समझती हूँ और मुझे अवधी कविता, "
     f"ख़ासकर तुलसीदास जी की रचनाओं से विशेष लगाव है। मुझे {CREATOR} ने एक लैपटॉप GPU पर शुरू से प्रशिक्षित किया है, "
     f"इसलिए मुझसे गलतियाँ हो सकती हैं। ज़रूरी बातों की जाँच अवश्य करें।"),
    (["tum kaun ho?", "tumhara naam kya hai?", "apna intro do"],
     f"Main MONA hoon, ek chhota multilingual language model. Main English, Hindi aur Hinglish samajhti hoon, "
     f"aur mujhe Awadhi kavita, khaaskar Tulsidas ji se khaas lagaav hai. Mujhe {CREATOR} ne ek laptop GPU par "
     f"shuru se train kiya hai, isliye mujhse galtiyan ho sakti hain."),
]


def identity(copies=40):
    for _ in range(copies):
        for questions, answer in IDENTITY:
            yield "identity", [{"role": "user", "content": random.choice(questions)},
                               {"role": "assistant", "content": answer}]


def main():
    out_dir = config.SFT_DIR
    out_dir.mkdir(parents=True, exist_ok=True)
    generators = [
        english(),
        aya_hindi(),
        wiki_qa("hindi_qa", RAW / "sft" / "hindi_wiki", limit=25_000, stop="।"),
        wiki_qa("hinglish", RAW / "hinglish_sangraha", limit=10_000, stop="."),
        tulsidas(),
        identity(),
    ]
    examples, counts, dropped = [], {}, 0
    for gen in generators:
        try:
            for source, msgs in gen:
                msgs = fit(with_system(msgs))
                if msgs is None:
                    dropped += 1
                    continue
                examples.append({"messages": msgs, "source": source})
                counts[source] = counts.get(source, 0) + 1
        except FileNotFoundError as e:
            print(f"  skipped a source: {e}")
    random.shuffle(examples)
    n_val = max(500, len(examples) // 50)
    for name, part in (("val", examples[:n_val]), ("train", examples[n_val:])):
        with open(out_dir / f"{name}.jsonl", "w", encoding="utf-8") as f:
            for ex in part:
                f.write(json.dumps(ex, ensure_ascii=False) + "\n")
    print("Conversations per source:")
    for s, c in sorted(counts.items(), key=lambda x: -x[1]):
        print(f"  {s:10s} {c:8,}")
    print(f"total {len(examples):,} (train {len(examples) - n_val:,}, val {n_val:,}); "
          f"dropped {dropped:,} that could not fit")


if __name__ == "__main__":
    main()
