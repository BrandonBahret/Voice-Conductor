"""Convert Standard MIDI files into the ASCII song demo notation."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import argparse
import struct
import sys

try:
    from ascii_song_demo import NOTE_CHARS
except ModuleNotFoundError:  # pragma: no cover - package-style import fallback
    from .ascii_song_demo import NOTE_CHARS


PITCH_CLASS_TO_ASCII = {
    0: ("C", ""),
    1: ("C", "#"),
    2: ("D", ""),
    3: ("D", "#"),
    4: ("E", ""),
    5: ("F", ""),
    6: ("F", "#"),
    7: ("G", ""),
    8: ("G", "#"),
    9: ("A", ""),
    10: ("A", "#"),
    11: ("B", ""),
}
NOTE_NAME_TO_CHAR = {value: key for key, value in NOTE_CHARS.items()}
TONE_VOICES = {
    "piano",
    "banjo",
    "bandoneon",
    "bass",
    "clarinet",
    "marimba",
    "oboe",
    "recorder",
    "tenor_sax",
    "trumpet",
    "tuba",
}
TRACK_NAME_VOICE_HINTS = (
    ("trumpet", "trumpet"),
    ("trompete", "trumpet"),
    ("tuba", "tuba"),
    ("bassoon", "oboe"),
    ("fagott", "oboe"),
    ("oboe", "oboe"),
    ("clarinet", "clarinet"),
    ("klarinette", "clarinet"),
    ("sax", "tenor_sax"),
    ("flute", "recorder"),
    ("floete", "recorder"),
    ("flote", "recorder"),
    ("fl_te", "recorder"),
    ("recorder", "recorder"),
    ("marimba", "marimba"),
    ("drum", "marimba"),
    ("perkussion", "marimba"),
    ("percussion", "marimba"),
    ("bass", "bass"),
    ("kontrabass", "bass"),
    ("banjo", "banjo"),
    ("guitar", "piano"),
    ("gitarre", "piano"),
    ("piano", "piano"),
    ("klavier", "piano"),
    ("accordion", "bandoneon"),
    ("akkordeon", "bandoneon"),
    ("bandoneon", "bandoneon"),
)


@dataclass(frozen=True, slots=True)
class MidiAsciiTrack:
    """One converted MIDI track."""

    name: str
    notation: str
    events: int
    source_name: str = ""
    arrangement_role: str = "primary"
    arrangement_gain: float = 1.0


@dataclass(frozen=True, slots=True)
class MidiAsciiSong:
    """Converted notation plus a few useful MIDI details."""

    bpm: float
    ticks_per_beat: int
    tracks: tuple[MidiAsciiTrack, ...]

    def as_voice_map(self) -> dict[str, str]:
        """Return tracks in the dictionary shape used by ``ascii_song_demo``."""

        return {track.name: track.notation for track in self.tracks}


@dataclass(frozen=True, slots=True)
class _MidiInterval:
    note: int
    start_tick: int
    end_tick: int
    volume: float


def convert_midi_to_ascii(
    midi_path: str | Path,
    *,
    quantize: int = 8,
    beats_per_bar: int = 4,
    start_measure: int | None = None,
    end_measure: int | None = None,
    transpose_to_range: bool = True,
    emphasize_primary_voices: bool = True,
) -> MidiAsciiSong:
    """Read ``midi_path`` and convert its note data to ASCII demo notation.

    ``quantize`` is the number of duration steps per beat. The default of 8
    keeps eighth-beat timing readable while still handling common MIDI files.
    ``start_measure`` and ``end_measure`` use 1-based measure numbers; the end
    measure is included in the output.
    Notes outside the demo's C3..B5 range are octave-transposed into range by
    default so the generated notation is immediately playable.
    """

    data = Path(midi_path).read_bytes()
    ticks_per_beat, raw_tracks, first_bpm = _read_midi_file(data)
    range_start_tick, range_end_tick = _measure_range_to_ticks(
        start_measure=start_measure,
        end_measure=end_measure,
        ticks_per_beat=ticks_per_beat,
        beats_per_bar=beats_per_bar,
    )
    tracks: list[MidiAsciiTrack] = []
    voice_counts: dict[str, int] = {}
    track_voice_pairs = [
        (
            track_name,
            _slice_intervals(
                intervals,
                start_tick=range_start_tick,
                end_tick=range_end_tick,
            ),
            midi_track_name_to_voice(track_name),
        )
        for track_name, intervals in raw_tracks
    ]
    has_primary_voice = any(
        _is_primary_voice(voice_name)
        for _track_name, _intervals, voice_name in track_voice_pairs
    )
    for track_index, (track_name, intervals, base_voice_name) in enumerate(
        track_voice_pairs, start=1
    ):
        arrangement_role = _arrangement_role_for_voice(
            base_voice_name,
            emphasize_primary_voices=emphasize_primary_voices,
            has_primary_voice=has_primary_voice,
        )
        arrangement_gain = _arrangement_gain_for_role(arrangement_role)
        notation, event_count = _intervals_to_notation(
            intervals,
            bpm=first_bpm,
            ticks_per_beat=ticks_per_beat,
            quantize=quantize,
            beats_per_bar=beats_per_bar,
            transpose_to_range=transpose_to_range,
            track_gain=arrangement_gain,
            include_origin_boundary=range_start_tick is not None,
            notation_end_tick=(
                range_end_tick - (range_start_tick or 0)
                if range_end_tick is not None
                else None
            ),
        )
        if event_count:
            voice_name = _unique_voice_name(
                base_voice_name,
                voice_counts=voice_counts,
            )
            tracks.append(
                MidiAsciiTrack(
                    name=voice_name,
                    notation=notation,
                    events=event_count,
                    source_name=track_name or f"track_{track_index}",
                    arrangement_role=arrangement_role,
                    arrangement_gain=arrangement_gain,
                )
            )
    return MidiAsciiSong(
        bpm=first_bpm,
        ticks_per_beat=ticks_per_beat,
        tracks=tuple(tracks),
    )


def midi_note_to_ascii(
    midi_note: int, *, transpose_to_range: bool = True
) -> str | None:
    """Return the notation token for a MIDI note number, or ``None`` if out of range."""

    note = int(midi_note)
    if transpose_to_range:
        while note < 48:
            note += 12
        while note > 83:
            note -= 12
    if note < 48 or note > 83:
        return None

    octave = (note // 12) - 1
    note_name, accidental = PITCH_CLASS_TO_ASCII[note % 12]
    note_char = NOTE_NAME_TO_CHAR[(note_name, octave)]
    return f"{note_char}{accidental}"


def midi_track_name_to_voice(name: str) -> str:
    """Return the closest playable ``tone`` provider voice for a MIDI track name."""

    normalized = _safe_track_name(name, fallback="")
    if normalized in TONE_VOICES:
        return normalized
    for hint, voice in TRACK_NAME_VOICE_HINTS:
        if hint in normalized:
            return voice
    return "piano"


def _is_primary_voice(voice_name: str) -> bool:
    return voice_name == "banjo"


def _arrangement_role_for_voice(
    voice_name: str,
    *,
    emphasize_primary_voices: bool,
    has_primary_voice: bool,
) -> str:
    if not emphasize_primary_voices or not has_primary_voice:
        return "primary"
    if _is_primary_voice(voice_name):
        return "primary"
    return "secondary"


def _arrangement_gain_for_role(role: str) -> float:
    if role == "secondary":
        return 0.55
    return 1.0


def format_midi_ascii_song(song: MidiAsciiSong) -> str:
    """Format a converted song as copy-pasteable Python source."""

    lines = [
        "# Paste this into ascii_song_demo.py's song dictionary, or import it.",
        "song = {",
    ]
    for track in song.tracks:
        if track.source_name and track.source_name != track.name:
            lines.append(f"    # MIDI track: {track.source_name}")
        if track.arrangement_role != "primary":
            lines.append(
                "    # Arrangement: "
                f"{track.arrangement_role}, "
                f"gain x{_format_number(track.arrangement_gain)}"
            )
        lines.append(f"    {track.name!r}: {track.notation!r},")
    lines.append("}")
    return "\n".join(lines)


def _read_midi_file(
    data: bytes,
) -> tuple[int, list[tuple[str, list[_MidiInterval]]], float]:
    cursor = 0
    chunk_type, payload, cursor = _read_chunk(data, cursor)
    if chunk_type != b"MThd":
        raise ValueError("Not a Standard MIDI file: missing MThd header.")
    if len(payload) != 6:
        raise ValueError("Unsupported MIDI header length.")

    _format_type, track_count, division = struct.unpack(">HHH", payload)
    if division & 0x8000:
        raise ValueError("SMPTE-time MIDI files are not supported.")
    ticks_per_beat = division

    tracks: list[tuple[str, list[_MidiInterval]]] = []
    first_bpm = 120.0
    for _ in range(track_count):
        chunk_type, payload, cursor = _read_chunk(data, cursor)
        if chunk_type != b"MTrk":
            continue
        track_name, intervals, tempos = _read_track(payload)
        if tempos and first_bpm == 120.0:
            first_bpm = tempos[0]
        tracks.append((track_name, intervals))
    return ticks_per_beat, tracks, first_bpm


def _read_chunk(data: bytes, cursor: int) -> tuple[bytes, bytes, int]:
    if cursor + 8 > len(data):
        raise ValueError("Unexpected end of MIDI data.")
    chunk_type = data[cursor : cursor + 4]
    length = int.from_bytes(data[cursor + 4 : cursor + 8], "big")
    cursor += 8
    payload = data[cursor : cursor + length]
    if len(payload) != length:
        raise ValueError("Unexpected end of MIDI chunk.")
    return chunk_type, payload, cursor + length


def _read_track(payload: bytes) -> tuple[str, list[_MidiInterval], list[float]]:
    cursor = 0
    tick = 0
    running_status: int | None = None
    track_name = ""
    tempos: list[float] = []
    channel_volume = [1.0] * 16
    channel_expression = [1.0] * 16
    active: dict[tuple[int, int], list[tuple[int, float]]] = {}
    intervals: list[_MidiInterval] = []

    while cursor < len(payload):
        delta, cursor = _read_varlen(payload, cursor)
        tick += delta
        status = payload[cursor]
        if status < 0x80:
            if running_status is None:
                raise ValueError("MIDI running status appeared before a status byte.")
            status = running_status
        else:
            cursor += 1
            if status < 0xF0:
                running_status = status

        if status == 0xFF:
            meta_type = payload[cursor]
            length, cursor = _read_varlen(payload, cursor + 1)
            meta = payload[cursor : cursor + length]
            cursor += length
            if meta_type == 0x03:
                track_name = meta.decode("utf-8", errors="replace").strip()
            elif meta_type == 0x51 and len(meta) == 3:
                microseconds = int.from_bytes(meta, "big")
                if microseconds > 0:
                    tempos.append(60_000_000.0 / microseconds)
            elif meta_type == 0x2F:
                break
            continue

        if status in {0xF0, 0xF7}:
            length, cursor = _read_varlen(payload, cursor)
            cursor += length
            continue

        event_type = status & 0xF0
        channel = status & 0x0F
        data_length = 1 if event_type in {0xC0, 0xD0} else 2
        event_data = payload[cursor : cursor + data_length]
        cursor += data_length
        if len(event_data) != data_length:
            raise ValueError("Unexpected end of MIDI event.")

        if event_type == 0xB0 and event_data[0] in {7, 11}:
            value = max(0.0, min(1.0, event_data[1] / 127.0))
            if event_data[0] == 7:
                channel_volume[channel] = value
            else:
                channel_expression[channel] = value
        elif event_type == 0x90 and event_data[1] > 0:
            note_volume = (
                (event_data[1] / 127.0)
                * channel_volume[channel]
                * channel_expression[channel]
            )
            active.setdefault((channel, event_data[0]), []).append(
                (tick, note_volume)
            )
        elif event_type in {0x80, 0x90}:
            starts = active.get((channel, event_data[0]))
            if starts:
                start_tick, note_volume = starts.pop(0)
                if tick > start_tick:
                    intervals.append(
                        _MidiInterval(
                            note=event_data[0],
                            start_tick=start_tick,
                            end_tick=tick,
                            volume=note_volume,
                        )
                    )

    return track_name, intervals, tempos


def _read_varlen(data: bytes, cursor: int) -> tuple[int, int]:
    value = 0
    for _ in range(4):
        if cursor >= len(data):
            raise ValueError("Unexpected end of MIDI variable-length value.")
        byte = data[cursor]
        cursor += 1
        value = (value << 7) | (byte & 0x7F)
        if byte < 0x80:
            return value, cursor
    raise ValueError("Invalid MIDI variable-length value.")


def _measure_range_to_ticks(
    *,
    start_measure: int | None,
    end_measure: int | None,
    ticks_per_beat: int,
    beats_per_bar: int,
) -> tuple[int | None, int | None]:
    if beats_per_bar <= 0:
        raise ValueError("beats_per_bar must be greater than zero.")
    if start_measure is None and end_measure is None:
        return None, None

    first_measure = 1 if start_measure is None else int(start_measure)
    if first_measure < 1:
        raise ValueError("start_measure must be 1 or greater.")
    if end_measure is not None and int(end_measure) < first_measure:
        raise ValueError("end_measure must be greater than or equal to start_measure.")

    measure_ticks = ticks_per_beat * beats_per_bar
    start_tick = (first_measure - 1) * measure_ticks
    end_tick = int(end_measure) * measure_ticks if end_measure is not None else None
    return start_tick, end_tick


def _slice_intervals(
    intervals: list[_MidiInterval],
    *,
    start_tick: int | None,
    end_tick: int | None,
) -> list[_MidiInterval]:
    if start_tick is None and end_tick is None:
        return intervals

    offset = start_tick or 0
    sliced: list[_MidiInterval] = []
    for interval in intervals:
        clipped_start = max(interval.start_tick, offset)
        clipped_end = (
            min(interval.end_tick, end_tick)
            if end_tick is not None
            else interval.end_tick
        )
        if clipped_end <= clipped_start:
            continue
        sliced.append(
            _MidiInterval(
                note=interval.note,
                start_tick=clipped_start - offset,
                end_tick=clipped_end - offset,
                volume=interval.volume,
            )
        )
    return sliced


def _intervals_to_notation(
    intervals: list[_MidiInterval],
    *,
    bpm: float,
    ticks_per_beat: int,
    quantize: int,
    beats_per_bar: int,
    transpose_to_range: bool,
    track_gain: float = 1.0,
    include_origin_boundary: bool = False,
    notation_end_tick: int | None = None,
) -> tuple[str, int]:
    if not intervals:
        return "", 0

    boundary_ticks = (
        {interval.start_tick for interval in intervals}
        | {interval.end_tick for interval in intervals}
    )
    if include_origin_boundary:
        boundary_ticks.add(0)
    if notation_end_tick is not None:
        boundary_ticks.add(notation_end_tick)
    boundaries = sorted(boundary_ticks)
    events: list[tuple[tuple[int, ...], float, float]] = []
    for start, end in zip(boundaries, boundaries[1:]):
        if end <= start:
            continue
        active_intervals = tuple(
            interval
            for interval in intervals
            if interval.start_tick <= start and interval.end_tick >= end
        )
        notes = tuple(sorted({interval.note for interval in active_intervals}))
        volume = _quantize_volume(
            sum(interval.volume for interval in active_intervals)
            / max(1, len(active_intervals))
        )
        beats = _quantize_beats(
            (end - start) / float(ticks_per_beat), quantize=quantize
        )
        if beats > 0:
            events.append((notes, beats, volume))

    merged: list[tuple[tuple[int, ...], float, float]] = []
    for notes, beats, volume in events:
        if merged and merged[-1][0] == notes and merged[-1][2] == volume:
            previous_notes, previous_beats, previous_volume = merged[-1]
            merged[-1] = (previous_notes, previous_beats + beats, previous_volume)
        else:
            merged.append((notes, beats, volume))

    tokens = []
    if track_gain != 1.0:
        tokens.append(f"^{_format_number(track_gain)}")
    tokens.append(f"@{_format_number(bpm)}")
    current_bar_beat = 0.0
    event_count = 0
    current_volume = 1.0
    for notes, beats, volume in merged:
        token = _event_to_token(notes, beats, transpose_to_range=transpose_to_range)
        if token is None:
            continue
        if notes and volume != current_volume:
            tokens.append(f"!{_format_number(volume)}")
            current_volume = volume
        tokens.append(token)
        event_count += 1
        current_bar_beat += beats
        if beats_per_bar > 0 and current_bar_beat >= beats_per_bar:
            tokens.append("|")
            current_bar_beat %= beats_per_bar

    if tokens[-1] == "|":
        tokens.pop()
    return " ".join(tokens), event_count


def _event_to_token(
    notes: tuple[int, ...], beats: float, *, transpose_to_range: bool
) -> str | None:
    duration = _format_duration(beats)
    if not notes:
        return f"-{duration}"

    note_tokens = [
        token
        for note in notes
        if (token := midi_note_to_ascii(note, transpose_to_range=transpose_to_range))
    ]
    if not note_tokens:
        return None
    if len(note_tokens) == 1:
        return f"{note_tokens[0]}{duration}"
    return f"[{''.join(note_tokens)}]{duration}"


def _quantize_beats(beats: float, *, quantize: int) -> float:
    steps = max(1, int(quantize))
    return max(0.0, round(beats * steps) / steps)


def _quantize_volume(volume: float) -> float:
    return round(max(0.0, min(1.5, volume)), 2)


def _format_duration(beats: float) -> str:
    rounded = round(beats, 6)
    if rounded == 1.0:
        return ""
    if rounded > 1.0 and float(rounded).is_integer():
        return str(int(rounded))
    reciprocal = 1.0 / rounded if rounded else 0.0
    if reciprocal and abs(reciprocal - round(reciprocal)) < 1e-6:
        return f"/{int(round(reciprocal))}"
    return _format_number(rounded)


def _format_number(value: float) -> str:
    return f"{value:.6f}".rstrip("0").rstrip(".")


def _safe_track_name(name: str, *, fallback: str) -> str:
    replacements = str.maketrans(
        {
            "ä": "ae",
            "ö": "oe",
            "ü": "ue",
            "Ä": "ae",
            "Ö": "oe",
            "Ü": "ue",
            "ß": "ss",
        }
    )
    text = (name or fallback).strip().translate(replacements)
    cleaned = "".join(
        character.lower() if character.isascii() and character.isalnum() else "_"
        for character in text
    ).strip("_")
    return cleaned or fallback


def _unique_voice_name(voice_name: str, *, voice_counts: dict[str, int]) -> str:
    count = voice_counts.get(voice_name, 0) + 1
    voice_counts[voice_name] = count
    if count == 1:
        return voice_name
    return f"{voice_name}_{count}"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Convert a Standard MIDI file to the custom provider ASCII notation."
    )
    parser.add_argument("midi_path", type=Path)
    parser.add_argument("-o", "--output", type=Path)
    parser.add_argument(
        "--quantize",
        type=int,
        default=8,
        help="duration steps per beat; higher keeps finer timing",
    )
    parser.add_argument(
        "--beats-per-bar",
        type=int,
        default=4,
        help="beats per measure for bar separators and measure range selection",
    )
    parser.add_argument(
        "--start-measure",
        type=int,
        help="1-based first measure to include in the output",
    )
    parser.add_argument(
        "--end-measure",
        type=int,
        help="1-based last measure to include in the output, inclusive",
    )
    parser.add_argument(
        "--keep-octaves",
        action="store_true",
        help="drop notes outside C3..B5 instead of octave-transposing them",
    )
    args = parser.parse_args(argv)

    song = convert_midi_to_ascii(
        args.midi_path,
        quantize=args.quantize,
        beats_per_bar=args.beats_per_bar,
        start_measure=args.start_measure,
        end_measure=args.end_measure,
        transpose_to_range=not args.keep_octaves,
    )
    output = format_midi_ascii_song(song)
    if args.output:
        args.output.write_text(output + "\n", encoding="utf-8")
        print(f"Wrote {args.output} with {len(song.tracks)} track(s).")
    else:
        print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
