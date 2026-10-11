"""Step ⑧ — evaluate MONA: bits per byte per language, and a comparison with MANAS v1.

Run from C:\\LLM:
    python -m scripts.mona_eval runs/mona_m/final.pt
    python -m scripts.mona_eval runs/mona_m/snap_0.5B.pt runs/mona_m/final.pt   # progress over training

📘 Why bits per byte (bpb)?
Loss per *token* can't be compared between models with different tokenizers: a model whose
tokens are whole words has fewer, harder predictions than a character-level model. Bits per
byte divides the total surprise (in bits) by the number of UTF-8 bytes of the text, which is
the same for every model. Lower = better. (A Devanagari character is 3 bytes, a Latin letter 1.)
"""
import argparse
import math

import numpy as np
import torch

from mona import config
from mona import tokenizer as T
from mona.model import MONA

p = argparse.ArgumentParser()
p.add_argument("weights", nargs="+")
p.add_argument("--size", choices=["M", "tiny"], default="M")
p.add_argument("--windows", type=int, default=64, help="1,024-token windows per language")
args = p.parse_args()

device = config.DEVICE
cfg = config.MONA_M if args.size == "M" else config.MONA_TINY
tok = T.load()
LANGS = ["english", "hindi", "hinglish", "awadhi"]


def windows(lang):
    """Evenly spaced windows of held-out tokens (identical for every model evaluated)."""
    path = config.TOKENS_DIR / f"{lang}_val.bin"
    if not path.exists():
        return None
    data = np.memmap(path, dtype=np.uint16, mode="r")
    n = min(args.windows, (len(data) - 1) // (cfg.context + 1))
    starts = np.linspace(0, len(data) - cfg.context - 2, n).astype(np.int64)
    return torch.from_numpy(np.stack([data[s:s + cfg.context + 1] for s in starts]).astype(np.int64))


@torch.no_grad()
def bits_per_byte(model, block):
    total_nats, total_bytes = 0.0, 0
    for i in range(0, len(block), 8):
        b = block[i:i + 8].to(device)
        x, y = b[:, :-1], b[:, 1:]
        with torch.autocast("cuda", dtype=torch.bfloat16, enabled=device == "cuda"):
            logits, _ = model(x, y)
        nats = torch.nn.functional.cross_entropy(logits.view(-1, logits.size(-1)), y.reshape(-1),
                                                 reduction="sum")
        total_nats += nats.item()
        total_bytes += sum(len(tok.decode(row.tolist()).encode("utf-8")) for row in y.cpu())
    return total_nats / math.log(2) / total_bytes


@torch.no_grad()
def manas_v1_bpb(text):
    """MANAS v1 (character-level) on the same text, for comparison."""
    from manas.inference import Manas
    m = Manas()
    ids, _ = m.tokenizer.encode_array(text)
    data = torch.from_numpy(ids.astype(np.int64))
    T_ = 256
    starts = torch.linspace(0, len(data) - T_ - 2, 200).long()
    x = torch.stack([data[s:s + T_] for s in starts]).to(device)
    y = torch.stack([data[s + 1:s + T_ + 1] for s in starts]).to(device)
    nats = sum(m.model(x[i:i + 50], y[i:i + 50])[1].item() * y[i:i + 50].numel() for i in range(0, 200, 50))
    chars = [m.tokenizer.decode(row.tolist()) for row in y.cpu()]
    return nats / math.log(2) / sum(len(c.encode("utf-8")) for c in chars)


blocks = {lang: windows(lang) for lang in LANGS}
print(f"{'model':40s} " + " ".join(f"{l:>9s}" for l in LANGS) + "   (bits per byte, lower is better)")
for w in args.weights:
    model = MONA(cfg).to(device)
    state = torch.load(w, map_location=device, weights_only=False)
    model.load_state_dict(state["model"] if "model" in state else state)
    model.eval()
    row = [f"{bits_per_byte(model, b):9.3f}" if b is not None else f"{'-':>9s}" for b in blocks.values()]
    print(f"{w[-40:]:40s} " + " ".join(row))
    del model

if blocks["awadhi"] is not None:
    awadhi_text = tok.decode(np.memmap(config.TOKENS_DIR / "awadhi_val.bin", dtype=np.uint16, mode="r").tolist())
    print(f"{'MANAS v1 (character-level, Awadhi only)':40s} {'':>9s} {'':>9s} {'':>9s} {manas_v1_bpb(awadhi_text):9.3f}")
