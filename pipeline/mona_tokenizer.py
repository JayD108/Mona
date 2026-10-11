"""Step ③ — train MONA's 32K byte-level BPE tokenizer and report how fair it is per language.

Run from C:\\LLM:   python -m pipeline.mona_tokenizer

Training sample (balanced on purpose, so Hindi isn't starved of merges just because the
web has more English):  English 150M chars, Hindi 150M, Hinglish 30M, Awadhi (all) x2.
Report uses different documents from the ones the tokenizer was trained on.
"""
import itertools

from mona import config
from mona import tokenizer as T

SEP = "\x1e"
BUDGET = {"english": 150_000_000, "hindi": 150_000_000, "hinglish": 30_000_000, "awadhi": 10_000_000}


def docs(lang, skip_chars=0, limit_chars=None):
    """Yield documents of one language, optionally skipping the first `skip_chars`."""
    seen = 0
    for path in sorted((config.CLEAN_DIR / lang).glob("*.txt")):
        with open(path, encoding="utf-8") as f:
            for doc in f.read().split(SEP):
                if not doc:
                    continue
                seen += len(doc)
                if seen <= skip_chars:
                    continue
                yield doc
                if limit_chars and seen - skip_chars >= limit_chars:
                    return


def training_text():
    for lang, budget in BUDGET.items():
        repeats = 2 if lang == "awadhi" else 1
        for _ in range(repeats):
            yield from docs(lang, limit_chars=budget)


def main():
    tok = T.train(training_text(), vocab_size=config.MONA_M.vocab_size)
    print(f"\nSaved {config.TOKENIZER_PATH}  (vocab {tok.get_vocab_size():,})")

    print("\n📘 Tokenizer fairness — held-out text (not used for training):")
    print(f"{'language':9s} | {'chars/token':>11s} | {'tokens/word':>11s}")
    print("-" * 38)
    for lang, budget in BUDGET.items():
        skip = budget * (2 if lang != "awadhi" else 0)      # Awadhi is too small to hold out
        sample = list(itertools.islice(docs(lang, skip_chars=skip, limit_chars=5_000_000), 5000))
        if not sample:
            print(f"{lang:9s} | (no held-out text available)")
            continue
        text = "\n".join(sample)
        n_tok = sum(len(e.ids) for e in tok.encode_batch(sample))
        print(f"{lang:9s} | {len(text) / n_tok:11.2f} | {n_tok / max(len(text.split()), 1):11.2f}")

    print("\nExamples:")
    for s in ["The quick brown fox jumps over the lazy dog.",
              "भारत एक विशाल देश है जहाँ अनेक भाषाएँ बोली जाती हैं।",
              "mujhe kal office jaana hai, par barish ho rahi hai",
              "मंगल भवन अमंगल हारी । द्रवउ सो दसरथ अजिर बिहारी ॥"]:
        pieces = tok.encode(s).tokens
        shown = [tok.decode([tok.token_to_id(p)]) for p in pieces]
        print(f"  {len(pieces):2d} tokens | " + " · ".join(shown))


if __name__ == "__main__":
    main()
