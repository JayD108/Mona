"""Where MONA's files live. No heavy imports here, so the app can start instantly.

Two modes:
  development  this repository has models/mona/tokenizer.json  -> use the repository's own data/, runs/, models/
  installed    (pip install) -> use ~/.mona/assets (downloaded once from Hugging Face by mona/assets.py)
Set the MONA_HOME environment variable to force a specific asset folder.
"""
import os
from pathlib import Path

CODE_ROOT = Path(__file__).resolve().parent.parent
DEV = (CODE_ROOT / "models" / "mona" / "tokenizer.json").exists()

if os.environ.get("MONA_HOME"):
    ROOT = Path(os.environ["MONA_HOME"])
elif DEV:
    ROOT = CODE_ROOT
else:
    ROOT = Path.home() / ".mona" / "assets"

DATA_DIR    = ROOT / "data"
CLEAN_DIR   = DATA_DIR / "mona_clean"          # cleaned text per language (*.txt)
TOKENS_DIR  = DATA_DIR / "mona_tokens"         # uint16 token shards (*.bin) + manifest
SFT_DIR     = DATA_DIR / "mona_sft"            # chat examples (train/val .jsonl)
MODEL_DIR   = ROOT / "models" / "mona"         # tokenizer + released weights
RUNS_DIR    = ROOT / "runs"                    # one folder per training run
OUTPUTS_DIR = ROOT / "outputs"
TOKENIZER_PATH = MODEL_DIR / "tokenizer.json"
VERSE_PATH  = DATA_DIR / "processed" / "tulsidas_verse_strict.txt"   # public-domain Tulsidas verse
