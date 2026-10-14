"""Evaluate MONA-Chat models on what a learner actually experiences: chatting.

Run from C:\\LLM:
    python -m scripts.mona_chat_eval runs/mona_m_chat/model.pt runs/mona_m_chat2/model.pt
    python -m scripts.mona_chat_eval runs/mona_m_chat2/model.pt --out runs/mona_m_chat2/chat_eval.txt

Three checks, the same for every model:
  1. HELD-OUT LOSS  how well she predicts the assistant's words in 1,000 English chats that NO model was trained on
                    (lower is better; comparable between models because it is the same data and the same tokenizer).
  2. IDENTITY       does she still say she is MONA, as a first message and deep into a conversation? (higher is better)
  3. GREETING       does "hello" get a friendly, sensible reply? (higher is better)
and a file of sample answers to the same prompts, so a person can read them side by side.
"""
import argparse
import json
import re

import torch

from mona import config
from mona import tokenizer as T
from mona.model import MONA

p = argparse.ArgumentParser()
p.add_argument("weights", nargs="+")
p.add_argument("--heldout", default=str(config.DATA_DIR / "mona_sft_v2" / "heldout_english.jsonl"))
p.add_argument("--n", type=int, default=400, help="held-out chats to score")
p.add_argument("--seeds", type=int, default=8)
p.add_argument("--out", default=None, help="write the sample answers here")
args = p.parse_args()

device = config.DEVICE
tok = T.load()
STOP = {tok.token_to_id(T.END), tok.token_to_id(T.EOT)}
SYSTEMS = {"name prompt": "You are MONA, a small multilingual language model. Your name is MONA. Reply in the same language as the user.",
           "trained prompt": "You are MONA, a helpful assistant. Reply in the same language as the user."}
U = lambda t: {"role": "user", "content": t}
A = lambda t: {"role": "assistant", "content": t}
IDENTITY_CASES = {
    "first message": [U("What is your name?")],
    "after hello": [U("hello"), A("Hello! How can I help you today?"), U("what is your name?")],
    "after a fact": [U("What is the capital of France?"), A("The capital of France is Paris."), U("Who are you?")],
    "after a task": [U("Write one sentence about the sea."), A("The sea is a vast, restless body of salt water."), U("Who made you?")],
}
BAD_NAMES = re.compile(r"\b(emily|wilson|rachel|karen|ryker|thompson|chatgpt|openai|google|anthropic|alibaba|qwen)\b", re.I)
SAMPLE_PROMPTS = ["hello", "Who are you?", "What is photosynthesis?", "Explain why the sky is blue in two sentences.",
                  "Give me three tips for studying better.", "Write a short poem about rain.", "What is 12 + 15?",
                  "Summarize in one sentence: The cat sat on the mat because it was tired after chasing a mouse all morning.",
                  "How do I make a cup of tea?", "What is the capital of India?", "Tell me a fun fact about space.",
                  "What is a language model?"]


def load(path):
    model = MONA(config.MONA_M).to(device).eval()
    state = torch.load(path, map_location=device, weights_only=False)
    model.load_state_dict(state["model"] if "model" in state else state)
    return model


@torch.no_grad()
def heldout_loss(model):
    rows = [json.loads(l) for l in open(args.heldout, encoding="utf-8")][: args.n]
    total_nll, total_tokens = 0.0, 0
    for r in rows:
        ids, mask = T.encode_chat(tok, r["messages"])
        ids, mask = ids[: config.MONA_M.context + 1], mask[: config.MONA_M.context + 1]
        if sum(mask) == 0 or len(ids) < 3:
            continue
        x = torch.tensor([ids[:-1]], device=device)
        y = torch.tensor([ids[1:]], device=device)
        m = torch.tensor([mask[1:]], device=device).float()
        with torch.autocast("cuda", dtype=torch.bfloat16, enabled=device == "cuda"):
            logits, _ = model(x, y)
        nll = torch.nn.functional.cross_entropy(logits.view(-1, logits.size(-1)).float(), y.reshape(-1), reduction="none")
        total_nll += float((nll * m.view(-1)).sum())
        total_tokens += float(m.sum())
    return total_nll / max(total_tokens, 1)


@torch.no_grad()
def reply(model, history, system, seed, max_new=120, temperature=0.5):
    torch.manual_seed(seed)
    ids = T.chat_prompt(tok, ([{"role": "system", "content": system}] if system else []) + history)
    out = list(model.generate(torch.tensor([ids], device=device), max_new, temperature=temperature, top_p=0.9, stop_ids=STOP))
    return tok.decode(out).strip()


def identity_scores(model, system):
    out = {}
    for name, hist in IDENTITY_CASES.items():
        ok = 0
        for s in range(args.seeds):
            r = reply(model, hist, system, 100 + s, max_new=60)
            ok += ("mona" in r.lower()[:120]) and not BAD_NAMES.search(r)
        out[name] = ok / args.seeds
    return out


def greeting_score(model, system):
    ok = 0
    for s in range(args.seeds):
        r = reply(model, [U("hello")], system, 200 + s, max_new=60)
        ok += r.lower().startswith(("hello", "hi", "hey", "good", "namaste")) and "programmer" not in r.lower() and "i'm hello" not in r.lower()
    return ok / args.seeds


report, samples = [], []
for path in args.weights:
    model = load(path)
    row = {"model": path, "heldout_loss": heldout_loss(model)}
    for sname, system in SYSTEMS.items():
        row[f"identity [{sname}]"] = identity_scores(model, system)
        row[f"greeting [{sname}]"] = greeting_score(model, system)
    report.append(row)
    samples.append(f"\n########## {path}\n")
    for q in SAMPLE_PROMPTS:
        samples.append(f"USER: {q}\nMONA: {reply(model, [U(q)], SYSTEMS['name prompt'], 7, max_new=140)}\n")
    del model
    if device == "cuda":
        torch.cuda.empty_cache()

lines = []
for r in report:
    lines.append(f"{r['model']}")
    lines.append(f"  held-out English chat loss : {r['heldout_loss']:.4f}   (lower is better)")
    for sname in SYSTEMS:
        ident = r[f"identity [{sname}]"]
        lines.append(f"  [{sname:14s}] says she is MONA: " + "  ".join(f"{k} {v:.0%}" for k, v in ident.items())
                     + f"   |  greeting ok {r[f'greeting [{sname}]']:.0%}")
text = "\n".join(lines)
print(text)
if args.out:
    import pathlib
    pathlib.Path(args.out).write_text(text + "\n\n" + "\n".join(samples), encoding="utf-8")
    print(f"sample answers -> {args.out}")
