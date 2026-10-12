"""Step ⑤ — pretrain MONA.

Run from C:\\LLM:
    python -m scripts.mona_pretrain --name mona_m                      # start (or continue with --resume)
    python -m scripts.mona_pretrain --name mona_m --resume --stop-at 08:30
    python -m scripts.mona_pretrain --name pilot --size tiny --total-tokens 30e6 --accum 4 --eval-every 25

Stopping safely: Ctrl+C, or create the file runs/<name>/STOP. Both save a checkpoint first.
Everything is written to runs/<name>/:
    ckpt.pt            latest full checkpoint (model + optimizer + progress), every --ckpt-minutes
    snap_<N>B.pt       model-only snapshot every 0.5B tokens
    train_log.csv      every 10 steps: tokens, lr, loss, tokens/s, GPU temperature
    eval_log.csv       every --eval-every steps: validation loss per language
    samples.txt        text generated in each language at every evaluation

📘 Learning-rate schedule: WSD (warmup - stable - decay).
    warmup  first 1% of tokens: 0 -> peak (random weights give chaotic gradients; start gently)
    stable  hold the peak. Because nothing here depends on the end, a run can be paused,
            resumed or even extended (raise --total-tokens) without restarting.
    decay   final 15%: peak -> 5% of peak. Most of the loss improvement at the end comes here.
            During decay the Awadhi share is raised ("annealing" on the rarest, most precious data).
"""
import argparse
import csv
import datetime as dt
import math
import os
import time

import torch

from mona import config
from mona import tokenizer as T
from mona.data import PretrainBatches
from mona.model import MONA

p = argparse.ArgumentParser()
p.add_argument("--name", required=True)
p.add_argument("--size", choices=["M", "tiny"], default="M")
p.add_argument("--total-tokens", type=float, default=2.5e9)
p.add_argument("--micro-batch", type=int, default=8)
p.add_argument("--accum", type=int, default=64, help="micro-batches per optimizer step")
p.add_argument("--lr", type=float, default=6e-4)
p.add_argument("--min-lr-ratio", type=float, default=0.05)
p.add_argument("--warmup-frac", type=float, default=0.01)
p.add_argument("--decay-frac", type=float, default=0.15)
p.add_argument("--weight-decay", type=float, default=0.1)
p.add_argument("--eval-every", type=int, default=250)
p.add_argument("--eval-batches", type=int, default=20)
p.add_argument("--ckpt-minutes", type=float, default=30)
p.add_argument("--snapshot-every", type=float, default=0.5e9)
p.add_argument("--stop-at", default=None, help="HH:MM local time: save and exit when reached")
p.add_argument("--resume", action="store_true")
p.add_argument("--temp-target", type=int, default=77, help="°C: pause between micro-batches to stay near this")
p.add_argument("--min-duty", type=float, default=0.85, help="never pause more than this lets (0.85 = <=18%% slower)")
args = p.parse_args()

# Awadhi = public-domain Tulsidas VERSE only (~246K tokens; the copyrighted Gita Press commentary was removed
# at 0.8B tokens). 0.026% (stable) + 0.104% (decay) of the remaining 1.7B tokens ≈ 3 passes: few enough
# repeats that MONA learns the style instead of memorising.
MIX_STABLE = {"english": 0.55, "hindi": 0.40, "hinglish": 0.04974, "awadhi": 0.00026}
MIX_DECAY  = {"english": 0.55, "hindi": 0.40, "hinglish": 0.04896, "awadhi": 0.00104}

torch.backends.cuda.matmul.allow_tf32 = True
torch.backends.cudnn.allow_tf32 = True
device = config.DEVICE
run_dir = config.RUNS_DIR / args.name
run_dir.mkdir(parents=True, exist_ok=True)
ckpt_path = run_dir / "ckpt.pt"
stop_file = run_dir / "STOP"
stop_file.unlink(missing_ok=True)

cfg = config.MONA_M if args.size == "M" else config.MONA_TINY
model = MONA(cfg).to(device)
tokens_per_step = args.micro_batch * args.accum * cfg.context
total_steps = math.ceil(args.total_tokens / tokens_per_step)

