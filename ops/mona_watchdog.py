"""MONA watchdog: keeps the GPU from sitting idle because training died or hung. Adapted from APALA's.

It only (re)starts the job queue (scripts/mona_run_all.py), which resumes from checkpoints and skips
finished steps, so it never changes a result. Checks every 60 s; logs to runs/logs/mona_watchdog.log.

  DONE    "QUEUE COMPLETE" in runs/logs/mona_run_all.log -> nothing left to do
  HELD    runs/mona_m/STOP exists (you stopped it on purpose) -> do nothing until you delete STOP
  FROZEN  the power guard has training frozen (on battery / adapter break) -> do nothing
  DEAD    no MONA process for >= 5 min -> start the queue
  HUNG    process alive but GPU < 5 % for 30 min AND nothing written under runs/ for 30 min
          -> kill it, then start the queue again
  LIMIT   at most 3 restarts in any 3 h; after that it stops acting and writes an ALERT
          (a crash that keeps repeating is a bug to fix, not something to retry forever)
"""
import datetime as dt
import os
import re
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(r"C:\LLM")
RUNS = ROOT / "runs"
LOG = RUNS / "logs" / "mona_watchdog.log"
LOCK = ROOT / "ops" / "mona_watchdog.lock"
GUARD_LOG = RUNS / "logs" / "mona_power_guard.log"
QUEUE_LOG = RUNS / "logs" / "mona_run_all.log"
PLAN_FILE = RUNS / "ACTIVE_PLAN"                 # "v2" while the English-centric v2 job is running; absent = the finished v1 job
PLAN = PLAN_FILE.read_text().strip() if PLAN_FILE.exists() else "v1"
if PLAN == "v2":
    QUEUE_LOG, QUEUE_MODULE, QUEUE_OUT, DONE_TEXT = RUNS / "logs" / "mona_run_v2.log", "scripts.mona_run_v2", "mona_run_v2.out", "V2 QUEUE COMPLETE"
    STOP = RUNS / "mona_v2" / "STOP"
    QUEUE_LOCK = ROOT / "ops" / "mona_run_v2.lock"
else:
    QUEUE_MODULE, QUEUE_OUT, DONE_TEXT = "scripts.mona_run_all", "mona_run_all.out", "QUEUE COMPLETE"
    STOP = RUNS / "mona_m" / "STOP"
    QUEUE_LOCK = ROOT / "ops" / "mona_run_all.lock"
PIPE = re.compile(r"scripts\.mona_(run_all|run_v2|pretrain|sft|eval|chat_eval|release)|pipeline\.mona_(build_sft|prep_v2|tokenize|clean|download)")
NO_WINDOW = subprocess.CREATE_NO_WINDOW          # started hidden at log-in: never flash console windows
DEAD_MIN, HUNG_MIN, GPU_IDLE_PCT = 5, 30, 5
MAX_RESTARTS, WINDOW_H = 3, 3


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
            r = subprocess.run(["tasklist", "/FI", f"PID eq {pid}", "/NH"], capture_output=True, text=True,
                               creationflags=NO_WINDOW)
            if str(pid) in r.stdout and "python" in r.stdout.lower():
                return False
        except ValueError:
            pass
    LOCK.write_text(str(os.getpid()))
    return True


def processes():
    # python.exe AND pythonw.exe: the watchdog runs windowless (pythonw), so the training it starts does too
    ps = ("Get-CimInstance Win32_Process -Filter \"Name='python.exe' OR Name='pythonw.exe'\" | "
          "ForEach-Object { \"$($_.ProcessId)`t$($_.ParentProcessId)`t$($_.CommandLine)\" }")
    r = subprocess.run(["powershell", "-NoProfile", "-Command", ps], capture_output=True, text=True,
                       creationflags=NO_WINDOW)
    out = []
    for line in r.stdout.splitlines():
        parts = line.split("\t", 2)
        if len(parts) == 3 and parts[0].isdigit():
            out.append((int(parts[0]), int(parts[1] or 0), parts[2]))
    return [p for p in out if PIPE.search(p[2])]


