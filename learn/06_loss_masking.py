"""LESSON 6 — Chat templates and loss masking: how a text-predictor becomes an assistant.

Run from C:\\LLM:  python -m learn.06_loss_masking      (needs models/mona/tokenizer.json)

A pretrained model only continues text. To make it *answer*, we train on conversations written
in a fixed template, and we grade the model only on the assistant's words.
"""
import sys

from mona import tokenizer as T

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
tok = T.load()
conversation = [
    {"role": "user", "content": "भारत की राजधानी क्या है?"},
    {"role": "assistant", "content": "भारत की राजधानी नई दिल्ली है।"},
]
ids, mask = T.encode_chat(tok, conversation)

print("Every token, and whether the model is graded on predicting it (mask):\n")
for i, m in zip(ids, mask):
    piece = tok.decode([i]) if tok.id_to_token(i) not in T.SPECIAL_TOKENS else tok.id_to_token(i)
    print(f"  {'LEARN' if m else '  -  '}  {piece!r}")

print(f"""
{sum(mask)} of {len(mask)} tokens count toward the loss.

Why mask the question?
  * we want MONA to learn how to ANSWER, not how users phrase questions
  * without the mask, a chat model also learns to imitate users (and wastes capacity on it)
At chat time, the prompt ends with <|assistant|>, and MONA writes until it produces <|end|>.""")
