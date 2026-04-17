from __future__ import annotations

import sys
from pathlib import Path


EXAMPLE_DIR = Path(__file__).resolve().parents[1] / "examples" / "custom_provider_demo"
if str(EXAMPLE_DIR) not in sys.path:
    sys.path.insert(0, str(EXAMPLE_DIR))

import ascii_song_demo as demo
import midi_to_ascii


def test_ascii_song_provider_exposes_instrument_voices() -> None:
    manager = demo.build_manager()
    try:
        voices = [voice.id for voice in manager.list_voices(demo.PROVIDER_NAME)]
    finally:
        demo.unregister_provider(demo.PROVIDER_NAME)
        demo.unregister_provider_config(demo.PROVIDER_NAME)

    assert voices == [
        "tone:piano",
        "tone:banjo",
        "tone:bandoneon",
        "tone:bass",
        "tone:clarinet",
        "tone:marimba",
        "tone:oboe",
        "tone:recorder",
        "tone:tenor_sax",
        "tone:trumpet",
        "tone:tuba",
    ]


def test_ascii_song_banjo_voice_uses_its_own_recipe() -> None:
    manager = demo.build_manager()
    try:
        track = manager.synthesize_voice(
            "a s d",
            provider=demo.PROVIDER_NAME,
            voice="banjo",
            use_cache=False,
        )
    finally:
        demo.unregister_provider(demo.PROVIDER_NAME)
        demo.unregister_provider_config(demo.PROVIDER_NAME)

    assert track.voice == "tone:banjo"
    assert track.metadata["base_voice"] == "tone:banjo"
    assert track.frame_count > 0
    assert float(abs(track.samples).max()) > 0.0


def test_ascii_song_secondary_parts_use_base_voice_recipe() -> None:
    manager = demo.build_manager()
    try:
        track = manager.synthesize_voice(
            "a s d",
            provider=demo.PROVIDER_NAME,
            voice="bandoneon_2",
            use_cache=False,
        )
    finally:
        demo.unregister_provider(demo.PROVIDER_NAME)
        demo.unregister_provider_config(demo.PROVIDER_NAME)

    assert track.voice == "tone:bandoneon_2"
    assert track.metadata["base_voice"] == "tone:bandoneon"
    assert track.metadata["part_number"] == 2


def test_ascii_score_supports_repeats_chords_tempo_and_volume() -> None:
    events, bpm = demo.parse_ascii_score("@144 !0.5 ([adg] s/2)*2", default_bpm=120.0)

    assert bpm == 144.0
    assert len(events) == 4
    assert len(events[0].notes) == 3
    assert events[0].volume == 0.5
    assert events[1].beats == 0.5


def test_ascii_score_supports_track_gain_before_tempo() -> None:
    events, bpm = demo.parse_ascii_score("^0.25 @144 !0.8 a s", default_bpm=120.0)

    assert bpm == 144.0
    assert len(events) == 2
    assert events[0].volume == 0.2
    assert events[1].volume == 0.2


def test_ascii_score_supports_accidentals_inside_chords() -> None:
    chord_events, _ = demo.parse_ascii_score("[a#d]", default_bpm=120.0)
    single_events, _ = demo.parse_ascii_score("a# d", default_bpm=120.0)

    assert chord_events[0].notes == (
        single_events[0].notes[0],
        single_events[1].notes[0],
    )


def test_merge_tracks_returns_normalized_ensemble_audio() -> None:
    manager = demo.build_manager()
    try:
        tracks = [
            manager.synthesize_voice(
                "a s d [adg]",
                provider=demo.PROVIDER_NAME,
                voice=voice,
                use_cache=False,
            )
            for voice in ("bandoneon", "bandoneon_2", "tenor_sax")
        ]
        merged = demo.merge_tracks(tracks)
    finally:
        demo.unregister_provider(demo.PROVIDER_NAME)
        demo.unregister_provider_config(demo.PROVIDER_NAME)

    assert merged.voice == "tone:ensemble"
    assert merged.sample_rate == tracks[0].sample_rate
    assert merged.frame_count == max(track.frame_count for track in tracks)
    assert float(abs(merged.samples).max()) <= 0.95


def test_midi_note_to_ascii_maps_accidentals_and_transposes_octaves() -> None:
    assert midi_to_ascii.midi_note_to_ascii(60) == "a"
    assert midi_to_ascii.midi_note_to_ascii(61) == "a#"
    assert midi_to_ascii.midi_note_to_ascii(84) == "q"
    assert midi_to_ascii.midi_note_to_ascii(84, transpose_to_range=False) is None


