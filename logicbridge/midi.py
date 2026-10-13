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
class Track:
    name: str
    notes: list = field(default_factory=list)
    channel: int = 0      # 9 = GM drums

    def add(self, pitch, start, dur, vel=100):
        self.notes.append(Note(pitch, start, dur, vel))
        return self

    def extend(self, notes):
        self.notes.extend(notes)
        return self

    def shifted(self, beats):
        return Track(self.name, [Note(n.pitch, n.start + beats, n.dur, n.vel)
                                 for n in self.notes], self.channel)

    def repeated(self, times, every):
        """Tile this track `times` times, `every` beats apart."""
        out = Track(self.name, [], self.channel)
        for i in range(times):
            out.extend(self.shifted(i * every).notes)
        return out


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
    for n in track.notes:
        on = int(round(n.start * TPQ))
        off = max(on + 1, int(round((n.start + n.dur) * TPQ)))
        p, v = max(0, min(127, n.pitch)), max(1, min(127, n.vel))
        events.append((off, 0, 0x80 | track.channel, p, 0))   # note-offs first at a tie
        events.append((on, 1, 0x90 | track.channel, p, v))
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
