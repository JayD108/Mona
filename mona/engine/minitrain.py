"""Train your own tiny language model in a few minutes: the same steps as MONA, shrunk to laptop-size.

Used by the guided course in the app (key G), and readable on its own:
    corpus()          → real text (MONA's held-out data, decoded)      step 1: data
    make_tokenizer()  → a 2,048-piece byte-level BPE                   step 2: tokenizer
    make_model()      → a ~1M-parameter MONA (same code, smaller)      step 3: model
    train()           → yields progress while it learns                step 4: training
    sample()          → writes text                                    step 5: generation
    bits_per_byte()   → a fair score, comparable with big MONA         step 6: evaluation
"""
import math
import time

import numpy as np
import torch

from .. import config
from ..model import MONA
from .. import tokenizer as T

TINY = dict(vocab_size=2048, d_model=128, n_layers=4, n_heads=4, ffn_hidden=352, context=128)
LANG_FILE = {"en": "english", "hi": "hindi", "hinglish": "hinglish"}


def training_running():
    """MONA's own pretraining is using the GPU right now: keep the course on the CPU."""
    run = config.RUNS_DIR / "mona_m"
    log = run / "train_log.csv"
    return log.exists() and not (run / "final.pt").exists() and time.time() - log.stat().st_mtime < 600


def pick_device():
    return "cuda" if torch.cuda.is_available() and not training_running() else "cpu"


def corpus(lang, n_tokens=150_000):
    """Real text MONA never trained on: its held-out shard for this language, turned back into text."""
    tok = T.load()
    ids = np.memmap(config.TOKENS_DIR / f"{LANG_FILE[lang]}_val.bin", dtype=np.uint16, mode="r")[:n_tokens]
    eot = tok.token_to_id(T.EOT)
    docs, start = [], 0
    arr = np.asarray(ids)
    for end in list(np.where(arr == eot)[0]) + [len(arr)]:
        if end > start:
            docs.append(tok.decode(arr[start:end].tolist()))
        start = end + 1
    text = "\n\n".join(d.strip() for d in docs if d.strip())
    cut = int(len(text) * 0.9)                    # last 10% kept aside as the test set
    return text[:cut], text[cut:]


def make_tokenizer(text, vocab_size=TINY["vocab_size"]):
    """Learn BPE merges on your text: same recipe as MONA's tokenizer, 16x fewer pieces."""
    chunks = [text[i:i + 2000] for i in range(0, len(text), 2000)]
    return T.train(iter(chunks), vocab_size=vocab_size, save_path=None)


def make_model(device="cpu"):
    torch.manual_seed(0)
    return MONA(config.ModelConfig(**TINY)).to(device)


def count_parts(model):
    """Where the parameters live: embedding table, attention, feed-forward, norms."""
    parts = {"embedding": 0, "attention": 0, "feed-forward": 0, "norms": 0}
    for name, p in model.named_parameters():
        key = ("embedding" if "embed" in name else "attention" if "attn" in name else
               "feed-forward" if "ffn" in name else "norms")
        parts[key] += p.numel()
    return parts


def encode(tok, text):
    return torch.tensor(tok.encode(text).ids, dtype=torch.long)


def batches(ids, batch=16, ctx=TINY["context"], device="cpu"):
    """Random windows of ctx+1 tokens: the input is the first ctx, the target is the same shifted by one."""
    while True:
        starts = torch.randint(0, len(ids) - ctx - 1, (batch,))
        x = torch.stack([ids[s:s + ctx] for s in starts])
        y = torch.stack([ids[s + 1:s + ctx + 1] for s in starts])
        yield x.to(device), y.to(device)


@torch.no_grad()
def test_loss(model, ids, device="cpu", ctx=TINY["context"], n=16):
    model.eval()
    g = torch.Generator().manual_seed(1)
    starts = torch.randint(0, len(ids) - ctx - 1, (n,), generator=g)
    x = torch.stack([ids[s:s + ctx] for s in starts]).to(device)
    y = torch.stack([ids[s + 1:s + ctx + 1] for s in starts]).to(device)
    _, loss = model(x, y)
    model.train()
    return loss.item()


def to_text(text):
    """Bytes the tokenizer can't print as letters (half a Hindi letter) are hidden in previews."""
    return text.replace("�", "")


def train(model, ids, steps=300, lr=3e-3, device="cpu", every=10):
    """AdamW + warmup + cosine decay, like MONA. Yields (step, train loss) every `every` steps."""
    opt = torch.optim.AdamW(model.parameters(), lr=lr, betas=(0.9, 0.95), weight_decay=0.1)
    data = batches(ids, device=device)
    model.train()
    for step in range(1, steps + 1):
        warm = 20
        f = step / warm if step < warm else 0.5 * (1 + math.cos(math.pi * (step - warm) / (steps - warm)))
        for g in opt.param_groups:
            g["lr"] = lr * max(f, 0.05)
        x, y = next(data)
        _, loss = model(x, y)
        loss.backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
        opt.step()
        opt.zero_grad(set_to_none=True)
        if step % every == 0 or step == 1:
            yield step, loss.item()


@torch.no_grad()
def sample(model, tok, prompt, n=40, temperature=0.8, device="cpu"):
    ids = encode(tok, prompt)[None].to(device)
    was_training = model.training
    out = list(model.generate(ids, n, temperature=temperature, top_p=0.9))
    model.train(was_training)
    return tok.decode(out)


@torch.no_grad()
def bits_per_byte(model, tok, text, device="cpu", chunks=4):
    """Total surprise (bits) divided by the text's size in bytes: fair across tokenizers of any size."""
    was_training = model.training
    model.eval()
    ctx = model.cfg.context
    ids = encode(tok, text)[: ctx * chunks + 1]
    bits, scored = 0.0, []
    for s in range(0, len(ids) - 1, ctx):
        x = ids[s:s + ctx]
        y = ids[s + 1:s + ctx + 1]
        x = x[:len(y)]
        _, loss = model(x[None].to(device), y[None].to(device))     # mean surprise per token, in nats
        bits += loss.item() * len(y) / math.log(2)
        scored += y.tolist()
    model.train(was_training)
    return bits / max(len(tok.decode(scored).encode("utf-8")), 1)
