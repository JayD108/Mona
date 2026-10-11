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
import unicodedata
from multiprocessing import Pool
from pathlib import Path

import pyarrow.parquet as pq
import regex

from mona import config

RAW = config.DATA_DIR / "raw"
SOURCES = {   # language: (raw folder, glob)
    "english":  (RAW / "english_fineweb", "**/*.parquet"),
    "hindi":    (RAW / "hindi_sangraha", "**/*.parquet"),
    "hinglish": (RAW / "hinglish_sangraha", "**/*.parquet"),
}
TULSIDAS = config.DATA_DIR / "processed" / "dataset_awadhi_tulsidas_verified.txt"
SEP = "\x1e"
MIN_CHARS = 200

INVISIBLE = regex.compile(r"[^\P{C}\n\t‌‍]")          # category C except allowed ones
SPACES    = regex.compile(r"[^\S\n]+")                           # runs of spaces/tabs (not newlines)
BLANKS    = regex.compile(r"\n\s*\n\s*\n+")                      # 2+ blank lines
LETTER    = regex.compile(r"\p{L}")
DEVA      = regex.compile(r"\p{Devanagari}")
LATIN     = regex.compile(r"\p{Latin}")


# Sangraha's romanized Hindi is machine-transliterated with spellings nobody types
# ("ack prajaati haye" for "ek prajati hai"). Map the most frequent ones (measured: the top
# function words) to common Hinglish spellings; everything else is left as it is.
HINGLISH_FIX = dict(pair.split(":") for pair in """
key:ke kii:ki haye:hai koo:ko seey:se ack:ek kaa:ka thaa:tha ney:ne gayaa:gaya parr:par joe:jo
they:the diyaa:diya bhee:bhi thee:thi taka:tak apane:apne jaataa:jata curr:kar naheen:nahi
nahin:nahi hoe:ho dee:di gaee:gayi pahale:pehle yaa:ya unake:unke unhein:unhe way:ve see:se
jisamen:jisme kartaa:karta apani:apni karate:karte vaale:wale jaba:jab dou:do huaa:hua
karane:karne kaee:kai hotey:hote hotaa:hota sakate:sakte isake:iske usake:uske unakaa:unka
unakee:unki inake:inke kahaa:kaha rahaa:raha rahee:rahi rahey:rahe liyaa:liya kiyaa:kiya
jaatey:jate jaatee:jati karatee:karti vaalaa:wala vaalee:wali sabase:sabse iskaa:iska
iskee:iski jisase:jisse kisee:kisi koee:koi jisakaa:jiska jisakee:jiski aapakaa:aapka
""".split())
HINGLISH_WORD = regex.compile(r"\b(" + "|".join(sorted(HINGLISH_FIX, key=len, reverse=True)) + r")\b")


def fix_hinglish(text):
    return HINGLISH_WORD.sub(lambda m: HINGLISH_FIX[m.group(1)], text)


def normalise(text):
    text = unicodedata.normalize("NFC", text)
    text = INVISIBLE.sub("", text)
    text = SPACES.sub(" ", text)
    text = BLANKS.sub("\n\n", text)
    return "\n".join(line.strip() for line in text.split("\n")).strip()


def keep(lang, text):
    if len(text) < MIN_CHARS:
        return False
    if lang == "english":
        return True
    letters = len(LETTER.findall(text)) or 1
    if lang == "hindi":
        return len(DEVA.findall(text)) / letters >= 0.6
    if lang == "hinglish":
        return len(LATIN.findall(text)) / letters >= 0.8
    return True


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
    """Tulsidas corpus -> ~2,000-character documents cut at line boundaries."""
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
