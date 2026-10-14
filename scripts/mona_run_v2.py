"""MONA v2 job queue: a better chat model now, then a better base model, then a better chat model on top of it.

Run from C:\\LLM:   python -m scripts.mona_run_v2
(normally started by the watchdog, ops/mona_watchdog.py; exits at once if already running)

The plan (the user's choice: A first, then B, English-centric with about 10% Hindi, overnight):

  A  more and better English chat data, re-tune the CURRENT base
        sft data v2 -> sft A (runs/mona_m_chat2) -> chat eval A  (v1 vs A, on held-out chats and identity checks)
  B  continue pretraining on more English, then chat-tune on top
        pretrain v2 (runs/mona_v2, +4B tokens, 87% English / 10% Hindi) -> base eval
        -> sft B (runs/mona_v2_chat) -> chat eval B  (v1 vs A vs B)

Data preparation for B (download six more FineWeb-Edu shards, clean, tokenize) runs in the BACKGROUND while step A
uses the GPU, and the pretraining step waits for it. Each step has a "done" marker, so the queue can be killed and
restarted at any time and skips finished work. Nothing is released automatically: v1 stays the released model until a
person looks at the comparison files and decides.
When everything is done it writes "V2 QUEUE COMPLETE" to runs/logs/mona_run_v2.log.
"""
import datetime as dt
import json
import os
import subprocess
import sys
import threading
import time

from mona import config

RUNS = config.RUNS_DIR
LOG = RUNS / "logs" / "mona_run_v2.log"
LOCK = config.ROOT / "ops" / "mona_run_v2.lock"
PREP_LOCK = config.ROOT / "ops" / "mona_prep_v2.lock"
HEARTBEAT = RUNS / "logs" / "v2_heartbeat"
SFT2 = config.DATA_DIR / "mona_sft_v2"
V1, V1_CHAT = RUNS / "mona_m", RUNS / "mona_m_chat"
CHAT_A, V2, CHAT_B = RUNS / "mona_m_chat2", RUNS / "mona_v2", RUNS / "mona_v2_chat"
PY = [sys.executable, "-u", "-m"]


def prep_ready():
    try:
        return "english2" in json.loads((config.TOKENS_DIR / "manifest.json").read_text())
    except (OSError, ValueError):
        return False


STEPS = [  # (name, done-marker, command, needs data prep first, capture stdout into the marker)
    ("sft data v2", SFT2 / "train.jsonl", PY + ["pipeline.mona_build_sft", "--v2"], False, False),
    ("sft A", CHAT_A / "DONE", PY + ["scripts.mona_sft", "--base", str(V1 / "final.pt"), "--name", "mona_m_chat2",
                                      "--data", str(SFT2), "--epochs", "2"], False, False),
    ("chat eval A", CHAT_A / "chat_eval.txt", PY + ["scripts.mona_chat_eval", str(V1_CHAT / "model.pt"),
                                                    str(CHAT_A / "model.pt"), "--out", str(CHAT_A / "chat_eval_samples.txt")], False, True),
    ("pretrain v2", V2 / "final.pt", PY + ["scripts.mona_pretrain", "--name", "mona_v2", "--init", str(V1 / "final.pt"),
                                           "--mix", "v2", "--total-tokens", "4e9", "--lr", "3e-4", "--resume"], True, False),
    ("base eval v2", V2 / "eval.txt", PY + ["scripts.mona_eval", str(V1 / "final.pt"), str(V2 / "final.pt")], False, True),
    ("sft B", CHAT_B / "DONE", PY + ["scripts.mona_sft", "--base", str(V2 / "final.pt"), "--name", "mona_v2_chat",
                                      "--data", str(SFT2), "--epochs", "2"], False, False),
    ("chat eval B", CHAT_B / "chat_eval.txt", PY + ["scripts.mona_chat_eval", str(V1_CHAT / "model.pt"), str(CHAT_A / "model.pt"),
                                                    str(CHAT_B / "model.pt"), "--out", str(CHAT_B / "chat_eval_samples.txt")], False, True),
]


def log(msg):
    LOG.parent.mkdir(parents=True, exist_ok=True)
    line = f"[{dt.datetime.now():%Y-%m-%d %H:%M:%S}] {msg}"
    print(line, flush=True)
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(line + "\n")


