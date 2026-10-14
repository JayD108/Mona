"""MONA's Brain: a compact, honest view of what the real model does with a sentence.

Everything shown comes from one real forward pass (`GlassBox.trace`):
  * per layer: how confident MONA already is about the next token after that layer (the logit lens)
  * the layer where her final answer first locks in and never changes again
  * the final next-token candidates with their real probabilities
  * how long the pass took, so the telemetry strip can show a measured tokens/second
Nothing here is simulated; if there is no measurement yet, the telemetry strip says N/A.
"""
import time
from dataclasses import dataclass

from rich.text import Text

from .widgets import show_piece

EXAMPLES = ["The cat sat on the mat because it",
            "The capital of India is",
            "Once upon a time, there was a",
            "Water boils at a temperature of",
            "I would like a cup of"]

LEVELS = "▁▂▃▄▅▆▇█"


@dataclass
class BrainReading:
    sentence: str
    n_tokens: int
    confidence: list        # per layer: probability of that layer's top guess at the last position
    guesses: list           # per layer: that layer's top guess (a token text)
    lock_layer: int         # 1-based layer from which the top guess never changes again
    final: list             # [Guess] the real final candidates
    seconds: float          # wall time of the pass

    @property
    def tokens_per_second(self):
        return self.n_tokens / self.seconds if self.seconds > 0 else None


def summarize(trace, seconds):
    """Turn a real `GlassBox.trace` into a BrainReading."""
    last = [layer[-1] for layer in trace.layer_guesses]            # per layer: top-k guesses at the last position
    ids = [g[0].token.id for g in last]
    lock = len(ids)
    while lock > 1 and ids[lock - 2] == ids[-1]:
        lock -= 1
    return BrainReading(sentence="", n_tokens=len(trace.tokens),
                        confidence=[g[0].prob for g in last], guesses=[g[0].token.text for g in last],
                        lock_layer=lock, final=trace.final, seconds=seconds)


def read(gb, sentence, top=5):
    """Run the real model on `sentence` and summarise the pass. Call from a worker thread."""
    t0 = time.perf_counter()
    trace = gb.trace(sentence, lens_top=top)
    reading = summarize(trace, time.perf_counter() - t0)
    reading.sentence = sentence
    return reading


def render(reading):
    """The 'Model activity' panel: 12 layer blocks, where the answer locks in, and the next-token ticker."""
    if reading is None:
        return Text("Waking MONA up…", style="#9399b2")
    top = max(reading.confidence) or 1.0
    out = Text()
    out.append(f"“{reading.sentence}”", style="bold #cdd6f4")
    out.append(f"   {reading.n_tokens} tokens\n", style="#9399b2")
    labels, bars = Text(), Text()
    for i, c in enumerate(reading.confidence, 1):
        locked = i >= reading.lock_layer
        labels.append(f"{i:>2}  ", style="bold #f9e2af" if i == reading.lock_layer else "#6c7086")
        bars.append(f"{LEVELS[min(7, int(c / top * 7.999))]}   ", style="bold #a6e3a1" if locked else "#89dceb")
    out.append("layer ", style="#6c7086")
    out.append_text(labels)
    out.append("\n      ")
    out.append_text(bars)
    out.append(f"\nbars = confidence per layer · answer locks in at layer {reading.lock_layer}\n", style="#9399b2")
    out.append("NEXT TOKEN\n", style="bold #f9e2af")
    peak = reading.final[0].prob or 1.0
    for g in reading.final[:3]:
        piece = show_piece(g.token.text)
        filled = max(1, round(18 * g.prob / peak))
        out.append(f"{piece:<10}", style="bold #cdd6f4")
        out.append("█" * filled, style="#89dceb")
        out.append("░" * (18 - filled), style="#45475a")
        out.append(f" {g.prob:5.1%}\n", style="bold")
    return out


def telemetry(gb, reading, done, total, badges):
    """The telemetry strip: only measured or known values; N/A when there is none."""
    if gb is None:
        facts = [("PARAMS", "N/A"), ("DEVICE", "N/A")]
    else:
        cfg = gb.cfg
        facts = [("PARAMS", f"{gb.model.num_params() / 1e6:.1f}M"), ("LAYERS", str(cfg.n_layers)),
                 ("CTX", f"{cfg.context:,}"), ("VOCAB", f"{cfg.vocab_size:,}"), ("DEVICE", str(gb.device).upper())]
    tps = reading.tokens_per_second if reading else None
    facts.append(("TRACE", f"{tps:,.0f} tok/s" if tps else "N/A"))
    line = Text()
    for k, v in facts:
        line.append(f"{k} ", style="#9399b2")
        line.append(f"{v}", style="bold #89dceb")
        line.append("  ·  ", style="#45475a")
    line.append("PROGRESS ", style="#9399b2")
    line.append(f"{done}/{total}", style="bold #a6e3a1")
    bar = Text("\n")
    bar.append("━" * (done * 4), style="bold #a6e3a1")
    bar.append("─" * ((total - done) * 4), style="#45475a")
    if badges:
        bar.append("   " + "  ".join(f"🏅 {b}" for b in badges), style="#f9e2af")
    line.append_text(bar)
    return line
