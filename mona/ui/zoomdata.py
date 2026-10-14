"""The real numbers behind "Inside MONA": one sentence, followed from the whole model down to a single neuron.

Everything returned here is computed from MONA's real weights (nothing is invented):
  * the next-word guess and the guess after every layer (the logit lens)
  * the 12 attention heads of one layer, and the head where the last word looks hardest at one earlier word
  * all 2,048 feed-forward neurons of one block, for the last word
  * one neuron taken apart: its inputs, weights, weighted sum, and the bend (SiLU) that turns it into its output
"""
import math
import time

import numpy as np
import torch
import torch.nn.functional as F

from ..model import apply_rope
from .brain import summarize
from .widgets import show_piece

SENTENCE = "The cat sat on the mat because it"
FFN_LAYER = 5            # 0-based, shown as "block 6"


@torch.no_grad()
def compute(gb, sentence=SENTENCE, ffn_layer=FFN_LAYER):
    m = gb.model
    t0 = time.perf_counter()
    trace = gb.trace(sentence, lens_top=5)
    brain = summarize(trace, time.perf_counter() - t0)
    tokens = [show_piece(t.text) for t in trace.tokens]
    T = len(tokens)
    att = trace.attention                                           # (layers, heads, T, T)

    # attention: in block `ffn_layer`, where does the LAST word look? pick the head with the strongest look at one
    # earlier word (looking at the very first word is only a parking spot, so it does not count)
    layer = ffn_layer
    last = att[layer, :, -1, :]                                     # (heads, T)
    masked = last[:, 1: T - 1]
    head, target = np.unravel_index(int(masked.argmax()), tuple(masked.shape))
    head, target = int(head), int(target) + 1
    heads_here = [(h, int(last[h, : T - 1].argmax()), float(last[h, : T - 1].max())) for h in range(last.shape[0])]

    # feed-forward: re-run the first blocks by hand and stop inside block `ffn_layer`
    ids = torch.tensor([gb.encode(sentence)[-m.cfg.context:]])
    cos, sin = m.rope_cos[:T], m.rope_sin[:T]
    mask = torch.ones(T, T, dtype=torch.bool).tril()
    with torch.no_grad():
        x = m.embed(ids)
        for li, block in enumerate(m.blocks):
            if li == ffn_layer:                                     # what RMSNorm does to a real vector
                xin = x[0, -1].clone()
                xnorm = block.attn_norm(x)[0, -1].clone()
            a = block.attn
            q, k, v = a.qkv(block.attn_norm(x)).view(1, T, 3, a.n_heads, a.head_dim).permute(2, 0, 3, 1, 4)
            q, k = apply_rope(q, cos, sin), apply_rope(k, cos, sin)
            w = F.softmax(((q @ k.transpose(-2, -1)) / a.head_dim ** 0.5).masked_fill(~mask, float("-inf")), dim=-1)
            x = x + a.out((w @ v).transpose(1, 2).reshape(1, T, -1))
            if li == ffn_layer:
                hn = block.ffn_norm(x)[0, -1]                       # what the neurons see for the last word (768 numbers)
                gate_pre = block.ffn.gate(hn)                       # 2048 weighted sums
                up_pre = block.ffn.up(hn)
                acts = F.silu(gate_pre) * up_pre                    # the 2048 neuron outputs
                gate_w, up_w = block.ffn.gate.weight, block.ffn.up.weight
                break
            x = x + block.ffn(block.ffn_norm(x))
    acts_np = acts.numpy()
    n = int(np.abs(acts_np).argmax())
    terms = (hn * gate_w[n]).numpy()                                # input_i x weight_i for the gate sum of neuron n
    order = np.argsort(-np.abs(terms))
    top = [(int(i), float(hn[i]), float(gate_w[n, i]), float(terms[i])) for i in order[:5]]
    pre = float(terms.sum())
    neuron = dict(index=n, n_inputs=int(hn.numel()), top=top, rest=float(terms[order[5:]].sum()), pre=pre,
                  silu=float(F.silu(torch.tensor(pre))), up=float(up_pre[n]), out=float(acts_np[n]))
    assert abs(neuron["out"] - neuron["silu"] * neuron["up"]) < 1e-3 * (1 + abs(neuron["out"]))

    rms = float(xin.pow(2).mean().sqrt())
    angles = lambda i: [round(math.degrees(math.atan2(float(m.rope_sin[p, i]), float(m.rope_cos[p, i]))), 1) for p in range(8)]
    rope = dict(theta=m.cfg.rope_theta, fast=angles(0), slow=angles(m.cfg.d_model // m.cfg.n_heads // 2 - 1))

    # writing, one word at a time: MONA's real next-word loop (the same code the Next-word lab uses)
    prompt = "The cat sat on the"
    steps = [dict(text=st.token.text, prob=st.prob, alts=[(g.token.text, g.prob) for g in st.alternatives])
             for st in gb.generate(prompt, n=4, temperature=0.8, top_p=0.9, seed=25, show=5)]

    block0 = m.blocks[0]
    count = lambda mod: sum(p.numel() for p in mod.parameters())
    params = dict(total=m.num_params(), embed=m.embed.weight.numel(), blocks=sum(count(b) for b in m.blocks),
                  block=count(block0), attn=count(block0.attn), ffn=count(block0.ffn),
                  norms=count(block0.attn_norm) + count(block0.ffn_norm), n_layers=len(m.blocks),
                  n_heads=m.cfg.n_heads, hidden=m.cfg.ffn_hidden, width=m.cfg.d_model,
                  context=m.cfg.context, vocab=m.cfg.vocab_size)
    return dict(sentence=sentence, tokens=tokens, brain=brain, final=trace.final,
                head=dict(layer=layer, head=head, target=target, matrix=att[layer, head].numpy(), p=float(att[layer, head, -1, target])),
                weights=m.blocks[ffn_layer].ffn.up.weight[:256, :32].detach().numpy().astype(float),
                heads_here=heads_here, ffn_layer=ffn_layer, acts=acts_np, neuron=neuron, params=params,
                rms_in=[float(v) for v in xin[:6]], rms_out=[float(v) for v in xnorm[:6]], rms=rms, rope=rope,
                prompt=prompt, steps=steps)
