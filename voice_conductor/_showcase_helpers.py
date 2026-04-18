"""Private notebook display helpers for the voice_conductor showcase."""

from __future__ import annotations

from IPython.display import Audio, display

from html import escape
import json
from uuid import uuid4

import pandas as pd

from voice_conductor.types import SynthesizedAudio


__all__ = [
    "audio_preview",
    "audio_summary",
    "build_word_timing_transcript_html",
    "render_word_timing_transcript",
    "summarize_output_devices",
]

def audio_preview(audio):
    return Audio(audio.samples[:, 0], rate=audio.sample_rate, autoplay=True)


def audio_summary(audio):
    word_timing = audio.metadata.get("word_timing") or []
    return pd.DataFrame(
        [
            {
                "provider": audio.provider,
                "voice": audio.voice,
                "duration_seconds": round(audio.duration_seconds, 3),
                "sample_rate": audio.sample_rate,
                "channels": audio.channels,
                "frames": audio.frame_count,
                "word_timing_items": len(word_timing),
                "style": audio.metadata.get("style"),
            }
        ]
    )

def summarize_output_devices(devices):
    return [
        {
            "id": device.id,
            "name": device.name,
            "hostapi": device.hostapi,
            "default": device.is_default,
            "virtual_cable": device.is_virtual_cable,
            "channels": device.max_output_channels,
            "sample_rate": device.default_samplerate,
        }
        for device in devices
    ]
    

def build_word_timing_transcript_html(
    audio: SynthesizedAudio,
    *,
    label: str = "Now speaking",
) -> str:
    """Build inline HTML/JS that highlights the current word over time."""
    word_timing = audio.metadata.get("word_timing") or []
    if not word_timing:
        return (
            "<div class=\"voice-conductor-word-sync voice-conductor-word-sync--missing\">"
            "Word timing metadata is unavailable for this audio."
            "</div>"
        )

    container_id = f"voice-conductor-word-sync-{uuid4().hex}"
    duration_seconds = max(audio.duration_seconds, float(word_timing[-1]["end_seconds"]))
    word_spans = " ".join(
        (
            f"<span class=\"voice-conductor-word\""
            f" data-start=\"{float(item['start_seconds']):.6f}\""
            f" data-end=\"{float(item['end_seconds']):.6f}\">"
            f"{escape(str(item['text']))}</span>"
        )
        for item in word_timing
    )
    label_html = (
        f"<div class=\"voice-conductor-word-sync__label\">{escape(label)}</div>"
        if label
        else ""
    )

    return f"""
<div id="{container_id}" class="voice-conductor-word-sync" data-duration="{duration_seconds:.6f}">
  <style>
    #{container_id} {{
      margin: 0.5rem 0 0.75rem;
      font-family: ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      line-height: 1.55;
      color: #f3f4f6;
      background: transparent;
    }}
    #{container_id} .voice-conductor-word-sync__label {{
      margin-bottom: 0.35rem;
      color: #cbd5e1;
      font-size: 0.9rem;
    }}
    #{container_id} .voice-conductor-word-sync__line {{
      font-size: 1.05rem;
      color: inherit;
      white-space: normal;
      font-weight: 500;
    }}
    #{container_id} .voice-conductor-word {{
      display: inline-block;
      padding: 0.04rem 0.18rem;
      border-radius: 6px;
      border: 1px solid transparent;
      color: #f3f4f6;
      opacity: 1;
      text-shadow: 0 0 0.01px currentColor;
      transition: background-color 80ms linear, color 80ms linear;
    }}
    #{container_id} .voice-conductor-word.is-active {{
      background: #fde047;
      color: #1f2937;
      border-color: rgba(251, 191, 36, 0.55);
      opacity: 1;
    }}
  </style>
  {label_html}
  <div class="voice-conductor-word-sync__line">{word_spans}</div>
</div>
<script>
(() => {{
  const root = document.getElementById({json.dumps(container_id)});
  if (!root) {{
    return;
  }}

  const words = Array.from(root.querySelectorAll(".voice-conductor-word"));
  if (!words.length) {{
    return;
  }}

  const duration = Number(root.dataset.duration || "0");
  const setActiveWord = (elapsedSeconds) => {{
    let activeIndex = words.length - 1;
    for (let index = 0; index < words.length; index += 1) {{
      const word = words[index];
      const start = Number(word.dataset.start);
      const end = Number(word.dataset.end);
      if (elapsedSeconds < start) {{
        activeIndex = Math.max(0, index - 1);
        break;
      }}
      if (elapsedSeconds >= start && (elapsedSeconds < end || index === words.length - 1)) {{
        activeIndex = index;
        break;
      }}
    }}

    words.forEach((word, index) => {{
      word.classList.toggle("is-active", index === activeIndex);
    }});
  }};

  let startedAt = null;
  const tick = (timestamp) => {{
    if (startedAt === null) {{
      startedAt = timestamp;
    }}
    const elapsedSeconds = Math.min((timestamp - startedAt) / 1000, duration);
    setActiveWord(elapsedSeconds);
    if (elapsedSeconds < duration) {{
      window.requestAnimationFrame(tick);
    }}
  }};

  setActiveWord(0);
  window.requestAnimationFrame(tick);
}})();
</script>
""".strip()


def render_word_timing_transcript(
    audio: SynthesizedAudio,
    *,
    label: str = "Now speaking",
):
    """Return a notebook-displayable transcript widget for demo audio."""
    html = build_word_timing_transcript_html(audio, label=label)
    try:
        from IPython.display import HTML
    except ImportError:
        return html
    return HTML(html)
