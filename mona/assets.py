"""First-run download of MONA's weights and demo data (for `pip install` users).

In development (this repository, with models/mona/tokenizer.json) nothing is downloaded.
Otherwise everything under `assets/` in the Hugging Face repo is fetched once into ~/.mona/assets:
tokenizer, base + chat weights, and a small, licence-clean demo bundle the labs read.
"""
import os
import sys

from . import paths

REPO = os.environ.get("MONA_REPO", "JayF14/MONA")
MARKER = paths.ROOT / "ASSETS_OK"


def ensure():
    if paths.DEV and not os.environ.get("MONA_HOME"):
        return
    if MARKER.exists():
        return
    print(f"MONA: first run, downloading the model and demo data from huggingface.co/{REPO} (~0.5 GB, once)…")
    os.environ.setdefault("HF_HUB_DISABLE_XET", "1")
    try:
        from huggingface_hub import snapshot_download
        snapshot_download(REPO, allow_patterns=["assets/*", "assets/**/*"], local_dir=str(paths.ROOT.parent))
    except Exception as e:
        sys.exit(f"MONA: download failed ({e}). Check your internet connection and run `mona` again.")
    MARKER.write_text("ok")
    print("MONA: ready.")
