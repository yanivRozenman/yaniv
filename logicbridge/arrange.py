"""Section-based arrangement: turn loops into a track with structure.

An arrangement is a list of Sections. Each one names which layers play, how
much energy it has, and how open the filter is across it. The engine builds
every layer per section, merges it into one Track per instrument (so Logic gets
one long region per instrument), and writes filter/expression automation as CC.
"""
from dataclasses import dataclass, field

from . import patterns as P
from .midi import Track, CUTOFF, EXPRESSION
from .theory import note

LAYERS = ("drums", "bass", "chords", "pad", "lead", "perc", "fx")
TONAL = ("bass", "chords", "pad", "lead")

PATCHES = {"drums": None, "bass": "trance_bass", "chords": "stab",
           "pad": "pad", "lead": "hypersaw_lead", "perc": None, "fx": None}

LEVELS = {"drums": 1.0, "bass": 0.95, "chords": 0.5, "pad": 0.45,
          "lead": 0.4, "perc": 0.35, "fx": 0.3}


@dataclass
class Section:
    name: str
    bars: int
    layers: tuple = ()
    energy: float = 0.8              # 0..1, drives which variant of a layer plays
    cutoff: tuple = (0.8, 0.8)       # (start, end) 0..1, written as CC74
    fill: str = None                 # "riser" | "snare" | "both", in the last 2 bars
    crash: bool = False              # crash on this section's downbeat


# i - VI - III - VII, the backbone of most trance
DEGREES = [0, -4, 3, -2]

TEMPLATES = {
    "club": [
        Section("intro",     8,  ("drums",),                              0.30, (0.35, 0.50)),
        Section("groove",    8,  ("drums", "bass"),                        0.55, (0.50, 0.62)),
        Section("build",     8,  ("drums", "bass", "chords"),              0.72, (0.40, 1.00), fill="riser"),
        Section("drop",      16, ("drums", "bass", "chords", "lead"),      1.00, (0.90, 0.90), crash=True),
        Section("breakdown", 16, ("pad", "lead"),                          0.35, (0.28, 0.75)),
        Section("rebuild",   8,  ("drums", "bass", "pad"),                 0.75, (0.45, 1.00), fill="both"),
        Section("drop2",     16, ("drums", "bass", "chords", "lead", "perc"), 1.00, (0.95, 0.95), crash=True),
        Section("outro",     8,  ("drums", "bass"),                        0.50, (0.70, 0.25)),
    ],
    "short": [
        Section("intro",  4,  ("drums",),                         0.35, (0.40, 0.55)),
        Section("build",  4,  ("drums", "bass"),                  0.70, (0.45, 1.00), fill="riser"),
        Section("drop",   16, ("drums", "bass", "chords", "lead"), 1.00, (0.90, 0.90), crash=True),
        Section("outro",  4,  ("drums", "bass"),                  0.50, (0.75, 0.30)),
    ],
    "extended": [
        Section("intro",     16, ("drums",),                              0.28, (0.30, 0.50)),
        Section("groove",    16, ("drums", "bass"),                        0.55, (0.50, 0.65)),
        Section("build",     8,  ("drums", "bass", "chords"),              0.72, (0.40, 1.00), fill="riser"),
        Section("drop",      32, ("drums", "bass", "chords", "lead"),      1.00, (0.90, 0.90), crash=True),
        Section("breakdown", 24, ("pad", "lead"),                          0.32, (0.25, 0.78)),
        Section("rebuild",   16, ("drums", "bass", "pad", "chords"),       0.78, (0.45, 1.00), fill="both"),
        Section("drop2",     32, ("drums", "bass", "chords", "lead", "perc"), 1.00, (0.95, 0.95), crash=True),
        Section("outro",     16, ("drums", "bass"),                        0.45, (0.70, 0.20)),
    ],
}


def progression(key, octave=2, qualities=("min9", "maj9", "maj9", "maj9")):
    root = note(f"{key}{octave}")
    return [(root + d, qualities[i % len(qualities)]) for i, d in enumerate(DEGREES)]


def bass_roots(key, octave=1):
    root = note(f"{key}{octave}")
    return [root + d for d in DEGREES]


