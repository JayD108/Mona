"""MONA writes her own welcome, live, on the learner's computer.

She is asked "Who are you?" (the question MONA-Chat was trained to answer about itself). A small model drifts
sometimes, so each draft is checked, and a draft that fails is thrown away and rewritten (up to MAX_DRAFTS):
  * it must name MONA right at the start and say how she was made,
  * it must not loop on itself, and it must end on a full sentence.
If every draft fails, a pre-written greeting is shown and labelled as such. Nothing is faked: the status lines in
the app correspond to real steps (loading the weights, generating tokens, checking the draft).
"""
import random
import re

import torch

from . import chatmodel

PROMPT = "Who are you?"
MAX_DRAFTS = 5
FALLBACK = ("I am MONA, a small language model with 110 million numbers inside me. I was trained from scratch on one "
            "laptop to read English, Hindi, Hinglish and Awadhi. I often make mistakes, and that is exactly why you can "
            "learn from me. Let's look inside together.")


def clean(text):
    """Keep whole sentences only."""
    text = " ".join(text.split())
    cut = max(text.rfind("."), text.rfind("!"), text.rfind("?"))
    return text[:cut + 1] if cut > 40 else text


def acceptable(text):
    words = re.findall(r"\w+", text.lower())
    return (len(text) >= 80
            and "mona" in text[:70].lower()
            and ("scratch" in text.lower() or "laptop" in text.lower())
            and len(set(words)) / max(len(words), 1) >= 0.6
            and text.rstrip()[-1] in ".!?")


def write_welcome(model, tok, on_status, on_text, cancel=None):
    """Returns (text, source, drafts). source is "live" or "fallback".

    on_status(stage, draft) with stage "writing" or "metamorphosing" (checking the draft, rewriting if it fails);
    on_text(text, n_tokens, seconds) while a draft is being written.
    """
    history = [{"role": "user", "content": PROMPT}]
    for draft in range(1, MAX_DRAFTS + 1):
        if cancel is not None and cancel.is_set():
            break
        torch.manual_seed(random.randrange(1 << 30))
        on_status("writing", draft)
        text, _, _ = chatmodel.stream_reply(model, tok, history, on_text, cancel=cancel, max_new=90, temperature=0.5,
                                           system=chatmodel.TRAINED_SYSTEM)
        on_status("metamorphosing", draft)
        text = clean(text)
        if acceptable(text):
            return text, "live", draft
    return FALLBACK, "fallback", MAX_DRAFTS
