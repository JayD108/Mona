"""What F9 saves for each lab: a Markdown report of what's on screen + a Python script that reproduces it.

Every script uses MONA's engine directly, so a learner can go from "playing" to "coding" in one step.
"""
HEADER = '''"""Reproduces an experiment from the MONA app. Run from the MONA project folder:  python {name}.py"""
from mona.engine.glassbox import GlassBox

gb = GlassBox()   # loads MONA's newest weights on the CPU
'''


def tokens(text, toks):
    rows = "\n".join(f"| {i} | `{t.text!r}` | {t.id} |" for i, t in enumerate(toks))
    report = f"Text: `{text}`\n\n{len(text)} characters → **{len(toks)} tokens**\n\n| # | piece | id |\n|---|---|---|\n{rows}"
    script = HEADER.format(name="tokens") + f'''
text = {text!r}
for t in gb.tokens(text):
    print(repr(t.text), t.id)
print("next-word guesses:")
for g in gb.next_word(text, top=8):
    print(f"  {{g.token.text!r:15}} {{g.prob:.1%}}")
'''
    return "Tokens: how MONA reads", report, script


def sampling(prompt, generated, temp, top_k, top_p):
    report = (f"Prompt: `{prompt}`\n\nKnobs: temperature **{temp}**, top-k **{top_k or 'off'}**, top-p **{top_p or 'off'}**\n\n"
              f"Generated (with MONA's confidence per piece):\n\n" +
              "\n".join(f"- `{tok.text!r}` {p:.1%}" for tok, p in generated))
    script = HEADER.format(name="sampling") + f'''
for step in gb.generate({prompt!r}, n=40, temperature={temp}, top_k={top_k}, top_p={top_p}, seed=0):
    print(repr(step.token.text), f"{{step.prob:.1%}}", " alternatives:", [a.token.text for a in step.alternatives])
'''
    return "Next word: how MONA chooses", report, script


def attention(text, toks, matrix, layer, head):
    header = "| | " + " | ".join(f"`{t.text.strip()}`" for t in toks) + " |"
    sep = "|---" * (len(toks) + 1) + "|"
    body = "\n".join(f"| `{toks[i].text.strip()}` | " + " | ".join(f"{matrix[i][j]:.2f}" if j <= i else "" for j in range(len(toks)))
                     + " |" for i in range(len(toks)))
    where = f"layer {layer}, " + ("average of all heads" if head is None else f"head {head}")
    report = f"Sentence: `{text}`\n\nAttention, {where} (row = word looking, column = word looked at):\n\n{header}\n{sep}\n{body}"
    pick = "tr.attention[{l}].mean(0)".format(l=layer) if head is None else f"tr.attention[{layer}, {head}]"
    script = HEADER.format(name="attention") + f'''
tr = gb.trace({text!r})
W = {pick}
names = [t.text for t in tr.tokens]
for i, row in enumerate(W):
    print(f"{{names[i]!r:12}}", " ".join(f"{{w:.2f}}" for w in row[:i + 1].tolist()))
'''
    return "Attention: what each word looks at", report, script


def layers(text, word, guesses):
    rows = "\n".join(f"| {l + 1} | " + " | ".join(f"`{g.token.text!r}` {g.prob:.1%}" for g in gs) + " |"
                     for l, gs in enumerate(guesses))
    report = f"Sentence: `{text}`\n\nGuess for the piece after `{word}`, after each layer (logit lens):\n\n| layer | 1st | 2nd | 3rd |\n|---|---|---|---|\n{rows}"
    script = HEADER.format(name="layers") + f'''
tr = gb.trace({text!r})
for layer, per_position in enumerate(tr.layer_guesses, 1):
    top = per_position[-1]          # guesses for the token after the last word
    print(layer, [(g.token.text, round(g.prob, 3)) for g in top])
'''
    return "Layers: watch a thought form", report, script


def exam(results):
    lines = []
    k = 0
    for q, opts, right, scores in results:
        pick = max(range(len(opts)), key=lambda i: scores[i])
        k += pick == right
        lines.append(f"- {'✓' if pick == right else '✗'} **{q} …**  MONA picked `{opts[pick]}`, right: `{opts[right]}`  "
                     f"(scores: {', '.join(f'{o} {s:.2f}' for o, s in zip(opts, scores))})")
    report = f"MONA scored **{k}/{len(results)}** (random guessing ≈ 25%).\n\n" + "\n".join(lines)
    script = HEADER.format(name="exam") + '''
import torch, torch.nn.functional as F

def score(question, option):
    """Mean log-probability of the option's tokens after the question (higher = more natural to MONA)."""
    q, o = gb.encode(question), gb.encode(" " + option)
    ids = torch.tensor([q + o])
    logits, _ = gb.model(ids[:, :-1], ids[:, 1:])
    logp = F.log_softmax(logits[0], dim=-1)
    return logp[torch.arange(len(q) - 1, len(q) + len(o) - 1), ids[0, len(q):]].mean().item()

''' + "EXAM = " + repr([(q, opts, right) for q, opts, right, _ in results]) + '''
correct = 0
for q, opts, right in EXAM:
    scores = [score(q, o) for o in opts]
    pick = max(range(len(opts)), key=lambda i: scores[i])
    correct += pick == right
    print("✓" if pick == right else "✗", q, "->", opts[pick])
print(f"{correct}/{len(EXAM)}")
'''
    return "Evals: MONA's mini exam", report, script
