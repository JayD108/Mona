"""MONA: a Llama-style decoder-only transformer.

Compared with MANAS v1 (a 2017-style GPT), each block uses the upgrades modern LLMs use:

  RMSNorm   instead of LayerNorm   simpler and cheaper: only rescales, no mean-centering
  RoPE      instead of learned     encodes position by *rotating* query/key vectors, so
            position embeddings    attention depends on relative distance between tokens
  SwiGLU    instead of ReLU MLP    a gated feed-forward layer; better quality per parameter
  SDPA      instead of hand-made   PyTorch's fused (flash) attention kernel: faster, less memory
            attention
  tied      embedding and output layer share one matrix (saves 25M parameters here)
  KV-cache  during generation, past keys/values are kept so each new token costs O(1) passes
"""
import math

import torch
import torch.nn as nn
import torch.nn.functional as F

from .config import ModelConfig


class RMSNorm(nn.Module):
    def __init__(self, dim, eps=1e-6):
        super().__init__()
        self.weight = nn.Parameter(torch.ones(dim))
        self.eps = eps

    def forward(self, x):
        # divide by the root-mean-square, then scale; computed in fp32 for stability
        x32 = x.float()
        return (x32 * torch.rsqrt(x32.pow(2).mean(-1, keepdim=True) + self.eps)).type_as(x) * self.weight


def rope_tables(context, head_dim, theta, device=None):
    """cos/sin tables: position p rotates dimension pair i by angle p / theta^(2i/head_dim)."""
    inv_freq = 1.0 / (theta ** (torch.arange(0, head_dim, 2, device=device).float() / head_dim))
    angles = torch.outer(torch.arange(context, device=device).float(), inv_freq)   # (T, head_dim/2)
    return angles.cos(), angles.sin()


def apply_rope(x, cos, sin):
    """x: (B, heads, T, head_dim). Rotate each (even, odd) pair of dimensions."""
    x1, x2 = x[..., 0::2], x[..., 1::2]
    return torch.stack((x1 * cos - x2 * sin, x1 * sin + x2 * cos), dim=-1).flatten(-2)


class Attention(nn.Module):
    def __init__(self, cfg: ModelConfig):
        super().__init__()
        self.n_heads = cfg.n_heads
        self.head_dim = cfg.d_model // cfg.n_heads
        self.qkv = nn.Linear(cfg.d_model, 3 * cfg.d_model, bias=False)
        self.out = nn.Linear(cfg.d_model, cfg.d_model, bias=False)
        self.dropout = cfg.dropout

    def forward(self, x, cos, sin, kv_cache=None):
        B, T, D = x.shape
        q, k, v = self.qkv(x).view(B, T, 3, self.n_heads, self.head_dim).permute(2, 0, 3, 1, 4)
        q, k = apply_rope(q, cos, sin), apply_rope(k, cos, sin)
        if kv_cache is not None:                       # generation: append to the cache
            if kv_cache[0] is not None:
                k = torch.cat([kv_cache[0], k], dim=2)
                v = torch.cat([kv_cache[1], v], dim=2)
            kv_cache[0], kv_cache[1] = k, v
        # causal mask only needed when the queries cover the same span as the keys
        y = F.scaled_dot_product_attention(q, k, v, is_causal=(T > 1 and T == k.shape[2]),
                                           dropout_p=self.dropout if self.training else 0.0)
        return self.out(y.transpose(1, 2).reshape(B, T, D))


class SwiGLU(nn.Module):
    def __init__(self, cfg: ModelConfig):
        super().__init__()
        self.gate = nn.Linear(cfg.d_model, cfg.ffn_hidden, bias=False)
        self.up   = nn.Linear(cfg.d_model, cfg.ffn_hidden, bias=False)
        self.down = nn.Linear(cfg.ffn_hidden, cfg.d_model, bias=False)

    def forward(self, x):
        return self.down(F.silu(self.gate(x)) * self.up(x))   # gate decides how much of "up" passes


