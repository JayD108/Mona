"""Check on a MONA training run at a glance (safe to run while training is going).

Run from C:\\LLM:   python -m scripts.mona_status            (default run: mona_m)
                    python -m scripts.mona_status pilot
"""
import csv
import sys

from mona import config

name = sys.argv[1] if len(sys.argv) > 1 else "mona_m"
run = config.RUNS_DIR / name
if not run.exists():
    sys.exit(f"No run at {run}")
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

train = list(csv.DictReader(open(run / "train_log.csv"))) if (run / "train_log.csv").exists() else []
evals = list(csv.DictReader(open(run / "eval_log.csv"))) if (run / "eval_log.csv").exists() else []

if train:
    last = train[-1]
    recent = train[-30:]
    tps = sum(int(r["tokens_per_s"]) for r in recent) / len(recent)
    print(f"Run {name}: step {int(last['step']):,} | {int(last['tokens']) / 1e9:.3f}B tokens | "
          f"loss {float(last['loss']):.3f} | lr {last['lr']} | {tps / 1e3:.1f}K tok/s | GPU {last['gpu_temp_c']}°C")
    temps = [int(r["gpu_temp_c"]) for r in recent if int(r["gpu_temp_c"]) > 0]
    if temps:
        print(f"GPU temperature over the last {len(recent) * 10} steps: {min(temps)}-{max(temps)}°C")
if evals:
    langs = [k for k in evals[0] if k not in ("step", "tokens")]
    print("\nValidation loss per language (lower is better):")
    print(f"{'tokens':>8s} " + " ".join(f"{l:>9s}" for l in langs))
    show = evals if len(evals) <= 8 else evals[:2] + evals[-6:]
    for r in show:
        print(f"{int(r['tokens']) / 1e9:7.2f}B " + " ".join(f"{float(r[l]):9.3f}" for l in langs))
samples = run / "samples.txt"
if samples.exists():
    text = samples.read_text(encoding="utf-8")
    print("\nLatest samples:" + text[text.rfind("====="):][5:])
for f in ("ckpt.pt", "final.pt"):
    if (run / f).exists():
        import datetime
        t = datetime.datetime.fromtimestamp((run / f).stat().st_mtime)
        print(f"{f}: saved {t:%H:%M}")
