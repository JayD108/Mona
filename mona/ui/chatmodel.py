"""MONA-Chat inside the app: load it once, then stream replies (used by the welcome paragraph and the chat screen)."""
import threading
import time

import torch

from .. import config
from .. import tokenizer as T

CHAT_WEIGHTS = config.RUNS_DIR / "mona_m_chat" / "model.pt"
# One of the two system prompts MONA-Chat was trained with (pipeline/mona_build_sft.py): chatting in the same
# format as training makes her answers far more reliable.
SYSTEM = "You are MONA, a helpful assistant. Reply in the same language as the user."
_lock = threading.Lock()
_model = None


def available():
    return CHAT_WEIGHTS.exists()


def get_model():
    """Load MONA-Chat on first use (a few seconds) and keep it."""
    global _model
    with _lock:
        if _model is None:
            from ..engine.lessons import load_model
            _model = load_model(CHAT_WEIGHTS)
        return _model


def stream_reply(model, tok, history, on_text, cancel=None, max_new=200, temperature=0.7, top_p=0.9):
    """Write a reply to `history` (a list of {"role", "content"}), one token at a time.

    on_text(text, n_tokens, seconds) is called every time the text grows. Returns (text, n_tokens, seconds).
    Stops early when `cancel` (a threading.Event) is set.
    """
    ctx = model.cfg.context
    head = [{"role": "system", "content": SYSTEM}]
    body = [m for m in history if m["role"] != "system"]
    ids = T.chat_prompt(tok, head + body)
    while len(ids) > ctx - max_new and len(body) > 1:           # forget the oldest turns, keep the system prompt
        body = body[2:]
        ids = T.chat_prompt(tok, head + body)
    stop = {tok.token_to_id(T.END), tok.token_to_id(T.EOT)}
    out, shown = [], ""
    t0 = time.perf_counter()
    for token in model.generate(torch.tensor([ids]), max_new, temperature=temperature, top_p=top_p, stop_ids=stop):
        out.append(token)
        text = tok.decode(out)
        if not text.endswith("�"):                         # wait until a multi-byte letter is complete
            shown = text
            on_text(shown, len(out), time.perf_counter() - t0)
        if cancel is not None and cancel.is_set():
            break
    return tok.decode(out).strip(), len(out), time.perf_counter() - t0