def gpu_util():
    try:
        r = subprocess.run(["nvidia-smi", "--query-gpu=utilization.gpu", "--format=csv,noheader,nounits"],
                           capture_output=True, text=True, timeout=20, creationflags=NO_WINDOW)
        return int(r.stdout.strip().splitlines()[0])
    except Exception:
        return -1


def read(p):
    try:
        return p.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return ""


def frozen():
    """True while the power guard holds training frozen (its latest event is a freeze)."""
    for line in reversed([l for l in read(GUARD_LOG).splitlines() if l.strip()]):
        if "frozen" in line:
            return True
        if "resumed" in line or "break over" in line or "guard started" in line:
            return False
    return False


def recent_write(minutes):
    cutoff = time.time() - minutes * 60
    for dirpath, _, files in os.walk(RUNS):
        for f in files:
            try:
                if os.path.getmtime(os.path.join(dirpath, f)) > cutoff:
                    return True
            except OSError:
                pass
    return False


def start_queue():
    flags = subprocess.CREATE_NEW_PROCESS_GROUP | NO_WINDOW   # hidden console, inherited by children
    subprocess.Popen([sys.executable, "-u", "-m", QUEUE_MODULE], cwd=ROOT, creationflags=flags,
                     env=dict(os.environ, PYTHONIOENCODING="utf-8"),
                     stdout=open(RUNS / "logs" / QUEUE_OUT, "a", encoding="utf-8"),
                     stderr=subprocess.STDOUT)
    log(f"started the job queue ({QUEUE_MODULE})")


def kill_tree(procs):
    pids = {p[0] for p in procs}
    for pid, parent, cmd in procs:
        if parent not in pids:
            subprocess.run(["taskkill", "/PID", str(pid), "/T", "/F"], capture_output=True, creationflags=NO_WINDOW)
            log(f"killed hung process tree {pid}: {cmd[-80:]}")
    QUEUE_LOCK.unlink(missing_ok=True)


def main():
    if not single_instance():
        print("watchdog already running; exiting")
        return
    log(f"watchdog started (dead >= {DEAD_MIN} min, hung >= {HUNG_MIN} min at GPU < {GPU_IDLE_PCT} %, "
        f"max {MAX_RESTARTS} restarts / {WINDOW_H} h)")
    dead_since = idle_since = None
    restarts, alerted, last_state = [], False, None
    while True:
        try:
            now = time.time()
            state = ("done" if DONE_TEXT in read(QUEUE_LOG) else
                     "held" if STOP.exists() else "frozen" if frozen() else "active")
            if state != last_state:
                log(f"state: {state}")
                last_state = state
            if state == "done":
                log("queue complete; watchdog exiting")
                break
            if state != "active":
                dead_since = idle_since = None
                time.sleep(60)
                continue
            procs = processes()
            action = None
            if not procs:
                idle_since = None
                dead_since = dead_since or now
                if now - dead_since >= DEAD_MIN * 60:
                    action = "dead"
            else:
                dead_since = None
                g = gpu_util()
                if 0 <= g < GPU_IDLE_PCT:
                    idle_since = idle_since or now
                    if now - idle_since >= HUNG_MIN * 60 and not recent_write(HUNG_MIN):
                        action = "hung"
                else:
                    idle_since = None
            if action:
                restarts = [t for t in restarts if now - t < WINDOW_H * 3600]
                if len(restarts) >= MAX_RESTARTS:
                    if not alerted:
                        log(f"ALERT: training {action} again after {len(restarts)} restarts in {WINDOW_H} h; "
                            "not restarting (repeating failure = bug). See runs/logs/mona_*.out")
                        alerted = True
                else:
                    log(f"training {action}; restarting")
                    if action == "hung":
                        kill_tree(procs)
                        time.sleep(20)
                    start_queue()
                    restarts.append(now)
                    alerted = False
                dead_since = idle_since = None
        except Exception as e:                       # the watchdog itself must never die
            log(f"watchdog error: {type(e).__name__}: {e}")
        time.sleep(60)
    LOCK.unlink(missing_ok=True)


if __name__ == "__main__":
    main()
