"""Note names, scales and chords. Everything speaks MIDI note numbers."""

NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
_ALIAS = {"DB": "C#", "EB": "D#", "GB": "F#", "AB": "G#", "BB": "A#"}

SCALES = {
    "major":            [0, 2, 4, 5, 7, 9, 11],
    "minor":            [0, 2, 3, 5, 7, 8, 10],
    "harmonic_minor":   [0, 2, 3, 5, 7, 8, 11],
    "phrygian":         [0, 1, 3, 5, 7, 8, 10],
    "dorian":           [0, 2, 3, 5, 7, 9, 10],
    "lydian":           [0, 2, 4, 6, 7, 9, 11],
    "minor_pentatonic": [0, 3, 5, 7, 10],
}

CHORDS = {
    "min":   [0, 3, 7],
    "maj":   [0, 4, 7],
    "dim":   [0, 3, 6],
    "sus2":  [0, 2, 7],
    "sus4":  [0, 5, 7],
    "min7":  [0, 3, 7, 10],
    "maj7":  [0, 4, 7, 11],
    "min9":  [0, 3, 7, 10, 14],
    "maj9":  [0, 4, 7, 11, 14],
    "5":     [0, 7],
}


def note(name):
    """'F#2' / 'Db1' / 'A3' -> MIDI number. C3 = 60, matching Logic's display."""
    s = name.strip()
    i = len(s)
    while i > 0 and (s[i - 1].isdigit() or s[i - 1] == "-"):
        i -= 1
    pitch, octave = s[:i].upper(), int(s[i:])
    pitch = _ALIAS.get(pitch, pitch)
    if pitch not in NAMES:
        raise ValueError(f"unknown note {name!r}")
    return NAMES.index(pitch) + (octave + 2) * 12


def name_of(midi):
    return f"{NAMES[midi % 12]}{midi // 12 - 2}"


def scale(root, mode="minor", octaves=3, start_octave=0):
    """Ascending scale note numbers starting at `root` (name or MIDI number)."""
    r = note(root) if isinstance(root, str) else root
    steps = SCALES[mode]
    return [r + 12 * (start_octave + o) + s for o in range(octaves) for s in steps]


def chord(root, quality="min", inversion=0, voicing=None):
    r = note(root) if isinstance(root, str) else root
    tones = [r + i for i in CHORDS[quality]]
    for _ in range(inversion):
        tones = tones[1:] + [tones[0] + 12]
    if voicing == "spread":          # drop the root an octave, open up the top
        tones = [tones[0] - 12] + tones[1:]
    elif voicing == "close":
        tones = [t - 12 if t - tones[0] >= 12 else t for t in tones]
    return tones


def transpose(notes, semitones):
    return [n + semitones for n in notes]


def quantize_to_scale(pitch, root, mode="minor"):
    """Snap a pitch to the nearest degree of the scale, keeping its octave region."""
    r = note(root) if isinstance(root, str) else root
    degrees = SCALES[mode]
    rel = (pitch - r) % 12
    oct_base = pitch - rel
    best = min(degrees, key=lambda d: abs(d - rel))
    return oct_base + best
