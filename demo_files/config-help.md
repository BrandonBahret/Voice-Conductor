# voice-synth config help

Generated next to `voice_synth.config.jsonc` so the config can stay compact and this guide can stay easy to scan.

## Edit map

| Area | Use it for | Start with |
| --- | --- | --- |
| `voice_synth` | Provider order, routing, and cache behavior. | `provider_chain` then `route_config` |
| `voice_synth.route_config` | Named speaker and virtual-mic playback targets. | `speakers` and `mic` routes |
| `providers` | Credentials, voices, models, and provider-specific tuning. | The provider named first in `provider_chain` |

## Quick changes

| When you want to... | Edit... |
| --- | --- |
| Try providers in a different order | `voice_synth.provider_chain` |
| Force one provider when no chain is set | `voice_synth.default_provider` |
| Send playback to speakers or a virtual mic | `voice_synth.route_config` |
| Pick a new default voice | `providers.<name>.default_voice` |
| Move or expire caches | `voice_synth.cache` |

## Available voices

Use the value in the `Voice id` column for `providers.<name>.default_voice`. Live provider lists come from the provider metadata cache when possible.

### ElevenLabs

Voice list unavailable: ElevenLabs requires providers.elevenlabs.api_key.

### Azure Speech

Voice list unavailable: Azure Speech requires providers.azure.speech_key and providers.azure.region.

### Kokoro

6 voices found.

| Voice | Voice id | Details |
| --- | --- | --- |
| af_heart | `af_heart` | - |
| af_sky | `af_sky` | - |
| am_adam | `am_adam` | - |
| am_michael | `am_michael` | - |
| bf_emma | `bf_emma` | - |
| bm_george | `bm_george` | - |

### Windows Speech

3 voices found.

| Voice | Voice id | Details |
| --- | --- | --- |
| Microsoft David Desktop | `david` | en-US |
| Microsoft Hazel Desktop | `hazel` | en-GB |
| Microsoft Zira Desktop | `zira` | en-US |

### Demo

3 voices found.

| Voice | Voice id | Details |
| --- | --- | --- |
| Animalese-ish | `animalese` | gibberish |
| SNES Pilot Comms | `pilot` | gibberish |
| Robot Radio | `robot` | gibberish |

### Guided Bonus

3 voices found.

| Voice | Voice id | Details |
| --- | --- | --- |
| Animalese-ish | `demo:animalese` | gibberish |
| SNES Pilot Comms | `demo:pilot` | gibberish |
| Robot Radio | `demo:robot` | gibberish |


## Field reference

Field names match the nested JSON path in `voice_synth.config.jsonc`.

### Voice synth settings

`voice_synth`

| Field | Notes |
| --- | --- |
| `voice_synth.default_provider` | Single preferred provider name used when provider_chain is not configured. |
| `voice_synth.provider_chain` | Ordered provider names to try for synthesis before falling back to availability-based selection. |
| `voice_synth.route_config` | Default audio device targets used for speaker and virtual-mic routing. |
| `voice_synth.cache` | Phrase-cache and provider-metadata cache settings. |

### Cache

`voice_synth.cache`

| Field | Notes |
| --- | --- |
| `voice_synth.cache.path` | SQLite phrase-cache file used to reuse synthesized audio; defaults under root. |
| `voice_synth.cache.api_dir` | Directory for provider metadata caches such as voice and model lists; defaults under root. |
| `voice_synth.cache.ttl_seconds` | Optional provider metadata cache lifetime in seconds; None keeps entries until manually invalidated. |
| `voice_synth.cache.root` | Base directory used to derive default phrase and provider cache locations. |

### Provider settings

`providers`