decay, no_decay = [], []
for n, prm in model.named_parameters():
    (decay if prm.dim() >= 2 else no_decay).append(prm)      # matrices decay; norm scales don't
optimizer = torch.optim.AdamW([{"params": decay, "weight_decay": args.weight_decay},
                               {"params": no_decay, "weight_decay": 0.0}],
                              lr=args.lr, betas=(0.9, 0.95), eps=1e-8, fused=device == "cuda")

step, tokens_seen, snapshots_done = 0, 0, 0
if args.resume and ckpt_path.exists():
    ck = torch.load(ckpt_path, map_location=device, weights_only=False)
    model.load_state_dict(ck["model"])
    optimizer.load_state_dict(ck["optimizer"])
    step, tokens_seen, snapshots_done = ck["step"], ck["tokens_seen"], ck.get("snapshots_done", 0)
    torch.set_rng_state(ck["torch_rng"].cpu())     # RNG state must stay on the CPU
    print(f"Resumed from step {step:,} ({tokens_seen / 1e9:.3f}B tokens)")
elif args.resume:
    print("No checkpoint found: starting fresh")

data = PretrainBatches(MIX_STABLE, cfg.context, args.micro_batch, device, seed=step + 1)
tok = T.load()
eot = tok.token_to_id(T.EOT)

print(f"Model: {model.num_params() / 1e6:.1f}M params ({model.num_params(True) / 1e6:.1f}M non-embedding)")
print(f"Plan: {args.total_tokens / 1e9:.2f}B tokens = {total_steps:,} steps x {tokens_per_step:,} tokens")
print("Data mix (stable phase):\n" + data.describe(args.total_tokens))


def lr_at(tokens):
    frac = tokens / args.total_tokens
    if frac < args.warmup_frac:
        return args.lr * max(frac / args.warmup_frac, 0.01)
    decay_start = 1 - args.decay_frac
    if frac < decay_start:
        return args.lr
    progress = min((frac - decay_start) / args.decay_frac, 1.0)
    return args.lr * (args.min_lr_ratio + (1 - args.min_lr_ratio) * (1 - progress))


def save_checkpoint():
    tmp = ckpt_path.with_suffix(".tmp")
    torch.save({"model": model.state_dict(), "optimizer": optimizer.state_dict(), "step": step,
                "tokens_seen": tokens_seen, "snapshots_done": snapshots_done,
                "torch_rng": torch.get_rng_state(), "config": cfg.__dict__, "args": vars(args)}, tmp)
    os.replace(tmp, ckpt_path)          # atomic: a crash mid-save never corrupts ckpt.pt


SAMPLE_PROMPTS = {
    "english": "The history of mathematics",
    "hindi": "भारत की नदियाँ",
    "hinglish": "aaj mausam bahut",
    "awadhi": "राम कथा सुंदर",
}


@torch.no_grad()
def evaluate():
    model.eval()
    losses = {}
    for lang in data.langs:
        total = 0.0
        for _ in range(args.eval_batches):
            x, y = data.val_batch(lang)
            with torch.autocast("cuda", dtype=torch.bfloat16, enabled=device == "cuda"):
                total += model(x, y)[1].item()
        losses[lang] = total / args.eval_batches
    with open(run_dir / "samples.txt", "a", encoding="utf-8") as f:
        f.write(f"\n===== step {step}  ({tokens_seen / 1e9:.3f}B tokens) =====\n")
        for lang, prompt in SAMPLE_PROMPTS.items():
            ids = torch.tensor([tok.encode(prompt).ids], device=device)
            out = list(model.generate(ids, 60, temperature=0.8, top_p=0.9, stop_ids={eot}))
            f.write(f"[{lang}] {prompt}{tok.decode(out)}\n")
    model.train()
    return losses


def gpu_temp():
    try:
        return torch.cuda.temperature()
    except Exception:
        return -1


def log_row(name, row, header):
    path = run_dir / name
    new = not path.exists()
    with open(path, "a", newline="") as f:
        w = csv.writer(f)
        if new:
            w.writerow(header)
        w.writerow(row)


