# Virtual Mic Setup

This guide routes synthesized speech into any voice chat app with Voicemeeter Banana or another virtual cable.

## Device Direction

`voice-synth` plays to Windows playback devices. Voicemeeter names can be confusing:

- `VoiceMeeter ... Input` is the playback side that `voice-synth` should use.
- `VoiceMeeter ... Output` and `VoiceMeeter Out B*` are recording devices that your voice chat app should use.

If you pass a recording-side Voicemeeter name such as `VoiceMeeter Aux Output` or `VoiceMeeter Out B2`, the device resolver maps it back to the matching playback-side `VoiceMeeter Aux Input` when possible.

## Recommended Virtual Mic Path

- `voice-synth` route: `VoiceMeeter Aux Input (VB-Audio VoiceMeeter AUX VAIO)`
- Voicemeeter bus: `B2`
- voice chat input: `VoiceMeeter Aux Output (VB-Audio VoiceMeeter AUX VAIO)` or `VoiceMeeter Out B2`

That keeps TTS on the AUX strip instead of mixing it with desktop audio on the main VAIO path.

## Install Audio Support

```console
pip install -e .[audio]
```

Use this if you also want Kokoro:

```console
pip install -e .[audio,kokoro]
```

## Configure Routes

Most setups do not need route config. `TTSManager()` creates two routes automatically:

- `speakers`: your default Windows output device.
- `mic`: the first available virtual cable output device.

Start with the default manager API:

```python
from voice_synth import TTSManager

tts = TTSManager()
tts.speak("Testing the virtual mic.", routes="mic")
```

Check what the package selected:

```python
from voice_synth import TTSManager

tts = TTSManager()
print(tts.settings.voice_synth.route_config.get("speakers").device)
print(tts.settings.voice_synth.route_config.get("mic").device)
```

Route to speakers and mic:

```python
tts.speak("This plays in both places.", routes=["speakers", "mic"])
```

If Windows audio devices change while your app is running, refresh the selected routes:

```python
tts.refresh_audio_devices()
```

Only set devices explicitly if auto-detection chooses the wrong endpoint:

```python
from voice_synth import RouteConfig, Settings, TTSManager, VoiceSynthSettings

routes = RouteConfig(
    speaker_device="Speakers",
    mic_device="VoiceMeeter Aux Input (VB-Audio VoiceMeeter AUX VAIO)",
)

tts = TTSManager(settings=Settings(voice_synth=VoiceSynthSettings(route_config=routes)))
tts.speak("Testing the virtual mic.", routes="mic")
```

## Voicemeeter Banana

Recommended bus toggles:

- Real mic strip: `B2` on if you want your real mic mixed with TTS.
- `Voicemeeter AUX` strip for TTS: `B2` on.
- Desktop audio strip on `Voicemeeter VAIO`: `B2` off.
- `A1` on only for strips you want to hear locally.

Recommended Windows defaults:

- Windows output: real headphones or speakers.
- Windows input: real microphone.

Avoid making `VoiceMeeter Input` your global Windows output unless you intentionally route all desktop audio through Voicemeeter.

## Voice Chat App

Set your voice chat app microphone input to:

```text
VoiceMeeter Aux Output (VB-Audio VoiceMeeter AUX VAIO)
```

or:

```text
VoiceMeeter Out B2
```

## Verify Devices

```python
from voice_synth import TTSManager

tts = TTSManager()
for device in tts.list_output_devices():
    print(
        f"id={device.id} "
        f"name={device.name!r} "
        f"default={device.is_default} "
        f"virtual={device.is_virtual_cable}"
    )
```

Look for the Voicemeeter AUX input device with `virtual=True`.

## Smoke Test

Run these snippets from Python after installing the audio extra.

Route speech to the virtual mic:

```python
from voice_synth import TTSManager

tts = TTSManager()
result = tts.speak("Testing the virtual mic.", routes="mic")
print("routes:", result.routes)
print("mic device:", result.devices["mic"].name)
```

Named route:

```python
from voice_synth import TTSManager

tts = TTSManager()
audio = tts.synthesize_voice("Testing the virtual mic.")
result = tts.route(audio, routes=["mic"])
print("routes:", result.routes)
for name, device in result.devices.items():
    print(name, device.name)
```

## Push To Talk Hooks

```python
from voice_synth import PlaybackHooks, TTSManager

tts = TTSManager()

tts.speak(
    "Push-to-talk test.",
    routes=["mic"],
    hooks=PlaybackHooks(
        on_audio_ready=press_push_to_talk,
        on_playback_complete=release_push_to_talk,
    ),
)
```

## Troubleshooting

`Audio playback requires the 'sounddevice' package`

Install the audio extra:

```console
pip install -e .[audio]
```

`No virtual cable output device was found`

Install or enable Voicemeeter or VB-CABLE, then rerun the device listing script.

`Could not find output device matching ...`

Copy the exact visible playback device name from `tts.list_output_devices()`.

`Voice chat hears desktop audio`

Make sure the desktop audio strip is not routed to `B2`. Keep `B2` on for the TTS AUX strip and optionally your real mic strip.

`Voice chat hears nothing`

Check that `voice-synth` plays to the AUX input, the AUX strip routes to `B2`, and your voice chat app listens on the AUX output or `Out B2`.
