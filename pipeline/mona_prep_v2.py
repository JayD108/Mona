"""Prepare the new English data for MONA v2: download six more FineWeb-Edu shards, clean them, tokenize them.

Run from C:\\LLM:   python -m pipeline.mona_prep_v2

Each step is resumable and skips finished work (downloads continue from the .part file; cleaning skips finished row
groups; tokenizing is the last step and writes the "english2" entry in data/mona_tokens/manifest.json, which is the
marker that the data is ready).
"""
import os
import subprocess
import sys

from mona import config

if __name__ == "__main__":
    lock = config.ROOT / "ops" / "mona_prep_v2.lock"
    lock.write_text(str(os.getpid()))
    try:
        for module, group in (("pipeline.mona_download", "english_more"), ("pipeline.mona_clean", "english2"),
                              ("pipeline.mona_tokenize", "english2")):
            print(f"=== {module} {group}", flush=True)
            r = subprocess.run([sys.executable, "-u", "-m", module, group])
            if r.returncode != 0:
                sys.exit(r.returncode)
        print("PREP DONE", flush=True)
    finally:
        lock.unlink(missing_ok=True)
