"""MONA settings: paths, model size, training schedule. One place to change things."""
from dataclasses import dataclass
from pathlib import Path

import torch

ROOT        = Path(__file__).resolve().parent.parent
DATA_DIR    = ROOT / "data"
CLEAN_DIR   = DATA_DIR / "mona_clean"          # cleaned text per language (*.txt)
TOKENS_DIR  = DATA_DIR / "mona_tokens"         # uint16 token shards (*.bin) + manifest
SFT_DIR     = DATA_DIR / "mona_sft"            # chat examples (train/val .jsonl)
MODEL_DIR   = ROOT / "models" / "mona"         # tokenizer + released weights
RUNS_DIR    = ROOT / "runs"                    # one folder per training run
TOKENIZER_PATH = MODEL_DIR / "tokenizer.json"

DEVICE = "cuda" if torch.cuda.is_available() else "cpu"


@dataclass
class ModelConfig:
    vocab_size: int = 32768
    d_model:    int = 768       # width of every token's vector
    n_layers:   int = 12        # transformer blocks
    n_heads:    int = 12        # attention heads (head size 64)
    ffn_hidden: int = 2048      # SwiGLU hidden size (~2.7 x d_model)
    context:    int = 1024      # tokens the model can see at once
    rope_theta: float = 10000.0
    dropout:    float = 0.0     # big data, one pass: no dropout needed (modern practice)


MONA_M = ModelConfig()                                                    # ~110M parameters
MONA_TINY = ModelConfig(d_model=256, n_layers=4, n_heads=4, ffn_hidden=704)  # for tests/pilots

# Pretraining mix: share of training tokens per language (Awadhi is upsampled separately)
MIX = {"english": 0.55, "hindi": 0.40, "hinglish": 0.04, "awadhi": 0.01}
