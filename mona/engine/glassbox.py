"""GlassBox: open MONA up and look inside. Every number the app shows comes from here.

    gb = GlassBox()                       # finds the best available weights, runs on CPU by default
    gb.tokens("भारत एक देश है")           # the pieces MONA reads, with ids
    gb.next_word("The capital of India is")   # MONA's top guesses for the next piece, with probabilities
    gb.trace("राम ने धनुष तोड़ा")           # attention of every head in every layer + the guess after each layer
    for step in gb.generate("Once upon a time", 20): ...   # one piece at a time, with the alternatives

The trace re-runs the model by hand (same weights, same maths) so it can record what the fast
fused-attention path hides. `selfcheck()` proves both paths give the same answer.
"""
from dataclasses import dataclass, field

import torch
import torch.nn.functional as F

from .. import config
from .. import tokenizer as T
from ..model import MONA, apply_rope


@dataclass
class Token:
    id: int
    text: str            # what it looks like ("" pieces of one letter are shown as "·")
    special: bool = False


@dataclass
class Guess:
    token: Token
    prob: float


@dataclass
class Trace:
    tokens: list                     # [Token]
    attention: torch.Tensor          # (layers, heads, T, T): attention[l, h, i, j] = how much i looks at j
    layer_guesses: list              # [layer] -> [position] -> [Guess] top-3: the logit lens
    final: list                      # [Guess] for the next piece after the last token


@dataclass
class Step:
    token: Token
    prob: float
    alternatives: list = field(default_factory=list)     # [Guess] the other candidates at this step


def find_weights():
    """Released weights first, then the newest training snapshot/checkpoint (useful while training)."""
    candidates = [config.MODEL_DIR / "mona.pt", config.RUNS_DIR / "mona_m" / "final.pt"]
    snaps = sorted((config.RUNS_DIR / "mona_m").glob("snap_*B.pt"),
                   key=lambda p: float(p.stem[5:-1]), reverse=True)
    candidates += snaps + [config.RUNS_DIR / "mona_m" / "ckpt.pt"]
    for c in candidates:
        if c.exists():
            return c
    raise FileNotFoundError("No MONA weights found (models/mona/mona.pt or runs/mona_m/*)")


class GlassBox:
    def __init__(self, weights=None, size="M", device="cpu"):
        self.device = device
        self.cfg = config.MONA_M if size == "M" else config.MONA_TINY
        self.weights = weights or find_weights()
        state = torch.load(self.weights, map_location=device, weights_only=False)
        self.model = MONA(self.cfg).to(device).eval()
        self.model.load_state_dict(state["model"] if "model" in state else state)
        self.tok = T.load()
        self.special_ids = {self.tok.token_to_id(s) for s in T.SPECIAL_TOKENS}

    # ── pieces ────────────────────────────────────────────────────────────────
    def piece(self, token_id):
        if token_id in self.special_ids:
            return Token(token_id, self.tok.id_to_token(token_id), special=True)
        text = self.tok.decode([token_id])
        return Token(token_id, "·" if "�" in text else text)   # part of a multi-byte letter

    def encode(self, text):
        return self.tok.encode(text).ids

    def tokens(self, text):
        return [self.piece(i) for i in self.encode(text)]

    # ── next word ─────────────────────────────────────────────────────────────
    @torch.no_grad()
    def probs(self, ids, temperature=1.0):
        ids = torch.tensor([ids[-self.cfg.context:]], device=self.device)
        logits, _ = self.model(ids)
        return F.softmax(logits[0, -1] / max(temperature, 1e-5), dim=-1)

    def next_word(self, text_or_ids, top=10, temperature=1.0):
        ids = self.encode(text_or_ids) if isinstance(text_or_ids, str) else list(text_or_ids)
        p = self.probs(ids, temperature)
        vals, idx = torch.topk(p, top)
        return [Guess(self.piece(i), v) for v, i in zip(vals.tolist(), idx.tolist())]

    # ── generation, one piece at a time ──────────────────────────────────────
    @torch.no_grad()
    def generate(self, text, n=40, temperature=0.8, top_p=0.9, top_k=None, seed=None, show=5):
        if seed is not None:
            torch.manual_seed(seed)
        ids = self.encode(text)
        for _ in range(n):
            p = self.probs(ids, temperature)
            filtered = p.clone()
            if top_k:
                kth = torch.topk(filtered, top_k).values[-1]
                filtered[filtered < kth] = 0
            if top_p and top_p < 1.0:
                sp, si = torch.sort(filtered, descending=True)
                sp[(sp.cumsum(0) - sp) >= top_p] = 0
                filtered = torch.zeros_like(filtered).scatter(0, si, sp)
            choice = torch.multinomial(filtered / filtered.sum(), 1).item()
            vals, idx = torch.topk(p, show)
            alts = [Guess(self.piece(i), v) for v, i in zip(vals.tolist(), idx.tolist())]
            yield Step(self.piece(choice), p[choice].item(), alts)
            if choice == self.tok.token_to_id(T.EOT):
                return
            ids.append(choice)

    # ── full trace: attention + logit lens ───────────────────────────────────
    @torch.no_grad()
    def trace(self, text, lens_top=3):
        ids = self.encode(text)[-self.cfg.context:]
        idx = torch.tensor([ids], device=self.device)
        m, Tn = self.model, len(ids)
        cos, sin = m.rope_cos[:Tn], m.rope_sin[:Tn]
        mask = torch.ones(Tn, Tn, dtype=torch.bool, device=self.device).tril()
        x = m.embed(idx)
        attn_all, lens = [], []
        for block in m.blocks:
            a = block.attn
            h = block.attn_norm(x)
            q, k, v = a.qkv(h).view(1, Tn, 3, a.n_heads, a.head_dim).permute(2, 0, 3, 1, 4)
            q, k = apply_rope(q, cos, sin), apply_rope(k, cos, sin)
            scores = (q @ k.transpose(-2, -1)) / a.head_dim ** 0.5
            weights = F.softmax(scores.masked_fill(~mask, float("-inf")), dim=-1)     # (1, H, T, T)
            attn_all.append(weights[0])
            y = (weights @ v).transpose(1, 2).reshape(1, Tn, -1)
            x = x + a.out(y)
            x = x + block.ffn(block.ffn_norm(x))
            p = F.softmax(m.lm_head(m.norm(x))[0].float(), dim=-1)                  # logit lens
            vals, top = torch.topk(p, lens_top, dim=-1)
            lens.append([[Guess(self.piece(t), v) for v, t in zip(vs.tolist(), ts.tolist())]
                         for vs, ts in zip(vals, top)])
        self._last_logits = m.lm_head(m.norm(x))[0, -1].float()
        return Trace(tokens=[self.piece(i) for i in ids], attention=torch.stack(attn_all),
                     layer_guesses=lens, final=lens[-1][-1])

    def selfcheck(self, text="MONA checks that the glass box matches the real model."):
        """The hand-written trace must give the same prediction as the model's fast path."""
        self.trace(text)
        fast, _ = self.model(torch.tensor([self.encode(text)], device=self.device))
        diff = (self._last_logits - fast[0, -1]).abs().max().item()
        return diff < 1e-3, diff
