# Understanding MONA: the whole project in one document

This guide explains everything in this project: what MONA is, how it was built step by step, what each
file does, how training runs unattended, how the release works, and what someone gets when they install it.
Read it top to bottom once. After that, each section works as a reference.

---

## 1. MONA in one paragraph

MONA is a **small language model built from scratch**: 110 million numbers (parameters) learned from
2.5 billion tokens of English, Hindi, Hinglish and Awadhi text. Nothing was borrowed from another model.
That includes the data cleaning, the tokenizer, the architecture, pretraining, chat tuning and evaluation,
all written and run on one laptop GPU. MONA is not meant to compete with ChatGPT. It is a **specimen**.
The **MONA app** is an interactive AI learning lab in the terminal: **understand AI from the inside**.
Learners look inside the model while it thinks, run experiments on it, investigate its mistakes, read
the real code behind each idea (F8), and train a small model of their own. The app is in English, at two depths
(Simple / Engineer); MONA herself works in English, हिंदी, Hinglish and Awadhi.

> Big models (GPT, Llama, Gemma) are built the same way, just 100–10,000× larger. Every idea you see
> in MONA is one of theirs too.

---

## 2. The big picture

```
 raw text ──► clean ──► tokenizer ──► token shards ──► PRETRAIN ──► base model (MONA)
 (Hugging Face)                                         2.5B tokens          │
                                                                             ▼
                          chat examples (125K) ──────────────────────► CHAT TUNE ──► MONA-Chat
                                                                             │
                                                                             ▼
                                                     EVALUATE ──► RELEASE (Hugging Face + pip)
                                                                             │
                                                                             ▼
                                                     the MONA app: 12 stages that show all of the above
```

| # | Stage | Script | Output | Time on this laptop |
|---|---|---|---|---|
| ① | Download data | `pipeline/mona_download.py` | `data/raw/` | ~2 h (network) |
| ② | Clean | `pipeline/mona_clean.py` | `data/mona_clean/<lang>/` | ~30 min |
| ③ | Train tokenizer | `pipeline/mona_tokenizer.py` | `models/mona/tokenizer.json` | ~15 min |
| ④ | Tokenize | `pipeline/mona_tokenize.py` | `data/mona_tokens/*.bin` | ~40 min |
| ⑤ | Pretrain | `scripts/mona_pretrain.py` | `runs/mona_m/final.pt` | ~19 h (one long night + a day) |
| ⑥ | Build chat data | `pipeline/mona_build_sft.py` | `data/mona_sft/train.jsonl` | ~5 min |
| ⑦ | Chat tuning (SFT) | `scripts/mona_sft.py` | `runs/mona_m_chat/model.pt` | ~1 h |
| ⑧ | Evaluate | `scripts/mona_eval.py` | `runs/mona_m/eval.txt` | ~5 min |
| ⑨ | Release | `scripts/mona_release.py` | Hugging Face `JayF14/MONA` | ~20 min upload |

Steps ⑤ to ⑨ run **by themselves** as a job queue (`scripts/mona_run_all.py`). See §8.

---

## 3. Data: what MONA learned from

### Sources and licences

| Language | Source | Licence | Tokens available |
|---|---|---|---|
| English | FineWeb-Edu (educational web pages) | ODC-By | 1.60 B |
| Hindi | AI4Bharat Sangraha, verified Hindi | CC-BY-4.0 | 0.97 B |
| Hinglish | Sangraha synthetic, romanized Hindi (`hin_Latn`) | CC-BY-4.0 | 0.13 B |
| Awadhi | Tulsidas's verse (Ramcharitmanas etc.) | **public domain** | 0.25 M |
| Chat (SFT) | smol-smoltalk, Aya, Hindi Wikipedia-derived Q&A | Apache-2.0 / CC BY-SA | 124,485 conversations (+2,540 held out) |

### Copyright rule

Tulsidas (16th century) is public domain. The **Gita Press Hindi commentary** (Hanuman Prasad Poddar) is
probably still under copyright. It was in the earliest training data, so it was **removed at 0.8 B tokens**.
From then on only the verse is used. The release script also **scans** everything it publishes for words
that appear only in the commentary (`श्रीरघुनाथजी`, `कहते हैं`, `अर्थात्‌` …), and it refuses to publish if it finds them.
The file with commentary was moved to `data/private/` and is never used or shared.

### Cleaning (`mona/textclean.py`, `pipeline/mona_clean.py`)
- Unicode normalisation, so the same Hindi letter is always stored the same way.
- Documents shorter than 200 characters, or with too little real text, are dropped.
- Wrong-script text is dropped, for example English pages inside the Hindi data.
- **Hinglish fix:** the synthetic Hinglish had odd spellings. About 70 common words are corrected to the
  way people actually type them (`HINGLISH_FIX`).

