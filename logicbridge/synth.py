"""A small virtual-analog engine, so a pattern can be heard without opening a DAW.

The sound comes from three things:
  blep_saw  - sawtooth with no aliasing (polynomial bandlimited step)
  hypersaw  - 7 detuned saws using the measured JP-8000 detune/mix curves
  ladder    - 4-pole filter with tanh in every stage, run at 4x oversampling

Patches are paraphonic: a whole track sums into one filter. That is not how a
Virus works, but it is accurate enough to judge a pattern by ear.
"""
import math, struct
from dataclasses import dataclass

import numpy as np

SR, OS = 44100, 4
SRO = SR * OS

# ------------------------------------------------------------------ oscillators
def blep_saw(freq, n, sr=SRO, phase0=0.0):
    dt = freq / sr
    ph = (phase0 + dt * np.arange(n)) % 1.0
    y = 2.0 * ph - 1.0
    m = ph < dt
    t = ph[m] / dt
    y[m] -= t + t - t * t - 1.0
    m = ph > 1.0 - dt
    t = (ph[m] - 1.0) / dt
    y[m] -= t * t + t + t + 1.0
    return y


_DETUNE_FIT = [10028.7312891634, -50818.8652045924, 111363.4808729368,
               -138150.6761080548, 106649.6679158292, -53046.9642751875,
               17019.9518580080, -3425.0836591318, 404.2703938388,
               -24.1878824391, 0.6717417634, 0.0030115596]
_OFFSETS = [-0.11002313, -0.06288439, -0.01952356, 0.0,
            0.01991221, 0.06216538, 0.10745242]


def detune_spread(knob):
    """Szabo's fit of the supersaw detune knob. Deliberately not linear."""
    return sum(c * knob ** (11 - i) for i, c in enumerate(_DETUNE_FIT))


def hypersaw(freq, n, detune=0.6, mix=0.7, seed=0):
    """Stereo supersaw. Width is just different oscillator phases per channel."""
    spread = detune_spread(detune)
    centre = -0.55366 * mix + 0.99785
    side = -0.73764 * mix * mix + 1.2841 * mix + 0.044372
    rng = np.random.default_rng(seed)
    out = np.zeros((2, n))
    for ch in range(2):
        for off in _OFFSETS:
            f = freq * (1.0 + off * spread)
            if not 0.0 < f < SRO * 0.45:
                continue
            amp = centre if off == 0.0 else side
            out[ch] += amp * blep_saw(f, n, SRO, rng.random())
    return out * 0.18


# ---------------------------------------------------------------------- filter
def ladder(x, cutoff, res=0.5, drive=1.0):
    """Nonlinear 4-pole lowpass. The tanh calls are the whole point: resonance
    saturates instead of exploding, and drive adds harmonics rather than clipping."""
    g = 1.0 - np.exp(-2.0 * math.pi * np.clip(cutoff, 20.0, SRO * 0.45) / SRO)
    k = 4.0 * res
    out = np.empty_like(x)
    y0 = y1 = y2 = y3 = t0 = t1 = t2 = t3 = 0.0
    tanh = math.tanh
    for i in range(x.shape[0]):
        gi = g[i]
        u = tanh((x[i] * drive - k * y3) * 0.5)
        y0 += gi * (u - t0);  t0 = tanh(y0 * 0.5)
        y1 += gi * (t0 - t1); t1 = tanh(y1 * 0.5)
        y2 += gi * (t1 - t2); t2 = tanh(y2 * 0.5)
        y3 += gi * (t2 - t3); t3 = tanh(y3 * 0.5)
        out[i] = y3
    return out * (1.0 + k * 0.45)


# ------------------------------------------------------------------- envelopes
def adsr(n, a=0.002, d=0.08, s=0.7, r=0.12, sustain_n=0, sr=SRO):
    env = np.zeros(n)
    i = 0
    for target, length in ((1.0, int(a * sr)), (s, int(d * sr))):
        seg = min(max(length, 1), n - i)
        if seg <= 0:
            break
        env[i:i + seg] = np.linspace(env[i - 1] if i else 0.0, target, seg)
        i += seg
    seg = min(max(sustain_n, 0), n - i)
    env[i:i + seg] = s
    i += seg
    if n - i > 0:
        env[i:] = np.linspace(s, 0.0, n - i) ** 1.5
    return env


