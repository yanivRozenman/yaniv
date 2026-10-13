"""logicbridge - generate music for Logic Pro, and hear it without a DAW.

    from logicbridge import patterns as P, midi, synth, logic
    drums = P.four_on_floor(4)
    bass  = P.offbeat_bass(['F1', 'Db1', 'Ab1', 'Eb1'], 4)
    midi.save('out/loop.mid', [drums, bass], bpm=138)
    synth.preview([(drums, None, 1.0), (bass, 'trance_bass', 1.0)], 138, 4, 'out/loop.wav')
    logic.deliver('out/loop.mid')      # macOS only
"""
from . import theory, midi, patterns, synth, styles, logic  # noqa: F401

__all__ = ["theory", "midi", "patterns", "synth", "styles", "logic"]
