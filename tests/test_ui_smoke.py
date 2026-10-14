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
EXPLORE = ["talk", "zoom", "words", "mysteries", "incidents", "course", "journey", "budget", "tour", "compare", "story", "teacher", "badges"]


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
        await pilot.press("escape")                                   # Esc = back to what I was doing: the choice
        await pilot.pause(0.3)
        assert type(app.screen).__name__ == "WelcomeScreen" and app.screen.phase == "begin"
        await pilot.press("down")
        await pilot.press("enter")                                    # "See how MONA works"
        await pilot.pause(0.6)
        assert type(app.screen).__name__ == "ZoomScreen"
        await pilot.press("escape")                                   # and back to the choice again
        await pilot.pause(0.3)
        assert type(app.screen).__name__ == "WelcomeScreen" and app.screen.phase == "begin"
        await pilot.press("escape")                                   # leaving the choice: the home screen
        await pilot.pause(0.3)
        assert type(app.screen).__name__ == "HomeScreen"
        await pilot.press("escape")                                   # the root: stays put (and says so)
        await pilot.pause(0.2)
        assert type(app.screen).__name__ == "HomeScreen"


async def _zoom_lesson():
    """The whole lesson plays through, every scene, then back out with the lesson marked done."""
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
        from mona.ui.zoom import SCENES
        for scene in range(len(SCENES) - 1):                          # Enter dives into the next scene
            await pilot.press("enter")
            assert await _wait(pilot, lambda: zoom.trans is None and zoom.i == scene + 1, 5), f"stuck at scene {scene}"
            await pilot.pause(0.3)
        await pilot.press("enter")                                    # the last scene: leave
        await pilot.pause(0.5)
        assert "zoom" in app.state.completed and type(app.screen).__name__ == "HomeScreen"


def test_identity_questions_are_asked_fresh():
    from mona.ui import chatmodel
    assert chatmodel.is_identity_question("what is your name?") and chatmodel.is_identity_question("Who are you")
    assert not chatmodel.is_identity_question("hello") and not chatmodel.is_identity_question("what is 2+2")
    assert "MONA" in chatmodel.SYSTEM


def test_intro_writes_welcome_then_chat():
    asyncio.run(_intro_to_chat())


def test_zoom_lesson_plays_through():
    asyncio.run(_zoom_lesson())


async def _words_lesson():
    """Type a sentence, follow it through all 12 pages, with pause / play and speed working along the way."""
    os.environ["MONA_REDUCED_MOTION"] = "1"
    app = MonaApp()
    async with app.run_test(size=(150, 46)) as pilot:
        await pilot.pause(0.5)
        await pilot.press("escape")
        assert await _wait(pilot, lambda: app.gb is not None, 90)
        app.screen.action_words()
        await pilot.pause(0.6)
        lesson = app.screen
        assert type(lesson).__name__ == "PathScreen" and lesson.asking
        for ch in "my cat sat":
            await pilot.press("space" if ch == " " else ch)
        await pilot.press("enter")
        assert await _wait(pilot, lambda: lesson.D is not None, 60), "lesson data did not load"
        assert lesson.D["text"] == "my cat sat" and lesson.D["n"] == len(lesson.D["ids"])
        from mona.ui.lesson import SPEEDS
        start = lesson.speed
        await pilot.press("plus")
        assert lesson.speed == SPEEDS[SPEEDS.index(start) + 1]
        await pilot.press("minus")
        assert lesson.speed == start
        await pilot.press("space")                                    # pause: the scene clock stops
        assert lesson.paused
        await pilot.pause(0.3)
        t0 = lesson.t
        await pilot.pause(0.6)
        assert lesson.t == t0
        await pilot.press("enter")                                    # Next still works while paused, and the dive completes
        assert await _wait(pilot, lambda: lesson.i == 1 and lesson.trans is None, 8), "paused dive did not finish"
        assert lesson.paused and lesson.t == 0.0
        await pilot.press("space")                                    # play again
        assert not lesson.paused
        for scene in range(1, len(lesson.SCENES) - 1):
            await pilot.press("enter")
            assert await _wait(pilot, lambda: lesson.i == scene + 1 and lesson.trans is None, 8), f"stuck at page {scene + 1}"
        assert lesson.i == 11
        await pilot.press("escape")                                   # Esc goes back to the typing step
        await pilot.pause(0.3)
        assert lesson.asking and type(app.screen).__name__ == "PathScreen"
        await pilot.press("escape")
        await pilot.pause(0.3)
        assert type(app.screen).__name__ == "HomeScreen"


def test_words_lesson_with_speed_and_pause():
    asyncio.run(_words_lesson())


if __name__ == "__main__":
    test_welcome_animation_can_be_skipped()
    test_identity_questions_are_asked_fresh()
    test_intro_writes_welcome_then_chat()
    test_zoom_lesson_plays_through()
    test_words_lesson_with_speed_and_pause()
    test_every_screen_opens()
    print("ok: welcome skips; MONA writes her welcome and chats; both lessons play with pause and speed; every screen opens at both depths")
