"""Real data for "Your words, step by step": what MONA's tokenizer and model do with the text you typed.

Everything is computed from the real tokenizer and weights for the learner's own text:
  clean-up (NFC), the pieces the text is cut into, its UTF-8 bytes, the BPE merges, the token ids, the embedding
  vectors, the rotation angles that encode position, the guess after every layer, one attention head, the scores
  (logits) for all 32,768 next tokens, and a few real steps of writing.
"""
import math

import numpy as np
import torch
import torch.nn.functional as F
from tokenizers import Regex, pre_tokenizers

from .. import tokenizer as T
from ..engine import lessons
from .brain import summarize
from .widgets import show_piece

DEFAULT = "The cat sat on the mat because it"
MAX_CHARS = 72
SHOW = 12                      # how many tokens the pictures show


@torch.no_grad()
def compute(gb, text):
    text = " ".join((text or "").split())[:MAX_CHARS] or DEFAULT
    tok, m = gb.tok, gb.model
    trimmed = False
    all_ids = tok.encode(text).ids
    if len(all_ids) > SHOW:                                # keep the first 12 tokens so every picture fits
        text, trimmed = tok.decode(all_ids[:SHOW]).strip(), True
    norm = tok.normalizer.normalize_str(text)
    splitter = pre_tokenizers.Split(Regex(T.PATTERN), behavior="isolated")
    pieces = [p for p, _ in splitter.pre_tokenize_str(norm)]
    ids = gb.encode(text)[-m.cfg.context:]
    tokens = [show_piece(gb.piece(i).text) for i in ids]
    n = len(ids)

    # the clean-up demo uses the real normaliser on a letter that can be written two ways
    demo_before = "é"
    demo_after = tok.normalizer.normalize_str(demo_before)

    # bytes, and the merges for the piece that needs the most of them
    byte_rows = [(p, [f"{b:02X}" for b in p.encode("utf-8")]) for p in pieces[:6]]
    hindi = "न"
    hindi_bytes = [f"{b:02X}" for b in hindi.encode("utf-8")]
    best, best_steps = None, []
    for p in pieces:
        w = p.strip()
        if len(w) < 3 or len(w) > 12:
            continue
        steps = lessons.bpe_replay(tok, p)
        if len(steps) > len(best_steps):
            best, best_steps = p, steps
    merges = [(" ".join(s.pieces), s.merged) for s in best_steps]

    # embeddings: one row of 768 numbers per token, squeezed into 48 cells for the picture
    emb = m.embed.weight[torch.tensor(ids)].detach().numpy()
    cells = np.array([row.reshape(48, -1).mean(axis=1) for row in emb[:SHOW]])

    # position: the first (fastest) rotation dial, in degrees, for every position
    fast = [round(math.degrees(math.atan2(float(m.rope_sin[p, 0]), float(m.rope_cos[p, 0]))), 1) for p in range(min(n, SHOW))]

    # the pass through all 12 blocks (guess after every layer) and the attention of every head
    trace = gb.trace(text, lens_top=5)
    brain = summarize(trace, 0.0)
    logits = gb._last_logits.clone()                       # the scores for all 32,768 tokens after the last word
    att = trace.attention
    layer = 5 if n > 2 else 0
    last = att[layer, :, -1, :]
    if n > 2:
        masked = last[:, 1: n - 1]
        head, target = np.unravel_index(int(masked.argmax()), tuple(masked.shape))
        head, target = int(head), int(target) + 1
    else:
        head, target = 0, 0
    heads_here = [(h, int(last[h, : n - 1].argmax()) if n > 1 else 0, float(last[h, : n - 1].max()) if n > 1 else 1.0)
                  for h in range(last.shape[0])]

    # scores -> probabilities, and what temperature does to them
    top = torch.topk(logits, 5)
    top_ids = top.indices.tolist()
    temps = {t: F.softmax(logits / t, dim=-1)[top_ids].tolist() for t in (0.5, 1.0, 1.5)}
    scores = [(gb.piece(i).text, float(logits[i]), temps[1.0][k]) for k, i in enumerate(top_ids)]

    # a few real steps of writing after the text
    steps = [dict(text=s.token.text, prob=s.prob, id=s.token.id)
             for s in gb.generate(text, n=3, temperature=0.5, top_p=0.9, seed=3, show=5)]
    picked = steps[0]
    block0 = m.blocks[0]
    count = lambda mod: sum(p.numel() for p in mod.parameters())
    params = dict(total=m.num_params(), embed=m.embed.weight.numel(), blocks=sum(count(b) for b in m.blocks),
                  block=count(block0), attn=count(block0.attn), ffn=count(block0.ffn), n_layers=len(m.blocks),
                  n_heads=m.cfg.n_heads, hidden=m.cfg.ffn_hidden, width=m.cfg.d_model, context=m.cfg.context,
                  vocab=m.cfg.vocab_size)
    return dict(sentence=text, text=text, trimmed=trimmed, norm=norm, changed=norm != text, demo=(demo_before, demo_after),
                pieces=pieces, byte_rows=byte_rows, hindi=(hindi, hindi_bytes), merge_piece=best, merges=merges,
                ids=ids, tokens=tokens, n=n, n_words=len(text.split()), emb=emb, cells=cells, fast=fast,
                brain=brain, head=dict(layer=layer, head=head, target=target, matrix=att[layer, head].numpy(),
                                       p=float(att[layer, head, -1, target]) if n > 1 else 1.0),
                heads_here=heads_here, ffn_layer=layer, scores=scores, temps=temps, top_ids=top_ids,
                n_vocab=m.cfg.vocab_size, logit_max=float(top.values[0]), steps=steps, picked=picked, params=params,
                final=trace.final)
