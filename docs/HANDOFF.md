# MONA: handoff for contributors

Read this first. It says what the project is, where things live, how to run and test it, and what is unfinished.
Written 2026-10-14 at the end of a long build session; the product direction is in `docs/PRODUCT_BRAINSTORM.md`.

## What MONA is
Two things in one repo:
1. **A real small language model**: 110M parameters, Llama-style decoder (RMSNorm, RoPE, SwiGLU, tied embeddings),
   32,768-token byte-level BPE, trained from scratch on one laptop GPU (2.5B tokens). Weights: <https://huggingface.co/JayF14/MONA> (MIT).
2. **A terminal learning lab** ("understand AI from the inside", Textual): every view runs on her real weights.

## Run it
```bash
pip install -e .              # Python 3.10+, installs torch, textual, tokenizers, ...
python -m mona                # first run downloads the weights + demo data (~0.5 GB) to ~/.mona
python tests/test_ui_smoke.py # opens every screen, plays both lessons, checks Esc / Q / quit (needs the weights; ~6 min on CPU)
```
Settings: `MONA_REDUCED_MOTION=1` skips the logo animation. The app is **English-only** with two depths (Simple / Engineer, key F3).

## How the app is organised (`mona/ui/`)
| File | What it is |
|---|---|
| `app.py` | the Textual `App`: one stylesheet (soft navy, titled borders), global keys (Q and Ctrl+C quit, F-keys, Ctrl+P palette), `FRAME_TITLES` |
| `hub.py` | **the home screen**: the 2017 Transformer diagram as a map of MONA; each part opens a lesson chapter |
| `screens.py` | the course dashboard (`HomeScreen`, key C on the hub) and `ExploreActions` (opens the explore screens) |
| `welcome.py`, `logo.py`, `intro.py` | animated logo, the name question, MONA writing her own welcome live (draft, check, rewrite, fallback) |
| `chat.py`, `chatmodel.py` | talk with MONA-Chat; identity questions are asked in a fresh context (her identity data was single-turn only) |
| `lesson.py` | **shared lesson player**: scenes, typed narration, zoom transitions, pause/play, speed 0.25x-3x, chapter picker (C, 1-9) |
| `zoom.py` + `zoomdata.py` | "Inside MONA": whole model down to one neuron, then what kind of model she is (11 scenes, real numbers) |
| `path.py` + `pathdata.py` | "Your words, step by step": 12 pages following the text the user types through tokenizer and model |
| `canvas.py` | character canvas: draw on a 96x17 logical grid, scaled to any terminal |
| `brain.py`, `palette.py` | the live Model-activity strip; the Ctrl+P command palette |
| `labs/`, `mysteries.py`, `course.py`, ... | the 12 stages and the other explore screens (older code, still using `text.py` strings) |

Other places: `mona/model.py` (the transformer, ~170 lines), `mona/engine/` (GlassBox: tokens, attention, logit lens),
`pipeline/` (download, clean, tokenize), `scripts/` (pretrain, sft, eval, release, queues), `ops/` (Windows guards), `learn/` (runnable lessons).

## Conventions that matter
- **Real data only.** Numbers on screen come from the model; narration is hand-written; nothing is faked. If a value is unavailable show `N/A`.
- **No CEO framing** (an earlier version had it; it was removed on purpose). Tone: plain-English, personal ("MONA" speaks in first person).
- **Esc goes back one screen**; Q and Ctrl+C quit everywhere.
- Commit messages: no `Co-Authored-By` trailer (the owner's rule for this repo).
- `.gitignore` is a **whitelist**: new top-level folders/files must be added to it, or they are silently untracked.
- Several files use Windows line endings (`scripts/mona_pretrain.py`, `ops/*`). Keep them when editing.
- Never release automatically: replacing the Hugging Face model is the owner's decision.

## State of the model work (the v2 job, started 2026-10-14)
Plan the owner approved: **A** (better English chat-tuning of the current base) **then B** (+4B tokens of English-centric pretraining, about 10% Hindi),
then chat-tune on B. It runs as one resumable queue: `python -m scripts.mona_run_v2` (Windows; supervised by `ops/mona_watchdog.py`, `ops/mona_power_guard.ps1`).

| Step | Marker | Status when this was written |
|---|---|---|
| sft data v2 | `data/mona_sft_v2/train.jsonl` | done (322K chats, 9.3% Hindi/Hinglish, held-out set `heldout_english.jsonl`) |
| sft A | `runs/mona_m_chat2/DONE` | **running**, about 3 h; ~2 epochs |
| chat eval A | `runs/mona_m_chat2/chat_eval.txt` | after A |
| data prep (download 6 FineWeb-Edu shards, clean, tokenize `english2`) | `english2` in `data/mona_tokens/manifest.json` | **running in the background** |
| pretrain v2 | `runs/mona_v2/final.pt` | **ON HOLD** (`runs/HOLD_V2`); resume with `ops/mona_v2_resume.cmd` (about 28 h) |
| sft B, evals | `runs/mona_v2_chat/DONE` ... | after pretrain |

`scripts/mona_adopt_a.py` decides, by clear rules (lower held-out loss, name kept, greeting ok), whether the app switches to the new chat model
(`runs/mona_m_chat2/ADOPTED`, read by `mona.config.chat_weights()`); it writes `runs/mona_m_chat2/ADOPTION.txt`. Delete `ADOPTED` to revert.
Data, weights and logs (`data/`, `models/`, `runs/`) are **not in git** (many GB). A contributor without them can still work on everything under
`mona/ui/` using the downloaded weights; only the training steps need the owner's local data.

## Known gaps / good next tasks
- README screenshots in `docs/img/` show the old look; regenerate (render with Textual's `export_screenshot` + Chrome).
- Hub: click-to-select on the diagram (today you pick parts from the list); chapters for "Your words" open after the typing step.
- Remove the dead Hindi/Hinglish/"student" strings from the older labs (`text.py` registers still carry them; they are never shown).
- The Brain strip on the course dashboard shows a finished pass; animate it from a real pass if wanted.
- Publish to PyPI as `mona-llm` (`docs/DISTRIBUTION.md`); run a fresh-virtualenv install first.
- After the v2 results: write a short comparison and decide on a Hugging Face release (needs the owner's go-ahead).
- Licence check: the weights are MIT but some chat data is CC BY-SA.
