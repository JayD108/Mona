"""LESSON 3 — Attention, step by step, with numbers small enough to read.

Run from C:\\LLM:  python learn/03_attention.py

The question attention answers: "when predicting the next word, which earlier words matter?"
Every token makes three vectors from its embedding:
    query  q = "what am I looking for?"
    key    k = "what do I contain?"
    value  v = "what do I pass on if you pick me?"
Score(i, j) = q_i · k_j  (dot product = how well token j answers token i's question)
Then: scale, hide the future (causal mask), softmax into percentages, and mix the values.
"""
import torch
import torch.nn.functional as F

torch.manual_seed(0)
torch.set_printoptions(precision=2, sci_mode=False)

words = ["राम", "ने", "धनुष", "तोड़ा"]           # "Ram broke the bow"
T, d = len(words), 4                            # 4 tokens, 4-dimensional vectors (MONA uses 64 per head)

x = torch.randn(T, d)                           # pretend embeddings
W_q, W_k, W_v = torch.randn(d, d), torch.randn(d, d), torch.randn(d, d)   # learned in training

q, k, v = x @ W_q, x @ W_k, x @ W_v
print("1) every token gets a query, key and value vector\n   q =\n", q)

scores = q @ k.T / d ** 0.5                     # scale by sqrt(d) so softmax doesn't saturate
print("\n2) scores[i, j] = how much word i wants word j\n", scores)

mask = torch.tril(torch.ones(T, T)).bool()      # word i may only look at words 0..i
scores = scores.masked_fill(~mask, float("-inf"))
print("\n3) causal mask: the future is hidden (-inf), so the model can't cheat\n", scores)

weights = F.softmax(scores, dim=-1)
print("\n4) softmax: each row becomes percentages that sum to 100%")
for i, w in enumerate(weights):
    print(f"   {words[i]:>6s} looks at: " + "  ".join(f"{words[j]} {w[j]:4.0%}" for j in range(i + 1)))

out = weights @ v
print("\n5) output = weighted mix of the values: each word now carries context from earlier words\n", out)

fast = F.scaled_dot_product_attention(q[None, None], k[None, None], v[None, None], is_causal=True)[0, 0]
print("\n6) PyTorch's fused kernel (what MONA uses) gives the same answer:",
      torch.allclose(out, fast, atol=1e-5))
print("""
In MONA: 12 heads do this in parallel per layer (each with its own W_q, W_k, W_v, head size 64),
over 1,024 tokens, in 12 layers. Training adjusts the W matrices so the percentages point at
the words that actually help predict what comes next.""")