def test_convert_midi_to_ascii_outputs_parseable_tracks(tmp_path: Path) -> None:
    midi_path = tmp_path / "tiny.mid"
    midi_path.write_bytes(_tiny_midi_file())

    song = midi_to_ascii.convert_midi_to_ascii(midi_path, quantize=4)

    assert song.bpm == 120.0
    assert len(song.tracks) == 1
    assert song.tracks[0].name == "piano"
    assert song.tracks[0].source_name == "Lead"
    assert song.tracks[0].notation == "@120 !0.5 [ad] -/2 s/2"

    events, bpm = demo.parse_ascii_score(song.tracks[0].notation, default_bpm=132.0)
    assert bpm == 120.0
    assert len(events) == 3
    assert len(events[0].notes) == 2
    assert events[0].volume == 0.5
    assert events[1].notes == ()
    assert events[1].beats == 0.5


def test_convert_midi_to_ascii_preserves_channel_volume_and_expression(
    tmp_path: Path,
) -> None:
    midi_path = tmp_path / "volume.mid"
    midi_path.write_bytes(_volume_midi_file())

    song = midi_to_ascii.convert_midi_to_ascii(midi_path, quantize=4)

    assert song.tracks[0].notation == "@120 !0.5 a !0.25 s"


def test_convert_midi_to_ascii_limits_output_to_measure_range(
    tmp_path: Path,
) -> None:
    midi_path = tmp_path / "measures.mid"
    midi_path.write_bytes(_four_measure_midi_file())

    song = midi_to_ascii.convert_midi_to_ascii(
        midi_path,
        quantize=4,
        start_measure=2,
        end_measure=3,
    )

    assert song.tracks[0].notation == "@120 s -3 | d -3"

    events, _ = demo.parse_ascii_score(song.tracks[0].notation, default_bpm=132.0)
    assert len(events) == 4
    assert events[0].notes
    assert events[1].beats == 3.0
    assert events[2].notes
    assert events[3].beats == 3.0


def test_convert_midi_to_ascii_clips_notes_at_measure_boundaries(
    tmp_path: Path,
) -> None:
    midi_path = tmp_path / "boundary.mid"
    midi_path.write_bytes(_boundary_crossing_midi_file())

    song = midi_to_ascii.convert_midi_to_ascii(
        midi_path,
        quantize=4,
        start_measure=2,
        end_measure=2,
    )

    assert song.tracks[0].notation == "@120 a2 -2"


def test_format_midi_ascii_song_returns_copy_pasteable_dictionary(
    tmp_path: Path,
) -> None:
    midi_path = tmp_path / "tiny.mid"
    midi_path.write_bytes(_tiny_midi_file())

    song = midi_to_ascii.convert_midi_to_ascii(midi_path, quantize=4)
    formatted = midi_to_ascii.format_midi_ascii_song(song)

    assert "song = {" in formatted
    assert "# MIDI track: Lead" in formatted
    assert "'piano': '@120 !0.5 [ad] -/2 s/2'" in formatted


def test_midi_track_names_map_to_playable_tone_voices() -> None:
    assert midi_to_ascii.midi_track_name_to_voice("Banjo Begleitung") == "banjo"
    assert midi_to_ascii.midi_track_name_to_voice("Flöte") == "recorder"
    assert midi_to_ascii.midi_track_name_to_voice("Trompete") == "trumpet"
    assert midi_to_ascii.midi_track_name_to_voice("Drums") == "marimba"
    assert midi_to_ascii.midi_track_name_to_voice("Bassoon") == "oboe"


def test_convert_midi_to_ascii_suffixes_duplicate_playable_voices(
    tmp_path: Path,
) -> None:
    midi_path = tmp_path / "duplicate.mid"
    midi_path.write_bytes(_two_banjo_tracks_midi_file())

    song = midi_to_ascii.convert_midi_to_ascii(midi_path, quantize=4)

    assert [track.name for track in song.tracks] == ["banjo", "banjo_2"]


def test_convert_midi_to_ascii_ducks_secondary_tracks_for_banjo_led_songs(
    tmp_path: Path,
) -> None:
    midi_path = tmp_path / "banjo-led.mid"
    midi_path.write_bytes(_banjo_and_flute_midi_file())

    song = midi_to_ascii.convert_midi_to_ascii(midi_path, quantize=4)
    formatted = midi_to_ascii.format_midi_ascii_song(song)

    assert [track.name for track in song.tracks] == ["banjo", "recorder"]
    assert [track.arrangement_role for track in song.tracks] == [
        "primary",
        "secondary",
    ]
    assert song.tracks[0].notation == "@120 a"
    assert song.tracks[1].notation == "^0.55 @120 d"
    assert "# Arrangement: secondary, gain x0.55" in formatted


