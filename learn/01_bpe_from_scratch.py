"""LESSON 1 — Byte-Pair Encoding (BPE) from scratch.

Run from C:\\LLM:  python learn/01_bpe_from_scratch.py

BPE in one sentence: repeatedly find the most frequent adjacent pair of tokens
and merge it into a new token. That's the whole algorithm used by GPT, Llama, Qwen.

(Real tokenizers work on UTF-8 bytes and are written in Rust for speed; this
version works on characters so the Devanagari merges are readable.)
"""
from collections import Counter
from pathlib import Path

text = Path("data/processed/tulsidas_verse.txt").read_text(encoding="utf-8")

# 1. Split into words (BPE never merges across a space) and count each word once.
#    A word is stored as a tuple of tokens; at the start every token is one character.
word_counts = Counter(text.split())
words = {tuple(w): c for w, c in word_counts.items()}
print(f"{len(text):,} characters, {len(word_counts):,} distinct words\n")


def most_frequent_pair(words):
    pairs = Counter()
    for tokens, count in words.items():
        for a, b in zip(tokens, tokens[1:]):
            pairs[a, b] += count
    return pairs.most_common(1)[0] if pairs else (None, 0)


def merge(words, pair):
    a, b = pair
    new_words = {}
    for tokens, count in words.items():
        out, i = [], 0
        while i < len(tokens):
            if i < len(tokens) - 1 and tokens[i] == a and tokens[i + 1] == b:
                out.append(a + b)        # the two tokens become one
                i += 2
            else:
                out.append(tokens[i])
                i += 1
        new_words[tuple(out)] = count
    return new_words


def tokenize(word, merges):
    """Apply learned merges, in the order they were learned, to a new word."""
    tokens = list(word)
    for a, b in merges:
        i = 0
        while i < len(tokens) - 1:
            if tokens[i] == a and tokens[i + 1] == b:
                tokens[i:i + 2] = [a + b]
            else:
                i += 1
    return tokens


# 2. Learn merges
N_MERGES = 1000
merges = []
for step in range(N_MERGES):
    pair, freq = most_frequent_pair(words)
    if pair is None:
        break
    merges.append(pair)
    words = merge(words, pair)
    if step < 25 or step in (99, 499, 999):
        print(f"merge {step + 1:4d}: '{pair[0]}' + '{pair[1]}' -> '{pair[0] + pair[1]}'   (seen {freq:,} times)")

# 3. Watch a verse get shorter as the tokenizer learns more merges
verse = "मंगल भवन अमंगल हारी । द्रवउ सो दसरथ अजिर बिहारी ॥"
print(f"\nVerse: {verse}  ({len(verse)} characters)\n")
for n in (0, 50, 200, 1000):
    toks = [t for w in verse.split() for t in tokenize(w, merges[:n])]
    print(f"after {n:4d} merges: {len(toks):2d} tokens  |  " + " · ".join(toks))
