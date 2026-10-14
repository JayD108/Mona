"""Release MONA: checks -> licence-clean bundle -> model card -> upload to Hugging Face.

Run from C:\\LLM:
    python -m scripts.mona_release              # build data/release/ and upload (repo made public)
    python -m scripts.mona_release --dry-run    # build and check only, no upload

Nothing is uploaded unless every check passes. The upload mirrors the app's asset layout under
assets/, so `pip install mona` users get a working app (mona/assets.py downloads it on first run).

Copyright: only public-domain Tulsidas verse and openly licensed data are bundled. The Gita Press
commentary (likely still under copyright) is never included; a scan below enforces that.
"""
import argparse
import csv
import json
import os
import re
import shutil
import sys
import time
from pathlib import Path

import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq
import torch

from mona import config
from mona import tokenizer as T
from mona.model import MONA

REPO = "JayF14/MONA"
OUT = config.DATA_DIR / "release"
A = OUT / "assets"
PRE, CHAT = config.RUNS_DIR / "mona_m", config.RUNS_DIR / "mona_m_chat"
RAW = config.DATA_DIR / "raw"
# words that only appear in the Hindi commentary, never in Tulsidas's verse (copyright scan)
COMMENTARY_MARKERS = ["श्रीरघुनाथजी", "श्रीरामचन्द्रजी", "श्रीरामजी", "कहते हैं", "इसलिये", "अर्थात्‌"]


def log(msg):
    line = f"[{time.strftime('%H:%M:%S')}] {msg}"
    print(line, flush=True)


def fail(msg):
    log("RELEASE CHECK FAILED: " + msg)
    sys.exit(1)


# ── 1. checks ────────────────────────────────────────────────────────────────
def load(path):
    m = MONA(config.MONA_M).eval()
    st = torch.load(path, map_location="cpu", weights_only=False)
    m.load_state_dict(st["model"] if "model" in st else st)
    return m


def checks(tok):
    for p in (PRE / "final.pt", CHAT / "model.pt"):
        if not p.exists():
            fail(f"missing {p}")
    eval_txt = (PRE / "eval.txt").read_text(encoding="utf-8") if (PRE / "eval.txt").exists() else ""
    m = re.search(r"final\.pt\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)", eval_txt)
    if not m:
        fail("eval.txt has no bits-per-byte row for final.pt")
    bpb = dict(zip(["english", "hindi", "hinglish"], map(float, m.groups())))
    if not all(0.3 < v < 2.0 for v in bpb.values()):
        fail(f"bits per byte out of the sane range: {bpb}")
    chat = load(CHAT / "model.pt")
    stop = {tok.token_to_id(T.EOT), tok.token_to_id(T.END)}
    replies = {}
    for q in ["Who are you?", "भारत की राजधानी क्या है?"]:
        torch.manual_seed(0)
        ids = T.chat_prompt(tok, [{"role": "user", "content": q}])
        replies[q] = tok.decode(list(chat.generate(torch.tensor([ids]), 60, temperature=0.3, top_p=0.9, stop_ids=stop)))
    if "MONA" not in replies["Who are you?"]:
        log(f"warning: chat model didn't say its name: {replies['Who are you?']!r}")
    if len(replies["Who are you?"].strip()) < 5:
        fail("chat model gave an empty English answer")
    if len(replies["भारत की राजधानी क्या है?"].strip()) < 5:
        fail("chat model gave an empty Hindi answer")
    log(f"checks passed: bpb {bpb}; chat: {replies['Who are you?'][:80]!r}")
    return bpb, replies


# ── 2. licence-clean bundle (mirrors the app's folder layout) ───────────────
def save_bf16(src, dst):
    st = torch.load(src, map_location="cpu", weights_only=False)
    st = st["model"] if "model" in st else st
    dst.parent.mkdir(parents=True, exist_ok=True)
    converted, out = {}, {}
    for k, v in st.items():           # keep tied weights shared (embedding = output layer): saved once, not twice
        key = v.data_ptr()
        if key not in converted:
            converted[key] = v.to(torch.bfloat16)
        out[k] = converted[key]
    torch.save(out, dst)


def small_parquet(src, dst, n):
    if not src.exists():
        return
    dst.parent.mkdir(parents=True, exist_ok=True)
    batch = next(pq.ParquetFile(src).iter_batches(batch_size=n, columns=["text"]))
    pq.write_table(pa.Table.from_batches([batch]), dst, compression="zstd")


