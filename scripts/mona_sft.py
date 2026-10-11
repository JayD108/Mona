"""Step ⑦ — instruction tuning (SFT): turn the pretrained MONA into MONA-Chat.

Run from C:\\LLM:
    python -m scripts.mona_sft --base runs/mona_m/final.pt --name mona_m_chat

📘 What changes compared with pretraining
  * the data is conversations in the chat template:
        <|system|>…<|end|><|user|>…<|end|><|assistant|>…<|end|><|endoftext|>
  * LOSS MASKING: the loss is computed only on the assistant's tokens. The model reads the
    question but is only graded on the answer, so it learns to *respond*, not to imitate users.
  * a smaller learning rate (the model already knows the languages; we only teach a format)
  * a few passes (epochs) over a small dataset instead of one pass over a huge one

Several short conversations are packed into each 1,024-token row (separated by
<|endoftext|>) so no compute is wasted on padding.
"""
import argparse
import csv
import json
import math
import random
import time

import torch

from mona import config
from mona import tokenizer as T
from mona.model import MONA

p = argparse.ArgumentParser()
p.add_argument("--base", required=True, help="pretrained weights (.pt state dict or ckpt.pt)")
p.add_argument("--name", required=True)
p.add_argument("--size", choices=["M", "tiny"], default="M")
p.add_argument("--epochs", type=float, default=2.0)
p.add_argument("--lr", type=float, default=1e-4)
p.add_argument("--micro-batch", type=int, default=8)
p.add_argument("--accum", type=int, default=8)
p.add_argument("--eval-every", type=int, default=200)
args = p.parse_args()

torch.backends.cuda.matmul.allow_tf32 = True
device = config.DEVICE
cfg = config.MONA_M if args.size == "M" else config.MONA_TINY
run_dir = config.RUNS_DIR / args.name
run_dir.mkdir(parents=True, exist_ok=True)
tok = T.load()
EOT = tok.token_to_id(T.EOT)
PAD = tok.token_to_id(T.PAD)


def load_rows(path):
    """Tokenize every conversation and pack them into rows of exactly `context`+1 tokens."""
    convs = [json.loads(l) for l in open(path, encoding="utf-8")]
    random.Random(0).shuffle(convs)
    rows, cur_ids, cur_mask = [], [], []
    T_ = cfg.context + 1
    for c in convs:
        ids, mask = T.encode_chat(tok, c["messages"])
        if len(cur_ids) + len(ids) > T_:
            pad = T_ - len(cur_ids)
            rows.append((cur_ids + [PAD] * pad, cur_mask + [0] * pad))
            cur_ids, cur_mask = [], []
        cur_ids += ids
        cur_mask += mask
    if cur_ids:
        pad = T_ - len(cur_ids)
        rows.append((cur_ids + [PAD] * pad, cur_mask + [0] * pad))
    ids = torch.tensor([r[0] for r in rows], dtype=torch.long)
    mask = torch.tensor([r[1] for r in rows], dtype=torch.long)
    return ids, mask, len(convs)


train_ids, train_mask, n_train = load_rows(config.SFT_DIR / "train.jsonl")
val_ids, val_mask, n_val = load_rows(config.SFT_DIR / "val.jsonl")
print(f"train: {n_train:,} conversations packed into {len(train_ids):,} rows; "
      f"answer tokens {train_mask.sum().item() / 1e6:.1f}M of {train_ids.numel() / 1e6:.1f}M")

model = MONA(cfg).to(device)
state = torch.load(args.base, map_location=device, weights_only=False)
model.load_state_dict(state["model"] if "model" in state else state)
print(f"Loaded {args.base}")