def _decimate(x):
    taps, cut = 127, 0.45 / OS
    m = np.arange(taps) - (taps - 1) / 2
    h = np.sinc(2 * cut * m) * np.hanning(taps)
    h /= h.sum()
    return np.convolve(x, h, mode="same")[::OS]


def chorus(l, r, rate=0.28, depth_ms=5.5, mix=0.4):
    n = len(l)
    t = np.arange(n) / SR
    out = []
    for sig, phase in ((l, 0.0), (r, 0.5)):
        d = depth_ms * 0.5 * (1.0 + np.sin(2 * math.pi * (rate * t + phase))) + 1.0
        idx = np.arange(n) - d * SR / 1000.0
        i0 = np.clip(np.floor(idx).astype(int), 0, n - 1)
        fr = idx - np.floor(idx)
        wet = sig[i0] * (1 - fr) + sig[np.clip(i0 + 1, 0, n - 1)] * fr
        out.append(sig * (1 - mix) + wet * mix)
    return out[0], out[1]


# ---------------------------------------------------------------------- patches
@dataclass
class Patch:
    detune: float = 0.6      # supersaw spread, 0..1
    mix: float = 0.7         # centre-vs-side saw balance
    cutoff: float = 900.0    # filter base, Hz
    res: float = 0.4         # 0..1, ~0.85+ self-oscillates
    drive: float = 1.2       # level into the filter nonlinearity
    env_amt: float = 1400.0  # cutoff envelope depth, Hz
    env_decay: float = 0.06  # cutoff envelope decay, seconds
    attack: float = 0.003
    decay: float = 0.08
    sustain: float = 0.8
    release: float = 0.08
    sub: float = 0.0         # sine an octave down
    gain: float = 1.0
    chorus_mix: float = 0.0


PRESETS = {
    "trance_bass":  Patch(detune=0.42, mix=0.6, cutoff=120, res=0.62, drive=1.5,
                          env_amt=1500, env_decay=0.035, sustain=0.85, sub=0.35),
    "hypersaw_lead": Patch(detune=0.85, mix=0.8, cutoff=1200, res=0.22, drive=1.1,
                           env_amt=2600, env_decay=0.25, sustain=0.75,
                           release=0.25, chorus_mix=0.45),
    "stab":         Patch(detune=0.78, mix=0.8, cutoff=700, res=0.3, drive=1.1,
                          env_amt=3000, env_decay=0.12, sustain=0.55,
                          release=0.3, chorus_mix=0.4),
    "pad":          Patch(detune=0.9, mix=0.85, cutoff=600, res=0.15, drive=0.9,
                          env_amt=900, env_decay=0.9, attack=0.12, sustain=0.9,
                          release=0.6, chorus_mix=0.55, gain=0.7),
    "acid":         Patch(detune=0.0, mix=0.0, cutoff=260, res=0.84, drive=2.2,
                          env_amt=2200, env_decay=0.09, sustain=0.4),
}


# ----------------------------------------------------------------------- render
def render_track(track, patch, bpm, bars, tail=0.5):
    """Sum a Track's notes through one filter. Returns stereo float arrays at SR."""
    beat = 60.0 / bpm
    total_o = int((bars * 4 * beat + tail) * SRO)
    osc = np.zeros((2, total_o))
    cut = np.full(total_o, patch.cutoff)

    for i, nt in enumerate(track.notes):
        start = int(nt.start * beat * SRO)
        n = int(max(nt.dur * beat, 0.02) * SRO)
        if start >= total_o:
            continue
        n = min(n, total_o - start)
        freq = 440.0 * 2.0 ** ((nt.pitch - 69) / 12.0)
        if patch.detune <= 0.0:
            wave = np.repeat(blep_saw(freq, n)[None, :], 2, axis=0) * 0.5
        else:
            wave = hypersaw(freq, n, patch.detune, patch.mix, seed=i)
        if patch.sub > 0.0:
            ph = 2 * math.pi * freq * 0.5 * np.arange(n) / SRO
            wave = wave + patch.sub * np.sin(ph) * 0.5
        env = adsr(n, patch.attack, patch.decay, patch.sustain, patch.release,
                   int(n * 0.6))
        osc[:, start:start + n] += wave * env * (nt.vel / 110.0)
        if patch.env_amt:
            ce = patch.cutoff + patch.env_amt * np.exp(
                -np.arange(n) / (patch.env_decay * SRO))
            seg = cut[start:start + n]
            cut[start:start + n] = np.maximum(seg, ce)

    L = _decimate(ladder(osc[0], cut, patch.res, patch.drive)) * patch.gain
    R = _decimate(ladder(osc[1], cut, patch.res, patch.drive)) * patch.gain
    if patch.chorus_mix > 0.0:
        L, R = chorus(L, R, mix=patch.chorus_mix)
    return L, R


