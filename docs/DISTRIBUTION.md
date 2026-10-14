# How people get MONA: packaging and distribution

**Short answer.** MONA does **not** install from a zip. People install it as **one pip package**:

```bash
pip install mona-llm      # 222 KB of code
mona                      # first run downloads the model (~0.5 GB, once), then the app opens
```

This document explains why, compares the options, and walks through publishing step by step.

---

## 1. Why not a zip?

GitHub's **Code → Download ZIP** gives only the *source code*. It does **not** include the weights, the tokenizer, the logs or the data (they are many GB and are not in git, on purpose). A person who unzips it can't run the app, and they'd have to install dependencies by hand.

So "a single package" means:

| Piece | Size | Where it lives | How it arrives |
|---|---|---|---|
| **Code** (the app, model, labs) | 222 KB | PyPI (`pip install mona-llm`) | `pip` |
| **Weights + demo data** (base MONA, MONA-Chat, tokenizer, logs, small licence-clean data samples) | ~0.5 GB | Hugging Face `JayF14/MONA` → `assets/` | downloaded **automatically on first run** into `~/.mona/assets` (`mona/assets.py`) |

The weights can't ride inside the pip package: PyPI limits a file to 100 MB by default, and each weights file is about 220 MB. Keeping them separate also means the code can be updated without re-downloading the model.

The package itself was built and checked while writing this document: `mona_llm-0.1.0-py3-none-any.whl` (222 KB) and the source archive (198 KB) both pass `twine check`, and an install into a clean folder runs in "installed mode" (`DEV=False`, assets under `~/.mona/assets`).

### A bug fixed while preparing this
`regex`, `pyarrow` and `huggingface_hub` are needed to run the app (stage 0, the Data and RAG stages, the first-run download), but they were listed only in the optional `train` extra. A plain `pip install` would have crashed on stage 0. They are now core dependencies in `pyproject.toml`.

### The name `mona` is taken
PyPI already has an unrelated project called `mona` ("Calculation framework", versions up to 0.2.6). The published name is therefore **`mona-llm`** (also `mona-ai` and `mona-lab` are free). The command people type stays **`mona`**.

---

## 2. The options

| # | Option | Command for the user | Good for | Weak spot |
|---|---|---|---|---|
| **A** | **pip from GitHub** (works today) | `pip install git+https://github.com/JayD108/Mona.git` | testing, early users | no versions; slow to update |
| **B** | **PyPI** ⭐ recommended | `pip install mona-llm` | everyone | needs a PyPI account (free) |
| **C** | **pipx / uv** (isolated, no environment clashes) ⭐ | `pipx install mona-llm` or `uv tool install mona-llm` | non-developers; keeps `mona` on PATH | user needs pipx or uv first |
| **D** | **One-line installer script** | `irm …/install.ps1 \| iex` (Windows) · `curl … \| sh` (Mac/Linux) | school students: it installs uv, then MONA | you maintain 2 small scripts |
| **E** | **Docker image** | `docker run -it mona` | classrooms with locked-down PCs | Docker is a big install itself (~2 GB image) |
| **F** | **Offline bundle** | copy a folder, `MONA_HOME=… mona` | schools without internet | you must prepare the folder |
| **G** | Standalone `.exe` (PyInstaller) | double-click | no Python at all | **not recommended**: PyTorch makes it 1–2 GB, slow to start, antivirus false alarms, and the terminal app still needs a console |

**Recommended combination: B + C + D.** Publish to PyPI (B), tell people to use `pipx`/`uv` (C), and give school users a one-line script (D). Add E or F only if a classroom needs it.

---

## 3. Publishing to PyPI step by step (Option B)

You do this once; later releases take about two minutes.