stop_time = None
if args.stop_at:
    hh, mm = map(int, args.stop_at.split(":"))
    now = dt.datetime.now()
    stop_time = now.replace(hour=hh, minute=mm, second=0, microsecond=0)
    if stop_time <= now:
        stop_time += dt.timedelta(days=1)
    print(f"Will save and stop at {stop_time:%Y-%m-%d %H:%M}")

model.train()
last_ckpt, t_last, tok_last = time.time(), time.time(), tokens_seen
in_decay = False
duty = 1.0          # share of time the GPU computes; lowered by the thermal limiter when it runs hot
try:
    while step < total_steps:
        lr = lr_at(tokens_seen)
        for g in optimizer.param_groups:
            g["lr"] = lr
        if not in_decay and tokens_seen >= (1 - args.decay_frac) * args.total_tokens:
            in_decay = True
            data.set_weights(MIX_DECAY)
            print(f"step {step}: entering decay + annealing phase")

        loss_sum = 0.0
        for _ in range(args.accum):
            t0 = time.time()
            x, y = data.train_batch()
            with torch.autocast("cuda", dtype=torch.bfloat16, enabled=device == "cuda"):
                _, loss = model(x, y)
            (loss / args.accum).backward()
            loss_sum += loss.item()                     # .item() waits for the GPU, so t0..now = real work
            if duty < 1.0:
                time.sleep((time.time() - t0) * (1 - duty) / duty)
        temp = gpu_temp()                               # thermal limiter: small steps, bounded slowdown
        if temp > args.temp_target:
            duty = max(args.min_duty, duty - 0.02)
        elif 0 <= temp < args.temp_target - 3:
            duty = min(1.0, duty + 0.02)
        grad_norm = torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0).item()
        optimizer.step()
        optimizer.zero_grad(set_to_none=True)
        step += 1
        tokens_seen += tokens_per_step

        if step % 10 == 0 or step == 1:
            now = time.time()
            tps = (tokens_seen - tok_last) / (now - t_last)
            t_last, tok_last = now, tokens_seen
            eta_h = (args.total_tokens - tokens_seen) / max(tps, 1) / 3600
            log_row("train_log.csv", [step, tokens_seen, f"{lr:.3e}", f"{loss_sum / args.accum:.4f}",
                                      f"{grad_norm:.3f}", int(tps), gpu_temp()],
                    ["step", "tokens", "lr", "loss", "grad_norm", "tokens_per_s", "gpu_temp_c"])
            print(f"step {step:6,}/{total_steps:,} | {tokens_seen / 1e9:6.3f}B tok | lr {lr:.2e} | "
                  f"loss {loss_sum / args.accum:.4f} | gnorm {grad_norm:5.2f} | {tps / 1e3:5.1f}K tok/s | "
                  f"{gpu_temp()}°C | duty {duty:.0%} | ETA {eta_h:5.1f} h", flush=True)

        if step % args.eval_every == 0 or step == total_steps:
            losses = evaluate()
            log_row("eval_log.csv", [step, tokens_seen] + [f"{losses[l]:.4f}" for l in data.langs],
                    ["step", "tokens"] + data.langs)
            print("  eval | " + " | ".join(f"{l} {v:.3f}" for l, v in losses.items()), flush=True)

        if tokens_seen >= (snapshots_done + 1) * args.snapshot_every:
            snapshots_done += 1
            torch.save(model.state_dict(), run_dir / f"snap_{snapshots_done * args.snapshot_every / 1e9:.1f}B.pt")

        if time.time() - last_ckpt > args.ckpt_minutes * 60:
            save_checkpoint()
            last_ckpt = time.time()

        if stop_file.exists() or (stop_time and dt.datetime.now() >= stop_time):
            print("Stop requested: saving checkpoint and exiting.")
            break
except KeyboardInterrupt:
    print("\nCtrl+C: saving checkpoint and exiting.")

save_checkpoint()
if step >= total_steps:
    torch.save(model.state_dict(), run_dir / "final.pt")
    print(f"Training complete: {run_dir / 'final.pt'}")
print(f"Saved {ckpt_path}  (step {step:,}, {tokens_seen / 1e9:.3f}B tokens)")
