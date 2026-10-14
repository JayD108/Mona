"""Step ④ — turn cleaned text into binary token shards for training.

Run from C:\\LLM:   python -m pipeline.mona_tokenize            (all languages)
                    python -m pipeline.mona_tokenize hindi      (one language)

Output, per language, in data/mona_tokens/:
    <lang>_train.bin   uint16 token ids, documents separated by <|endoftext|>
    <lang>_val.bin     held-out tokens (the last documents of the language)
    manifest.json      token counts per language

📘 Why uint16: the vocabulary has 32,768 tokens (< 65,536), so every id fits in 2 bytes.
2.5B tokens = 5 GB on disk, read straight from disk during training (memory-mapped).
"""
import json
import sys
import time

import numpy as np

from mona import config
from mona import tokenizer as T

SEP = "\x1e"
CAP = {"english": 1_600_000_000, "english2": None, "hindi": 1_150_000_000, "hinglish": 130_000_000, "awadhi": None}
VAL = {"english": 2_000_000, "english2": 1_000_000, "hindi": 2_000_000, "hinglish": 1_000_000, "awadhi": None}  # awadhi: last 5%
BATCH_DOCS = 2000


def tokenize_language(tok, lang):
    eot = tok.token_to_id(T.EOT)
    files = sorted((config.CLEAN_DIR / lang).glob("*.txt"))
    out_dir = config.TOKENS_DIR
    out_dir.mkdir(parents=True, exist_ok=True)
    all_path = out_dir / f"{lang}_all.tmp"
    n_tokens, n_docs, t0 = 0, 0, time.time()
    with open(all_path, "wb") as out:
        for i_file, path in enumerate(files, 1):
            docs = [d for d in path.read_text(encoding="utf-8").split(SEP) if d]
            for i in range(0, len(docs), BATCH_DOCS):
                encs = tok.encode_batch(docs[i:i + BATCH_DOCS], add_special_tokens=False)
                ids = np.fromiter((t for e in encs for t in (*e.ids, eot)), dtype=np.uint16)
                out.write(ids.tobytes())
                n_tokens += len(ids)
                n_docs += len(encs)
            if i_file % 20 == 0 or i_file == len(files):
                print(f"  {lang:9s} file {i_file}/{len(files)} total {n_tokens / 1e6:9,.1f}M tokens "
                  f"({n_tokens / (time.time() - t0) / 1e6:.2f}M tok/s)", flush=True)
            if CAP[lang] and n_tokens >= CAP[lang] + (VAL[lang] or 0):
                break

    # split: the last documents become validation, cut at an <|endoftext|> boundary
    data = np.memmap(all_path, dtype=np.uint16, mode="r")
    n_val = VAL[lang] or int(len(data) * 0.05)
    cut = len(data) - n_val
    while data[cut - 1] != eot:
        cut -= 1
    np.asarray(data[:cut]).tofile(out_dir / f"{lang}_train.bin")
    np.asarray(data[cut:]).tofile(out_dir / f"{lang}_val.bin")
    del data
    all_path.unlink()
    return {"train_tokens": int(cut), "val_tokens": int(n_tokens - cut), "docs": n_docs}


def main(langs):
    tok = T.load()
    manifest_path = config.TOKENS_DIR / "manifest.json"
    manifest = json.loads(manifest_path.read_text()) if manifest_path.exists() else {}
    for lang in langs:
        print(f"[{lang}]", flush=True)
        manifest[lang] = tokenize_language(tok, lang)
        manifest_path.write_text(json.dumps(manifest, indent=2))
        print(f"  -> {manifest[lang]}", flush=True)


if __name__ == "__main__":
    main(sys.argv[1:] or ["awadhi", "hinglish", "hindi", "english"])