### The mix (what share of each training batch comes from each language)

| | English | Hindi | Hinglish | Awadhi |
|---|---|---|---|---|
| Main phase (first 85%) | 55% | 40% | ~5% | 0.03% |
| Final "decay" phase (last 15%) | 55% | 40% | ~4.9% | 0.1% (4× more) |

Awadhi is tiny on purpose. There are only 246K tokens of verse, and repeating them too often would make
MONA memorise instead of learn the style. About 3 passes is the safe amount.

---

## 4. Tokenizer: how MONA reads

A model cannot read letters. It reads **tokens**, which are pieces of words, each with a number.
MONA uses **byte-level BPE** (the same family as GPT and Llama):
1. Start with raw bytes, so any text in any script can be read and nothing is ever "unknown".
2. Find the most common pair of neighbouring pieces in the data and merge it into a new piece.
3. Repeat until there are **32,768** pieces.

The Hindi rule: a regex with `\p{M}` keeps Hindi vowel signs (मात्रा) attached to their letter, so `कि` is
never split into `क` + `ि`.

**Fairness check:** how many tokens one word costs (lower is cheaper and better).

| Hindi | English | Hinglish | Awadhi |
|---|---|---|---|
| 1.33 | 1.48 | 1.55 | 1.77 |

Many big English-first models spend 4–8 tokens per Hindi word. MONA's tokenizer was trained on Hindi
too, so Hindi is cheap.

Special tokens: `<|endoftext|> <|pad|> <|system|> <|user|> <|assistant|> <|end|>` (the last four are for chat).

---

## 5. The model: what is inside MONA

MONA is a **Llama-style decoder-only transformer** (`mona/model.py`, ~170 lines you can read).

```
token ids ─► Embedding (32,768 × 768) ─► [ Block × 12 ] ─► RMSNorm ─► Output (tied to Embedding) ─► next-token probabilities

Block = RMSNorm ─► Attention (12 heads, RoPE positions) ─► + ─► RMSNorm ─► SwiGLU feed-forward (768→2048→768) ─► +
```

| Setting | Value | In simple words |
|---|---|---|
| Layers | 12 | 12 rounds of "look around, then think" |
| Width (d_model) | 768 | every token is a list of 768 numbers |
| Attention heads | 12 | 12 different "ways of looking" per layer |
| Feed-forward | 2048 | the "thinking" part inside each layer |
| Context | 1024 tokens | how much text it can see at once |
| Vocabulary | 32,768 | how many different tokens it knows |
| Parameters | **110.1 M** (85.0 M without the embedding table) | |

Modern ingredients and why they're used:
- **RMSNorm:** keeps numbers at a stable size so training doesn't blow up.
- **RoPE:** tells the model word order by rotating vectors (lesson: `learn/04_rope.py`).
- **SwiGLU:** a better feed-forward layer, used by Llama.
- **Flash attention (SDPA):** the same maths, much faster and lighter on memory.
- **Tied embeddings:** the input and output tables share weights, which saves 25 M parameters.
- **KV-cache:** while writing, MONA remembers earlier work instead of redoing it (shown in the Beyond lab).

---

## 6. Pretraining: how MONA learned language

The task is always the same: **guess the next token**. MONA is shown real text, guesses, gets graded
(the "loss"), and every weight is nudged to guess better. That happens 2.5 billion times.

| Setting | Value |
|---|---|
| Tokens | 2.5 B (about 23 tokens per parameter, close to the "Chinchilla" rule of ~20) |
| Batch | 524,288 tokens per step (8 sequences × 1024 tokens × 64 accumulation) |
| Steps | 4,769 |
| Optimiser | AdamW (β 0.9 / 0.95), weight decay 0.1, gradient clip 1.0 |
| Precision | bfloat16 |
| Learning rate | **WSD:** warm up over the first 1%, hold at 6e-4, then decay to 5% over the last 15% |
| Speed | ~38–45 K tokens/s on an RTX 5080 Laptop GPU |

**Why WSD (warmup–stable–decay)?** The long flat part can be stopped or extended at any time. The final
decay is where loss drops sharply, and the data mix is "annealed" there (more of the rare languages).

**Loss so far** (lower is better):

| Point | Loss |
|---|---|
| Start | about 10.4 (random guessing over 32K tokens) |
| 0.8 B tokens | about 3.45 |
| 1.58 B tokens | about 3.25 |
| **2.5 B tokens (final)** | **3.07** training loss; held-out: English 3.15, Hindi 3.06, Hinglish 2.90, Awadhi 5.44 |