def bundle():
    if OUT.exists():
        shutil.rmtree(OUT)
    # weights (bf16) + tokenizer
    save_bf16(PRE / "final.pt", A / "models/mona/mona.pt")
    save_bf16(CHAT / "model.pt", A / "runs/mona_m_chat/model.pt")
    shutil.copy(config.TOKENIZER_PATH, A / "models/mona/tokenizer.json")
    # training logs + recorded samples (time machine, status)
    (A / "runs/mona_m").mkdir(parents=True, exist_ok=True)
    for f in ("train_log.csv", "eval_log.csv", "samples.txt", "eval.txt"):
        if (PRE / f).exists():
            shutil.copy(PRE / f, A / "runs/mona_m" / f)
    # held-out token samples (lm game, evals, quantization)
    (A / "data/mona_tokens").mkdir(parents=True, exist_ok=True)
    manifest = json.loads((config.TOKENS_DIR / "manifest.json").read_text())
    for lang in manifest:
        val = np.memmap(config.TOKENS_DIR / f"{lang}_val.bin", dtype=np.uint16, mode="r")
        np.asarray(val[:200_000]).tofile(A / f"data/mona_tokens/{lang}_val.bin")
        np.zeros(2048, dtype=np.uint16).tofile(A / f"data/mona_tokens/{lang}_train.bin")   # placeholder
    (A / "data/mona_tokens/manifest.json").write_text(json.dumps(manifest, indent=2))
    # public-domain Tulsidas verse (RAG library, chat examples)
    (A / "data/processed").mkdir(parents=True, exist_ok=True)
    shutil.copy(config.VERSE_PATH, A / "data/processed/tulsidas_verse_strict.txt")
    # small raw samples, same paths the labs read (FineWeb-Edu ODC-By, Sangraha CC-BY-4.0, Wikipedia-derived CC BY-SA)
    for rel, n in [("english_fineweb/sample/10BT/000_00000.parquet", 600),
                   ("hindi_sangraha/verified/hin/data-3.parquet", 600),
                   ("hinglish_sangraha/synthetic/hin_Latn/wiki_hin_Latn_0000_of_0063.parquet", 1500),
                   ("sft/hindi_wiki/synthetic/hin_Deva/wiki_hin_Deva_0000_of_0063.parquet", 3000)]:
        small_parquet(RAW / rel, A / "data/raw" / rel, n)
    # a few chat-training examples per source
    src = config.SFT_DIR / "train.jsonl"
    if src.exists():
        by = {}
        for line in open(src, encoding="utf-8"):
            ex = json.loads(line)
            if len(by.setdefault(ex["source"], [])) < 40:
                by[ex["source"]].append(line)
        (A / "data/mona_sft").mkdir(parents=True, exist_ok=True)
        (A / "data/mona_sft/train.jsonl").write_text("".join(sum(by.values(), [])), encoding="utf-8")
    size = sum(f.stat().st_size for f in OUT.rglob("*") if f.is_file()) / 1e6
    log(f"bundle built: {size:.0f} MB")


def copyright_scan():
    """Refuse to release if any bundled Tulsidas text looks like the copyrighted commentary.

    Scans the verse file and the Tulsidas chat examples (modern Hindi elsewhere legitimately uses
    words like these, so only Tulsidas content is checked).
    """
    texts = [(A / "data/processed/tulsidas_verse_strict.txt").read_text(encoding="utf-8")]
    sft = A / "data/mona_sft/train.jsonl"
    if sft.exists():
        texts += [l for l in sft.read_text(encoding="utf-8").splitlines() if '"source": "tulsidas"' in l]
    n = sum(t.count(m) for t in texts for m in COMMENTARY_MARKERS)
    if n > 3:
        fail(f"{n} commentary markers found in bundled Tulsidas text")
    log(f"copyright scan passed ({n} commentary markers in bundled Tulsidas text)")


