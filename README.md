# MONA — a multilingual small LLM built from scratch

> **The MONA app** (in progress): an interactive, playful terminal app where anyone can open up a real
> LLM and see how it works, step by step, in English, Hindi or Hinglish.
> Try it: `pip install -e .` then run **`mona`**. Plan: [`docs/MONA_APP_PLAN.md`](docs/MONA_APP_PLAN.md)

**MONA** is a ~110M-parameter Llama-style model (English + Hindi + Hinglish + Awadhi), built through
every stage of a real LLM: data → tokenizer → architecture → pretraining → chat tuning → evaluation.
Plan and numbers: [`docs/MONA_PLAN.md`](docs/MONA_PLAN.md).

| Step | Command (run from `C:\LLM`) |
|---|---|
| ① Download data | `python -m pipeline.mona_download english hindi hinglish sft hindi_wiki` |
| ② Clean | `python -m pipeline.mona_clean` |
| ③ Train tokenizer | `python -m pipeline.mona_tokenizer` |
| ④ Tokenize | `python -m pipeline.mona_tokenize` |
| ⑤ Pretrain (resumable) | `python -m scripts.mona_pretrain --name mona_m` (add `--resume` to continue) |
| Check progress | `python -m scripts.mona_status` |
| Stop safely | create the file `runs\mona_m\STOP` (or Ctrl+C) |
| ⑥ Chat data | `python -m pipeline.mona_build_sft` |
| ⑦ Chat tuning | `python -m scripts.mona_sft --base runs/mona_m/final.pt --name mona_m_chat` |
| ⑧ Evaluate | `python -m scripts.mona_eval runs/mona_m/final.pt` |
| ⑨ Chat | `python -m scripts.mona_chat --weights runs/mona_m_chat/model.pt` |

**Unattended training (APALA strategy):** `ops\MONA_resume.cmd` starts a power guard (freezes training on
battery, 20-min charger break every 6 h) and a watchdog (restarts training if it dies or hangs), which runs
the whole queue via `python -m scripts.mona_run_all`. Pause for the day: create `runs\mona_m\STOP`;
continue: delete it. Details: `docs/MONA_PLAN.md` §4b.

Code: `mona/` (config, tokenizer, model, data). Lessons you can run: `learn/01`–`06`.

## Folder layout

```
mona/        library: config.py, tokenizer.py (byte-level BPE), model.py (Llama-style decoder), data.py
  engine/    glass box: tokens, next-word probabilities, attention maps, layer-by-layer guesses
  ui/        the interactive terminal app (Textual): home, display check, stages
pipeline/    mona_download, mona_clean, mona_tokenizer, mona_tokenize, mona_build_sft
scripts/     mona_pretrain, mona_sft, mona_eval, mona_chat, mona_status, mona_run_all (job queue)
ops/         unattended-training kit: power guard, watchdog, MONA_resume.cmd (Windows Startup)
learn/       lessons you can run: 01 BPE, 03 attention, 04 RoPE, 05 scaling laws, 06 loss masking
docs/        MONA_PLAN.md: the full plan with measured numbers
```

Not in this repo (local only, many GB): `data/` (raw + cleaned text, token shards), `models/`
(tokenizer + weights), `runs/` (checkpoints, logs).

## Data sources and licenses
FineWeb-Edu (ODC-By) · AI4Bharat Sangraha (CC-BY-4.0) · smol-smoltalk (Apache-2.0) · Aya (Apache-2.0).
The Tulsidas text is used for private research only and is not distributed here.

## License
MIT (see [`LICENSE`](LICENSE)). Datasets and model weights keep their own licenses (above).

## Acknowledgement
Coding assisted by Claude (Anthropic).

## Origin
MONA grew out of **MANAS v1**, a 10.8M-parameter character-level model of Tulsidas's Awadhi
(https://huggingface.co/JayF14/MANAS). Its code stays in the local project (`docs/MANAS_README.md`).