Losses per language on held-out text are logged every 250 steps (`runs/mona_m/eval_log.csv`). At every
evaluation MONA also writes four sample sentences (`runs/mona_m/samples.txt`). That file is MONA's
"growing up diary", and the app's Time Machine lab plays it back.

**Checkpoints and snapshots:**
- `ckpt.pt` is saved every 30 minutes and holds everything needed to resume.
- `snap_0.5B.pt`, `snap_1.0B.pt`, … are frozen copies of MONA's brain at each half-billion tokens.

---

## 7. Chat tuning (SFT): from text-continuer to assistant

A pretrained model only continues text. Ask "What is the capital of India?" and it might write three more
questions. **Supervised fine-tuning** teaches a *format*: conversations written as

```
<|system|>You are MONA…<|end|><|user|>question<|end|><|assistant|>answer<|end|>
```

- **Loss masking:** MONA is graded only on the assistant's words, never on the question
  (lesson: `learn/06_loss_masking.py`).
- **Data:** 124,485 training conversations (2,540 more are held out for validation).

  | Source | Conversations |
  |---|---|
  | English (smol-smoltalk) | 78,173 |
  | Hindi Q&A | 25,000 |
  | Tulsidas verse-completion | 12,545 |
  | Hinglish | 10,000 |
  | Hindi Aya | 1,147 |
  | "Who are you?" identity | 160 |

- **Settings:** learning rate 1e-4 with cosine decay, 2 epochs, conversations packed into 1,025-token rows.
- **Output:** `runs/mona_m_chat/model.pt` (**MONA-Chat**)

---

## 8. Running unattended: the guards

Training took about 19 hours on a laptop, so it has to survive heat, a loose charger, crashes and
reboots without anyone watching. The approach was reused from the earlier APALA project.

| Guard | File | What it does |
|---|---|---|
| **Job queue** | `scripts/mona_run_all.py` | Runs pretrain → chat data → chat tuning → eval → release in order. Each step has a "done" file, so after any interruption it skips finished work. |
| **Heat limiter** | inside `scripts/mona_pretrain.py` | Above 77°C it pauses ~0.03 s after each ~0.18 s of GPU work, never more than 15% of the time. |
| **Power guard** | `ops/mona_power_guard.ps1` | Charger unplugged → freezes training in place (no progress lost) and resumes it on charger. A 20-minute cool-down break every 6 hours. |
| **Watchdog** | `ops/mona_watchdog.py` | Training dead for 5 min, or GPU idle for 30 min → restart from the last checkpoint (max 3 times per 3 h). |
| **Startup** | `ops/MONA_resume.cmd` (in the Windows Startup folder) | After a reboot everything starts again by itself. |
| **Checkpoints** | `runs/mona_m/ckpt.pt` every 30 min | A crash loses at most 30 minutes. |
| **Windows power settings** | | Closing the lid on charger does nothing; sleep and hibernate are off. |

**What you can do:**

| You want to | Do this |
|---|---|
| Check progress | `python -m scripts.mona_status` |
| Pause for the day | create the empty file `runs\mona_m\STOP` (a checkpoint is saved, then it stops) |
| Continue | delete `runs\mona_m\STOP` (the watchdog restarts it within ~5 min) |

**Logs** are in `runs/logs/`:
- `mona_pretrain.out` (every 10 steps)
- `mona_run_all.log` (queue)
- `mona_watchdog.log`
- `mona_power_guard.log`

---

## 9. Evaluation: how good is MONA?

`scripts/mona_eval.py` writes `runs/mona_m/eval.txt`:
- **Bits per byte (bpb)** per language: how surprised the model is by new text. Lower is better. Unlike loss,
  bpb is fair across tokenizers, so MONA can be compared with other models. (The MANAS v1 row in `eval.txt` is indicative only: it was scored on different Awadhi text, and MONA saw the Awadhi verse about 3 times in training, so treat that comparison with care.)
- **Multiple-choice by likelihood:** which answer does MONA find most probable?
- **Chat checks:** does MONA-Chat answer in the right language, and know its name?

The Evals lab in the app shows all of this, plus why benchmarks can mislead.

---

## 10. Release: what gets published and how the package looks

`scripts/mona_release.py` runs **checks first** and publishes only if every check passes:
1. `final.pt` and the chat model exist.
2. The evaluation numbers are sensible (bpb between 0.3 and 2.0).
3. MONA-Chat gives real, non-empty replies.
4. The copyright scan finds no commentary text.

