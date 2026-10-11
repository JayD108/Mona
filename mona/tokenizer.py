"""MONA tokenizer: byte-level BPE for English + Hindi + Hinglish + Awadhi.

    train(texts_iterator, vocab_size)  learn merges, save to models/mona/tokenizer.json
    load()                             -> tokenizers.Tokenizer
    chat_tokens(tok)                   ids of the special chat tokens
    encode_chat(tok, messages)         ids + loss mask for instruction tuning

Choices (lesson: learn/01_bpe_from_scratch.py):
  * NFC normalisation: the same visible text always maps to the same code points
  * word splitting before BPE (GPT-4 style) but with Unicode *marks* (\\p{M}) kept inside
    words, so Devanagari vowel signs (ि ी ं ्) are never cut off their letters
  * numbers split into chunks of at most 3 digits (helps arithmetic-like patterns)
  * byte-level: any text at all can be encoded; nothing is ever "unknown"
"""
from tokenizers import Regex, Tokenizer, decoders, models, normalizers, pre_tokenizers, trainers

from . import config

EOT, PAD, SYSTEM, USER, ASSISTANT, END = (
    "<|endoftext|>", "<|pad|>", "<|system|>", "<|user|>", "<|assistant|>", "<|end|>")
SPECIAL_TOKENS = [EOT, PAD, SYSTEM, USER, ASSISTANT, END]

PATTERN = (
    r"(?i:'s|'t|'re|'ve|'m|'ll|'d)"                       # English contractions
    r"| ?[\p{L}\p{M}\x{200C}\x{200D}]+"                   # a word: letters + combining marks (+ZWNJ/ZWJ)
    r"|\p{N}{1,3}"                                        # numbers, max 3 digits per piece
    r"| ?[^\s\p{L}\p{M}\p{N}]+[\r\n]*"                    # punctuation runs (incl. । ॥)
    r"|\s*[\r\n]+|\s+(?!\S)|\s+"                          # newlines and spaces
)


def _empty():
    tok = Tokenizer(models.BPE())
    tok.normalizer = normalizers.NFC()
    tok.pre_tokenizer = pre_tokenizers.Sequence([
        pre_tokenizers.Split(Regex(PATTERN), behavior="isolated"),
        pre_tokenizers.ByteLevel(add_prefix_space=False, use_regex=False),
    ])
    tok.decoder = decoders.ByteLevel()
    return tok


def train(text_iterator, vocab_size=32768, save_path=config.TOKENIZER_PATH):
    tok = _empty()
    trainer = trainers.BpeTrainer(vocab_size=vocab_size, min_frequency=2, special_tokens=SPECIAL_TOKENS,
                                  initial_alphabet=pre_tokenizers.ByteLevel.alphabet(), show_progress=True)
    tok.train_from_iterator(text_iterator, trainer=trainer)
    if save_path:
        save_path.parent.mkdir(parents=True, exist_ok=True)
        tok.save(str(save_path))
    return tok


def load(path=config.TOKENIZER_PATH):
    return Tokenizer.from_file(str(path))


def chat_tokens(tok):
    return {name: tok.token_to_id(name) for name in SPECIAL_TOKENS}


def encode_chat(tok, messages, add_eot=True):
    """messages: [{"role": "system"|"user"|"assistant", "content": str}, ...]

    Layout:  <|system|>...<|end|><|user|>...<|end|><|assistant|>...<|end|> ... <|endoftext|>
    Returns (ids, mask): mask=1 on assistant answer tokens (incl. their <|end|>), so the model
    learns to *answer*, not to imitate the user.
    """
    sp = chat_tokens(tok)
    role_tok = {"system": sp[SYSTEM], "user": sp[USER], "assistant": sp[ASSISTANT]}
    ids, mask = [], []
    for m in messages:
        body = tok.encode(m["content"].strip(), add_special_tokens=False).ids
        learn = 1 if m["role"] == "assistant" else 0
        ids += [role_tok[m["role"]]] + body + [sp[END]]
        mask += [0] + [learn] * len(body) + [learn]
    if add_eot:
        ids.append(sp[EOT])
        mask.append(0)
    return ids, mask


def chat_prompt(tok, messages):
    """Prompt ids that end with <|assistant|>, ready for the model to write its reply."""
    ids, _ = encode_chat(tok, messages, add_eot=False)
    return ids + [tok.token_to_id(ASSISTANT)]
