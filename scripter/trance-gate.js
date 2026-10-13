/* Trance Gate — Logic Pro Scripter (MIDI FX)
 *
 * Holds whatever you play and re-triggers it on a grid: offbeat eighths for a
 * classic rolling trance bass, or straight 16ths for a gate. Swing offsets the
 * odd steps only.
 *
 * Use: insert Scripter as a MIDI FX on an instrument track, open it, paste this
 * into the Code Editor, hit Run Script. Then hold a note or a chord.
 */

var NeedsTimingInfo = true;

var RATES = ["1/4", "1/8", "1/8 offbeat", "1/16", "1/16 triplet"];
var RATE_BEATS = [1.0, 0.5, 0.5, 0.25, 1.0 / 6.0];

var held = [];
var nextBeat = -1;

function HandleMIDI(event) {
  if (event instanceof NoteOn) {
    held.push(event);
  } else if (event instanceof NoteOff) {
    for (var i = held.length - 1; i >= 0; i--) {
      if (held[i].pitch === event.pitch) held.splice(i, 1);
    }
  } else {
    event.send();            // pass CC, pitch bend, everything else through
  }
}

function ProcessMIDI() {
  var info = GetTimingInfo();
  if (!info.playing) {
    held = [];
    nextBeat = -1;
    MIDI.allNotesOff();
    return;
  }

  var rate = Math.round(GetParameter("Rate"));
  var step = RATE_BEATS[rate];
  var offbeatOnly = rate === 2;
  var gate = GetParameter("Gate") / 100.0;
  var swing = GetParameter("Swing") / 100.0;
  var accent = GetParameter("Accent");
  var octave = Math.round(GetParameter("Octave Push"));

  if (nextBeat < info.blockStartBeat) {
    nextBeat = Math.ceil(info.blockStartBeat / step) * step;
  }

  while (nextBeat < info.blockEndBeat) {
    var index = Math.round(nextBeat / step);
    var odd = (index % 2) === 1;

    if (held.length && (!offbeatOnly || odd)) {
      var at = nextBeat + (odd ? swing * step * 0.5 : 0.0);
      var onBar = (index % Math.round(4 / step)) === 0;
      for (var i = 0; i < held.length; i++) {
        var on = new NoteOn(held[i]);
        // push the last step of each bar up an octave — the trance bass lift
        var lastOfBar = octave > 0 &&
          (Math.round(nextBeat / step) % Math.round(4 / step)) === Math.round(4 / step) - 1;
        if (lastOfBar) on.pitch = Math.min(127, on.pitch + 12);
        on.velocity = Math.max(1, Math.min(127,
          on.velocity + (onBar ? accent : 0)));
        on.sendAtBeat(at);

        var off = new NoteOff(on);
        off.sendAtBeat(at + step * gate);
      }
    }
    nextBeat += step;
  }
}

var PluginParameters = [
  { name: "Rate", type: "menu", valueStrings: RATES, defaultValue: 2 },
  { name: "Gate", type: "lin", unit: "%", minValue: 5, maxValue: 100,
    numberOfSteps: 95, defaultValue: 45 },
  { name: "Swing", type: "lin", unit: "%", minValue: 0, maxValue: 100,
    numberOfSteps: 100, defaultValue: 0 },
  { name: "Accent", type: "lin", unit: "vel", minValue: 0, maxValue: 40,
    numberOfSteps: 40, defaultValue: 12 },
  { name: "Octave Push", type: "checkbox", defaultValue: 1 }
];