### 3.1 Before you publish
1. **The Hugging Face release must be public and finished** (`runs/mona_m/RELEASED` exists). Otherwise the first run, which downloads the weights, will fail for everyone.
2. **Fix the README images for PyPI.** PyPI does not resolve relative paths such as `docs/img/home.svg`. Use absolute URLs, and prefer **PNG** files (SVG served from `raw.githubusercontent.com` often doesn't display). For example `https://github.com/JayD108/Mona/raw/main/docs/img/home.png`. You can render PNGs from the SVGs with Chrome: `chrome --headless --screenshot=home.png --window-size=1629,1120 file:///…/home.svg`.
3. Set the version in `pyproject.toml` (`version = "0.1.0"`). Every upload needs a new version number.
4. Test locally (this is what was done for this document):
   ```bash
   pip install build twine
   python -m build                 # makes dist/*.whl and dist/*.tar.gz
   twine check dist/*              # both must say PASSED
   pip install dist/*.whl          # try it in a fresh environment, then run: mona
   ```

### 3.2 Create the accounts (free)
- https://test.pypi.org and https://pypi.org. Turn on two-factor authentication.

### 3.3 Dry run on TestPyPI
```bash
twine upload --repository testpypi dist/*
pip install --index-url https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple mona-llm
```
(`--extra-index-url` is needed because PyTorch and the other dependencies come from the real PyPI.)

### 3.4 The real upload (two ways)

**Manual** (simplest the first time): create an API token on pypi.org → *Account settings → API tokens*, then
```bash
twine upload dist/*
```
When asked for a username type `__token__`, and paste the token as the password. Never commit the token.

**Automatic, safer** (no token to store): *Trusted Publishing*. On pypi.org → *Publishing* → add a pending publisher for owner `JayD108`, repository `Mona`, workflow `release.yml`. Then add `.github/workflows/release.yml`:

```yaml
name: Release
on:
  release:
    types: [published]
jobs:
  pypi:
    runs-on: ubuntu-latest
    environment: pypi
    permissions:
      id-token: write          # lets PyPI trust this workflow, no password needed
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: "3.11" }
      - run: python -m pip install build && python -m build
      - uses: pypa/gh-action-pypi-publish@release/v1
```
After that, **creating a GitHub Release publishes to PyPI by itself**.

### 3.5 Every later release
1. Bump `version` in `pyproject.toml` (for example `0.1.1`).
2. `git tag v0.1.1 && git push --tags`, then create a GitHub Release from the tag.
3. The workflow (or `twine upload`) publishes it. Users run `pip install -U mona-llm`.

---

## 4. Installing for users (what to put in the README)

```bash
# Easiest, isolated, puts `mona` on your PATH (recommended)
pipx install mona-llm          # or:  uv tool install mona-llm
mona

# Plain pip
pip install mona-llm
mona                           # if the command isn't found:  python -m mona
```

Two things worth telling users:
- **Python 3.10 or newer** is required.
- **PyTorch size.** On Linux, `pip` may pull the 2.5 GB GPU build. To get the small CPU build (everything in MONA works on CPU): `pip install torch --index-url https://download.pytorch.org/whl/cpu`, then `pip install mona-llm`.

---

## 5. One-line installers (Option D)

These install `uv` (a fast Python tool manager from Astral) and then MONA. Keep them in the repo, for example `scripts/install.ps1` and `scripts/install.sh`, so people can read them before running them.

**Windows** (`install.ps1`):
```powershell
if (-not (Get-Command uv -ErrorAction SilentlyContinue)) { irm https://astral.sh/uv/install.ps1 | iex }
uv tool install mona-llm --python 3.11
Write-Host "Done. Open a NEW terminal and type: mona"
```

**macOS / Linux** (`install.sh`):
```bash
#!/bin/sh
command -v uv >/dev/null 2>&1 || curl -LsSf https://astral.sh/uv/install.sh | sh
uv tool install mona-llm --python 3.11
echo "Done. Open a new terminal and type: mona"
```

Then the README can say: `irm https://raw.githubusercontent.com/JayD108/Mona/main/scripts/install.ps1 | iex`. (Piping a script into the shell means trusting its source; that is why the scripts stay small and readable in the repo.)

---

## 6. Docker (Option E, for classrooms)

`Dockerfile`:
```dockerfile
FROM python:3.11-slim
RUN pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu \
 && pip install --no-cache-dir mona-llm
ENV LANG=C.UTF-8 TERM=xterm-256color
ENTRYPOINT ["mona"]
```
```bash
docker build -t mona .
docker run -it -v mona-data:/root/.mona mona      # the volume keeps the 0.5 GB download between runs
```
The `-it` flags are required: the app is interactive.

---

## 7. Offline / no-internet classroom (Option F)

On one computer with internet:
```bash
pip download mona-llm -d wheels/                  # all packages, for another machine
pip install huggingface_hub
huggingface-cli download JayF14/MONA --include "assets/*" --local-dir mona_home
```
Copy `wheels/` and `mona_home/` to the other machines, then:
```bash
pip install --no-index --find-links wheels mona-llm
set MONA_HOME=C:\path\to\mona_home\assets        # Windows   (Mac/Linux: export MONA_HOME=…)
mona
```
`MONA_HOME` tells MONA where its weights are, so nothing is downloaded.

---

## 8. Checklist before announcing

- [ ] Hugging Face repo `JayF14/MONA` is **public** and has `assets/` (the release step does this after the checks pass)
- [ ] `pip install` in a **fresh** virtual environment works, and `mona` opens, on Windows and one Linux/Mac machine
- [ ] First run really downloads the assets (delete `~/.mona` and try)
- [ ] README images use absolute URLs (PNG) so they show on PyPI
- [ ] `twine check dist/*` says PASSED
- [ ] The version number is new
- [ ] Licence: code and weights MIT; data credits are in the Hugging Face `NOTICE.md`
- [ ] Tested on a terminal with the Nirmala UI / Mangal font on Windows (Hindi letters), or romanized mode (R)

## 9. Common problems

| Symptom | Cause and fix |
|---|---|
| `mona: command not found` | The scripts folder isn't on PATH. Use `python -m mona`, or install with `pipx`/`uv tool`. |
| "download failed" on first run | No internet, or the Hugging Face repo isn't public yet. Retry, or use the offline bundle (§7). |
| Install takes very long on Linux | It is downloading the GPU build of PyTorch. Use the CPU wheel (§4). |
| Hindi letters look broken | Terminal font. Windows Terminal → Settings → profile → Appearance → Font face: **Nirmala UI**. Or press **R** for romanized Hindi. |
| `pip install mona` installs something else | That is a different, unrelated project. The right name is **`mona-llm`**. |
