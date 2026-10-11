"""Extra glass-box tools for the labs: BPE replay, sampling filters, attention-head detectors,
and the training time machine. All of it uses MONA's real tokenizer, weights and logs.
"""
import csv
import json
from dataclasses import dataclass
from functools import lru_cache

import torch

from .. import config
from ..model import MONA


# ── Tokens lab: replay BPE on one word ──────────────────────────────────────
@lru_cache(maxsize=1)
def _byte_tables():
    """GPT-2's byte <-> printable-character table (byte-level BPE stores bytes as these characters)."""
    bs = list(range(ord("!"), ord("~") + 1)) + list(range(ord("¡"), ord("¬") + 1)) + list(range(ord("®"), ord("ÿ") + 1))
    cs = bs[:]
    n = 0
    for b in range(256):
        if b not in bs:
            bs.append(b)
            cs.append(256 + n)
            n += 1
    to_char = {b: chr(c) for b, c in zip(bs, cs)}
    return to_char, {v: k for k, v in to_char.items()}


@lru_cache(maxsize=1)
def _merge_ranks():
    merges = json.loads(config.TOKENIZER_PATH.read_text(encoding="utf-8"))["model"]["merges"]
    return {tuple(m if isinstance(m, list) else m.split(" ")): i for i, m in enumerate(merges)}


def piece_text(piece):
    """A byte-level piece -> readable text. Incomplete letters are shown as their raw bytes, e.g. ⟨E0 A4⟩."""
    _, to_byte = _byte_tables()
    raw = bytes(to_byte[c] for c in piece)
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError:
        return "⟨" + " ".join(f"{b:02X}" for b in raw) + "⟩"


@dataclass
class MergeStep:
    pieces: list        # readable pieces after this step
    merged: str         # the new piece made in this step ("" for the starting bytes)
    rank: int           # how early this merge was learned (0 = the most common pair in the data)


def bpe_replay(tok, word):
    """Apply MONA's learned merges to `word`, one merge at a time, like the real tokenizer does."""
    ranks = _merge_ranks()
    steps = []
    for chunk, _ in tok.pre_tokenizer.pre_tokenize_str(word):
        pieces = list(chunk)
        steps.append(MergeStep([piece_text(p) for p in pieces], "", -1))
        while len(pieces) > 1:
            pairs = [(ranks.get((a, b), 10**9), i) for i, (a, b) in enumerate(zip(pieces, pieces[1:]))]
            rank, i = min(pairs)
            if rank == 10**9:
                break
            a, b = pieces[i], pieces[i + 1]
            out, j = [], 0
            while j < len(pieces):                      # merge every occurrence of this pair
                if j < len(pieces) - 1 and pieces[j] == a and pieces[j + 1] == b:
                    out.append(a + b)
                    j += 2
                else:
                    out.append(pieces[j])
                    j += 1
            pieces = out
            steps.append(MergeStep([piece_text(p) for p in pieces], piece_text(a + b), rank))
    return steps


# ── Sampling lab: the three knobs ───────────────────────────────────────────
def shape(logits, temperature=1.0, top_k=None, top_p=None):
    """Return (probabilities after temperature, mask of tokens still allowed by top-k / top-p)."""
    p = torch.softmax(logits / max(temperature, 1e-5), dim=-1)
    keep = torch.ones_like(p, dtype=torch.bool)
    if top_k:
        kth = torch.topk(p, min(top_k, p.numel())).values[-1]
        keep &= p >= kth
    if top_p and top_p < 1.0:
        sp, si = torch.sort(p, descending=True)
        drop = (sp.cumsum(0) - sp) >= top_p
        keep_sorted = torch.zeros_like(keep)
        keep_sorted[si] = ~drop
        keep &= keep_sorted
    return p, keep


# ── Attention lab: find heads with a recognisable job ───────────────────────
def head_roles(attention):
    """attention: (layers, heads, T, T). Scores in [0, 1] for two well-known head behaviours."""
    L, H, T, _ = attention.shape
    idx = torch.arange(1, T)
    prev = attention[:, :, idx, idx - 1].mean(-1)            # looks at the token just before
    first = attention[:, :, 1:, 0].mean(-1)                  # parks attention on the first token ("sink")
    roles = []
    for l in range(L):
        for h in range(H):
            roles.append({"layer": l, "head": h, "previous": prev[l, h].item(), "first": first[l, h].item()})
    return roles


# ── Training time machine ────────────────────────────────────────────────────
RUN = config.RUNS_DIR / "mona_m"


def checkpoints():
    """[(label, tokens_seen_in_billions, path or None)] — None = an untrained model (step 0)."""
    out = [("step 0 (untrained)", 0.0, None)]
    for snap in sorted(RUN.glob("snap_*B.pt"), key=lambda p: float(p.stem[5:-1])):
        out.append((f"{snap.stem[5:]} tokens", float(snap.stem[5:-1]), snap))
    if (RUN / "final.pt").exists():
        out.append(("final", 2.5, RUN / "final.pt"))
    elif (config.MODEL_DIR / "mona.pt").exists():                 # installed copy: released weights
        out.append(("final (released)", 2.5, config.MODEL_DIR / "mona.pt"))
    elif (RUN / "ckpt.pt").exists():
        rows = list(csv.DictReader(open(RUN / "train_log.csv")))
        seen = int(rows[-1]["tokens"]) / 1e9 if rows else 0.0
        out.append((f"latest ({seen:.2f}B tokens)", seen, RUN / "ckpt.pt"))
    return out


def load_model(path, cfg=config.MONA_M, device="cpu"):
    model = MONA(cfg).to(device).eval()
    if path is not None:
        state = torch.load(path, map_location=device, weights_only=False)
        model.load_state_dict(state["model"] if "model" in state else state)
    else:
        torch.manual_seed(0)                       # untrained: the random starting weights
        model = MONA(cfg).to(device).eval()
    return model


def training_curves():
    """Real logs from MONA's pretraining run: (train rows, eval rows)."""
    train = list(csv.DictReader(open(RUN / "train_log.csv"))) if (RUN / "train_log.csv").exists() else []
    evals = list(csv.DictReader(open(RUN / "eval_log.csv"))) if (RUN / "eval_log.csv").exists() else []
    return train, evals


def recorded_samples():
    """What MONA wrote at every evaluation during its real training run (runs/mona_m/samples.txt).

    Returns [(tokens_in_billions, {language: text})], oldest first. Works without any snapshot files.
    """
    path = RUN / "samples.txt"
    if not path.exists():
        return []
    out, cur = [], None
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith("===== step"):
            billions = float(line.split("(")[1].split("B")[0])
            cur = (billions, {})
            out.append(cur)
        elif cur is not None and line.startswith("[") and "] " in line:
            lang, text = line[1:].split("] ", 1)
            cur[1][lang] = text
    return out