class Block(nn.Module):
    def __init__(self, cfg: ModelConfig):
        super().__init__()
        self.attn_norm = RMSNorm(cfg.d_model)
        self.attn = Attention(cfg)
        self.ffn_norm = RMSNorm(cfg.d_model)
        self.ffn = SwiGLU(cfg)

    def forward(self, x, cos, sin, kv_cache=None):
        x = x + self.attn(self.attn_norm(x), cos, sin, kv_cache)   # pre-norm + residual
        return x + self.ffn(self.ffn_norm(x))


class MONA(nn.Module):
    def __init__(self, cfg: ModelConfig):
        super().__init__()
        self.cfg = cfg
        self.embed = nn.Embedding(cfg.vocab_size, cfg.d_model)
        self.blocks = nn.ModuleList(Block(cfg) for _ in range(cfg.n_layers))
        self.norm = RMSNorm(cfg.d_model)
        self.lm_head = nn.Linear(cfg.d_model, cfg.vocab_size, bias=False)
        self.lm_head.weight = self.embed.weight                    # weight tying
        cos, sin = rope_tables(cfg.context, cfg.d_model // cfg.n_heads, cfg.rope_theta)
        self.register_buffer("rope_cos", cos, persistent=False)
        self.register_buffer("rope_sin", sin, persistent=False)
        self.apply(self._init)
        for block in self.blocks:   # GPT-2 trick: shrink layers that write into the residual stream
            for w in (block.attn.out.weight, block.ffn.down.weight):
                nn.init.normal_(w, std=0.02 / math.sqrt(2 * cfg.n_layers))

    @staticmethod
    def _init(m):
        if isinstance(m, (nn.Linear, nn.Embedding)):
            nn.init.normal_(m.weight, std=0.02)

    def num_params(self, non_embedding=False):
        n = sum(p.numel() for p in self.parameters())
        return n - self.embed.weight.numel() if non_embedding else n

    def forward(self, idx, targets=None, loss_mask=None, start_pos=0, kv_caches=None):
        """idx: (B, T) token ids. targets: (B, T) next-token ids, or None.
        loss_mask: (B, T) 1 where the loss counts (used in SFT to train only on answers)."""
        B, T = idx.shape
        cos = self.rope_cos[start_pos:start_pos + T]
        sin = self.rope_sin[start_pos:start_pos + T]
        x = self.embed(idx)
        for i, block in enumerate(self.blocks):
            x = block(x, cos, sin, None if kv_caches is None else kv_caches[i])
        x = self.norm(x)
        if targets is None:
            return self.lm_head(x[:, -1:, :]).float(), None        # only the last position is needed
        logits = self.lm_head(x).float()
        loss = F.cross_entropy(logits.view(-1, logits.size(-1)), targets.reshape(-1), reduction="none")
        if loss_mask is None:
            return logits, loss.mean()
        mask = loss_mask.reshape(-1).float()
        return logits, (loss * mask).sum() / mask.sum().clamp(min=1)

    @torch.no_grad()
    def generate(self, idx, max_new_tokens, temperature=0.8, top_p=0.9, top_k=None, stop_ids=()):
        """Sample tokens after idx (shape (1, T)), using a KV-cache. Yields token ids one by one."""
        self.eval()
        idx = idx[:, -self.cfg.context:]
        caches = [[None, None] for _ in self.blocks]
        logits, _ = self(idx, kv_caches=caches)                   # prefill: whole prompt at once
        pos = idx.shape[1]
        for _ in range(max_new_tokens):
            logits = logits[:, -1, :] / max(temperature, 1e-5)
            if top_k:
                kth = torch.topk(logits, top_k).values[:, [-1]]
                logits = logits.masked_fill(logits < kth, float("-inf"))
            probs = F.softmax(logits, dim=-1)
            if top_p and top_p < 1.0:
                sp, si = torch.sort(probs, descending=True)
                sp = sp.masked_fill(sp.cumsum(-1) - sp >= top_p, 0.0)
                probs = torch.zeros_like(probs).scatter(-1, si, sp)
                probs = probs / probs.sum(-1, keepdim=True)
            nxt = torch.multinomial(probs, 1)
            tok = nxt.item()
            if tok in stop_ids:
                return
            yield tok
            if pos >= self.cfg.context:                           # context full: stop
                return
            logits, _ = self(nxt, kv_caches=caches, start_pos=pos)  # only the new token
            pos += 1
