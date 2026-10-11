# MONA: implementation plan

> **MONA** is a ~110M-parameter multilingual small LLM (English + Hindi + Hinglish + Awadhi),
> built from scratch on one laptop GPU (RTX 5080 Laptop, 16 GB) over **two nights**.
> Supersedes `MANAS2_PLAN.md`. MANAS v1 (`manas/`, `models/`, `apps/`) is left untouched.

---

## 1. Target numbers (measured on this laptop, not guessed)

| | Value | How we got it |
|---|---|---|
| Model | **MONA-M: 12 layers, width 768, 12 heads, SwiGLU 2048, vocab 32,768, context 1,024** | Config `mona/config.py` |
| Parameters | **~110M** (85M "non-embedding" + 25M embedding, shared with the output layer) | Counted |
| Speed | **43K tokens/s** at batch 16 (bf16, fast attention) | Benchmarked 2026-10-11 |
| Sustained speed (assumed) | ~37K tokens/s (−15% for heat over many hours) | Safety margin |
| Training time | Two overnight sessions, **~19 h** | Your choice |
| **Training tokens** | **~2.5B** (≈23 per parameter, compute-optimal) | 37K × 19 h × 3600 |
| Batch | 8 sequences × 1,024 tokens × **64 accumulation steps = 524K tokens/step** | Fits in 16 GB |
| Steps | **~4,800** (~14 s each) | 2.5B / 524K |
| Downloads | ~11.5 GB at 1.7 MB/s ≈ 2 h | Measured |

### Pretraining data mix
| Language | Source | License | Share | ≈ Tokens | Times each text is seen |
|---|---|---|---|---|---|
| English | FineWeb-Edu `sample-10BT` (3 shards) | ODC-By | 55% | 1.37B | ~1× |
| Hindi | Sangraha `verified/hin` (10 files) | CC-BY-4.0 | 40% | 1.0B | ~1× |
| Hinglish | Sangraha `synthetic/hin_Latn` (3 files) | CC-BY-4.0 | 4.5% | 110M | ~1× |
| Awadhi | Tulsidas corpus (~1M tokens) | personal use | 0.2% → 0.8% in the final phase | ~5M | ~5× in total |

Exact token counts are printed by the pipeline once the data is tokenized. The script then shows the real "times seen" for each language.

---

## 2. Codebase

```
C:\LLM
├── mona/                       library (import mona)
│   ├── config.py               paths, ModelConfig (MONA_M, MONA_TINY), data mix
│   ├── tokenizer.py            byte-level BPE: train / load, special tokens, chat template
│   ├── model.py                the transformer: RMSNorm, RoPE, SwiGLU, fast attention, KV-cache generation
│   └── data.py                 token-shard reader, weighted language mixing, chat (SFT) batches
├── pipeline/
│   ├── mona_download.py        ① download raw data
│   ├── mona_clean.py           ② clean each language → data/mona_clean/<lang>.txt
│   ├── mona_tokenizer.py       ③ train the 32K BPE; report tokens per word for each language
│   ├── mona_tokenize.py        ④ text → uint16 token shards + per-language validation sets
│   └── mona_build_sft.py       ⑥ chat data: smol-smoltalk + Aya Hindi + Tulsidas pairs
├── scripts/
│   ├── mona_pretrain.py        ⑤ pretraining: resume, checkpoints, WSD schedule, logs
│   ├── mona_sft.py             ⑦ instruction tuning → MONA-Chat
│   ├── mona_eval.py            ⑧ per-language bits-per-byte, samples, comparisons
│   └── mona_chat.py            ⑨ chat in the terminal
├── learn/                      lessons: 01 BPE ✅, 02 tokenizer fairness, 03 attention,
│                               04 RoPE, 05 scaling laws, 06 loss masking, 07 KV-cache
├── data/raw/…                  downloads        data/mona_clean/  data/mona_tokens/  data/mona_sft/
├── models/mona/                tokenizer.json + released weights
└── runs/mona_m/                checkpoints, log.csv, loss plots, samples
```

