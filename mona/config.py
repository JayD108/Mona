"""MONA settings: paths, model size, training schedule. One place to change things."""
from dataclasses import dataclass

import torch

from .paths import (CLEAN_DIR, CODE_ROOT, DATA_DIR, DEV, MODEL_DIR, OUTPUTS_DIR, ROOT, RUNS_DIR,  # noqa: F401
                    SFT_DIR, TOKENIZER_PATH, TOKENS_DIR, VERSE_PATH)

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


def chat_weights():
    """The MONA-Chat the app talks with: the v2 model once it has been adopted (the marker file
    runs/mona_m_chat2/ADOPTED), otherwise the original. Deleting the marker switches back."""
    v2 = RUNS_DIR / "mona_m_chat2"
    if (v2 / "ADOPTED").exists() and (v2 / "model.pt").exists():
        return v2 / "model.pt"
    return RUNS_DIR / "mona_m_chat" / "model.pt"


MONA_M = ModelConfig()                                                    # ~110M parameters
MONA_TINY = ModelConfig(d_model=256, n_layers=4, n_heads=4, ffn_hidden=704)  # for tests/pilots

# Pretraining mix: share of training tokens per language (Awadhi is upsampled separately)
MIX = {"english": 0.55, "hindi": 0.40, "hinglish": 0.04, "awadhi": 0.01}