def _tiny_midi_file() -> bytes:
    header = b"MThd" + (6).to_bytes(4, "big") + b"\x00\x01\x00\x01\x01\xe0"
    events = b"".join(
        [
            _varlen(0),
            b"\xff\x03",
            _varlen(4),
            b"Lead",
            _varlen(0),
            b"\xff\x51\x03\x07\xa1\x20",
            _varlen(0),
            b"\x90\x3c\x40",
            _varlen(0),
            b"\x90\x40\x40",
            _varlen(480),
            b"\x80\x3c\x00",
            _varlen(0),
            b"\x80\x40\x00",
            _varlen(240),
            b"\x90\x3e\x40",
            _varlen(240),
            b"\x80\x3e\x00",
            _varlen(0),
            b"\xff\x2f\x00",
        ]
    )
    return header + b"MTrk" + len(events).to_bytes(4, "big") + events


def _volume_midi_file() -> bytes:
    header = b"MThd" + (6).to_bytes(4, "big") + b"\x00\x01\x00\x01\x01\xe0"
    events = b"".join(
        [
            _varlen(0),
            b"\xff\x03",
            _varlen(6),
            b"Volume",
            _varlen(0),
            b"\xff\x51\x03\x07\xa1\x20",
            _varlen(0),
            b"\xb0\x07\x40",
            _varlen(0),
            b"\x90\x3c\x7f",
            _varlen(480),
            b"\x80\x3c\x00",
            _varlen(0),
            b"\xb0\x0b\x40",
            _varlen(0),
            b"\x90\x3e\x7f",
            _varlen(480),
            b"\x80\x3e\x00",
            _varlen(0),
            b"\xff\x2f\x00",
        ]
    )
    return header + b"MTrk" + len(events).to_bytes(4, "big") + events


def _two_banjo_tracks_midi_file() -> bytes:
    header = b"MThd" + (6).to_bytes(4, "big") + b"\x00\x01\x00\x02\x01\xe0"
    first = _single_note_track("Banjo", note=60)
    second = _single_note_track("Banjo Begleitung", note=64)
    return (
        header
        + b"MTrk"
        + len(first).to_bytes(4, "big")
        + first
        + b"MTrk"
        + len(second).to_bytes(4, "big")
        + second
    )


def _banjo_and_flute_midi_file() -> bytes:
    header = b"MThd" + (6).to_bytes(4, "big") + b"\x00\x01\x00\x02\x01\xe0"
    first = _single_note_track("Banjo", note=60)
    second = _single_note_track("Flute", note=64)
    return (
        header
        + b"MTrk"
        + len(first).to_bytes(4, "big")
        + first
        + b"MTrk"
        + len(second).to_bytes(4, "big")
        + second
    )


def _four_measure_midi_file() -> bytes:
    header = b"MThd" + (6).to_bytes(4, "big") + b"\x00\x01\x00\x01\x01\xe0"
    events = [
        _varlen(0),
        b"\xff\x03",
        _varlen(8),
        b"Measures",
        _varlen(0),
        b"\xff\x51\x03\x07\xa1\x20",
    ]
    tick = 0
    for measure_index, note in enumerate((60, 62, 64, 65)):
        note_tick = measure_index * 1920
        events.extend(
            [
                _varlen(note_tick - tick),
                bytes([0x90, note, 0x7F]),
                _varlen(480),
                bytes([0x80, note, 0]),
            ]
        )
        tick = note_tick + 480
    events.extend([_varlen(0), b"\xff\x2f\x00"])
    payload = b"".join(events)
    return header + b"MTrk" + len(payload).to_bytes(4, "big") + payload


def _boundary_crossing_midi_file() -> bytes:
    header = b"MThd" + (6).to_bytes(4, "big") + b"\x00\x01\x00\x01\x01\xe0"
    events = b"".join(
        [
            _varlen(0),
            b"\xff\x03",
            _varlen(8),
            b"Boundary",
            _varlen(0),
            b"\xff\x51\x03\x07\xa1\x20",
            _varlen(960),
            b"\x90\x3c\x7f",
            _varlen(1920),
            b"\x80\x3c\x00",
            _varlen(0),
            b"\xff\x2f\x00",
        ]
    )
    return header + b"MTrk" + len(events).to_bytes(4, "big") + events


def _single_note_track(name: str, *, note: int) -> bytes:
    encoded_name = name.encode("utf-8")
    return b"".join(
        [
            _varlen(0),
            b"\xff\x03",
            _varlen(len(encoded_name)),
            encoded_name,
            _varlen(0),
            b"\xff\x51\x03\x07\xa1\x20",
            _varlen(0),
            bytes([0x90, note, 0x7F]),
            _varlen(480),
            bytes([0x80, note, 0]),
            _varlen(0),
            b"\xff\x2f\x00",
        ]
    )


def _varlen(value: int) -> bytes:
    buffer = value & 0x7F
    value >>= 7
    while value:
        buffer <<= 8
        buffer |= ((value & 0x7F) | 0x80)
        value >>= 7

    output = []
    while True:
        output.append(buffer & 0xFF)
        if buffer & 0x80:
            buffer >>= 8
        else:
            break
    return bytes(output)
