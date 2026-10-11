# MONA Lab: plan

> **Goal:** help anyone, from a school student to a curious adult to a developer, *understand how an LLM
> works* by playing with a real one, step by step, in their own language.
> **MONA** (the model we are training) is the **specimen** the learner dissects, not the end product.
> **MONA Lab** is the product: an interactive, visual, playful terminal environment.
> This is a draft for your review. Nothing in it is built yet.

---

## 1. What makes it different

| Most LLM tutorials | MONA Lab |
|---|---|
| Slides, static diagrams, toy numbers | **A real model, real numbers.** Every chart comes from MONA's actual weights, activations and training logs |
| English only | **English, Hindi and Hinglish** for every explanation, and the model itself speaks all three. Built for India's students first |
| Read, then (maybe) code | **Play → See → Build**: try it, look inside, then read the ~20 lines of code that do it |
| A finished model appears from nowhere | **The real build story**: MANAS v1 overfitting, the data cleaning, the tokenizer fairness numbers, the resume bug the pilot caught, MONA's actual loss curves. Learners relive how a model was really made |
| Needs a GPU / cloud / API key | **Runs on any laptop, offline.** MONA-Tiny (11M) for CPU-only machines, MONA-M (110M) with a GPU |
| Passive | **Predict-then-reveal** games, challenges, quests, badges, and a sandbox |

**One-line pitch:** *"An LLM you can open up and play with: in your terminal, in your language."*

---

## 2. Who it's for

**Primary audience: college students and developers.** It must also stay approachable for school students.

| Learner | What they get | Depth |
|---|---|---|
| **College student** (primary) | Attention, embeddings, training, evals, RAG with real internals | **Student mode** (default) |
| **Developer** (primary) | The exact code behind each screen, training their own tiny model, building an eval and a RAG | **Engineer mode** |
| School student / beginner | "What is a language model?", guess the next word, see tokens and probabilities | **Simple mode** |
| Teacher | Classroom mode, projector-friendly screens, quizzes, worksheets | Teacher mode |

Every lesson has these **3 depth levels × 3 languages**, switchable at any time.

**Plain-language rule:** no technical term appears without a one-line plain explanation the first time
(e.g. "**embedding**: the list of numbers MONA uses to represent a word"). Technical names are
introduced *after* the learner has seen the thing, never before. Formulas only in Engineer mode.

---

## 3. The experience

### 3.1 Home screen (sketch)
```
╭─ MONA Lab ──────────────────────────────────────── EN | हिं | Hinglish ─ ⚙ ─╮
│   ◕‿◕  MONA: "Namaste! I'm a 110M-parameter language model.                 │
│            Want to see what happens inside me when you type?"                │
│                                                                              │
│  THE JOURNEY OF A SENTENCE                         your progress  ███░░ 38%  │
│  ① Data ─ ② Tokens ─ ③ Embeddings ─ ④ Attention ─ ⑤ Layers ─ ⑥ Next word    │
│     ✓          ✓           ●              ○              ○           ○       │
│  ⑦ Training ─ ⑧ Chat tuning ─ ⑨ Evals ─ ⑩ RAG ─ ⑪ Beyond                   │
│                                                                              │
│  [S] Story mode   [L] Labs   [P] Playground   [C] Chat with MONA   [Q] Quiz  │
│  🏅 Token Tamer   🏅 Attention Detective   🔥 3-day streak                   │
╰──────────────────────────────────────────────────────────────────────────────╯
```

### 3.2 Three ways to use it
- **Story mode:** a guided path through all 11 stages, following *one sentence* the learner types as it travels through MONA, plus the real story of how MONA was built.
- **Labs:** jump to any stage and experiment freely.
- **Playground:** chat with MONA with every internal visible (tokens, probabilities, attention), and with all the knobs (temperature, top-p…).

---

## 4. The labs (the curriculum = the real LLM pipeline)