Then it builds a **licence-clean bundle** in `data/release/` and uploads it to Hugging Face `JayF14/MONA`.
The repo is made public only after a successful upload.

### On Hugging Face (`huggingface.co/JayF14/MONA`)

```
JayF14/MONA
├── README.md            model card: what MONA is, numbers, limits, data + licences, copyright note
├── NOTICE.md            attributions for every dataset
├── LICENSE              MIT (code + weights)
├── config.json          model shape (layers, width, heads, vocab …)
└── assets/              exactly the folders the app reads (≈0.5 GB)
    ├── models/mona/
    │   ├── mona.pt              base model, bfloat16 (~220 MB)
    │   └── tokenizer.json       32K byte-level BPE
    ├── runs/mona_m/             train_log.csv, eval_log.csv, samples.txt, eval.txt  (Time Machine, Evals)
    ├── runs/mona_m_chat/model.pt    MONA-Chat, bfloat16 (~220 MB)
    ├── data/mona_tokens/        200K held-out tokens per language (LM game, evals, quantization)
    ├── data/processed/tulsidas_verse_strict.txt   public-domain verse (RAG library)
    ├── data/raw/…               a few hundred sample documents per language (Data lab)
    └── data/mona_sft/train.jsonl    40 chat examples per source (Chat-tuning lab)
```

### The pip package (`pyproject.toml`)

```
mona/                      ← what `pip install` puts on your computer (code only, < 1 MB)
├── paths.py               where files live (this repo, or ~/.mona/assets after install)
├── assets.py              first run: downloads assets/ from Hugging Face, once
├── config.py              model sizes, data mix
├── model.py               the transformer
├── tokenizer.py           train / load / chat template
├── data.py                training batches
├── textclean.py           cleaning rules
├── engine/                the "glass box"
│   ├── glassbox.py        tokens, next-word probabilities, attention, logit lens
│   ├── minitrain.py       train-your-own course: a tiny model, same code
│   ├── lessons.py         BPE replay, sampling filters, head detectors, time machine
│   └── rag.py             BM25 search library
└── ui/                    the terminal app (Textual)
    ├── app.py  screens.py  text.py (EN/हिं/Hinglish)  state.py  widgets.py
    ├── welcome.py  mysteries.py  course.py  codeview.py (F8)  glossary.py (F1)
    ├── journey.py  incidents.py  budget.py  tour.py
    ├── story.py  teacher.py  exports.py
    └── labs/              one file per stage (12 stages + compare)
```

**What a user does:**

```
pip install mona                (or: pip install -e .  inside this repo)
mona
```

1. The first run downloads ~0.5 GB from Hugging Face into `~/.mona/assets`. This happens once.
2. A display check confirms Hindi letters render correctly.
3. The home screen opens with the 12 stages. Progress is saved in `~/.mona/state.json` (no account needed).

Inside this repo (development mode) nothing is downloaded. The app reads `models/`, `runs/` and `data/`
directly.

---

## 11. The MONA app

The home screen has two columns. On the left is **the learning path**: the 12 stages in four tracks. On
the right is **Explore further**: hands-on work. The greeting box suggests **Next up**; press **N** to go
there. The suggested order mixes the hands-on course in at the right moment (after stage 6, before
training).

**The learning path**

| Track | # | Stage | What you do |
|---|---|---|---|
| ① Foundations: how text becomes numbers | 0 | What is a language model? | Play "guess the next word" against MONA |
| | 1 | Data | Be the data curator: keep or drop real documents, see the cleaning rules |
| | 2 | Tokens | Peek at tokens, replay BPE merges, race languages by token cost |
| | 3 | Embeddings | Find word neighbours; see that similar words get similar numbers |
| ② Inside the model: how it thinks | 4 | Attention | See which earlier words each word looks at, per layer and head |
| | 5 | Layers | Watch the guess form layer by layer (logit lens) |
| | 6 | Next word & sampling | Turn the temperature / top-k / top-p knobs |
| ③ Learning: how it got good | 7 | Training | Time machine: MONA at 0, 0.5 B, 1 B … tokens, plus the real loss curves |
| | 8 | Chat tuning | Base MONA vs MONA-Chat on the same question; see the chat template and loss mask |
| | 9 | Evals | Bits per byte, multiple choice, why benchmarks mislead |
| ④ Beyond: using and shrinking models | 10 | RAG | Give MONA a library (Tulsidas verse, Wikipedia) and watch it look things up |
| | 11 | Beyond | Quantization (shrink MONA), tool use, KV-cache speed-up |

**Explore further**

