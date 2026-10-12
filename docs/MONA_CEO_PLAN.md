# MONA app, phase 5: "You are the CEO"

Source: `my_plan.txt` (user, 2026-10-12). Approved scope: everything below. PyPI later; the README uses the GitHub install.

| # | Feature | Where | Key |
|---|---|---|---|
| 1 | **CEO welcome.** Asked on every launch: Sir / Ma'am / your name / custom, last choice pre-selected (Enter keeps it). The address is used everywhere: home greeting, every lab briefing, notifications. EN / हिं / Hinglish (`{name} जी`). | `ui/welcome.py`, `state.py`, `app.tr` | F7 change |
| 2 | **Lab Tour.** How a frontier lab works: the model lifecycle + 7 teams (Research, Data, Infra, Pretraining, Post-training, Evals & Safety, Launch). Each team briefs the CEO: what real labs do, what MONA did, and which stage to open. | `ui/tour.py` | O |
| 3 | **Easy language.** A glossary popup for any term, available everywhere. | `ui/glossary.py` | F1 |
| 4 | **Train your own model.** A guided 6-step course that really trains a tiny model on the user's laptop in minutes: data → tokenizer → model → train (live loss + samples) → generate → evaluate. Each step shows the real command for the full-size MONA. | `ui/course.py`, `engine/minitrain.py` | G |
| 5 | **README.** A curiosity hook, install commands, the first 10 minutes, and an FAQ. | `README.md` | |
| 6 | **Training journey.** MONA's real story from start to end, built from its logs: data, tokenizer, nights of training, incidents, loss and samples at each stage, chat tuning, eval, release. | `ui/journey.py`, `mona/journey.json` | J |
| 7a | **Incident room.** The real crises from MONA's training as CEO decisions (heat, copyright, false watchdog alarm, charger, bad Hinglish, stalled downloads). | `ui/incidents.py` | I |
| 7b | **Budget planner.** Choose GPU-hours and model size, then see Chinchilla-predicted quality, time and cost vs MONA / GPT-3 / Llama. | `ui/budget.py` | P |
| 7c | **Morning memo.** The home greeting gets a lab memo of the day and progress. | home | |
| 7d | **CEO certificate.** After all 12 stages, a certificate with the user's name (exportable with F9). | `ui/story.py` | B |

The home screen gets a **CEO desk** column next to the 12 stages.
All features are CPU-only app code, so they're safe while training runs.