Each lab: **🎮 Play** (a game or experiment) → **🔬 See** (MONA's real internals) → **🛠 Build** (press `c` to see the exact code in `mona/`, plus a `learn/` script to run).

| # | Lab | 🎮 Play | 🔬 See (real data from MONA) | 🛠 Build |
|---|---|---|---|---|
| 0 | **What is a language model?** | *Human vs MONA*: both guess the next word of real sentences; score each other | MONA's top guesses with probabilities | The 1-line idea: P(next word given previous words) |
| 1 | **Data** | *Be the data curator*: keep or drop real web documents, then see what the cleaner decided and why | Before/after cleaning, the language mix pie, the "haye → hai" Hinglish fix, duplicates | `mona_clean.py` |
| 2 | **Tokens** | Type anything and watch it shatter into colored tokens. *Tokenizer race*: the same sentence in English / Hindi / Hinglish. *Break the tokenizer* challenge | **BPE merges animated** on your own text; token ids; fairness table (Hindi 1.33 vs English 1.48 tokens/word) | Lesson 01 BPE from scratch; train a mini tokenizer in 10 seconds |
| 3 | **Embeddings** | *Word neighbourhoods*: pick a word, see its nearest neighbours; *odd one out* game | 2D map of MONA's embedding space in the terminal (राम near सीता? king near queen?) | Embedding = a row in a 32,768 × 768 table |
| 4 | **Attention** | *Attention detective*: guess which word "तोड़ा" looks at, then reveal | Live **heatmap per layer/head** for your sentence; find special heads (previous-token, copying/induction heads) | Lesson 03 attention by hand; `Attention.forward` |
| 5 | **Layers / the forward pass** | *Watch a thought form*: step through 12 layers | **Logit lens**: MONA's best guess after each layer, sharpening layer by layer; residual stream size | RMSNorm, SwiGLU, residuals; RoPE lesson 04 |
| 6 | **Next word & sampling** | *Be the sampler*: you pick each next token; *make MONA say X* using only temperature and top-p | Probability bars that change live as you move the temperature / top-k / top-p sliders; text coloured by confidence | `generate()`; KV-cache demo |
| 7 | **Training** | *Time machine*: the same prompt answered by MONA at 0, 0.5B, 1B… 2.5B tokens, from gibberish to sentences. *Train a tiny model live* on CPU in 3 minutes | MONA's **real loss curves** per language, LR schedule (WSD), tokens/s, GPU temperature, overfitting story from MANAS v1 | Scaling-law calculator (lesson 05); `mona_pretrain.py` |
| 8 | **Chat tuning (SFT)** | *Base vs Chat*: the same question to both models side by side | Chat template and **loss masking** coloured token by token; how 7,747 Tulsidas pairs taught it to explain verses | Lesson 06 loss masking; `mona_sft.py` |
| 9 | **Evals** | *Make your own exam*: write 5 questions, run MONA, get a scorecard. *Spot the cheat* (data contamination) | Bits-per-byte per language; benchmark results; where MONA fails and why | `mona_eval.py`; how real benchmarks work (MMLU, HellaSwag) |
| 10 | **RAG** | *Ask without vs with a library*: watch hallucination disappear when MONA can look things up | Chunking, retrieval scores, which passages were found, the final prompt that MONA sees | A mini RAG over Tulsidas + Wikipedia in ~60 lines |
| 11 | **Beyond** | *Shrink MONA*: quantize to 8-bit and 4-bit, compare size vs quality; *give MONA a calculator* (tool use) | Memory, speed, quality trade-offs; how agents call tools | Quantization and tool-use code |

---

## 5. Playful layer

- **Predict-then-reveal:** before every reveal, the learner makes a guess ("Will Hindi or English need more tokens?"). Guessing first is proven to make things stick.
- **Quests and badges:** e.g. *Token Tamer* (break the tokenizer), *Attention Detective* (find a previous-token head), *Temperature Tamer* (make MONA repeat itself, then make it go wild), *Exam Maker* (build your own eval).
- **MONA as the guide:** a small character with a face (`◕‿◕`, `◔_◔` when confused) who talks in the learner's chosen language and reacts to experiments.
- **Challenges with real answers:** each is checked against the real model, not a script.
- **Progress, streaks and a "learning passport"** saved locally (no account, no internet needed).
- **Easter eggs:** MONA quoting Tulsidas, the "haye → hai" story, the 3 AM resume bug.

---

## 6. Ideas that make it genuinely useful

1. **Hindi-first LLM education.** Almost all LLM teaching material is English-only. Full Hindi/Hinglish explanations, with a model that itself speaks Hindi, opens this to millions of students.
2. **Concept ↔ code bridge:** on any screen, press `c` to see the exact lines of MONA's code that produced what you're looking at.
3. **Real build diary as content:** our actual logs, bugs and decisions, turned into "behind the scenes" cards.
4. **Teacher mode:** large-font projector layout, a quiz generator, printable worksheets, and a lesson-plan per lab (45-minute class format).
5. **Bring your own text:** paste a paragraph from a textbook and see it tokenized, attended to and predicted.
6. **Compare with big models (optional):** if Ollama is installed, run the same prompt through a bigger model and see what scale buys. Compare tokenizers of Llama/Qwen with MONA's.
7. **Export:** any experiment → a Python script or Jupyter notebook that reproduces it.
8. **Glossary everywhere:** every technical word is clickable, with a 1-line explanation in all three languages.
9. **Works offline on weak laptops:** MONA-Tiny on CPU; all lessons cached.
10. **Romanized display mode:** if a terminal can't draw Devanagari well, every Hindi word can be shown in Latin script (भारत → bhaarat) with one key, so nobody is locked out.

---

## 7. Technical design

```
mona_lab/
├── engine/          "glass-box" API over MONA (no UI code)
│   ├── inspect.py   tokenize, forward with hooks: attention maps, hidden states, logit lens
│   ├── sample.py    step-by-step generation with full probability tables
│   ├── embed.py     nearest neighbours, 2D projection
│   ├── timemachine  load training snapshots, compare outputs over training
│   ├── evals.py     run question sets, score, report
│   └── rag.py       chunk, index (BM25 first, embeddings later), retrieve, build prompt
├── ui/              Textual app: one screen per lab, shared widgets
│   └── widgets/     token chips, heatmap, probability bars, sliders, loss chart, MONA avatar
├── content/         lessons as Markdown/YAML in en / hi / hinglish, 3 depth levels; quizzes; quests
└── progress.py      local JSON: completed labs, badges, streaks
```
- **Terminal only, always.** No web version: the terminal *is* the experience.
- **Framework:** [Textual](https://textual.textualize.io/) (Python terminal UI: mouse, widgets, layouts, animation) + Rich for formatting. *(Exact versions to verify before building.)*
- **One command:** `pip install mona-lab` → `mona` opens the Lab; `mona chat`, `mona train-tiny`, `mona eval`.
- **Models:** downloaded on first run from Hugging Face (MONA-Tiny ~45 MB, MONA-M ~440 MB) or used locally.
- **Model change needed:** fast attention doesn't expose attention weights, so the engine adds an "inspection" path that computes them explicitly, used only for visualization.
- ⚠️ **Known risk: Devanagari in terminals.** Hindi vowel signs render badly in some terminals and fonts. Mitigations (terminal only): a **display check on first run** (show a test word, ask "does this look right?") with fix steps per terminal (Windows Terminal + Nirmala UI, macOS Terminal, GNOME Terminal), and the **romanized display mode** as a fallback.

---

## 8. Phases

| Phase | What ships | Rough effort |
|---|---|---|
| **0. Foundation** | Engine API (tokens, probabilities, attention, logit lens), Textual shell, home screen, language/depth toggle, progress | 2–3 sessions |
| **1. MVP (4 labs)** | ② Tokens, ⑥ Next word & sampling, ④ Attention, ⑦ Training time machine (MONA's real snapshots) + Playground chat | 4–6 sessions |
| **2. The full journey** | ⓪ What is an LM, ① Data, ③ Embeddings, ⑤ Logit lens, ⑧ Chat tuning, ⑨ Evals, Story mode, quests and badges | 6–8 sessions |
| **3. Beyond** | ⑩ RAG, ⑪ Quantization and tools, Ollama comparison, teacher mode, export | 5–7 sessions |
| **4. Release** | `pip install mona-lab`, models on Hugging Face, docs, demo GIFs/videos, translations reviewed by native speakers | 2–3 sessions |

MONA-M's training (running now) is not blocked by any of this. Phase 0–1 can start on MONA-Tiny and the pilot model, then switch to MONA-M once it's done.

---

## 9. How we'll know it works
- A beginner can explain "tokens, attention, next-word prediction" in their own words after Story mode (a short quiz at start and end measures it).
- A student can build an eval and a mini RAG in the Lab without writing code.
- Testers in Hindi and English both finish the MVP labs without help.
- It runs on a CPU-only laptop.

---

## 10. Decisions (made 2026-10-11)
1. **Name:** MONA Lab.
2. **Audience:** college students and developers first; approachable for school students too (plain-language rule, §2).
3. **Terminal only, always.**
4. **MVP labs:** ② Tokens, ⑥ Next word & sampling, ④ Attention, ⑦ Training time machine.
5. **License:** MIT (simplest, most permissive; standard for open educational tools).

---
*Draft prepared 2026-10-11. MONA-M pretraining continues in the background throughout.*
