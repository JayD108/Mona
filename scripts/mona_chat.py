"""Step ⑨ — chat with MONA in the terminal.

Run from C:\\LLM:
    python -m scripts.mona_chat                                  # models/mona/mona_chat.pt
    python -m scripts.mona_chat --weights runs/mona_m_chat/model.pt
    python -m scripts.mona_chat --weights runs/mona_m/final.pt --base   # raw text completion

Commands while chatting:  /reset (new conversation)   /quit
"""
import argparse
import sys

import torch

from mona import config
from mona import tokenizer as T
from mona.model import MONA

p = argparse.ArgumentParser()
p.add_argument("--weights", default=str(config.MODEL_DIR / "mona_chat.pt"))
p.add_argument("--size", choices=["M", "tiny"], default="M")
p.add_argument("--base", action="store_true", help="pretrained model: plain text completion, no chat")
p.add_argument("--temperature", type=float, default=0.7)
p.add_argument("--top-p", type=float, default=0.9)
p.add_argument("--max-new", type=int, default=300)
args = p.parse_args()

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
cfg = config.MONA_M if args.size == "M" else config.MONA_TINY
model = MONA(cfg).to(config.DEVICE)
state = torch.load(args.weights, map_location=config.DEVICE, weights_only=False)
model.load_state_dict(state["model"] if "model" in state else state)
model.eval()
tok = T.load()
stop = {tok.token_to_id(T.END), tok.token_to_id(T.EOT)}


def stream(ids):
    """Print tokens as they are generated; decode the growing list so multi-byte characters stay intact."""
    out, shown = [], ""
    for t in model.generate(torch.tensor([ids], device=config.DEVICE), args.max_new,
                            temperature=args.temperature, top_p=args.top_p, stop_ids=stop):
        out.append(t)
        text = tok.decode(out)
        if not text.endswith("\ufffd"):            # wait until a character is complete
            print(text[len(shown):], end="", flush=True)
            shown = text
    print()
    return tok.decode(out)


print(f"MONA ({'base' if args.base else 'chat'}) loaded from {args.weights}. /reset, /quit\n")
history = []
while True:
    try:
        user = input("You: ").strip()
    except (EOFError, KeyboardInterrupt):
        break
    if not user:
        continue
    if user == "/quit":
        break
    if user == "/reset":
        history = []
        print("(new conversation)\n")
        continue
    print("MONA: ", end="")
    if args.base:
        stream(tok.encode(user).ids)
        continue
    history.append({"role": "user", "content": user})
    ids = T.chat_prompt(tok, history)
    while len(ids) > cfg.context - args.max_new and len(history) > 1:   # forget the oldest turns
        history = history[2:]
        ids = T.chat_prompt(tok, history)
    reply = stream(ids)
    history.append({"role": "assistant", "content": reply})
    print()
