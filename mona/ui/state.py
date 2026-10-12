"""The learner's settings and progress, saved in ~/.mona/state.json (no account, works offline)."""
import json
from dataclasses import asdict, dataclass, field
from pathlib import Path

STATE_PATH = Path.home() / ".mona" / "state.json"
LANGS = ["en", "hi", "hinglish"]
DEPTHS = ["simple", "student", "engineer"]


@dataclass
class State:
    lang: str = "en"
    depth: str = "student"
    romanize: bool = False          # show Hindi in Latin letters (for terminals that can't draw Devanagari)
    display_checked: bool = False
    address: str = ""               # how MONA addresses the learner: "sir" | "maam" | "name" ("" = not chosen yet)
    user_name: str = ""
    completed: list = field(default_factory=list)   # stage ids
    badges: list = field(default_factory=list)
    records: dict = field(default_factory=dict)     # challenge high scores

    @classmethod
    def load(cls):
        try:
            data = json.loads(STATE_PATH.read_text(encoding="utf-8"))
            return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})
        except (OSError, ValueError, TypeError):
            return cls()

    def save(self):
        STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
        STATE_PATH.write_text(json.dumps(asdict(self), ensure_ascii=False, indent=2), encoding="utf-8")

    def cycle(self, attr, options):
        setattr(self, attr, options[(options.index(getattr(self, attr)) + 1) % len(options)])
        self.save()

    def complete(self, stage_id, badge=None):
        if stage_id not in self.completed:
            self.completed.append(stage_id)
        if badge and badge not in self.badges:
            self.badges.append(badge)
        self.save()
