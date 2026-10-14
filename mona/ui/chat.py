"""Talk with MONA: a real chat with MONA-Chat, running on this computer, one token at a time."""
import threading

from rich.text import Text
from textual import work
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical, VerticalScroll
from textual.screen import Screen
from textual.widgets import Input, Static

from . import chatmodel

NOTE = ("MONA-Chat is small (110 million numbers) and runs on your own computer. She is fluent but often wrong, "
        "and that is part of the lesson. Ask her anything.")


class ChatScreen(Screen):
    BINDINGS = [Binding("escape", "back", "back"), Binding("f5", "watch", "watch how MONA works")]

    def compose(self) -> ComposeResult:
        with Vertical(id="chat-box"):
            yield Static(id="chat-note")
            with VerticalScroll(id="chat-scroll"):
                yield Static(id="chat-log")
            yield Static(id="chat-status")
            yield Input(id="chat-input")
        yield Static(id="keys", classes="keys")

    def on_mount(self):
        self.history, self.shown, self.busy, self.alive, self.fresh = [], [], False, True, False
        self.cancel = threading.Event()
        self.query_one("#chat-note", Static).update(Text(NOTE, style="#9399b2"))
        self.query_one("#chat-input", Input).placeholder = "Say something to MONA and press Enter…"
        self.query_one("#keys", Static).update("Enter send   /reset new chat   F5 watch how MONA works   F8 the real code   Esc back")
        self.query_one("#chat-scroll").border_title = "Conversation"
        if not chatmodel.available():
            self.set_status("MONA-Chat's weights were not found, so she cannot chat yet.", "#f38ba8")
            self.query_one("#chat-input", Input).disabled = True
            return
        self.set_status("Waking MONA up… (loading her chat weights, once)", "#f9e2af")
        self.query_one("#chat-input", Input).disabled = True
        self.load()

    @work(thread=True, exclusive=True, group="chatload")
    def load(self):
        chatmodel.get_model()
        self.app.call_from_thread(self._ready)

    def _ready(self):
        if not self.alive:
            return
        self.set_status("Ready. Everything runs on this computer.", "#a6e3a1")
        box = self.query_one("#chat-input", Input)
        box.disabled = False
        box.focus()

    # ── transcript ────────────────────────────────────────────────────────────
    def set_status(self, text, colour="#9399b2"):
        self.query_one("#chat-status", Static).update(Text(text, style=colour))

    def draw(self):
        out = Text()
        for who, text in self.shown:
            out.append("You   " if who == "user" else "MONA  ", style="bold #f9e2af" if who == "user" else "bold #cba6f7")
            out.append(text + "\n\n", style="#cdd6f4")
        self.query_one("#chat-log", Static).update(out)
        self.query_one("#chat-scroll", VerticalScroll).scroll_end(animate=False)

    def on_input_submitted(self, event: Input.Submitted):
        text = event.value.strip()
        event.input.value = ""
        if not text or self.busy:
            return
        if text == "/reset":
            self.history, self.shown = [], []
            self.draw()
            self.set_status("New conversation.", "#a6e3a1")
            return
        self.history.append({"role": "user", "content": text})
        self.fresh = chatmodel.is_identity_question(text) and len(self.history) > 1
        self.shown += [("user", text), ("mona", "")]
        self.busy = True
        self.cancel.clear()
        event.input.disabled = True
        self.set_status("MONA is thinking…", "#f9e2af")
        self.draw()
        self.reply(self.history[-1:] if self.fresh else list(self.history))

    @work(thread=True, exclusive=True, group="chatreply")
    def reply(self, history):
        model, tok = chatmodel.get_model(), self.app.gb.tok if self.app.gb else None
        if tok is None:
            from .. import tokenizer as T
            tok = T.load()

        def on_text(text, n, secs):
            self.app.call_from_thread(self._writing, text, n, secs)
        text, n, secs = chatmodel.stream_reply(model, tok, history, on_text, cancel=self.cancel, max_new=220)
        self.app.call_from_thread(self._done, text, n, secs)

    def _writing(self, text, n, secs):
        if not self.alive:
            return
        self.shown[-1] = ("mona", text + "▌")
        self.set_status(f"MONA is writing…  {n / secs:.0f} tokens/s on your computer" if secs > 0 else "MONA is writing…", "#89dceb")
        self.draw()

    def _done(self, text, n, secs):
        if not self.alive:
            return
        self.shown[-1] = ("mona", text or "…")
        self.history.append({"role": "assistant", "content": text})
        self.busy = False
        note = "  ·  asked fresh: she was only taught to answer this as a first message" if getattr(self, "fresh", False) else ""
        self.set_status(f"Done: {n} tokens in {secs:.1f} s ({n / max(secs, 1e-6):.0f} tokens/s, on your own hardware){note}", "#a6e3a1")
        box = self.query_one("#chat-input", Input)
        box.disabled = False
        box.focus()
        self.draw()

    def action_watch(self):
        from .zoom import ZoomScreen
        self.app.push_screen(ZoomScreen())            # on top, so Esc comes back to the chat

    def action_back(self):
        self.cancel.set()
        self.app.pop_screen()

    def on_unmount(self):
        self.alive = False
        self.cancel.set()
