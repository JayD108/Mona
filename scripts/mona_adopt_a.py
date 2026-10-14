"""After chat-tuning A: decide, with clear rules, whether the app should talk with the new MONA-Chat, and write a report.

Run from C:\\LLM (it waits for the evaluation to appear, so it can be started before A finishes):
    python -m scripts.mona_adopt_a

It reads runs/mona_m_chat2/chat_eval.txt (written by scripts/mona_chat_eval.py: the original MONA-Chat first, the new
one second) and ADOPTS the new model, locally only, by creating runs/mona_m_chat2/ADOPTED, when ALL of these hold:
  1. its held-out English chat loss is lower than the original's        (it predicts unseen English chats better)
  2. it says "I am MONA" at least as often as the original, averaged over the identity checks
  3. its greeting rate is at least the original's
Deleting the ADOPTED file switches the app back. Nothing is uploaded or released: that stays your decision.
The verdict and the numbers go to runs/mona_m_chat2/ADOPTION.txt.
"""
import re
import sys
import time

from mona import config

RUN = config.RUNS_DIR / "mona_m_chat2"
EVAL = RUN / "chat_eval.txt"


def parse(text):
    """-> list of dicts, one per model, in the order they were evaluated."""
    models, cur = [], None
    for line in text.splitlines():
        if line and not line.startswith(" ") and ("model.pt" in line or line.endswith(".pt")):
            cur = {"name": line.strip(), "loss": None, "identity": [], "greeting": []}
            models.append(cur)
        elif cur is not None and "held-out English chat loss" in line:
            cur["loss"] = float(re.search(r":\s*([\d.]+)", line).group(1))
        elif cur is not None and "says she is MONA" in line and "name prompt" in line:
            cur["identity"] = [int(x) for x in re.findall(r"(\d+)%", line.split("|")[0])]
            cur["greeting"] = [int(x) for x in re.findall(r"(\d+)%", line.split("|")[1])]
    return models


def mean(xs):
    return sum(xs) / len(xs) if xs else 0.0


def main():
    print("waiting for", EVAL, flush=True)
    while not EVAL.exists():
        time.sleep(60)
    time.sleep(5)
    models = parse(EVAL.read_text(encoding="utf-8"))
    if len(models) < 2 or any(m["loss"] is None for m in models[:2]):
        (RUN / "ADOPTION.txt").write_text("Could not read the evaluation; the app keeps the original MONA-Chat.\n", encoding="utf-8")
        sys.exit("could not parse the evaluation")
    old, new = models[0], models[1]
    checks = {
        "held-out loss is lower": new["loss"] < old["loss"],
        "says she is MONA at least as often": mean(new["identity"]) >= mean(old["identity"]),
        "greets at least as well": mean(new["greeting"]) >= mean(old["greeting"]),
    }
    adopt = all(checks.values())
    lines = ["MONA-Chat v2 (A) vs the original, on the same held-out chats and checks", "",
             f"  held-out English chat loss : {old['loss']:.4f} -> {new['loss']:.4f}   (lower is better)",
             f"  says she is MONA (mean of the identity checks) : {mean(old['identity']):.0f}% -> {mean(new['identity']):.0f}%",
             f"  greeting ok (mean) : {mean(old['greeting']):.0f}% -> {mean(new['greeting']):.0f}%", ""]
    lines += [f"  [{'x' if ok else ' '}] {name}" for name, ok in checks.items()]
    lines += ["", "VERDICT: " + ("ADOPTED. The app now talks with the new MONA-Chat (delete runs/mona_m_chat2/ADOPTED to go back)."
                                if adopt else "NOT adopted. The app keeps the original MONA-Chat; the new model is in runs/mona_m_chat2/model.pt."),
              "Nothing was uploaded: releasing to Hugging Face is still your decision."]
    (RUN / "ADOPTION.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
    if adopt:
        (RUN / "ADOPTED").write_text("adopted by scripts.mona_adopt_a\n")
    print("\n".join(lines), flush=True)


if __name__ == "__main__":
    main()