| Key | Screen | What it teaches |
|---|---|---|
| M | Model mysteries | Debugging. 5 cases (repetition loops, questions answered with questions, confident wrong facts, weak Awadhi, token costs). Run up to 3 experiments on the real model, then name the cause; the answer explains the mechanism and the code |
| I | Training failures | 6 real problems from MONA's run (heat, copyright, false watchdog alarm, charger, bad Hinglish, stuck downloads): what would you do, what was done, and the general lesson |
| G | Train a model yourself | 7 steps that really train a ~1M-parameter model (same code as MONA) in ~2 minutes, test it against MONA, then a controlled **learning-rate experiment** (3 runs, overlaid curves) |
| J | How MONA was trained | 17 chapters from MANAS v1 to release, with real dates, the loss at each moment, and what MONA wrote then |
| P | Scaling laws explorer | Pick a compute budget and a size; see the U-shaped quality curve, time, cost, and famous models |
| O | How AI labs build models | The 7 teams of a frontier lab, what each does, what MONA's build did, and the key question each faces |
| C | Compare | MONA vs a big model in Ollama |
| S | Follow one sentence | Your sentence travels through every stage |
| T | Teacher mode | 45-minute lesson plans and printable quizzes |
| B | Progress & certificate | Badges, plus a certificate of completion with your name after all 12 stages |

**Personal, not corporate.** On every launch MONA asks what to call you (your name, Sir or Ma'am). The
last answer is pre-selected, so Enter keeps it. She uses it in the greeting and at the top of each stage
("💡 Asha, here's the idea:"), in Hindi as "Asha जी". The home screen also shows one **"Did you know?"**
fact a day.

**Global keys:**
- **F1** explain any word (glossary with everyday comparisons)
- **F3** depth (Simple / Engineer)
- **F7** change your name / form of address
- **F8 show the code**: the real MONA source behind the current screen, read live with `inspect`, with a plain-language walkthrough. Examples: Attention → `Attention.forward` + `apply_rope`, Next word → `shape` + `MONA.generate`, Evals → `bits_per_byte`
- **F9** export: a screenshot, a Markdown report, and a Python script that reproduces the experiment

Product direction and the full idea list: [`PRODUCT_BRAINSTORM.md`](PRODUCT_BRAINSTORM.md).

---

## 12. Folder map (this repository)

```
C:\LLM
├── mona/          the library + app (see §10)
├── pipeline/      ① download  ② clean  ③ tokenizer  ④ tokenize  ⑥ chat data
├── scripts/       ⑤ pretrain  ⑦ sft  ⑧ eval  ⑨ chat  status  run_all (queue)  release
├── ops/           unattended-training guards (power guard, watchdog, startup)
├── learn/         small lessons you can run: BPE, attention, RoPE, scaling laws, loss masking
├── docs/          this guide, MONA_PLAN.md (numbers), MONA_APP_PLAN.md (app design)
├── README.md  LICENSE  pyproject.toml
│
│   local only (not on GitHub, many GB):
├── data/          raw → mona_clean → mona_tokens, mona_sft, processed (verse), release (bundle)
├── models/        tokenizer.json, released mona.pt
└── runs/          mona_m (pretraining), mona_m_chat (chat), logs
```

---

## 13. Glossary (simple words)

| Word | Meaning |
|---|---|
| Token | A piece of a word. The model's "letter". |
| Parameter / weight | One learned number. MONA has 110 million of them. |
| Loss | How wrong the guesses are. Training pushes it down. |
| Bits per byte | Loss made fair across languages and tokenizers. |
| Epoch | One full pass over a dataset. |
| Learning rate | How big each nudge to the weights is. |
| Embedding | The list of numbers that stands for a token. |
| Attention | Each word deciding which earlier words matter to it. |
| Logit lens | Peeking at the model's guess after each layer, not just the last. |
| Temperature | Higher = more adventurous word choices; lower = safer. |
| SFT | Supervised fine-tuning: teaching the chat format with example conversations. |
| RAG | Retrieval-augmented generation: look things up, then answer. |
| Quantization | Storing weights with fewer bits so the model is smaller and faster. |
| Checkpoint | A saved copy of training, so it can resume after a stop. |

---

## 14. Where it came from

MONA grew out of **MANAS v1**, a 10.8M-parameter character-level model of Tulsidas's Awadhi
(`huggingface.co/JayF14/MANAS`). MONA scales that up:
- a real tokenizer instead of characters
- 10× the parameters
- four languages
- a modern architecture
- chat tuning

On top of that, a teaching app makes every step visible.

**Licence:** MIT for code and weights. Datasets keep their own licences (§3).
**Acknowledgement:** coding assisted by Claude (Anthropic).
