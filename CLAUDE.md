# Working on this repo

This is a music toolkit for Logic Pro. When running on the user's Mac, you can
generate MIDI and audio and hand both to Logic. When running in a cloud session,
everything except the `logicbridge.logic` module still works — generate the
files and send them to the user.

## Make music when asked

The normal flow for "make me a <something> loop":

1. Compose with `logicbridge.patterns` / `logicbridge.theory`, or start from a
   recipe in `logicbridge.styles`.
2. Write MIDI with `logicbridge.midi.save()` into `out/`. One `Track` per
   instrument — Logic makes one region per track when the file is imported.
3. Render a WAV preview with `logicbridge.synth.preview()`. **Always do this.**
   You cannot hear it, but you can measure it (see below), and the user can
   play it immediately without wiring up instruments.
4. On a Mac, `logicbridge.logic.deliver(path)` copies it to
   `~/Music/Logic/claude-loops` and reveals it in Finder, ready to drag onto a
   track. Prefer this over `import_midi()`, which drives Logic's menus through
   System Events and needs Accessibility permission.
5. Send the user both files.

`bin/make-loop` does all of this for the stock styles. Use it for a quick
starting point, then edit patterns directly for anything specific.

## Check your work before claiming it sounds good

You cannot hear the render, so measure it. After writing a WAV, check duration,
RMS, peak and the rough spectral balance, and say what you found:

```python
import numpy as np, wave
w = wave.open("out/loop.wav"); d = np.frombuffer(w.readframes(w.getnframes()), "<i2") / 32768
L = d[0::2]
print(len(L) / 44100, L.std(), abs(L).max())
```

Red flags worth fixing rather than shipping: peak at 1.0 (clipping), RMS under
0.05 (too quiet to judge), nothing above 8 kHz (filter shut, or no hats),
nothing under 100 Hz in a dance loop (no sub).

Never tell the user a loop "sounds great" — you do not know that. Say what you
built and what you measured; let them judge.

## Conventions

- Note numbers follow Logic's display: **C3 = 60**, kick = C1 = 36.
- Positions and durations are in **beats as floats**, never ticks. 0.5 = eighth.
- Drum tracks use `channel=9` and the GM map in `patterns.py`.
- Pattern functions return a `Track` and take `bars` — keep them composable and
  free of side effects.
- A new genre goes in `styles.py` as a function returning `(tracks, parts, bpm)`.

## What Logic cannot do

There is no AppleScript API for tracks, regions, plugins, mixing or bouncing.
Do not promise it. The three real routes in are drag-and-drop (reliable), UI
scripting via System Events (fragile), and **Scripter**, Logic's JavaScript MIDI
FX plugin — the only genuine programmatic hook. Write Scripter code into
`scripter/`; the user pastes it into the plugin window. Syntax-check with
`node --check` before handing it over.

## Setup notes

`pip install -r requirements.txt` (numpy only). The synth renders roughly
real-time: a 4-bar loop takes a few seconds because the ladder filter runs
sample-by-sample at 4x oversampling. That is expected — do not "optimize" it by
removing the oversampling or the tanh saturation, which is where the sound is.