| Field | Notes |
| --- | --- |
| `providers.elevenlabs` | ElevenLabs provider credentials, voice, model, format, and voice-setting overrides. |
| `providers.azure` | Azure Speech provider credentials and default neural voice. |
| `providers.kokoro` | Kokoro local-provider auth, voice, and language settings. |
| `providers.windows` | Windows System.Speech provider voice and volume settings. |
| `providers.demo` | Dependency-free demo provider voice and speed settings. |

### ElevenLabs settings

`providers.elevenlabs`

| Field | Notes |
| --- | --- |
| `providers.elevenlabs.api_key` | ElevenLabs API key sent as the xi-api-key request header. |
| `providers.elevenlabs.default_voice` | ElevenLabs voice name or voice id used when synthesis does not specify one. |
| `providers.elevenlabs.model_id` | ElevenLabs text-to-speech model id used in synthesis requests. |
| `providers.elevenlabs.output_format` | ElevenLabs generated-audio format string, such as codec_sample-rate_bitrate or a pcm_* format. |
| `providers.elevenlabs.speed` | ElevenLabs voice-settings speed multiplier; 1.0 means normal speed. |
| `providers.elevenlabs.language_code` | Optional ElevenLabs language code included in synthesis requests. |
| `providers.elevenlabs.stability` | Optional ElevenLabs voice-setting override controlling stability and generation randomness. |
| `providers.elevenlabs.similarity_boost` | Optional ElevenLabs voice-setting override controlling how closely output adheres to the original voice. |
| `providers.elevenlabs.style` | Optional ElevenLabs voice-setting override that exaggerates the source voice style. |
| `providers.elevenlabs.speaker_boost` | Optional ElevenLabs voice-setting override for use_speaker_boost, trading latency for speaker similarity. |

### Azure Speech settings

`providers.azure`

| Field | Notes |
| --- | --- |
| `providers.azure.speech_key` | Azure Speech resource key sent as the Ocp-Apim-Subscription-Key header. |
| `providers.azure.region` | Azure Speech resource region used to build text-to-speech REST endpoints. |
| `providers.azure.default_voice` | Azure neural voice name used in the SSML voice element by default. |
| `providers.azure.speed` | Azure SSML prosody rate multiplier clamped to the supported speech range. |
| `providers.azure.language_code` | Optional Azure SSML xml:lang code; None uses en-US. |

### Kokoro settings

`providers.kokoro`

| Field | Notes |
| --- | --- |
| `providers.kokoro.hf_token` | Hugging Face token required before loading Kokoro model assets. |
| `providers.kokoro.default_voice` | Kokoro voice preset or voice tensor name used when synthesis does not specify one. |
| `providers.kokoro.language_code` | Kokoro KPipeline language code; it should match the configured Kokoro voice. |
| `providers.kokoro.speed` | Kokoro synthesis speed multiplier passed to the local pipeline. |

### Windows Speech settings

`providers.windows`

| Field | Notes |
| --- | --- |
| `providers.windows.default_voice` | Provider-local Windows System.Speech voice id selected before speaking. |
| `providers.windows.volume` | Windows SpeechSynthesizer output volume from 0 through 100; None uses 100. |
| `providers.windows.speed` | Windows speech rate multiplier mapped onto the System.Speech -10 through 10 rate. |

### Demo settings

`providers.demo`

| Field | Notes |
| --- | --- |
| `providers.demo.default_voice` | Demo provider-local voice id used when synthesis does not specify one. |
| `providers.demo.speed` | Demo synthesis speed multiplier; 1.0 means normal speed. |


## Provider notes

- `providers.elevenlabs.default_voice` accepts an ElevenLabs voice name or id; phrase caching stores the stable voice id.
- `providers.kokoro.default_voice` should be a Kokoro voice id such as `af_heart`.
- `providers.windows.default_voice` should be a short provider-local voice id such as `david` or `zira`; installed Windows voice names still work.
- `providers.demo.default_voice` should be a short provider-local voice id such as `animalese`.
- Inline JSONC voice hints are intentionally truncated; call `list_voices(provider)` for the complete live list.