# ── 3. model card + notice ───────────────────────────────────────────────────
def model_card(bpb, replies):
    evals = list(csv.DictReader(open(PRE / "eval_log.csv"))) if (PRE / "eval_log.csv").exists() else []
    last = evals[-1] if evals else {}
    card = f"""---
language: [en, hi]
license: mit
library_name: pytorch
pipeline_tag: text-generation
tags: [education, multilingual, hindi, hinglish, awadhi, from-scratch, small-language-model]
---

# MONA: a multilingual small language model you can open up

MONA is a **110M-parameter Llama-style language model trained from scratch on one laptop GPU** for
**English, Hindi, Hinglish and Awadhi** (Tulsidas). It was built to **teach how LLMs work**: the
companion terminal app lets anyone look inside it, stage by stage, in English (the model itself reads and writes English, Hindi, Hinglish and Awadhi).

- Code, app and full build story: https://github.com/JayD108/Mona
- `pip install` the repo, then run `mona`: the app downloads these files on first run.

## Model
| | |
|---|---|
| Architecture | decoder-only transformer: 12 layers, width 768, 12 heads, SwiGLU 2048, RMSNorm, RoPE, tied embeddings |
| Parameters | 110.1M (85.0M non-embedding) |
| Tokenizer | byte-level BPE, 32,768 tokens, trained on a balanced EN / HI / Hinglish / Awadhi sample (Hindi 1.33 tokens/word) |
| Context | 1,024 tokens |
| Pretraining | 2.5B tokens, AdamW, bf16, WSD learning-rate schedule (peak 6e-4), ~19 h on an RTX 5080 Laptop GPU |
| Chat tuning | supervised fine-tuning with loss masking on ~125K conversations |

## Evaluation (held-out text, bits per byte, lower is better)
| English | Hindi | Hinglish |
|---|---|---|
| {bpb['english']:.3f} | {bpb['hindi']:.3f} | {bpb['hinglish']:.3f} |

Final held-out loss per language (nats/token): {', '.join(f'{k} {float(v):.3f}' for k, v in last.items() if k not in ('step', 'tokens'))}

Sample (MONA-Chat, "Who are you?"): *{replies['Who are you?'].strip()[:200]}*

## Files
- `assets/models/mona/mona.pt`: base model (bf16 state dict)  ·  `assets/runs/mona_m_chat/model.pt`: MONA-Chat
- `assets/models/mona/tokenizer.json`: tokenizer (Hugging Face `tokenizers` format)
- `assets/…`: a small, licence-clean demo bundle used by the app (see NOTICE.md)

```python
from mona.engine.glassbox import GlassBox          # from the GitHub repo
gb = GlassBox()                                    # loads the newest weights on CPU
print(gb.next_word("The capital of India is", top=5))
```

## Intended use and limits
For **education and experimentation**. MONA is small: it writes fluent text but **often states things
that are wrong**, cannot do arithmetic, and must not be used for factual, medical, legal or other
consequential decisions.

## Training data and licences
English: FineWeb-Edu (ODC-By 1.0) · Hindi and romanized Hindi: AI4Bharat Sangraha (CC-BY-4.0; its
Wikipedia-derived parts are CC BY-SA) · chat: smol-smoltalk (Apache-2.0), Aya dataset (Apache-2.0) ·
Awadhi: Tulsidas's verses (public domain). See NOTICE.md for full attribution.

**Copyright note:** an earlier Tulsidas corpus also contained a modern Hindi commentary (Gita Press,
likely still under copyright). When this was noticed, at 0.8B of 2.5B training tokens (~0.1% of
batches up to then), it was removed: the rest of pretraining, the chat tuning and everything in this
repository use only public-domain verse. No commentary text is distributed here.

## Credits
Built by Mrittunjay Dubey. Coding assisted by Claude (Anthropic).
"""
    (OUT / "README.md").write_text(card, encoding="utf-8")
    notice = """# NOTICE: data attribution

MONA's code is MIT-licensed. Data used for training and in the demo bundle:

- **FineWeb-Edu** (HuggingFaceFW/fineweb-edu), ODC-By 1.0. © the FineWeb authors; underlying web text belongs to its owners.
- **Sangraha** (ai4bharat/sangraha), CC-BY-4.0. © AI4Bharat. Its Wikipedia-derived (synthetic) parts originate
  from Wikipedia, CC BY-SA 4.0; the bundled samples of those parts are shared under CC BY-SA 4.0.
- **smol-smoltalk** (HuggingFaceTB/smol-smoltalk), Apache-2.0. © Hugging Face.
- **Aya dataset** (CohereLabs/aya_dataset), Apache-2.0. © Cohere For AI and contributors.
- **Tulsidas** (Ramcharitmanas, Vinay Patrika, Kavitavali, Parvati Mangal and other works): 16th–17th century
  verse, public domain. Only the verse text is used; no modern commentary or translation is included.
"""
    (OUT / "NOTICE.md").write_text(notice, encoding="utf-8")
    (OUT / "config.json").write_text(json.dumps({**config.MONA_M.__dict__, "model_type": "mona",
                                                 "tokenizer": "assets/models/mona/tokenizer.json"}, indent=2))
    lic = config.CODE_ROOT / "LICENSE"
    if lic.exists():
        shutil.copy(lic, OUT / "LICENSE")
    log("model card, NOTICE, config written")


# ── 4. upload ────────────────────────────────────────────────────────────────
def heartbeat():
    """Touch a file under runs/ every minute, so the watchdog never mistakes a long upload for a hang."""
    import threading
    beat = config.RUNS_DIR / "logs" / "release_heartbeat"

    def loop():
        while True:
            beat.write_text(time.strftime("%H:%M:%S"))
            time.sleep(60)
    threading.Thread(target=loop, daemon=True).start()


def upload():
    heartbeat()
    os.environ["HF_HUB_DISABLE_XET"] = "1"          # plain LFS uploads (xet stalled on this connection)
    from huggingface_hub import HfApi
    api = HfApi()
    api.create_repo(REPO, repo_type="model", exist_ok=True)
    for attempt in range(1, 6):
        try:
            api.upload_folder(repo_id=REPO, folder_path=str(OUT), commit_message="Release MONA (base + chat) and app assets")
            break
        except Exception as e:
            log(f"upload attempt {attempt} failed: {e}")
            if attempt == 5:
                fail("upload failed 5 times")
            time.sleep(60 * attempt)
    api.update_repo_settings(REPO, private=False)
    log(f"released: https://huggingface.co/{REPO} (public)")


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args()
    tok = T.load()
    bpb, replies = checks(tok)
    bundle()
    copyright_scan()
    model_card(bpb, replies)
    if args.dry_run:
        log(f"dry run: release folder ready at {OUT} (nothing uploaded)")
    else:
        upload()
        (PRE / "RELEASED").write_text(time.strftime("%Y-%m-%d %H:%M"))
