"""LESSON 4 — RoPE: how MONA knows word order.

Run from C:\\LLM:  python learn/04_rope.py

Attention by itself is order-blind: "राम ने रावण को मारा" and "रावण ने राम को मारा" contain the
same words. Models must be told positions.
  MANAS v1 (2017 style): add a learned "position vector" to each token embedding.
  MONA (RoPE, used by Llama, Qwen, Mistral): ROTATE the query and key vectors by an angle
  proportional to the position. A dot product between two rotated vectors depends only on the
  DIFFERENCE of their angles, so attention scores depend on *relative* distance between tokens.
"""
import torch

from mona.model import apply_rope, rope_tables

torch.manual_seed(0)
head_dim = 8
cos, sin = rope_tables(context=64, head_dim=head_dim, theta=10000.0)

q = torch.randn(head_dim)       # the same query word...
k = torch.randn(head_dim)       # ...and the same key word, placed at different positions


def rotated(vec, pos):
    return apply_rope(vec[None, None, None, :], cos[pos:pos + 1], sin[pos:pos + 1])[0, 0, 0]


print("Same two words, different absolute positions, same distance (3) -> same score:")
for qpos in (5, 20, 40):
    kpos = qpos - 3
    print(f"  query at {qpos:2d}, key at {kpos:2d}:  score = {rotated(q, qpos) @ rotated(k, kpos):+.4f}")

print("\nSame query position, key further and further away -> the score changes with distance:")
for dist in (0, 1, 2, 5, 10, 30):
    print(f"  distance {dist:2d}:  score = {rotated(q, 40) @ rotated(k, 40 - dist):+.4f}")

print("""
Why this matters:
  * the model learns patterns like "the verb is usually ~3 tokens after the subject",
    no matter where in the text the sentence appears
  * no position parameters to learn (MANAS v1 had 98K of them)
  * pairs of dimensions rotate at different speeds (fast for nearby detail, slow for long range),
    like the hands of a clock""")