def pid_alive(path):
    if path.exists():
        try:
            pid = int(path.read_text())
            r = subprocess.run(["tasklist", "/FI", f"PID eq {pid}", "/NH"], capture_output=True, text=True)
            return str(pid) in r.stdout
        except ValueError:
            pass
    return False


BEAT = threading.Event()          # set while the GPU is NOT the one working (waiting for data, evaluating, building data)


def heartbeat():
    """While BEAT is set, touch a file under runs/ every minute, so the watchdog never mistakes a long wait for a hang.
    It is NOT set during pretraining or chat tuning: those write their own logs, and a silent GPU there is a real hang."""
    def loop():
        while True:
            if BEAT.is_set():
                HEARTBEAT.parent.mkdir(parents=True, exist_ok=True)
                HEARTBEAT.write_text(time.strftime("%H:%M:%S"))
            time.sleep(60)
    threading.Thread(target=loop, daemon=True).start()


def start_prep(env):
    """Download, clean and tokenize the new English data in the background (resumable; one copy at a time)."""
    if prep_ready() or pid_alive(PREP_LOCK):
        return None
    out = open(RUNS / "logs" / "mona_prep_v2.out", "a", encoding="utf-8")
    proc = subprocess.Popen(PY + ["pipeline.mona_prep_v2"], cwd=config.ROOT, env=env, stdout=out, stderr=subprocess.STDOUT)
    PREP_LOCK.write_text(str(proc.pid))
    log(f"started data preparation for v2 in the background (pid {proc.pid})")
    return proc


def main():
    if pid_alive(LOCK):
        print("queue already running; exiting")
        return
    LOCK.parent.mkdir(parents=True, exist_ok=True)
    LOCK.write_text(str(os.getpid()))
    env = dict(os.environ, PYTHONIOENCODING="utf-8")
    heartbeat()
    prep, prep_failures = start_prep(env), 0
    try:
        for name, marker, cmd, needs_prep, capture in STEPS:
            if marker.exists():
                continue
            gpu_step = name.startswith("sft ") and name != "sft data v2" or name.startswith("pretrain")
            if needs_prep:
                BEAT.set()
                log("waiting for the new English data (download, clean, tokenize)…")
                while not prep_ready():
                    time.sleep(30)
                    if prep is not None and prep.poll() is not None and not prep_ready():
                        prep_failures += 1
                        log(f"data preparation stopped (exit {prep.returncode}), attempt {prep_failures}; see runs/logs/mona_prep_v2.out")
                        if prep_failures >= 3:
                            log("giving up on data preparation: fix the problem, then run the queue again")
                            sys.exit(1)
                        PREP_LOCK.unlink(missing_ok=True)
                        prep = start_prep(env)
            BEAT.clear() if gpu_step else BEAT.set()
            out_path = RUNS / "logs" / f"mona_v2_{name.replace(' ', '_')}.out"
            log(f"starting step '{name}' -> {out_path.name}")
            with open(out_path, "a", encoding="utf-8") as out:
                if capture:
                    r = subprocess.run(cmd, cwd=config.ROOT, env=env, stdout=subprocess.PIPE, stderr=out, text=True, encoding="utf-8")
                    if r.returncode == 0:
                        marker.parent.mkdir(parents=True, exist_ok=True)
                        marker.write_text(r.stdout, encoding="utf-8")
                        out.write(r.stdout)
                else:
                    r = subprocess.run(cmd, cwd=config.ROOT, env=env, stdout=out, stderr=subprocess.STDOUT)
            if r.returncode != 0:
                log(f"step '{name}' FAILED (exit {r.returncode}); see {out_path}")
                sys.exit(1)
            if name.startswith("sft ") and name != "sft data v2":
                marker.write_text("done")
            if not marker.exists():                      # e.g. pretrain stopped early by STOP / --stop-at
                log(f"step '{name}' exited without finishing (stopped on request); queue paused")
                return
            log(f"finished step '{name}'")
        log("V2 QUEUE COMPLETE")
    finally:
        LOCK.unlink(missing_ok=True)


if __name__ == "__main__":
    main()
