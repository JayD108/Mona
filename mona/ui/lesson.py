"""The shared player for MONA's animated lessons (Inside MONA, Your words step by step).

A lesson is a list of scenes. Each scene is drawn on a scaled canvas, with typed narration under it, and the camera
dives from one scene to the next. The player gives every lesson the same controls:

    Space           pause / play        + / -   faster / slower (0.25x to 3x)      R   replay the scene
    Enter or →      next scene          ←       previous scene                      Esc go back
and the same controls as clickable buttons under the picture.
"""
import time

from rich.text import Text
from textual import work
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen, Screen
from textual.widgets import Button, OptionList, Static
from textual.widgets.option_list import Option

from .canvas import LH, LW, Canvas

FPS = 30
TRANSITION = 1.1
CPS = 62                                  # narration typing speed (at 1x)
HOLD = 3.5                                # seconds to linger after a scene has finished (at 1x)
MAX_SCALE = 3                             # the drawing grows up to 3x the base size
SPEEDS = [0.25, 0.5, 0.75, 1.0, 1.5, 2.0, 3.0]

CYAN, AMBER, GREEN, PINK, TEXT, MUTE, MAUVE, LAV = ("#89dceb", "#f9e2af", "#a6e3a1", "#f5c2e7", "#cdd6f4", "#9399b2", "#cba6f7", "#b4befe")
BG = "#1e1e2e"


def _rgb(h):
    return tuple(int(h[i:i + 2], 16) for i in (1, 3, 5))


def mix(a, b, t):
    a, b = (_rgb(a) if isinstance(a, str) else a), (_rgb(b) if isinstance(b, str) else b)
    t = max(0.0, min(1.0, t))
    return "#%02x%02x%02x" % tuple(round(a[i] + (b[i] - a[i]) * t) for i in range(3))


def heat(v):
    """0 -> dark, 1 -> bright: dark blue, cyan, then amber."""
    v = max(0.0, min(1.0, v)) ** 0.6
    return mix("#313244", CYAN, v * 2) if v < 0.5 else mix(CYAN, AMBER, (v - 0.5) * 2)


def typed(s, t, t0, cps=40):
    return s[: max(0, int((t - t0) * cps))]


def ease(x):
    x = max(0.0, min(1.0, x))
    return x * x * (3 - 2 * x)


def num(n):
    return f"{n:,}"


def human(v):
    for unit, size in (("trillion", 1e12), ("billion", 1e9), ("million", 1e6)):
        if v >= size:
            x = v / size
            return f"{x:.0f} {unit}" if x >= 10 or abs(x - round(x)) < 0.05 else f"{x:.1f} {unit}"
    return num(int(v))


def word(tok):
    return tok.replace("▁", "").strip()


class ChapterScreen(ModalScreen):
    """The chapter picker: choose any chapter of a lesson and jump straight to it, without the animations in between."""
    BINDINGS = [Binding("escape", "close", "close"), Binding("c", "close", "close")]

    def __init__(self, scenes, current):
        super().__init__()
        self.scenes, self.current = scenes, current

    def compose(self) -> ComposeResult:
        with Vertical(id="chap-box"):
            yield Static("Chapters", id="chap-title")
            yield OptionList(id="chap-list")
            yield Static("↑↓ choose   Enter jump there   Esc close   (or press 1-9 inside the lesson)", classes="dim")

    def on_mount(self):
        lst = self.query_one("#chap-list", OptionList)
        for i, scene in enumerate(self.scenes):
            here = "▶" if i == self.current else " "
            lst.add_option(Option(Text.assemble((f" {here} {i + 1:>2}  ", f"bold {AMBER}"), (scene["title"], "bold")), id=str(i)))
        lst.highlighted = self.current
        lst.focus()

    def on_option_list_option_selected(self, event: OptionList.OptionSelected):
        self.dismiss(int(event.option.id))

    def action_close(self):
        self.dismiss(None)


def duration(scene, S):
    """How long a scene plays at 1x: its narration, or its animation, whichever is longer, plus a short hold."""
    return max(0.3 + len(scene["say"].format(**S)) / CPS, scene["anim"]) + HOLD


