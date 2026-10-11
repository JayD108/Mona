"""Batches for training MONA.

PretrainBatches  draws each training sequence from a language chosen by its mix weight,
                 at a random position in that language's token shard (memory-mapped, so
                 the 5 GB of tokens are read from disk, not loaded into RAM).
"""
import json

import numpy as np
import torch

from . import config


class PretrainBatches:
    def __init__(self, weights, context, micro_batch, device, seed=0):
        self.context, self.micro_batch, self.device = context, micro_batch, device
        manifest = json.loads((config.TOKENS_DIR / "manifest.json").read_text())
        self.langs = [l for l in weights if l in manifest]
        self.train = {l: np.memmap(config.TOKENS_DIR / f"{l}_train.bin", dtype=np.uint16, mode="r")
                      for l in self.langs}
        self.val = {l: np.memmap(config.TOKENS_DIR / f"{l}_val.bin", dtype=np.uint16, mode="r")
                    for l in self.langs}
        self.rng = np.random.default_rng(seed)
        self.set_weights(weights)

    def set_weights(self, weights):
        w = np.array([weights.get(l, 0.0) for l in self.langs], dtype=np.float64)
        self.weights = w / w.sum()

    def _sample(self, arrays, langs):
        T = self.context
        rows = []
        for lang in langs:
            arr = arrays[lang]
            start = self.rng.integers(0, len(arr) - T - 1)
            rows.append(arr[start:start + T + 1])
        block = torch.from_numpy(np.stack(rows).astype(np.int64))
        block = block.pin_memory().to(self.device, non_blocking=True) if self.device == "cuda" else block
        return block[:, :-1], block[:, 1:]

    def train_batch(self):
        langs = self.rng.choice(self.langs, size=self.micro_batch, p=self.weights)
        return self._sample(self.train, langs)

    def val_batch(self, lang):
        return self._sample(self.val, [lang] * self.micro_batch)

    def describe(self, total_tokens):
        """How many times each language's data will be seen, for a planned number of tokens."""
        lines = []
        for lang, w in zip(self.langs, self.weights):
            n = len(self.train[lang])
            lines.append(f"  {lang:9s} {w:6.1%} of batches | {n / 1e6:8,.0f}M tokens available | "
                         f"seen ~{w * total_tokens / n:4.1f}x")
        return "\n".join(lines)
