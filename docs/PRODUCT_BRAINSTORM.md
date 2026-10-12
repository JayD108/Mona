# MONA product brainstorm: from "CEO simulator" to "understand AI from the inside"

*2026-10-12. Written after a review of the codebase (`mona/ui/**`, `mona/engine/**`, README, docs/MONA_GUIDE.md).*

## 1. What the review found

### Features that really teach (keep, build on)
| Feature | Why it works |
|---|---|
| 12 stages (`ui/labs/*`) | Every view uses MONA's **real weights**: real tokens, real attention, real logit lens, real training logs. That is rare and valuable. |
| Train-your-own course (`ui/course.py`, `engine/minitrain.py`) | The learner actually trains a model and sees the loss fall. It is hands-on, not a simulation. |
| Journey (`ui/journey.py`) | A true training story with real numbers and real samples at each moment. |
| Incident room (`ui/incidents.py`) | The *content* is good engineering (heat, checkpoints, data licensing, false alarms). Only the "CEO decides" framing is off. |
| Budget planner (`ui/budget.py`) | Real scaling-law maths with a clear U-shaped curve. The money framing hides the real lesson. |
| F1 glossary, F9 export (report + runnable script), 3 languages × 3 depths | Strong accessibility and reproducibility. |

### What makes MONA feel like a CEO simulator (fix)
| Where | What |
|---|---|
| `ui/welcome.py` | "MONA LABS · CEO entrance", "From today you are the CEO of an AI lab" |
| `ui/screens.py` | "THE CEO DESK", "Today's lab memo" |
| `ui/app.py` | "📋 {name}, here is your briefing" on every stage |
| `ui/text.py` | "your lab's model", "your lab built from scratch" |
| `ui/tour.py` | "🎯 Your decision as CEO", "Walk the floor: each team will brief you" |
| `ui/incidents.py` | "Your call, Sir", "Great call!", "Crisis score", badge "Crisis Manager" |
| `ui/budget.py` | "Budget planner", "Your lab: MONA's two nights" |
| `ui/story.py` | "CEO certificate", "as CEO of MONA Labs" |
| README / guide | "What if you were the CEO of an AI lab?" |

### Missed educational opportunities
1. **The concepts never connect to the code.** A learner sees attention but never sees `CausalSelfAttention.forward`, even though the real code is ~15 lines.
2. **No investigations.** Everything is shown; nothing is *discovered*. Debugging a model's odd behaviour is how practitioners actually learn.
3. **No controlled experiments.** The course trains one model; it never changes one variable and compares. That is the core habit of ML research.
4. **No guided path.** 12 stages and 9 extras with no sense of "what next".
5. **Memorisation and contamination are never demonstrated**, even though MONA has a perfect real example: it saw Tulsidas's verse about 3 times.

### Must keep
Real-weights glass box, trilingual text and depths, the course, the journey, F1/F9, the Teacher mode, the unattended-training story, and the user's chosen form of address (asked at every launch; the user asked for this explicitly).

---

## 2. Ideas (scored 1–5: educational value · originality · effort (5 = easy) · feasibility · fit)

| # | Idea | Edu | Orig | Effort | Feas | Fit | Notes |
|---|---|---|---|---|---|---|---|
| 1 | **Model mysteries**: debugging cases. A symptom ("MONA repeats itself forever"), live experiments on the real model to gather evidence, then a diagnosis and the explanation | 5 | 5 | 3 | 5 | 5 | Turns watching into investigating. Uses GlassBox only. **Build.** |
| 2 | **Show me the code (F8)**: from any screen, open the exact MONA source behind it (attention → `model.py`, sampling → `generate`, BPE → `lessons.bpe_replay`), with a plain-language walkthrough | 5 | 4 | 4 | 5 | 5 | Closes the concept → code gap; `inspect.getsource` keeps it always in sync. **Build.** |
| 3 | **Controlled experiment in the course**: train the tiny model with 3 learning rates and overlay the loss curves | 5 | 3 | 4 | 5 | 5 | Teaches "change one variable". About 1 minute on CPU. **Build.** |
| 4 | **Learning path + "next up"**: four tracks (Foundations → How models learn → Build & investigate → Scale & deploy) and a suggested next step on the home screen | 4 | 2 | 5 | 5 | 5 | Cheap and removes "where do I go?" **Build.** |
| 5 | **Memorisation detector**: compare MONA's surprise on text it trained on (Tulsidas verse, ~3 passes) vs unseen text | 5 | 4 | 4 | 5 | 5 | Becomes one of the mysteries ("suspiciously good score"). **Build inside #1.** |
| 6 | **Identity reframe**: "MONA: understand AI from the inside", a welcoming non-corporate tone, "Explore further" instead of the CEO desk, "Did you know?" instead of "lab memo" | 4 | 2 | 4 | 5 | 5 | Required. **Build.** |
| 7 | **Reframe the incident room as "Training failures"**: same real cases, framed as engineering ("What would you do?"), with the root cause and the code/ops fix | 4 | 3 | 5 | 5 | 5 | **Build.** |
| 8 | **Reframe the budget planner as the "Scaling laws explorer"**: compute instead of money as the main axis | 4 | 2 | 5 | 5 | 5 | **Build.** |
| 9 | **Predict-then-reveal everywhere**: before showing a result, ask the learner to commit to a guess | 4 | 3 | 2 | 4 | 4 | Good, but needs per-lab changes. The mysteries already use it. *Later.* |
| 10 | **Watch embeddings move during training**: project the tiny model's embeddings every N steps | 4 | 4 | 2 | 3 | 4 | Striking, but a 2-D projection in a terminal is crude. *Later.* |
| 11 | **Decoding shoot-out**: greedy vs beam vs top-p on the same prompt, with repetition and diversity scores | 4 | 3 | 3 | 5 | 4 | Partly covered by stage 6 and mystery 1. *Later.* |
| 12 | **Tokenizer arena**: char-level vs 2K vs 32K BPE on the same text: tokens per word, context use, loss | 4 | 3 | 3 | 5 | 4 | Partly in course step 2. *Later.* |
| 13 | **Architecture swap**: train the tiny model with and without RoPE, or with LayerNorm instead of RMSNorm | 5 | 4 | 2 | 3 | 4 | Needs config flags in `model.py`. *Later.* |
| 14 | **Hallucination heat-map**: colour each generated token by MONA's confidence; low-confidence "facts" glow | 5 | 3 | 3 | 5 | 5 | Built as part of mystery "confident but wrong". |
| 15 | **Experiment notebook**: every experiment run is logged to `~/mona_exports/notebook.md` with settings and results | 3 | 3 | 3 | 5 | 4 | F9 covers most of it. *Later.* |

---

## 3. What was built in this round
1. **Identity**: "MONA: understand AI from the inside." New welcome (still asks how to address you, as requested, but as a friendly guide, not a CEO entrance), home "Explore further" column, "Did you know?", "Next up" suggestion, a certificate without the CEO framing, and README and guide rewritten.
2. **Model mysteries** (`ui/mysteries.py`, key **M**): 5 cases with live experiments on real MONA.
3. **Show me the code** (`ui/codeview.py`, **F8** anywhere).
4. **Course experiment**: step 7, a learning-rate comparison with overlaid curves.
5. **Learning path**: four tracks and "Next up" on the home screen.
6. **Reframes**: lab tour → "How AI labs build models", incident room → "Training failures", budget planner → "Scaling laws explorer".

## 4. Next candidates
Predict-then-reveal in every lab (#9), architecture swap (#13), tokenizer arena (#12), embedding motion (#10).