rows_per_step = args.micro_batch * args.accum
total_steps = math.ceil(args.epochs * len(train_ids) / rows_per_step)
warmup = max(1, total_steps // 30)
optimizer = torch.optim.AdamW(model.parameters(), lr=args.lr, betas=(0.9, 0.95), weight_decay=0.0,
                              fused=device == "cuda")


def lr_at(step):
    if step < warmup:
        return args.lr * (step + 1) / warmup
    progress = (step - warmup) / max(1, total_steps - warmup)
    return args.lr * (0.1 + 0.9 * 0.5 * (1 + math.cos(math.pi * progress)))   # cosine to 10%


def batch(ids, mask, idx):
    x = ids[idx, :-1].to(device, non_blocking=True)
    y = ids[idx, 1:].to(device, non_blocking=True)
    m = mask[idx, 1:].to(device, non_blocking=True)      # mask aligned with the *targets*
    return x, y, m


@torch.no_grad()
def val_loss():
    model.eval()
    total, n = 0.0, 0
    for i in range(0, len(val_ids), args.micro_batch):
        x, y, m = batch(val_ids, val_mask, torch.arange(i, min(i + args.micro_batch, len(val_ids))))
        with torch.autocast("cuda", dtype=torch.bfloat16, enabled=device == "cuda"):
            total += model(x, y, loss_mask=m)[1].item()
        n += 1
    model.train()
    return total / max(n, 1)


TEST_PROMPTS = ["Who are you?", "What is photosynthesis?", "भारत की राजधानी क्या है?",
                "mujhe neend nahi aa rahi, kya karun?", "इस चौपाई का अर्थ बताइए:\nमंगल भवन अमंगल हारी । द्रवउ सो दसरथ अजिर बिहारी ॥"]


def samples(step):
    model.eval()
    with open(run_dir / "samples.txt", "a", encoding="utf-8") as f:
        f.write(f"\n===== step {step} =====\n")
        for q in TEST_PROMPTS:
            ids = torch.tensor([T.chat_prompt(tok, [{"role": "user", "content": q}])], device=device)
            out = list(model.generate(ids, 150, temperature=0.7, top_p=0.9,
                                      stop_ids={tok.token_to_id(T.END), EOT}))
            f.write(f"USER: {q}\nMONA: {tok.decode(out)}\n\n")
    model.train()


print(f"{total_steps:,} steps x {rows_per_step} rows | val loss before SFT: {val_loss():.4f}")
log = open(run_dir / "sft_log.csv", "w", newline="")
w = csv.writer(log)
w.writerow(["step", "lr", "train_loss", "val_loss"])
order = torch.randperm(len(train_ids))
pos, best, t0 = 0, float("inf"), time.time()
model.train()
for step in range(total_steps):
    for g in optimizer.param_groups:
        g["lr"] = lr_at(step)
    loss_sum = 0.0
    for _ in range(args.accum):
        if pos + args.micro_batch > len(order):
            order, pos = torch.randperm(len(train_ids)), 0
        x, y, m = batch(train_ids, train_mask, order[pos:pos + args.micro_batch])
        pos += args.micro_batch
        with torch.autocast("cuda", dtype=torch.bfloat16, enabled=device == "cuda"):
            _, loss = model(x, y, loss_mask=m)
        (loss / args.accum).backward()
        loss_sum += loss.item()
    torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
    optimizer.step()
    optimizer.zero_grad(set_to_none=True)

    if (step + 1) % args.eval_every == 0 or step + 1 == total_steps:
        vl = val_loss()
        w.writerow([step + 1, f"{lr_at(step):.2e}", f"{loss_sum / args.accum:.4f}", f"{vl:.4f}"])
        log.flush()
        saved = ""
        if vl < best:
            best = vl
            torch.save(model.state_dict(), run_dir / "model.pt")
            saved = "  ✓ saved best"
        samples(step + 1)
        print(f"step {step + 1:5,}/{total_steps:,} | train {loss_sum / args.accum:.4f} | val {vl:.4f} | "
              f"{(time.time() - t0) / 60:5.1f} min{saved}", flush=True)
    elif (step + 1) % 20 == 0:
        print(f"step {step + 1:5,}/{total_steps:,} | train {loss_sum / args.accum:.4f} | lr {lr_at(step):.2e}",
              flush=True)

print(f"Best val loss {best:.4f} -> {run_dir / 'model.pt'}")
