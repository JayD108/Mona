"""MONA-Chat inside the app: load it once, then stream replies (used by the welcome paragraph and the chat screen)."""
import re
import threading
import time

import torch

from .. import config
from .. import tokenizer as T

CHAT_WEIGHTS = config.chat_weights()
# A system message in the style MONA-Chat was trained with (pipeline/mona_build_sft.py), plus her name. Without the
# name she sometimes answers "hello" with "I'm hello": her chat training was only 160 identity examples.
TRAINED_SYSTEM = "You are MONA, a helpful assistant. Reply in the same language as the user."   # used in training
SYSTEM = ("You are MONA, a small multilingual language model. Your name is MONA. "
          "Reply in the same language as the user.")
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


def stream_reply(model, tok, history, on_text, cancel=None, max_new=200, temperature=0.5, top_p=0.9, system=None):
    """Write a reply to `history` (a list of {"role", "content"}), one token at a time.

    on_text(text, n_tokens, seconds) is called every time the text grows. Returns (text, n_tokens, seconds).
    Stops early when `cancel` (a threading.Event) is set.
    """
    ctx = model.cfg.context
    head = [{"role": "system", "content": system or SYSTEM}]
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


IDENTITY = re.compile("|".join(["your name", "who are you", "what are you", "who made you", "who built you",
                                          "who created you", "who trained you", "tell me about yourself",
                                          "introduce yourself"]), re.I)


def is_identity_question(text):
    """MONA learned to answer these only as the FIRST message of a chat (her identity examples were single-turn),
    so deep into a conversation she may invent a person. The chat screen asks them in a fresh context."""
    return bool(IDENTITY.search(text))
