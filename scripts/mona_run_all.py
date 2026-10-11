"""MONA job queue: pretrain -> chat data -> chat tuning -> evaluation, skipping finished steps.

Run from C:\\LLM:   python -m scripts.mona_run_all
(normally started by the watchdog, ops/mona_watchdog.py; exits at once if already running)

Each step has a "done" marker, so the queue can be killed and restarted at any time:
  pretrain   runs/mona_m/final.pt          (resumes from runs/mona_m/ckpt.pt)
  sft data   data/mona_sft/train.jsonl     (built after pretraining, when all chat data is downloaded)
  sft        runs/mona_m_chat/DONE
  eval       runs/mona_m/eval.txt
  release    runs/mona_m/RELEASED          (only written after a successful upload to Hugging Face)
When everything is done it writes "QUEUE COMPLETE" to runs/logs/mona_run_all.log.
"""
import datetime as dt
import os
import subprocess
import sys

from mona import config

LOG = config.RUNS_DIR / "logs" / "mona_run_all.log"
LOCK = config.ROOT / "ops" / "mona_run_all.lock"
PRE = config.RUNS_DIR / "mona_m"
CHAT = config.RUNS_DIR / "mona_m_chat"

STEPS = [  # (name, done-marker, command)
    ("pretrain", PRE / "final.pt",
     [sys.executable, "-u", "-m", "scripts.mona_pretrain", "--name", "mona_m", "--resume"]),
    ("sft data", config.SFT_DIR / "train.jsonl",
     [sys.executable, "-u", "-m", "pipeline.mona_build_sft"]),
    ("sft", CHAT / "DONE",
     [sys.executable, "-u", "-m", "scripts.mona_sft", "--base", str(PRE / "final.pt"), "--name", "mona_m_chat"]),
    ("eval", PRE / "eval.txt",
     [sys.executable, "-u", "-m", "scripts.mona_eval", str(PRE / "final.pt"), str(CHAT / "model.pt")]),
    ("release", PRE / "RELEASED",                      # checks, licence-clean bundle, model card, upload to HF
     [sys.executable, "-u", "-m", "scripts.mona_release"]),
]


def log(msg):
    LOG.parent.mkdir(parents=True, exist_ok=True)
    line = f"[{dt.datetime.now():%Y-%m-%d %H:%M:%S}] {msg}"
    print(line, flush=True)
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(line + "\n")


def single_instance():
    if LOCK.exists():
        try:
            pid = int(LOCK.read_text())
            r = subprocess.run(["tasklist", "/FI", f"PID eq {pid}", "/NH"], capture_output=True, text=True)
            if str(pid) in r.stdout:
                return False
        except ValueError:
            pass
    LOCK.parent.mkdir(parents=True, exist_ok=True)
    LOCK.write_text(str(os.getpid()))
    return True


def main():
    if not single_instance():
        print("queue already running; exiting")
        return
    env = dict(os.environ, PYTHONIOENCODING="utf-8")
    try:
        for name, marker, cmd in STEPS:
            if marker.exists():
                continue
            out_path = config.RUNS_DIR / "logs" / f"mona_{name.replace(' ', '_')}.out"
            log(f"starting step '{name}' -> {out_path.name}")
            with open(out_path, "a", encoding="utf-8") as out:
                if name == "eval":                      # eval prints a table: keep it next to the model
                    r = subprocess.run(cmd, cwd=config.ROOT, env=env, stdout=subprocess.PIPE,
                                       stderr=out, text=True, encoding="utf-8")
                    if r.returncode == 0:
                        marker.write_text(r.stdout, encoding="utf-8")
                        out.write(r.stdout)
                else:
                    r = subprocess.run(cmd, cwd=config.ROOT, env=env, stdout=out, stderr=subprocess.STDOUT)
            if r.returncode != 0:
                log(f"step '{name}' FAILED (exit {r.returncode}); see {out_path}")
                sys.exit(1)
            if name == "sft":
                marker.write_text("done")
            if not marker.exists():                      # e.g. pretrain stopped early by STOP / --stop-at
                log(f"step '{name}' exited without finishing (stopped on request); queue paused")
                return
            log(f"finished step '{name}'")
        log("QUEUE COMPLETE")
    finally:
        LOCK.unlink(missing_ok=True)


if __name__ == "__main__":
    main()
