"""Smoke test: the app starts, and every screen opens and draws without raising.

Run:  python -m pytest tests -q        (or:  python tests/test_ui_smoke.py)
It needs MONA's weights (models/mona/ or ~/.mona/assets). Settings are redirected to a temp folder.
"""
import asyncio
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from mona.ui import state as state_mod  # noqa: E402

state_mod.STATE_PATH = Path(tempfile.mkdtemp()) / "state.json"      # never touch the real ~/.mona

from mona.ui.app import MonaApp  # noqa: E402
from mona.ui.screens import open_lab  # noqa: E402

STAGES = ["lm", "data", "tokens", "embeddings", "attention", "layers", "next", "training", "chat", "evals", "rag", "beyond"]
EXPLORE = ["mysteries", "incidents", "course", "journey", "budget", "tour", "compare", "story", "teacher", "badges"]


async def _run():
    app = MonaApp()
    async with app.run_test(size=(150, 46)) as pilot:
        await pilot.pause(0.5)
        await pilot.press("escape")                       # leave the welcome screen
        for _ in range(120):                              # wait for the model to load
            if app.gb is not None:
                break
            await pilot.pause(0.5)
        assert app.gb is not None, "model did not load"
        assert app.state.lang == "en" and app.state.depth in ("simple", "engineer")
        home = app.screen
        for depth in ("simple", "engineer"):              # every screen, at both depths
            app.state.depth = depth
            for sid in STAGES:
                app.push_screen(open_lab(sid))
                await pilot.pause(0.6)
                await pilot.press("escape")
                await pilot.pause(0.2)
            for sid in EXPLORE:
                getattr(home, f"action_{sid}")()
                await pilot.pause(0.6)
                await pilot.press("escape")
                await pilot.pause(0.2)
        await pilot.press("d")                            # depth key on the home screen
        await pilot.press("f1")                           # glossary
        await pilot.pause(0.3)
        await pilot.press("escape")
        await pilot.press("f8")                           # code view
        await pilot.pause(0.3)


def test_every_screen_opens():
    asyncio.run(_run())


if __name__ == "__main__":
    test_every_screen_opens()
    print("ok: every screen opened at both depths")
