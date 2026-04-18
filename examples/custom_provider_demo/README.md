# Custom Provider ASCII Song Demo

Run the demo from the repository root:

```powershell
python examples/custom_provider_demo/custom_provider_demo.py
```

The demo registers a local `tone` provider with a small offline ensemble:
`tone:piano`, `tone:electric_piano`, `tone:banjo`, `tone:bandoneon`,
`tone:bass`, `tone:electric_bass`, `tone:synth_bass`, `tone:clarinet`,
`tone:marimba`, `tone:drum_kit`, `tone:oboe`, `tone:recorder`,
`tone:tenor_sax`, `tone:square_lead`, `tone:synth_strings`, `tone:trumpet`,
and `tone:tuba`. Each score key gets its own ASCII score string, the provider
synthesizes those strings into separate WAV tracks, and then the tracks are
mixed into `.runtime/ascii-ensemble-song.wav` and routed to `speakers`.

## Notation

Each printable character maps to a note, rest, or command. The basic note rows are:

```text
z x c v b n m  ->  C3 D3 E3 F3 G3 A3 B3
a s d f g h j  ->  C4 D4 E4 F4 G4 A4 B4
q w e r t y u  ->  C5 D5 E5 F5 G5 A5 B5
```

Other notation:

```text
. or -        rest for one beat
^0.55         set track gain to 55%
@144          set tempo to 144 BPM
a#            C-sharp 4
qb            C-flat 5
a2            C4 for two beats
s/2           D4 for half a beat
[adg]         C4, E4, and G4 chord
!0.5          set following event volume to 50%
(a s d)*2     repeat the phrase twice
|             visual bar separator; ignored by the parser
```

Example:

```text
^0.85 @132 !0.72 ([adg] [sfh] [dgj] [fha])*2 | [adq]2 - [sgw]2 -
```

That sets a track gain of 85%, uses a 132 BPM tempo, lowers the event volume a bit, repeats four chords twice, then plays two longer chords with rests between them.

## MIDI Conversion

The helper in `midi_to_ascii.py` converts Standard MIDI files into the same
notation used by this demo:

```powershell
python examples/custom_provider_demo/midi_to_ascii.py path/to/song.mid --output examples/custom_provider_demo/.runtime/generated_song.py
```

The output is a small Python `song = {...}` dictionary. Paste the tracks into
`main.py`, or import the generated file from another experiment and
pass each notation string to `manager.synthesize_voice(...)`.

Dictionary keys are playable `tone` voices, not raw MIDI track labels. The
converter maps common instrument labels, channel programs, and percussion
channels to the closest demo voices. It adds suffixes like `trumpet_2` when
several MIDI tracks land on the same voice recipe.

The converter carries MIDI note velocity, channel volume, and channel
expression into `!volume` commands. That gives quieter parts a smaller
contribution before `merge_tracks()` normalizes the final ensemble.
It does not add preset `^gain` changes; manual `^gain` notation remains
available for hand-written scores.

By default, notes outside the playable `C3..B5` demo range are transposed by
octaves into range. Use `--keep-octaves` to drop out-of-range notes instead.
Use `--quantize 16` for denser timing, or a smaller number like `4` for simpler
notation.

To export only part of a MIDI file, pass a 1-based inclusive measure range:

```powershell
python examples/custom_provider_demo/midi_to_ascii.py path/to/song.mid --start-measure 9 --end-measure 16 --output examples/custom_provider_demo/.runtime/clip.py
```

The converter assumes 4 beats per measure by default. Use `--beats-per-bar 3`
or another value when the source material uses a different meter.

## Audio Generation

`parse_ascii_score()` expands repeats and turns the string into `ScoreEvent` objects. Each event stores the note frequencies, duration in beats, and current volume. Notes are converted to frequency with A4 = 440 Hz.

`ToneProvider.synthesize()` converts beats to sample frames using the active BPM and sample rate. For every event it renders one or more oscillator waves, applies a short ADSR-style envelope, and writes the result into a mono float32 sample buffer.

The instrument voices use different simple wave recipes:

- `piano` uses a bright harmonic stack with a fast attack and exponential decay.
- `electric_piano` adds bell partials and tremolo for a brighter keyed tone.
- `banjo` uses a sharp plucked string attack with bright harmonics and quick decay.
- `bandoneon` layers slightly detuned free-reed stacks with slow bellows tremolo.
- `bass` uses plucked low harmonics with a half-frequency weight for body.
- `electric_bass` uses a rounded pluck with a little saturation and low body.
- `synth_bass` uses square and sub oscillators with a tight sustained envelope.
- `clarinet` emphasizes odd harmonics with a smoother sustained envelope.
- `marimba` uses a fast mallet strike plus bar-like partials around `1:4:9.8`.
- `drum_kit` maps low, mid, and high score notes into kick, snare, tom, and hat-like hits.
- `oboe` uses a bright double-reed buzz and a small nasal formant.
- `recorder` favors odd harmonics with a little deterministic breath noise.
- `tenor_sax` uses a conical-reed harmonic stack with mild growl and breath.
- `square_lead` uses bright square-wave stacks with a small vibrato.
- `synth_strings` layers detuned sustained harmonics with a slow attack.
- `trumpet` leans toward a mellower cornet profile with softer attack and rounder brass harmonics.
- `tuba` uses a lower brass stack with slower attack and extra low body.

Score keys may include numbered part suffixes. For example, a score named
`bandoneon_2` is rendered with the `bandoneon` voice recipe, while the returned
audio metadata keeps `voice="tone:bandoneon_2"`, `base_voice="tone:bandoneon"`,
and `part_number=2` so the merged song can still identify the secondary track.

`merge_tracks()` pads the generated tracks to the longest length, sums them, scales by the square root of the track count, and peak-limits the result so the merged clip stays in the normal `[-1.0, 1.0]` audio range.

## VoiceConductor Wiring

`ToneProviderSettings` is registered with `register_provider_config()`, and `ToneProvider` is registered with `register_provider()`. `build_manager()` creates a `TTSManager` whose provider chain prefers `tone`, so normal calls like `manager.synthesize_voice(score, provider="tone", voice="piano")` use the custom provider.

The generated audio is returned as `SynthesizedAudio`, which means the regular VoiceConductor cache, WAV export, and routing APIs work without special handling. The demo writes each stem with `copy_to()` and sends the merged `SynthesizedAudio` to `manager.route(..., routes="speakers")`.