# ----------------------------------------------------------------- layer builders
def _drums(key, bars, energy):
    if energy < 0.42:
        return P.kick_only(bars)
    return P.four_on_floor(bars, hats=energy > 0.45,
                           claps_from=0 if energy > 0.65 else None)


def _bass(key, bars, energy):
    return P.offbeat_bass(bass_roots(key), bars,
                          octave_push=energy > 0.6,
                          sixteenths=(1, 3) if energy > 0.5 else (),
                          vel=int(88 + 24 * energy))


def _chords(key, bars, energy):
    beats = (0.5, 2.5) if energy > 0.6 else (0.5,)
    return P.chord_stabs(progression(key), bars, beats=beats,
                         vel=int(80 + 22 * energy))


def _pad(key, bars, energy):
    return P.pad(progression(key), bars, vel=int(60 + 24 * energy))


def _lead(key, bars, energy):
    return P.arp(f"{key}3", "minor", bars, rate=0.25 if energy > 0.5 else 0.5,
                 octaves=2, shape="updown", vel=int(78 + 20 * energy))


def _perc(key, bars, energy):
    return P.rolling_toms(bars)


BUILDERS = {"drums": _drums, "bass": _bass, "chords": _chords,
            "pad": _pad, "lead": _lead, "perc": _perc}


# ------------------------------------------------------------------------ engine
@dataclass
class Arrangement:
    tracks: list
    parts: list
    bpm: float
    bars: int
    sections: list
    key: str

    def section_bar(self, name):
        """Starting bar of a named section, for previewing just that part."""
        at = 0
        for s in self.sections:
            if s.name == name:
                return at
            at += s.bars
        raise KeyError(name)

    def summary(self):
        rows, at = [], 0
        for s in self.sections:
            rows.append(f"  bar {at:>3}  {s.name:<10} {s.bars:>2} bars  "
                        f"energy {s.energy:.2f}  {','.join(s.layers)}")
            at += s.bars
        return "\n".join(rows)


def build(key="F", bpm=138.0, template="club"):
    sections = TEMPLATES[template]
    masters = {}

    def master(layer, channel=0):
        if layer not in masters:
            masters[layer] = Track(layer.capitalize(), channel=channel)
        return masters[layer]

    at_bar = 0
    for sec in sections:
        start = at_bar * 4.0
        span = sec.bars * 4.0

        for layer in sec.layers:
            part = BUILDERS[layer](key, sec.bars, sec.energy)
            if sec.fill and layer in ("drums", "bass"):
                # the move that makes a drop land: everything cuts out for the
                # last bar of a build, leaving only the riser and the roll
                cut_from = (sec.bars - 1) * 4.0
                part.notes = [n for n in part.notes
                              if not (n.start >= cut_from
                                      and (layer == "bass" or n.pitch == P.KICK))]
            master(layer, part.channel).merge(part, start)

        # filter + expression moves, so the section actually breathes
        for layer in sec.layers:
            if layer not in TONAL:
                continue
            t = master(layer)
            lo, hi = sec.cutoff
            if abs(hi - lo) < 0.02:
                t.set_cc(CUTOFF, lo * 127, start)
                t.set_cc(EXPRESSION, (0.55 + 0.45 * sec.energy) * 127, start)
            else:
                t.ramp(CUTOFF, start, start + span, lo * 127, hi * 127,
                       steps=max(8, sec.bars * 2), curve=1.6 if hi > lo else 0.8)
                t.ramp(EXPRESSION, start, start + span,
                       (0.45 + 0.35 * sec.energy) * 127, 127 if hi > lo else 70,
                       steps=max(8, sec.bars))

        if sec.fill in ("riser", "both"):
            fill_at = start + max(0.0, span - 8.0)
            master("fx", 9).merge(P.riser_hats(2), fill_at)
        if sec.fill in ("snare", "both"):
            master("drums", 9).merge(P.snare_roll(2), start + max(0.0, span - 8.0))
        if sec.crash:
            master("drums", 9).merge(P.crash_hits([0]), start)

        at_bar += sec.bars

    order = [l for l in LAYERS if l in masters]
    tracks = [masters[l] for l in order]
    parts = [(masters[l], PATCHES[l], LEVELS[l]) for l in order]
    return Arrangement(tracks, parts, bpm, at_bar, list(sections), key)
