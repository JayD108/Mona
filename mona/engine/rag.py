"""A tiny, readable RAG library: chunks of real text + BM25 search.

BM25 in one line: a chunk scores high when it contains the question's words, especially RARE words
(a match on "तुलसीदास" counts far more than a match on "का"), with diminishing returns for repeats
and a small penalty for very long chunks. Search engines used this for decades before embeddings.
"""
import json
import math
from collections import Counter
from dataclasses import dataclass, field

import pyarrow.parquet as pq
import regex

from .. import config

WORD = regex.compile(r"[\p{L}\p{M}\p{N}]+")


def words(text):
    return [w.lower() for w in WORD.findall(text)]


@dataclass
class Chunk:
    source: str          # "tulsidas" | "hindi-wiki" | "hinglish-wiki" | "yours"
    title: str
    text: str
    terms: Counter = field(default_factory=Counter)


@dataclass
class Hit:
    chunk: Chunk
    score: float
    matched: list        # question words found in this chunk


class Library:
    def __init__(self, k1=1.5, b=0.75):
        self.chunks, self.df, self.k1, self.b = [], Counter(), k1, b

    def add(self, source, title, text):
        c = Chunk(source, title, text, Counter(words(title + " " + text)))
        self.chunks.append(c)
        self.df.update(c.terms.keys())

    @property
    def avg_len(self):
        return sum(sum(c.terms.values()) for c in self.chunks) / max(len(self.chunks), 1)

    def idf(self, w):
        n, d = len(self.chunks), self.df.get(w, 0)
        return math.log(1 + (n - d + 0.5) / (d + 0.5))

    def search(self, question, k=3):
        q = [w for w in dict.fromkeys(words(question))]          # unique, in order
        avg = self.avg_len
        hits = []
        for c in self.chunks:
            length = sum(c.terms.values())
            score, matched = 0.0, []
            for w in q:
                tf = c.terms.get(w, 0)
                if tf:
                    matched.append(w)
                    score += self.idf(w) * tf * (self.k1 + 1) / (tf + self.k1 * (1 - self.b + self.b * length / avg))
            if score > 0:
                hits.append(Hit(c, score, matched))
        return sorted(hits, key=lambda h: -h.score)[:k]


def build_library(n_wiki=3000, n_hinglish=1500):
    """MONA's demo library: Tulsidas verses (public domain) + Hindi and Hinglish Wikipedia openings (CC BY-SA)."""
    lib = Library()
    # Public-domain Tulsidas verses only, 4 lines per passage. The Gita Press commentary is likely still
    # under copyright, so it is never part of MONA's library.
    verse = config.DATA_DIR / "processed" / "tulsidas_verse_strict.txt"
    if verse.exists():
        lines = [l.strip() for l in open(verse, encoding="utf-8") if l.strip()]
        for i in range(0, len(lines), 4):
            lib.add("tulsidas", lines[i][:60], "\n".join(lines[i:i + 4]))
    for source, path, n in (("hindi-wiki", config.DATA_DIR / "raw/sft/hindi_wiki/synthetic/hin_Deva/wiki_hin_Deva_0000_of_0063.parquet", n_wiki),
                            ("hinglish-wiki", config.DATA_DIR / "raw/hinglish_sangraha/synthetic/hin_Latn/wiki_hin_Latn_0000_of_0063.parquet", n_hinglish)):
        if not path.exists():
            continue
        batch = next(pq.ParquetFile(path).iter_batches(batch_size=n, columns=["text"]))
        for doc in batch.column("text").to_pylist():
            parts = doc.strip().split("\n", 1)
            if len(parts) == 2 and 2 <= len(parts[0]) <= 60:
                body = " ".join(l.strip() for l in parts[1].split("\n") if len(l.strip()) > 40)[:700]
                if source == "hinglish-wiki":
                    from ..textclean import fix_hinglish
                    body, title = fix_hinglish(body), fix_hinglish(parts[0].strip())
                else:
                    title = parts[0].strip()
                if len(body) > 150:
                    lib.add(source, title, body)
    return lib
