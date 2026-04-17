# voice-synth

`voice-synth` is an importable Python text-to-speech package for generating voice lines and routing them to speakers, a virtual microphone, or both. It is built for Windows-friendly voice chat workflows.

The main entry point is `TTSManager`.

## Features

- Provider fallback across ElevenLabs, Kokoro, Azure Speech, Windows Speech.
- SQLite phrase caching so repeated lines do not need to be synthesized again.
- Named playback routes for speakers and virtual mic devices.
- Background playback tasks for non-blocking speech.
- Playback lifecycle hooks.
- JSON configuration with provider credentials, default voices, route settings, and cache paths.

## Requirements

- Python 3.11 or newer.
- Optional audio playback support via `sounddevice`.
- Optional provider dependencies and credentials depending on the backend you want to use.

Install the package for local development:

```powershell
pip install -e .
```

Install audio playback support:

```powershell
pip install -e .[audio]
```

Install audio playback plus Kokoro support:

```powershell
pip install -e .[audio,kokoro]
```

## Quick Start

```python
from voice_synth import TTSManager

tts = TTSManager()
tts.speak("This is a test.", routes="speakers")
```

Route to a virtual mic:

```python
from voice_synth import TTSManager

tts = TTSManager()
tts.speak("Now, to the virtual microphone.", routes="mic")
```

Route to both speakers and mic:

```python
tts.speak("Routed to both output devices.", routes=["speakers", "mic"])
```

Synthesize once, then route the resulting audio:

```python
audio = tts.synthesize_voice("This audio sample is stored in audio.")
result = tts.route(audio, routes=["speakers", "mic"])
print(result.routes)
```

## Configuration

By default, `voice_synth` looks for one of these files in the current working directory:

- `voice_synth.config.jsonc`
- `voice_synth.config.json`

Start from `voice_synth.config.example.jsonc`, then fill in only the providers and routes you use. 
If one is not found, one will be automatically generated.



Provider selection follows `voice_synth.provider_chain`. When `speak()` or `synthesize_voice()` does not specify a provider, the manager uses the first available provider in that chain.

## Providers

Built-in providers:

| Provider | Use case | Availability |
| --- | --- | --- |
| `elevenlabs` | Hosted high-quality voices. | Requires API key. |
| `kokoro` | Local Kokoro synthesis. | Requires the `kokoro` extra and model access. |
| `azure` | Azure neural voices. | Requires Speech key and region. |
| `windows` | Installed Windows System.Speech voices. | Requires Windows speech support. |
| `demo` | Offline test voice. | No external service. |

List available providers:

```python
from voice_synth import TTSManager

tts = TTSManager()
print(tts.list_providers())
```

List voices for a provider:

```python
for voice in tts.list_voices("windows"):
    print(voice.id, voice.name)
```

## Audio Routes

Routes are named outputs. The default route names are:

- `speakers`
- `mic`

You can pass one route name or a list of route names:

```python
tts.speak("Hello, World!", routes="speakers")
tts.speak("Hello, World!", routes=["speakers", "mic"])
```

Use `docs/mic-setup.md` for the Voicemeeter virtual microphone setup.

## Cache

Synthesized phrases are cached in SQLite. Cache entries are keyed by:

- text
- provider
- normalized voice key
- provider settings that affect audio output

Useful cache methods:

```python
tts.invalidate_synthesis_cache(text="Hello, World!")
tts.invalidate_synthesis_cache(provider="elevenlabs")
tts.clear_synthesis_cache()
```

Pass `refresh_cache=True` to regenerate a phrase and replace the cached entry:

```python
tts.speak("New take.", refresh_cache=True)
```

## Background Playback

Use `background=True` when the caller should continue immediately:

```python
task = tts.speak("Now we're not blocking the main thread.", routes="mic", background=True)
result = task.result(timeout=10)
```

## Push-To-Talk Hooks

Playback hooks run after audio and routes are ready and after playback completes. They are useful for pressing and releasing push-to-talk around virtual mic playback.

```python
from voice_synth import PlaybackHooks, TTSManager

tts = TTSManager()

tts.speak(
    "Swing on contact.",
    routes="mic",
    hooks=PlaybackHooks(
        on_audio_ready=lambda event: press_push_to_talk(),
        on_playback_complete=lambda event: release_push_to_talk(),
    ),
)
```

## Development

Run tests:

```powershell
pytest
```

Run a focused test file:

```powershell
pytest tests/test_manager.py
```

Useful project files:

- `voice_synth/manager.py`: high-level public orchestration.
- `voice_synth/config.py`: JSONC settings loading and serialization.
- `voice_synth/providers/`: provider adapters and registry.
- `voice_synth/audio/`: device discovery, playback, and route resolution.
- `voice_synth/phrase_cache.py`: SQLite-backed phrase cache.
- `docs/mic-setup.md`: virtual microphone setup guide.