---

## 3. Step-by-step

### ① Download (now, ~2 h, in the background)
Three parallel downloads, logged to `runs/logs/download_*.log`.

### ② Clean (`pipeline/mona_clean.py`, ~30 min)
- **All languages:** Unicode NFC; remove control and private-use characters; collapse whitespace; drop documents under 200 characters; exact-duplicate removal by hash.
- **English:** FineWeb-Edu is already quality-filtered; keep it as it is.
- **Hindi:** keep documents whose letters are ≥60% Devanagari. **Keep English words now** (the earlier cleaner deleted them, which was right for Tulsidas and wrong here).
- **Hinglish:** keep documents that are mostly Latin script; spot-check the quality.
- **Awadhi:** the Tulsidas corpus, cut into ~2,000-character documents.
- Documents are separated by `<|endoftext|>`, so the model learns where texts begin and end.

### ③ Tokenizer (`pipeline/mona_tokenizer.py`, ~15 min)
- **Byte-level BPE, 32,768 tokens** (fits in 16-bit integers, which halves disk and memory use).
- **Word-splitting pattern:** GPT-4-style, plus Unicode *marks* (`\p{M}`) so Devanagari vowel signs stay attached to their letters; numbers split into chunks of at most 3 digits.
- **Balanced training sample:** ~150M characters each of English and Hindi, 30M of Hinglish, plus Awadhi. Training on a balanced sample means Hindi isn't starved of tokens just because English is the majority language.
- **Special tokens:** `<|endoftext|> <|pad|> <|system|> <|user|> <|assistant|> <|end|>`
- **Report:** tokens per word for each language (the 📘 fairness lesson).

### ④ Tokenize (`pipeline/mona_tokenize.py`, ~40 min)
- Fast batch encoding (Rust, all CPU cores) into `data/mona_tokens/<lang>_train.bin` and `<lang>_val.bin` (uint16).
- Validation: ~2M tokens per language held out (Awadhi: the last 5% of the corpus).
- Capped at what training needs (+10%), so no time is wasted.

### ⑤ Pretraining (`scripts/mona_pretrain.py`, nights 1–2)
- **Model:** pre-norm decoder, RMSNorm, RoPE, SwiGLU, `scaled_dot_product_attention` (flash), tied embeddings, initialization std 0.02 (residual projections scaled down by 1/√(2·layers)).
- **Optimizer:** AdamW (fused), β = (0.9, 0.95), weight decay 0.1 on weight matrices only, gradient clipping 1.0, bf16 autocast.
- **Learning rate: WSD (warmup–stable–decay).** 1% warmup to a peak of 6e-4, hold steady, then decay over the **final 15%**.
  - 📘 Why: with a steady LR the run can be stopped, resumed and even *extended* without restarting. Only the final decay needs to know when the end is.
- **"Annealing" in the decay phase:** the Awadhi share goes up (0.2% → 0.8%), so MONA leaves training with Tulsidas fresh.
- **Mixing:** each sequence is drawn from a language chosen by its weight, at a random position in that language's shards.
- **Reliability:**
  - checkpoint every 30 min, written to a temporary file and then renamed, so a crash can't corrupt it
  - `--resume` continues exactly where it stopped
  - Ctrl+C, or creating a `STOP` file, saves before exiting
  - an extra snapshot every 0.5B tokens
- **Logging every 10 steps:** loss, learning rate, tokens/s, GPU temperature, ETA.
- **Every ~250 steps:** validation loss **per language**, plus sample generations in English / Hindi / Hinglish / Awadhi.
- **A pilot comes first:** a tiny model (`MONA_TINY`) for ~10 min on real data. It catches bugs cheaply and confirms that the loss falls and that resume works.

