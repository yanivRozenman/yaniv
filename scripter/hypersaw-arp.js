/* HyperSaw Arp — Logic Pro Scripter (MIDI FX)
 *
 * Arpeggiates held chords with shape, octave range and a per-step velocity
 * ramp. Pair it with any supersaw patch for uplifting-trance leads.
 */

var NeedsTimingInfo = true;

var SHAPES = ["up", "down", "up/down", "down/up", "inside out", "random"];
var RATES = ["1/8", "1/16", "1/16 triplet", "1/32"];
var RATE_BEATS = [0.5, 0.25, 1.0 / 6.0, 0.125];

var held = [];
var nextBeat = -1;
var stepIndex = 0;

function HandleMIDI(event) {
  if (event instanceof NoteOn) {
    held.push(event.pitch);
    held.sort(function (a, b) { return a - b; });
  } else if (event instanceof NoteOff) {
    var i = held.indexOf(event.pitch);
    if (i >= 0) held.splice(i, 1);
    if (!held.length) stepIndex = 0;
  } else {
    event.send();
  }
}

function buildSequence() {
  var octaves = Math.round(GetParameter("Octaves"));
  var base = [];
  for (var o = 0; o < octaves; o++) {
    for (var i = 0; i < held.length; i++) base.push(held[i] + 12 * o);
  }
  if (!base.length) return base;

  switch (Math.round(GetParameter("Shape"))) {
    case 1: return base.slice().reverse();
    case 2: return base.concat(base.slice(1, -1).reverse());
    case 3: var d = base.slice().reverse(); return d.concat(d.slice(1, -1).reverse());
    case 4:                                   // inside out
      var out = [], lo = 0, hi = base.length - 1;
      while (lo <= hi) { out.push(base[lo++]); if (lo <= hi) out.push(base[hi--]); }
      return out;
    case 5: return base;                      // random, picked per step
    default: return base;
  }
}

function ProcessMIDI() {
  var info = GetTimingInfo();
  if (!info.playing) {
    held = [];
    nextBeat = -1;
    stepIndex = 0;
    MIDI.allNotesOff();
    return;
  }

  var step = RATE_BEATS[Math.round(GetParameter("Rate"))];
  var gate = GetParameter("Gate") / 100.0;
  var accent = GetParameter("Accent");
  var random = Math.round(GetParameter("Shape")) === 5;

  if (nextBeat < info.blockStartBeat) {
    nextBeat = Math.ceil(info.blockStartBeat / step) * step;
  }

  while (nextBeat < info.blockEndBeat) {
    var seq = buildSequence();
    if (seq.length) {
      var pitch = random
        ? seq[Math.floor(Math.random() * seq.length)]
        : seq[stepIndex % seq.length];

      var on = new NoteOn();
      on.pitch = Math.max(0, Math.min(127, pitch));
      var downbeat = (Math.round(nextBeat / step) % Math.round(1 / step)) === 0;
      on.velocity = Math.max(1, Math.min(127, 90 + (downbeat ? accent : 0)));
      on.sendAtBeat(nextBeat);

      var off = new NoteOff(on);
      off.sendAtBeat(nextBeat + step * gate);
      stepIndex++;
    }
    nextBeat += step;
  }
}

var PluginParameters = [
  { name: "Rate", type: "menu", valueStrings: RATES, defaultValue: 1 },
  { name: "Shape", type: "menu", valueStrings: SHAPES, defaultValue: 2 },
  { name: "Octaves", type: "lin", minValue: 1, maxValue: 4,
    numberOfSteps: 3, defaultValue: 2 },
  { name: "Gate", type: "lin", unit: "%", minValue: 5, maxValue: 100,
    numberOfSteps: 95, defaultValue: 80 },
  { name: "Accent", type: "lin", unit: "vel", minValue: 0, maxValue: 37,
    numberOfSteps: 37, defaultValue: 15 }
];