def draw_transition(prev, rect, p, caption):
    """The camera dives into `rect` (physical cells): the old scene dims, and a frame grows from the box to the whole screen."""
    c = Canvas(prev.w, prev.h)
    c.copy_from(prev)
    x, y, w, h = rect
    w, h = max(w, 5), max(h, 3)
    x, y = x - (w - rect[2]) // 2, y - (h - rect[3]) // 2
    k = ease(p)
    for echo, strength in ((0.0, 1.0), (-0.12, 0.55), (-0.24, 0.3)):
        kk = ease(max(0.0, p + echo))
        if kk <= 0:
            continue
        rx, ry = round(x * (1 - kk)), round(y * (1 - kk))
        rw, rh = round(w + (c.w - w) * kk), round(h + (c.h - h) * kk)
        if echo == 0.0:
            c.rclear(rx, ry, rw, rh)
        c.rbox(rx, ry, max(rw, 2), max(rh, 2), mix(AMBER, BG, 1 - strength))
    if caption and k > 0.25:
        text = f" {caption} "
        c.rput(max(0, (c.w - len(text)) // 2), c.h // 2, text, f"bold {AMBER}")
    return c


class LessonScreen(Screen):
    """Subclasses set SCENES and implement compute() (real data, run off the UI thread) and derive()."""
    SCENES = []
    STAGE_NAME = "Lesson"
    AUTO_FOCUS = ""                      # never focus a button: Enter and Space must reach the lesson's own keys
    BINDINGS = [Binding("escape", "back", "back"), Binding("space", "pause", "pause / play"), Binding("enter", "next", "next"),
                Binding("right", "next", "next"), Binding("left", "prev", "back"), Binding("r", "replay", "replay"),
                Binding("plus,equals_sign", "faster", "faster"), Binding("minus,underscore", "slower", "slower"),
                Binding("c", "chapters", "chapters")] + [Binding(str(n), f"chapter({n - 1})", f"chapter {n}", show=False) for n in range(1, 10)]

    # ── to override ───────────────────────────────────────────────────────────
    def compute(self, gb):
        raise NotImplementedError

    def derive(self, D):
        return {}

    def finished(self):
        self.app.pop_screen()

    def compose_extra(self):
        return ()

    # ── layout ────────────────────────────────────────────────────────────────
    def __init__(self, start=0, **kwargs):
        super().__init__(**kwargs)
        self.start_scene = start                  # the chapter to open at (the hub's parts open their own chapter)

    def compose(self) -> ComposeResult:
        with Vertical(id="zoom-box"):
            yield Static(id="zoom-stage")
            yield Static(id="zoom-say")
            yield from self.compose_extra()
            with Horizontal(id="zoom-ctl"):
                yield Button("◀ Back", id="ctl-prev")
                yield Button("− Slower", id="ctl-slower")
                yield Button("⏸ Pause", id="ctl-pause", variant="primary")
                yield Button("+ Faster", id="ctl-faster")
                yield Button("Next ▶", id="ctl-next")
                yield Button("☰ Chapters", id="ctl-chapters")
                yield Static(id="ctl-speed")
        yield Static(id="keys", classes="keys")

    def on_mount(self):
        self.D = self.S = None
        self.i, self.t, self.trans, self.paused = 0, 0.0, None, False
        self.speed_i = SPEEDS.index(1.0)
        self.last = time.monotonic()
        for button in self.query(Button):
            button.can_focus = False                 # keep the keyboard shortcuts working; the mouse can still click
        self.query_one("#keys", Static).update(
            "Space pause / play   + / − speed   Enter / → next   ← back   C chapters (or 1-9)   R replay   F8 code   Esc go back")
        self.query_one("#zoom-say").border_title = "MONA"
        self.query_one("#zoom-stage", Static).update(Text("MONA is getting ready…", style=MUTE))
        self.show_controls()
        self.timer = self.set_interval(1 / FPS, self.tick)
        self.after_mount()

    def after_mount(self):
        self.start()

    def start(self):
        if self.app.gb is not None:
            self.load()

    def on_engine_ready(self):
        if self.D is None:
            self.start()

    @work(thread=True, exclusive=True, group="lesson")
    def load(self):
        D = self.compute(self.app.gb)
        self.app.call_from_thread(self._loaded, D)

    def _loaded(self, D):
        self.D, self.S = D, self.derive(D)
        self.i, self.t, self.trans = min(self.start_scene, len(self.SCENES) - 1), 0.0, None
        self.last = time.monotonic()

    @property
    def speed(self):
        return SPEEDS[self.speed_i]

    def stage_size(self):
        """The drawing fills the stage: any size from the base 96 x 17 up to 3x that."""
        size = self.query_one("#zoom-stage").content_size
        return max(LW, min(size.width, LW * MAX_SCALE)), max(LH, min(size.height, LH * MAX_SCALE))

    # ── playback ──────────────────────────────────────────────────────────────
    def tick(self):
        now = time.monotonic()
        dt, self.last = min(now - self.last, 0.2), now
        if self.D is None:
            return
        dt *= self.speed
        if self.trans:                                       # a dive between scenes always completes, even when paused
            self.trans["t"] += dt
            if self.trans["t"] >= TRANSITION:
                self.i, self.t, self.trans = self.trans["to"], 0.0, None
        elif not self.paused:
            self.t += dt
            if self.t >= duration(self.SCENES[self.i], self.S) and self.i < len(self.SCENES) - 1:
                self.action_next()
        self.paint()

    def paint(self):
        scene = self.SCENES[self.i]
        pw, ph = self.stage_size()
        if self.trans:
            canvas = draw_transition(self.trans["prev"], self.trans["rect"], self.trans["t"] / TRANSITION, self.trans["caption"])
            say = ""
        else:
            canvas = Canvas(pw, ph)
            scene["draw"](canvas, self.t, self.D, self.S)
            say = typed(scene["say"].format(**self.S), self.t, 0.3, CPS)
        stage = self.query_one("#zoom-stage", Static)
        stage.update(canvas.render())
        state = "⏸ paused" if self.paused else f"▶ {self.speed:g}×"
        stage.border_title = f"{self.i + 1} / {len(self.SCENES)}  ·  {scene['title']}   ·   {state}"
        self.query_one("#zoom-say", Static).update(Text(say, style="#cdd6f4"))

    def show_controls(self):
        self.query_one("#ctl-pause", Button).label = "▶ Play" if self.paused else "⏸ Pause"
        self.query_one("#ctl-speed", Static).update(Text(f"  speed {self.speed:g}×", style=f"bold {AMBER}"))

    # ── actions ───────────────────────────────────────────────────────────────
    def action_next(self):
        if self.D is None or self.trans:
            return
        scene = self.SCENES[self.i]
        if self.i >= len(self.SCENES) - 1:
            self.finished()
            return
        pw, ph = self.stage_size()
        prev = Canvas(pw, ph)
        scene["draw"](prev, 1e6, self.D, self.S)
        self.trans = dict(t=0.0, to=self.i + 1, prev=prev.dimmed(), rect=scene["target"](self.D, prev), caption=scene["caption"])

    def action_prev(self):
        if self.D is not None and not self.trans and self.i > 0:
            self.i, self.t = self.i - 1, 0.0

    def action_replay(self):
        if self.D is not None and not self.trans:
            self.t = 0.0

    def action_pause(self):
        self.paused = not self.paused
        self.show_controls()

    def action_faster(self):
        self.speed_i = min(len(SPEEDS) - 1, self.speed_i + 1)
        self.show_controls()

    def action_slower(self):
        self.speed_i = max(0, self.speed_i - 1)
        self.show_controls()

    def goto(self, index):
        """Jump straight to a chapter: no dive through the chapters in between."""
        if self.D is None or not 0 <= index < len(self.SCENES):
            return
        self.i, self.t, self.trans = index, 0.0, None

    def action_chapter(self, index: int):
        self.goto(index)

    def action_chapters(self):
        if self.D is not None:
            self.app.push_screen(ChapterScreen(self.SCENES, self.i), self.goto_picked)

    def goto_picked(self, index):
        if index is not None:
            self.goto(index)

    def action_back(self):
        self.app.pop_screen()

    def on_button_pressed(self, event: Button.Pressed):
        {"ctl-prev": self.action_prev, "ctl-next": self.action_next, "ctl-pause": self.action_pause,
         "ctl-faster": self.action_faster, "ctl-slower": self.action_slower,
         "ctl-chapters": self.action_chapters}[event.button.id]()
