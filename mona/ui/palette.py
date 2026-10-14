"""Ctrl+P command palette: search every lesson, experiment and command without remembering shortcuts."""
from functools import partial

from textual.command import DiscoveryHit, Hit, Hits, Provider

from .text import STAGES


def _home(app):
    """Return to the home screen (the palette can be opened from anywhere) and give it back."""
    from .screens import HomeScreen
    for _ in range(12):
        if isinstance(app.screen, HomeScreen):
            break
        app.pop_screen()
    return app.screen


def _open_stage(app, sid):
    from .screens import open_lab
    _home(app)
    app.push_screen(open_lab(sid))


def _open_explore(app, sid):
    getattr(_home(app), f"action_{sid}")()


def commands(app):
    """(label, help, callback) for everything the palette can do."""
    from .screens import EXPLORE
    items = []
    for i, (sid, name, *_rest) in enumerate(STAGES):
        items.append((f"Stage {i} · {name}", "Open this stage", partial(_open_stage, app, sid)))
    for sid, key, name, *_rest in EXPLORE:
        if sid:
            items.append((name, f"Explore further · key {key}", partial(_open_explore, app, sid)))
    items += [("Switch depth (Simple / Engineer)", "F3", app.action_cycle_depth),
              ("Show the code behind this screen", "F8", app.action_code),
              ("Explain a word (glossary)", "F1", app.action_glossary),
              ("Change what MONA calls you", "F7", app.action_address),
              ("Export screenshot, report and script", "F9", app.action_export)]
    return items


class MonaCommands(Provider):
    async def discover(self) -> Hits:
        for label, help_, callback in commands(self.app):
            yield DiscoveryHit(label, callback, help=help_)

    async def search(self, query: str) -> Hits:
        matcher = self.matcher(query)
        for label, help_, callback in commands(self.app):
            score = matcher.match(label)
            if score > 0:
                yield Hit(score, matcher.highlight(label), callback, help=help_)
