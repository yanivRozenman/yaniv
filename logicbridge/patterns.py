"""Genre building blocks. Each returns a Track, positioned from beat 0."""
import random
from .midi import Track
from .theory import note, scale, chord

# GM drum map (Logic's Drum Machine Designer and Ultrabeat follow it)
KICK, SNARE, CLAP, CHAT, OHAT, PHAT = 36, 38, 39, 42, 46, 44
RIDE, CRASH, TOM_LO, TOM_HI = 51, 49, 45, 50


def four_on_floor(bars=4, vel=118, hats=True, claps_from=2):
    """The trance/house engine room: kick on every beat, open hat on every offbeat."""
    t = Track("Drums", channel=9)
    for b in range(bars):
        for beat in range(4):
            at = b * 4 + beat
            t.add(KICK, at, 0.5, vel)
            if hats:
                t.add(OHAT, at + 0.5, 0.33, 88)
                t.add(CHAT, at + 0.25, 0.12, 54)
                t.add(CHAT, at + 0.75, 0.12, 62)
        if claps_from is not None and b >= claps_from:
            t.add(CLAP, b * 4 + 1, 0.5, 100)
            t.add(CLAP, b * 4 + 3, 0.5, 100)
    return t


def offbeat_bass(roots, bars=4, octave_push=True, sixteenths=(1, 3), vel=104):
    """Rolling offbeat eighths — the other half of the trance engine.
    `roots` is one root per bar, cycled: ['F1','Db1','Ab1','Eb1']."""
    t = Track("Bass")
    roots = [note(r) if isinstance(r, str) else r for r in roots]
    for b in range(bars):
        root = roots[b % len(roots)]
        for beat in range(4):
            at = b * 4 + beat
            t.add(root, at + 0.5, 0.42, vel)
            if beat in sixteenths:
                t.add(root, at + 0.75, 0.20, int(vel * 0.82))
        if octave_push:
            t.add(root + 12, b * 4 + 3.5, 0.40, int(vel * 0.92))
    return t


def chord_stabs(progression, bars=4, beats=(0.5, 2.5), dur=1.2, vel=96, voicing=None):
    """Offbeat supersaw stabs. `progression` is [(root, quality), ...] per bar."""
    t = Track("Chords")
    for b in range(bars):
        root, quality = progression[b % len(progression)]
        tones = chord(root, quality, voicing=voicing)
        for at in beats:
            for i, p in enumerate(tones):
                t.add(p, b * 4 + at, dur, vel - i * 4)
    return t


def pad(progression, bars=4, vel=72, voicing="spread"):
    """One sustained chord per bar."""
    t = Track("Pad")
    for b in range(bars):
        root, quality = progression[b % len(progression)]
        for i, p in enumerate(chord(root, quality, voicing=voicing)):
            t.add(p, b * 4, 4.0, vel - i * 3)
    return t


def arp(root, mode="minor", bars=4, rate=0.25, octaves=2, shape="updown",
        start_octave=2, vel=92, gate=0.85):
    """Sixteenth-note arpeggio — rate 0.25 = 16ths, 0.5 = 8ths."""
    t = Track("Arp")
    notes = scale(root, mode, octaves=octaves, start_octave=start_octave)
    if shape == "down":
        notes = notes[::-1]
    elif shape == "updown":
        notes = notes + notes[-2:0:-1]
    elif shape == "random":
        notes = notes[:]
    steps = int(bars * 4 / rate)
    for i in range(steps):
        p = random.choice(notes) if shape == "random" else notes[i % len(notes)]
        accent = 12 if i % 4 == 0 else 0
        t.add(p, i * rate, rate * gate, min(127, vel + accent))
    return t


def acid_line(root, mode="minor", bars=4, rate=0.25, density=0.72, seed=None,
              octave_jump=0.18, vel=100):
    """303-style line: mostly stepwise, occasional octave jumps and rests."""
    rng = random.Random(seed)
    t = Track("Acid")
    notes = scale(root, mode, octaves=1, start_octave=1)
    idx = 0
    for i in range(int(bars * 4 / rate)):
        if rng.random() > density:
            continue
        idx = max(0, min(len(notes) - 1, idx + rng.choice([-2, -1, -1, 0, 1, 1, 2])))
        p = notes[idx] + (12 if rng.random() < octave_jump else 0)
        slide = rate * (1.6 if rng.random() < 0.22 else 0.55)   # long = glide in Logic
        t.add(p, i * rate, slide, vel if i % 4 == 0 else int(vel * 0.8))
    return t


def rolling_toms(bars=4, rate=0.5, vel=88):
    t = Track("Toms", channel=9)
    for i in range(int(bars * 4 / rate)):
        t.add(TOM_LO if i % 4 < 2 else TOM_HI, i * rate, rate * 0.6,
              vel if i % 2 == 0 else vel - 18)
    return t


def riser_hats(bars=2, vel_from=50, vel_to=118):
    """Accelerating hats for a build — halves the rate each bar."""
    t = Track("Build Hats", channel=9)
    at, rate, n = 0.0, 0.5, 0
    total = bars * 4
    while at < total:
        f = at / total
        t.add(CHAT, at, rate * 0.5, int(vel_from + (vel_to - vel_from) * f))
        n += 1
        if n % 8 == 0 and rate > 0.0625:
            rate /= 2
        at += rate
    return t


def snare_roll(bars=2, start_rate=0.5, end_rate=0.0625, vel_from=60, vel_to=120):
    """Accelerating snare into a drop. Halves the step length as it goes."""
    t = Track("Snare Roll", channel=9)
    total = bars * 4
    at, rate = 0.0, start_rate
    while at < total:
        f = at / total
        t.add(SNARE, at, rate * 0.6, int(vel_from + (vel_to - vel_from) * f))
        at += rate
        if f > 0.45 and rate > end_rate:
            rate /= 2
    return t


def crash_hits(at_bars, vel=104):
    """Single crashes on the downbeat of each listed bar (bar numbers, 0-based)."""
    t = Track("Crash", channel=9)
    for b in at_bars:
        t.add(CRASH, b * 4, 2.0, vel)
    return t


def kick_only(bars=4, vel=118):
    """Stripped intro groove: kick and a quiet closed hat, nothing else."""
    t = Track("Drums", channel=9)
    for b in range(bars):
        for beat in range(4):
            at = b * 4 + beat
            t.add(KICK, at, 0.5, vel)
            t.add(CHAT, at + 0.5, 0.12, 44)
    return t
