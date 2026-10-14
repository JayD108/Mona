"""Smoke test: the app starts, and every screen opens and draws without raising.

Run:  python -m pytest tests -q        (or:  python tests/test_ui_smoke.py)
It needs MONA's weights (models/mona/ or ~/.mona/assets). Settings are redirected to a temp folder.
"""
import asyncio
import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from mona.ui import state as state_mod  # noqa: E402

state_mod.STATE_PATH = Path(tempfile.mkdtemp()) / "state.json"      # never touch the real ~/.mona

from mona.ui.app import MonaApp  # noqa: E402
from mona.ui.screens import open_lab  # noqa: E402

STAGES = ["lm", "data", "tokens", "embeddings", "attention", "layers", "next", "training", "chat", "evals", "rag", "beyond"]
EXPLORE = ["talk", "zoom", "mysteries", "incidents", "course", "journey", "budget", "tour", "compare", "story", "teacher", "badges"]


async def _run():
    os.environ["MONA_REDUCED_MOTION"] = "1"             # welcome screen shows everything at once
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
        for _ in range(60):                               # the Brain strip runs one real forward pass
            if getattr(home, "reading", None) is not None:
                break
            await pilot.pause(0.5)
        r = home.reading
        assert r is not None and len(r.confidence) == 12 and 1 <= r.lock_layer <= 12
        assert abs(sum(g.prob for g in r.final) - 1) < 1 and r.tokens_per_second > 0
        await pilot.press("e")                            # next example sentence
        await pilot.pause(1.5)
        await pilot.press("ctrl+p")                       # command palette opens a stage
        await pilot.pause(0.5)
        for ch in "layers":
            await pilot.press(ch)
        await pilot.pause(0.8)
        await pilot.press("enter")
        await pilot.pause(1.0)
        assert type(app.screen).__name__ == "LayersLab", type(app.screen).__name__
        await pilot.press("escape")
        await pilot.pause(0.3)
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


async def _welcome_animation():
    os.environ.pop("MONA_REDUCED_MOTION", None)
    app = MonaApp()
    async with app.run_test(size=(150, 46)) as pilot:
        await pilot.pause(0.3)
        welcome = app.screen
        assert type(welcome).__name__ == "WelcomeScreen" and welcome.phase == "logo"   # logo animating, choices hidden
        await pilot.press("space")                                                   # any key skips the animation
        await pilot.pause(0.3)
        assert welcome.phase == "name"
        await pilot.press("escape")                                                  # now Esc leaves the screen
        await pilot.pause(0.3)
        assert type(app.screen).__name__ == "HomeScreen"


def test_every_screen_opens():
    asyncio.run(_run())


def test_welcome_animation_can_be_skipped():
    asyncio.run(_welcome_animation())


async def _wait(pilot, cond, seconds, step=0.4):
    for _ in range(int(seconds / step)):
        if cond():
            return True
        await pilot.pause(step)
    return cond()


async def _intro_to_chat():
    """Name -> MONA writes her own welcome (real generation) -> Talk with MONA -> one real reply."""
    os.environ["MONA_REDUCED_MOTION"] = "1"
    app = MonaApp()
    async with app.run_test(size=(150, 46)) as pilot:
        await pilot.pause(0.5)
        welcome = app.screen
        assert type(welcome).__name__ == "WelcomeScreen" and welcome.phase == "name"
        await pilot.press("enter")                                    # "Sir"
        assert await _wait(pilot, lambda: welcome.phase == "begin", 120), "MONA never finished her welcome"
        assert len(welcome.written) > 60
        await pilot.press("enter")                                    # "Talk with MONA"
        await pilot.pause(0.5)
        chat = app.screen
        assert type(chat).__name__ == "ChatScreen"
        assert await _wait(pilot, lambda: not chat.query_one("#chat-input").disabled, 90), "chat model did not load"
        for ch in "hello":
            await pilot.press(ch)
        await pilot.press("enter")
        assert await _wait(pilot, lambda: len(chat.history) == 2 and not chat.busy, 120), "no reply"
        assert chat.history[-1]["content"].strip()
        await pilot.press("escape")
        await pilot.pause(0.3)
        assert type(app.screen).__name__ == "HomeScreen"


async def _zoom_lesson():
    """The whole lesson plays through: 7 scenes, then back to the home screen with the lesson marked done."""
    os.environ["MONA_REDUCED_MOTION"] = "1"
    app = MonaApp()
    async with app.run_test(size=(150, 46)) as pilot:
        await pilot.pause(0.5)
        await pilot.press("escape")
        assert await _wait(pilot, lambda: app.gb is not None, 90)
        app.screen.action_zoom()
        await pilot.pause(0.5)
        zoom = app.screen
        assert type(zoom).__name__ == "ZoomScreen"
        assert await _wait(pilot, lambda: zoom.D is not None, 30), "zoom data did not load"
        await pilot.pause(1.0)
        for scene in range(6):                                        # Enter dives into the next scene
            await pilot.press("enter")
            assert await _wait(pilot, lambda: zoom.trans is None and zoom.i == scene + 1, 5), f"stuck at scene {scene}"
            await pilot.pause(0.3)
        await pilot.press("enter")                                    # the last scene: leave
        await pilot.pause(0.5)
        assert type(app.screen).__name__ == "HomeScreen" and "zoom" in app.state.completed


def test_intro_writes_welcome_then_chat():
    asyncio.run(_intro_to_chat())


def test_zoom_lesson_plays_through():
    asyncio.run(_zoom_lesson())


if __name__ == "__main__":
    test_welcome_animation_can_be_skipped()
    test_intro_writes_welcome_then_chat()
    test_zoom_lesson_plays_through()
    test_every_screen_opens()
    print("ok: welcome skips; MONA writes her welcome and chats; zoom lesson plays; every screen opens at both depths")