_DRUM_GAIN = {36: 0.9, 38: 0.5, 39: 0.5, 42: 0.17, 44: 0.15, 46: 0.2,
              45: 0.4, 50: 0.4, 51: 0.2, 49: 0.5}


def render_drums(track, bpm, bars, tail=0.5, seed=1):
    """Synthesized GM-mapped drums: sine-sweep kick, filtered noise for the rest."""
    beat = 60.0 / bpm
    total = int((bars * 4 * beat + tail) * SR)
    buf = np.zeros(total)
    rng = np.random.default_rng(seed)
    for nt in track.notes:
        s = int(nt.start * beat * SR)
        if s >= total:
            continue
        g = _DRUM_GAIN.get(nt.pitch, 0.3) * (nt.vel / 110.0)
        if nt.pitch == 36:                                    # kick
            n = min(int(0.26 * SR), total - s)
            t = np.arange(n) / SR
            f = 48.0 + 120.0 * np.exp(-t / 0.013)
            hit = np.sin(2 * math.pi * np.cumsum(f) / SR) * np.exp(-t / 0.085)
            hit += rng.normal(0, 1, n) * np.exp(-t / 0.002) * 0.3
            hit = np.tanh(hit * 1.6)
        elif nt.pitch in (38, 39):                            # snare / clap
            n = min(int(0.22 * SR), total - s)
            t = np.arange(n) / SR
            hit = rng.normal(0, 1, n) * np.exp(-t / 0.055)
            hit += np.sin(2 * math.pi * 185 * t) * np.exp(-t / 0.03) * 0.5
        elif nt.pitch in (45, 50, 47, 48):                    # toms
            n = min(int(0.3 * SR), total - s)
            t = np.arange(n) / SR
            f = (150.0 if nt.pitch == 45 else 240.0) * np.exp(-t / 0.3)
            hit = np.sin(2 * math.pi * np.cumsum(f) / SR) * np.exp(-t / 0.12)
        else:                                                 # hats / cymbals
            length = 0.045 if nt.pitch == 42 else (0.5 if nt.pitch == 49 else 0.13)
            n = min(int(length * 3 * SR), total - s)
            t = np.arange(n) / SR
            hit = rng.normal(0, 1, n) * np.exp(-t / length)
            hit = np.convolve(hit, [1.0, -0.92], mode="same")
        buf[s:s + len(hit)] += hit[:total - s] * g
    return buf, buf.copy()


def write_wav(path, L, R, headroom=0.89):
    peak = max(float(np.abs(L).max()), float(np.abs(R).max()), 1e-9)
    L, R = L / peak * headroom, R / peak * headroom
    inter = np.empty(len(L) * 2)
    inter[0::2], inter[1::2] = L, R
    pcm = (np.clip(inter, -1, 1) * 32767).astype("<i2").tobytes()
    with open(path, "wb") as f:
        f.write(b"RIFF" + struct.pack("<I", 36 + len(pcm)) + b"WAVEfmt " +
                struct.pack("<IHHIIHH", 16, 1, 2, SR, SR * 4, 4, 16) +
                b"data" + struct.pack("<I", len(pcm)) + pcm)
    return path


def preview(parts, bpm, bars, path, master_drive=0.8):
    """parts: [(track, patch_or_name_or_None, level), ...]  None patch = drums."""
    mixL = mixR = None
    for track, patch, level in parts:
        if patch is None or track.channel == 9:
            L, R = render_drums(track, bpm, bars)
        else:
            p = PRESETS[patch] if isinstance(patch, str) else patch
            L, R = render_track(track, p, bpm, bars)
        if mixL is None:
            mixL, mixR = np.zeros(len(L)), np.zeros(len(R))
        n = min(len(mixL), len(L))
        mixL[:n] += L[:n] * level
        mixR[:n] += R[:n] * level
    return write_wav(path, np.tanh(mixL * master_drive), np.tanh(mixR * master_drive))
