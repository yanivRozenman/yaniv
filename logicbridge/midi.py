"""Standard MIDI File writer. Positions and durations are in beats (floats)."""
import struct
from dataclasses import dataclass, field

TPQ = 480


@dataclass
class Note:
    pitch: int
    start: float          # beats from the top of the region
    dur: float            # beats
    vel: int = 100


@dataclass
class CC:
    controller: int       # 74 = filter cutoff, 11 = expression, 1 = mod wheel
    value: int
    at: float             # beats


# the controllers worth automating, and what Logic does with them
CUTOFF, RESONANCE, EXPRESSION, MODWHEEL, VOLUME = 74, 71, 11, 1, 7


@dataclass
class Track:
    name: str
    notes: list = field(default_factory=list)
    channel: int = 0      # 9 = GM drums
    cc: list = field(default_factory=list)

    def add(self, pitch, start, dur, vel=100):
        self.notes.append(Note(pitch, start, dur, vel))
        return self

    def extend(self, notes):
        self.notes.extend(notes)
        return self

    def merge(self, other, at=0.0):
        """Fold another track's notes and automation in, offset by `at` beats."""
        shifted = other.shifted(at)
        self.notes.extend(shifted.notes)
        self.cc.extend(shifted.cc)
        return self

    def set_cc(self, controller, value, at):
        self.cc.append(CC(controller, int(round(value)), at))
        return self

    def ramp(self, controller, start, end, frm, to, steps=24, curve=1.0):
        """Write a controller ramp. curve > 1 starts slow, < 1 starts fast."""
        steps = max(int(steps), 1)
        for i in range(steps + 1):
            f = i / steps
            self.set_cc(controller, frm + (to - frm) * (f ** curve),
                        start + (end - start) * f)
        return self

    def shifted(self, beats):
        return Track(self.name,
                     [Note(n.pitch, n.start + beats, n.dur, n.vel) for n in self.notes],
                     self.channel,
                     [CC(c.controller, c.value, c.at + beats) for c in self.cc])

    def repeated(self, times, every):
        """Tile this track `times` times, `every` beats apart."""
        out = Track(self.name, [], self.channel)
        for i in range(times):
            out.merge(self, i * every)
        return out

    def window(self, start_beat, end_beat, rebase=True):
        """The slice of this track between two beats, optionally moved to zero."""
        off = -start_beat if rebase else 0.0
        notes = [Note(n.pitch, n.start + off, n.dur, n.vel) for n in self.notes
                 if start_beat <= n.start < end_beat]
        cc = [CC(c.controller, c.value, max(0.0, c.at + off)) for c in self.cc
              if start_beat <= c.at < end_beat]
        return Track(self.name, notes, self.channel, cc)


def _vlq(n):
    out = bytearray([n & 0x7F])
    n >>= 7
    while n:
        out.insert(0, (n & 0x7F) | 0x80)
        n >>= 7
    return bytes(out)


def _chunk(kind, data):
    return kind + struct.pack(">I", len(data)) + bytes(data)


def _meta_track(bpm, numerator, denominator, name):
    d = bytearray()
    nb = name.encode()[:127]
    d += b"\x00\xFF\x03" + _vlq(len(nb)) + nb
    d += b"\x00\xFF\x51\x03" + struct.pack(">I", int(60_000_000 / bpm))[1:]
    den_pow = {1: 0, 2: 1, 4: 2, 8: 3, 16: 4}[denominator]
    d += b"\x00\xFF\x58\x04" + bytes([numerator, den_pow, 24, 8])
    d += b"\x00\xFF\x2F\x00"
    return _chunk(b"MTrk", d)


def _note_track(track):
    events = []
    for c in track.cc:
        events.append((int(round(c.at * TPQ)), 0, 0xB0 | track.channel,
                       max(0, min(127, c.controller)), max(0, min(127, c.value))))
    for n in track.notes:
        on = int(round(n.start * TPQ))
        off = max(on + 1, int(round((n.start + n.dur) * TPQ)))
        p, v = max(0, min(127, n.pitch)), max(1, min(127, n.vel))
        events.append((off, 1, 0x80 | track.channel, p, 0))   # offs before ons at a tie
        events.append((on, 2, 0x90 | track.channel, p, v))
    events.sort(key=lambda e: (e[0], e[1]))

    d = bytearray()
    nb = track.name.encode()[:127]
    d += b"\x00\xFF\x03" + _vlq(len(nb)) + nb
    last = 0
    for tick, _, status, d1, d2 in events:
        d += _vlq(tick - last) + bytes([status, d1, d2])
        last = tick
    d += b"\x00\xFF\x2F\x00"
    return _chunk(b"MTrk", d)


def save(path, tracks, bpm=138.0, time_sig=(4, 4), name="Loop"):
    """Write a type-1 SMF. Each Track becomes its own MIDI track, so Logic
    creates one region per instrument when you drag the file in."""
    tracks = [tracks] if isinstance(tracks, Track) else list(tracks)
    body = _meta_track(bpm, time_sig[0], time_sig[1], name)
    for t in tracks:
        body += _note_track(t)
    header = _chunk(b"MThd", struct.pack(">HHH", 1, 1 + len(tracks), TPQ))
    with open(path, "wb") as f:
        f.write(header + body)
    return path
