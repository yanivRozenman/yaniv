# logicbridge

Generate music for Logic Pro from code — and hear it before Logic is even open.

```bash
bin/make-loop --style trance --key F --bpm 138 --bars 8 --audio --deliver
```

That writes `out/trance_138_F.mid` plus a rendered `.wav` preview, copies the
MIDI to `~/Music/Logic/claude-loops`, and reveals it in Finder so you can drag
it straight onto a track.

For a whole track instead of a loop:

```bash
bin/make-track --key F --bpm 138 --template club --preview drop
```

88 bars of intro / groove / build / drop / breakdown / rebuild / drop / outro,
with filter and expression automation written as CC74 and CC11, and an audio
preview of just the drop. Templates: `short`, `club`, `extended`.

## Setup

```bash
git clone https://github.com/yanivRozenman/yaniv.git
cd yaniv
pip3 install -r requirements.txt
bin/make-loop --style trance --audio
```

To work on it with Claude Code on your Mac:

```bash
npm install -g @anthropic-ai/claude-code
cd yaniv && claude
```

Then just ask — "make me a 140 BPM psytrance loop in F#, rolling bass, acid
lead". Claude composes it, renders a preview, and drops it into Logic.

## What's here

| | |
|---|---|
| `logicbridge/theory.py` | notes, scales, chords |
| `logicbridge/midi.py` | standard MIDI file writer, positions in beats |
| `logicbridge/patterns.py` | four-on-the-floor, offbeat bass, arps, acid lines, builds |
| `logicbridge/styles.py` | whole-loop recipes: trance, psytrance, uplifting, techno |
| `logicbridge/arrange.py` | section-based arrangements with filter/expression automation |
| `logicbridge/synth.py` | virtual-analog engine for previews |
| `logicbridge/logic.py` | macOS bridge — deliver, reveal, import, transport |
| `scripter/` | Logic Scripter plugins (JavaScript MIDI FX) |

## The synth

`synth.py` is a small virtual-analog engine, there so a pattern can be judged
by ear without assigning instruments in Logic. Three things give it its
character:

- **`blep_saw`** — sawtooth with the aliasing removed by subtracting a
  polynomial bandlimited step at each wrap. The difference between this and a
  naive `2*phase-1` saw is most of the gap between a cheap-sounding synth and a
  hardware one.
- **`hypersaw`** — seven detuned saws using the detune-spread and
  centre/side-level curves Adam Szabo measured off a JP-8000. Neither curve is
  linear, and that non-linearity is why the stack sounds like *that*.
- **`ladder`** — 4-pole lowpass with `tanh()` in every stage and in the
  resonance feedback, oversampled 4×. Resonance saturates instead of blowing
  up; drive adds harmonics instead of clipping. This is the "analog" part.

It is paraphonic — a whole track shares one filter — so it is a preview tool,
not a plugin. The honest version of this is C++ in JUCE, built as an AU.

## Getting sound into Logic

1. **Drag and drop.** `--deliver` reveals the file in Finder. Always works.
2. **UI scripting.** `--import-into-logic` drives File ▸ Import ▸ MIDI File
   through System Events. Needs Accessibility permission for your terminal, and
   breaks if Logic moves its menus.
3. **Scripter.** Logic's JavaScript MIDI FX plugin — the only real programmatic
   hook into Logic. Insert Scripter as a MIDI FX, open it, paste in a file from
   `scripter/`, hit Run Script.

Logic has no scripting API for tracks, regions, plugins, mixing or bouncing.
Those stay manual.