### ⑥ Chat data (`pipeline/mona_build_sft.py`)
- smol-smoltalk (English, Apache-2.0): ~100K conversations.
- Aya dataset, Hindi rows (Apache-2.0).
- Tulsidas verse→meaning pairs (7,747) with several Hindi and English phrasings, e.g. "इस चौपाई का अर्थ बताइए" / "Explain this chaupai".
- 2% held out for validation.

### ⑦ Instruction tuning (`scripts/mona_sft.py`, ~1 h)
- Chat template: `<|system|>…<|end|><|user|>…<|end|><|assistant|>…<|end|>`
- **Loss only on the assistant's words** (📘 loss masking).
- ~2 passes over the data, LR 1e-4 with cosine decay.

### ⑧ Evaluation (`scripts/mona_eval.py`)
- **Bits per byte** for each language on held-out text. This is fair across different tokenizers, so MONA can be compared directly with MANAS v1.
- A fixed set of prompts in each language, with base and chat models side by side.

### ⑨ Chat (`scripts/mona_chat.py`)
KV-cache generation, temperature / top-p, streamed output.

---

## 4. Timeline
| When | What |
|---|---|
| Night 0 (now) | Downloads ① → clean ② → tokenizer ③ → tokenize ④ → pilot → **start pretraining ⑤** |
| Night 1 | Pretraining continues (stable LR). I check in on the loss curves |
| Night 2 | Pretraining ends with decay + annealing |
| After | Chat data ⑥ → SFT ⑦ → evaluation ⑧ → chat ⑨ |
| In between | Lessons in `learn/` (02–07), using numbers from the real run |

**Your laptop during training:** plugged in, sleep off, lid open (or "lid close: do nothing"). If you need the laptop during the day, stop with Ctrl+C or the `STOP` file and restart with `--resume`. Nothing is lost except the minutes since the last checkpoint.

---

## 4b. Running unattended for days (the APALA strategy, reused)

APALA v2 trained for 6 straight days on this laptop. MONA reuses the same setup (`C:\LLM\ops\`):

| Piece | What it does |
|---|---|
| `mona_power_guard.ps1` | **Freezes** training in place the moment the laptop goes on battery (2 AC drops were logged today alone), and gives the charger a **20-min break every 6 h**. Frozen = suspended with `NtSuspendProcess`: zero progress lost |
| `mona_watchdog.py` | Restarts training if it **dies** (no process for 5 min) or **hangs** (GPU < 5% and nothing written for 30 min). At most 3 restarts per 3 h. Does nothing while frozen, or while you've **held** it with the `STOP` file |
| `scripts/mona_run_all.py` | The job queue: pretrain → chat data → chat tuning → evaluation, skipping finished steps and resuming from checkpoints |
| `MONA_resume.cmd` | Copied into the Windows **Startup folder**, so after a reboot or log-in, everything comes back by itself |
| Thermal pauses | **Not used.** You removed them from APALA; GPU temperature is only logged |

**To use the laptop during the day:** create `C:\LLM\runs\mona_m\STOP`. Training saves and exits, and the watchdog waits. **To continue:** delete `STOP`; the watchdog restarts within ~5 minutes.
**Logs:** `runs\logs\mona_power_guard.log`, `mona_watchdog.log`, `mona_run_all.log`, and the `mona_*.out` files.

## 5. Risks and how we handle them
| Risk | Mitigation |
|---|---|
| Crash or reboot overnight | Checkpoint every 30 min, `--resume` |
| Laptop overheats and slows down | GPU temperature is logged; WSD lets us shift the end without restarting |
| Loss spikes (instability) | Warmup, gradient clipping, pre-norm, β₂ = 0.95; resume from the last good checkpoint if needed |
| Out of memory | Batch 8 × accumulation 64; tested in the pilot |
| Data bug (e.g. the wrong text) | Pilot run + printed samples of the token shards before the main run |
| Hindi weaker than English | Measured per language; the tokenizer is trained on a balanced sample |
| Awadhi memorized | ≤ ~5 passes in total; Awadhi validation loss is watched |

---
*Prepared 2026-10-11 18:45.*
