"""LESSON 5 — Scaling laws: how labs decide model size and training length before spending compute.

Run from C:\\LLM:  python learn/05_scaling_laws.py

Two facts do most of the work:
  1. Training compute C ≈ 6 × N × D   (N = parameters, D = training tokens)
     forward pass ≈ 2 operations per parameter per token, backward pass ≈ 4.
  2. "Chinchilla" (DeepMind, 2022): for a fixed compute budget, the best loss comes from
     roughly D ≈ 20 × N  (20 tokens per parameter).  Then  C = 6 × N × 20N = 120 N²,
     so  N_opt ≈ sqrt(C / 120)  and  D_opt ≈ 20 × N_opt.
Modern small models (SmolLM, Llama-3) train far *beyond* 20 tokens/parameter on purpose:
a smaller model trained longer is cheaper to run afterwards.
"""
import math

# Numbers measured on this laptop (RTX 5080 Laptop GPU, bf16, 1,024-token context)
MEASURED = {  # name: (total params, tokens per second)
    "XS": (42.5e6, 100_200),
    "S":  (71.8e6, 64_400),
    "M":  (110.1e6, 43_000),
}
SUSTAINED = 0.85          # laptops slow down when hot for hours

print("If you train for H hours, how many tokens does each size see?\n")
print(f"{'size':4s} {'params':>8s} | " + " | ".join(f"{h:>2d} h: tokens (tok/param)" for h in (9, 19, 36)))
for name, (n, tps) in MEASURED.items():
    cells = []
    for hours in (9, 19, 36):
        d = tps * SUSTAINED * hours * 3600
        cells.append(f"{d / 1e9:5.2f}B ({d / n:5.1f})       ")
    print(f"{name:4s} {n / 1e6:6.0f}M | " + " | ".join(cells))

print("\nCompute-optimal size for a budget (Chinchilla rule):")
for hours in (9, 19, 36):
    # effective FLOP/s ~ 6 * N * tokens/s, roughly constant across our sizes (~30 TFLOPS)
    flops = 6 * 85e6 * 43_000 * SUSTAINED * hours * 3600
    n_opt = math.sqrt(flops / 120)
    print(f"  {hours:2d} h ≈ {flops:.1e} FLOPs  ->  N_opt ≈ {n_opt / 1e6:4.0f}M non-embedding params, "
          f"D_opt ≈ {20 * n_opt / 1e9:.2f}B tokens")

print("""
MONA-M: 85M non-embedding parameters, ~19 h  ->  ~2.5B tokens, ~23 tokens/parameter.
That sits right at the compute-optimal point, which is why we picked it.
For comparison: GPT-3 (175B) used 1.7 tokens/param (under-trained by today's standards),
Chinchilla (70B) used 20, Llama-3 8B used ~1,900.""")
