"""Step ② — clean raw text for each language into data/mona_clean/<lang>/*.txt

Run from C:\\LLM:   python -m pipeline.mona_clean            (all languages)
                    python -m pipeline.mona_clean hindi      (one language)

Each parquet row group is cleaned by its own worker (20 in parallel). Safe to re-run:
row groups that are already cleaned are skipped, so it can be run again as
more downloads finish. Documents in the output are separated by the ASCII record
separator \\x1e (the cleaner removes that character from the text itself), which the
tokenize step turns into the <|endoftext|> token.

Rules (all languages): Unicode NFC, remove invisible/control/private-use characters
(keeping newline, tab, ZWNJ, ZWJ), collapse spaces, at most one blank line in a row,
drop documents under 200 characters, drop exact duplicates.
Per language: Hindi needs >= 60% Devanagari letters (English words inside are kept);
Hinglish needs >= 80% Latin letters and has
its ~70 most frequent machine-transliteration misspellings fixed (haye -> hai, ack -> ek, ...); English is already quality-filtered (FineWeb-Edu).
"""
import hashlib
import sys

from multiprocessing import Pool
from pathlib import Path

import pyarrow.parquet as pq


from mona import config

RAW = config.DATA_DIR / "raw"
SOURCES = {   # language: (raw folder, glob)
    "english":  (RAW / "english_fineweb", "**/*.parquet"),
    "english2": (RAW / "english_fineweb", "**/*.parquet"),   # v2: the shards that "english" did not use
    "hindi":    (RAW / "hindi_sangraha", "**/*.parquet"),
    "hinglish": (RAW / "hinglish_sangraha", "**/*.parquet"),
}
# Public-domain Tulsidas VERSE only. The source corpus also contains Hanuman Prasad Poddar's Hindi
# commentary (Gita Press), which is likely still under copyright, so it is never used for MONA.
USED_BY_ENGLISH = {"000_00000", "001_00000"}      # the two shards the first MONA read (english)
TULSIDAS = config.DATA_DIR / "processed" / "tulsidas_verse_strict.txt"
SEP = "\x1e"
# Cleaning rules live in the package (mona/textclean.py) so the app can use them too.
from mona.textclean import (DEVA, LATIN, LETTER, MIN_CHARS, fix_hinglish, keep,  # noqa: E402,F401
                            normalise)


def clean_file(job):
    """Clean one row group of one parquet file (row groups are cleaned in parallel)."""
    lang, src, rg, dst = job
    seen, n_in, n_out, chars = set(), 0, 0, 0
    tmp = dst.with_suffix(".tmp")
    with open(tmp, "w", encoding="utf-8") as out:
        table = pq.ParquetFile(src).read_row_group(rg, columns=["text"])
        for batch in table.to_batches(max_chunksize=2000):
            for doc in batch.column("text").to_pylist():
                n_in += 1
                if not doc:
                    continue
                doc = normalise(doc)
                if lang == "hinglish":
                    doc = fix_hinglish(doc)
                if not keep(lang, doc):
                    continue
                h = hashlib.blake2b(doc.encode("utf-8"), digest_size=8).digest()
                if h in seen:
                    continue
                seen.add(h)
                out.write(doc + SEP)
                n_out += 1
                chars += len(doc)
    tmp.replace(dst)
    return lang, f"{src.name}[{rg}]", n_in, n_out, chars


def clean_awadhi():
    """Tulsidas verse (public domain, no commentary) -> ~2,000-character documents cut at line boundaries."""
    dst = config.CLEAN_DIR / "awadhi" / "tulsidas.txt"
    dst.parent.mkdir(parents=True, exist_ok=True)
    text = normalise(TULSIDAS.read_text(encoding="utf-8"))
    docs, cur = [], []
    for line in text.split("\n"):
        cur.append(line)
        if sum(map(len, cur)) >= 2000:
            docs.append("\n".join(cur).strip())
            cur = []
    if cur:
        docs.append("\n".join(cur).strip())
    docs = [d for d in docs if len(d) >= MIN_CHARS]
    dst.write_text(SEP.join(docs) + SEP, encoding="utf-8")
    print(f"awadhi: {len(docs):,} docs, {sum(map(len, docs)):,} chars")


def main(langs):
    jobs = []
    for lang in langs:
        if lang == "awadhi":
            clean_awadhi()
            continue
        folder, pattern = SOURCES[lang]
        for src in sorted(folder.glob(pattern)):
            if lang == "english2" and src.stem in USED_BY_ENGLISH:
                continue
            for rg in range(pq.ParquetFile(src).num_row_groups):
                dst = config.CLEAN_DIR / lang / f"{src.stem}_rg{rg:03d}.txt"
                if not dst.exists():
                    dst.parent.mkdir(parents=True, exist_ok=True)
                    jobs.append((lang, src, rg, dst))
    if not jobs:
        print("nothing new to clean")
        return
    print(f"{len(jobs)} row groups to clean", flush=True)
    totals = {}
    with Pool(min(len(jobs), 20)) as pool:
        for i, (lang, name, n_in, n_out, chars) in enumerate(pool.imap_unordered(clean_file, jobs), 1):
            t = totals.setdefault(lang, [0, 0, 0])
            t[0] += n_in; t[1] += n_out; t[2] += chars
            if i % 50 == 0 or i == len(jobs):
                print(f"  {i}/{len(jobs)} row groups done", flush=True)
    for lang, (n_in, n_out, chars) in totals.items():
        print(f"{lang:9s} kept {n_out:>10,}/{n_in:<10,} docs ({n_out / max(n_in, 1):4.0%})  "
              f"{chars / 1e6:9,.0f}M chars (this run)")


if __name__ == "__main__":
    main(sys.argv[1:] or ["awadhi", "english", "hindi", "hinglish"])
