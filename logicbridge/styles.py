"""Whole-loop recipes. Each returns (tracks, parts, bpm) where `parts` carries
the patch assignment used for audio previews."""
from . import patterns as P
from .theory import note

# i - VI - III - VII in the minor key, the backbone of most trance
DEGREES = [0, -4, 3, -2]


def _progression(key, qualities=("min9", "maj9", "maj9", "maj9"), octave=2):
    root = note(f"{key}{octave}")
    out = []
    for i, deg in enumerate(DEGREES):
        out.append((root + deg, qualities[i % len(qualities)]))
    return out


def _bass_roots(key, octave=1):
    root = note(f"{key}{octave}")
    return [root + d for d in DEGREES]


def trance(key="F", bpm=138, bars=8):
    prog = _progression(key, octave=2)
    drums = P.four_on_floor(bars)
    bass = P.offbeat_bass(_bass_roots(key), bars)
    stabs = P.chord_stabs(prog, bars, beats=(0.5, 2.5))
    parts = [(drums, None, 1.0),
             (bass, "trance_bass", 0.95),
             (stabs, "stab", 0.5)]
    return [drums, bass, stabs], parts, bpm


def psytrance(key="F", bpm=145, bars=8):
    drums = P.four_on_floor(bars, hats=True, claps_from=None)
    bass = P.offbeat_bass(_bass_roots(key), bars, octave_push=False,
                          sixteenths=(0, 1, 2, 3))
    lead = P.acid_line(f"{key}2", "phrygian", bars, rate=0.25, seed=7)
    parts = [(drums, None, 1.0), (bass, "trance_bass", 1.0), (lead, "acid", 0.45)]
    return [drums, bass, lead], parts, bpm


def uplifting(key="A", bpm=140, bars=8):
    prog = _progression(key, octave=2)
    drums = P.four_on_floor(bars)
    bass = P.offbeat_bass(_bass_roots(key), bars)
    pad = P.pad(prog, bars)
    lead = P.arp(f"{key}3", "minor", bars, rate=0.25, octaves=2, shape="updown")
    parts = [(drums, None, 1.0), (bass, "trance_bass", 0.9),
             (pad, "pad", 0.45), (lead, "hypersaw_lead", 0.4)]
    return [drums, bass, pad, lead], parts, bpm


def techno(key="C", bpm=128, bars=8):
    drums = P.four_on_floor(bars, claps_from=1)
    bass = P.offbeat_bass(_bass_roots(key), bars, octave_push=False, sixteenths=())
    acid = P.acid_line(f"{key}1", "minor_pentatonic", bars, seed=3, density=0.6)
    parts = [(drums, None, 1.0), (bass, "trance_bass", 1.0), (acid, "acid", 0.5)]
    return [drums, bass, acid], parts, bpm


STYLES = {"trance": trance, "psytrance": psytrance,
          "uplifting": uplifting, "techno": techno}
