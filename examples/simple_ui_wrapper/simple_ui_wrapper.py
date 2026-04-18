"""Small tkinter wrapper around voice_conductor.

Run from the repository root after installing the package in editable mode:

    python examples/simple_ui_wrapper/simple_ui_wrapper.py

The UI is intentionally thin. The important part is the direct use of
``TTSManager``: list providers, list voices, synthesize audio, route playback,
and write a WAV.
"""

from __future__ import annotations

import os
from pathlib import Path
import sys
import tkinter as tk
from tkinter import filedialog, ttk

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    # This keeps the example runnable straight from a source checkout. Once the
    # package is installed, the normal environment import would work too.
    sys.path.insert(0, str(REPO_ROOT))

from voice_conductor import SynthesizedAudio, TTSManager


EXAMPLE_DIR = Path(__file__).resolve().parent
DEFAULT_TEXT = "Wow?! We're really skipping to the examples?"


def build_manager() -> TTSManager:
    """Build the package entry point used by the UI."""

    current_dir = Path.cwd()
    try:
        # Let voice_conductor discover this example's voice_conductor.config.jsonc.
        os.chdir(EXAMPLE_DIR)
        return TTSManager()
    finally:
        os.chdir(current_dir)


def provider_names(manager: TTSManager) -> list[str]:
    """Ask voice_conductor which configured providers are currently usable."""

    return manager.list_providers()


def voice_names(manager: TTSManager, provider: str) -> list[str]:
    """Return provider-local voice ids that can be passed back to synthesis."""

    prefix = f"{provider}:"
    return [voice.id.removeprefix(prefix) for voice in manager.list_voices(provider)]


def apply_speed(manager: TTSManager, provider: str | None, speed: float) -> None:
    """Update the selected provider config before synthesis."""

    if provider is None:
        return

    settings = manager.settings.provider_settings(provider)
    if hasattr(settings, "speed"):
        settings.speed = round(speed, 2)


def synthesize_line(
    manager: TTSManager,
    text: str,
    *,
    provider: str | None,
    voice: str | None,
    speed: float,
    use_cache: bool,
    refresh_cache: bool,
) -> SynthesizedAudio:
    """Generate audio through the same public API an app would use."""

    apply_speed(manager, provider, speed)
    return manager.synthesize_voice(
        text,
        provider=provider,
        voice=voice,
        use_cache=use_cache,
        refresh_cache=refresh_cache,
    )


class VoiceConductorApp(tk.Tk):
    """Minimal desktop UI that wraps the high-level TTSManager API."""

    def __init__(self) -> None:
        super().__init__()
        self.title("VoiceConductor simple UI wrapper")
        self.geometry("720x460")
        self.minsize(620, 420)

        self.manager = build_manager()

        self.provider_var = tk.StringVar()
        self.voice_var = tk.StringVar()
        self.route_var = tk.StringVar(value="speakers")
        self.speed_var = tk.DoubleVar(value=1.0)
        self.speed_label_var = tk.StringVar(value="1.00x")
        self.use_cache_var = tk.BooleanVar(value=True)
        self.refresh_cache_var = tk.BooleanVar(value=False)
        self.status_var = tk.StringVar(value="Ready. The demo provider works offline.")

        self._build_layout()
        self.refresh_providers()

    def _build_layout(self) -> None:
        root = ttk.Frame(self, padding=16)
        root.pack(fill=tk.BOTH, expand=True)
        root.columnconfigure(0, weight=1)
        root.rowconfigure(1, weight=1)

        controls = ttk.Frame(root)
        controls.grid(row=0, column=0, sticky="ew")
        controls.columnconfigure(1, weight=1)
        controls.columnconfigure(3, weight=1)

        ttk.Label(controls, text="Provider").grid(row=0, column=0, sticky="w", padx=(0, 8))
        self.provider_combo = ttk.Combobox(
            controls,
            textvariable=self.provider_var,
            state="readonly",
        )
        self.provider_combo.grid(row=0, column=1, sticky="ew", padx=(0, 16))
        self.provider_combo.bind("<<ComboboxSelected>>", self._on_provider_changed)

        ttk.Label(controls, text="Voice").grid(row=0, column=2, sticky="w", padx=(0, 8))
        self.voice_combo = ttk.Combobox(controls, textvariable=self.voice_var, state="readonly")
        self.voice_combo.grid(row=0, column=3, sticky="ew")

        settings_frame = ttk.LabelFrame(root, text="Synthesis")
        settings_frame.grid(row=2, column=0, sticky="ew", pady=(12, 0))
        settings_frame.columnconfigure(1, weight=1)
        settings_frame.columnconfigure(3, weight=1)

        ttk.Label(settings_frame, text="Speed").grid(row=0, column=0, sticky="w", padx=8, pady=8)
        self.speed_scale = ttk.Scale(
            settings_frame,
            from_=0.5,
            to=2.0,
            variable=self.speed_var,
            command=self._on_speed_changed,
        )
        self.speed_scale.grid(row=0, column=1, sticky="ew", padx=(0, 8), pady=8)
        ttk.Label(settings_frame, textvariable=self.speed_label_var, width=6).grid(
            row=0,
            column=2,
            sticky="w",
            padx=(0, 8),
            pady=8,
        )

        route_frame = ttk.LabelFrame(root, text="Route")
        route_frame.grid(row=3, column=0, sticky="ew", pady=(12, 0))

        # Routes are just named outputs. ``speakers`` plays locally, ``mic``
        # targets a virtual cable when one is configured, and both asks
        # voice_conductor to route the same clip to both outputs.
        ttk.Radiobutton(route_frame, text="Speakers", variable=self.route_var, value="speakers").pack(
            side=tk.LEFT, padx=8, pady=8
        )
        ttk.Radiobutton(route_frame, text="Mic", variable=self.route_var, value="mic").pack(
            side=tk.LEFT, padx=8, pady=8
        )
        ttk.Radiobutton(route_frame, text="Both", variable=self.route_var, value="both").pack(
            side=tk.LEFT, padx=8, pady=8
        )

        cache_frame = ttk.LabelFrame(root, text="Cache")
        cache_frame.grid(row=4, column=0, sticky="ew", pady=(12, 0))

        # Phrase caching means repeated lines do not need to be synthesized
        # again. Refresh cache is useful when you want a new take of the same
        # phrase after changing provider settings.
        ttk.Checkbutton(cache_frame, text="Use cache", variable=self.use_cache_var).pack(
            side=tk.LEFT, padx=8, pady=8
        )
        ttk.Checkbutton(cache_frame, text="Refresh cache", variable=self.refresh_cache_var).pack(
            side=tk.LEFT, padx=8, pady=8
        )

        text_frame = ttk.LabelFrame(root, text="Line")
        text_frame.grid(row=1, column=0, sticky="nsew", pady=(12, 0))
        text_frame.rowconfigure(0, weight=1)
        text_frame.columnconfigure(0, weight=1)

        self.text_box = tk.Text(text_frame, wrap=tk.WORD, height=8)
        self.text_box.insert("1.0", DEFAULT_TEXT)
        self.text_box.grid(row=0, column=0, sticky="nsew", padx=8, pady=8)

        button_frame = ttk.Frame(root)
        button_frame.grid(row=5, column=0, sticky="ew", pady=(12, 0))

        ttk.Button(button_frame, text="Speak", command=self.speak).pack(side=tk.LEFT, padx=(0, 8))
        ttk.Button(button_frame, text="Export WAV", command=self.export_wav).pack(
            side=tk.LEFT, padx=(0, 8)
        )
        ttk.Button(button_frame, text="Refresh Voices", command=self.refresh_voices).pack(side=tk.LEFT)

        ttk.Label(root, textvariable=self.status_var, wraplength=700).grid(
            row=6,
            column=0,
            sticky="ew",
            pady=(12, 0),
        )

    def _selected_routes(self) -> str | list[str]:
        selected = self.route_var.get()
        if selected == "both":
            return ["speakers", "mic"]
        return selected

    def _text(self) -> str:
        return self.text_box.get("1.0", tk.END).strip()

    def _provider(self) -> str | None:
        # Empty provider means "use the configured fallback chain".
        provider = self.provider_var.get().strip()
        return provider or None

    def _voice(self) -> str | None:
        # Empty voice means "use the provider's configured default voice".
        voice = self.voice_var.get().strip()
        return voice or None

    def _on_provider_changed(self, _event: tk.Event) -> None:
        self.refresh_voices()

    def _on_speed_changed(self, _value: str) -> None:
        self.speed_label_var.set(f"{self.speed_var.get():.2f}x")

    def apply_provider_config(self) -> None:
        apply_speed(self.manager, self._provider(), self.speed_var.get())

    def _voice_values_for_provider(self, provider: str) -> list[str]:
        return voice_names(self.manager, provider)

    def refresh_voices(self) -> None:
        provider = self._provider()
        if provider is None:
            self.voice_combo["values"] = []
            self.voice_var.set("")
            self.status_var.set("No configured provider is currently available.")
            return

        values = self._voice_values_for_provider(provider)
        self.voice_combo["values"] = values
        current = self.voice_var.get().strip()
        if values and current not in values:
            self.voice_var.set(values[0])
        elif not values:
            self.voice_var.set("")
        self.status_var.set(
            f"{provider!r} voices: " + (", ".join(values[:8]) if values else "none reported")
        )

    def synthesize_current_line(self) -> SynthesizedAudio | None:
        text = self._text()
        if not text:
            self.status_var.set("Type a line first.")
            return None

        return synthesize_line(
            self.manager,
            text,
            provider=self._provider(),
            voice=self._voice(),
            speed=self.speed_var.get(),
            use_cache=self.use_cache_var.get(),
            refresh_cache=self.refresh_cache_var.get(),
        )

    def speak(self) -> None:
        audio = self.synthesize_current_line()
        if audio is None:
            return

        task = self.manager.route(audio, self._selected_routes(), background=True)
        self.status_var.set(f"Queued {audio.duration_seconds:.2f}s for playback.")
        self.after(100, lambda: self._poll_speak_task(task))

    def _poll_speak_task(self, task) -> None:
        if not task.done():
            self.after(100, lambda: self._poll_speak_task(task))
            return

        result = task.result(timeout=0)
        devices = ", ".join(device.name for device in result.devices.values())
        self.status_var.set(f"Played {result.audio.duration_seconds:.2f}s through {devices}.")

    def export_wav(self) -> None:
        audio = self.synthesize_current_line()
        if audio is None:
            return

        target = filedialog.asksaveasfilename(
            title="Export synthesized WAV",
            defaultextension=".wav",
            filetypes=[("WAV audio", "*.wav")],
            initialdir=str(EXAMPLE_DIR),
            initialfile="VoiceConductor-example.wav",
        )
        if not target:
            self.status_var.set("Export cancelled.")
            return

        written = audio.copy_to(target)
        self.status_var.set(f"Exported {audio.duration_seconds:.2f}s WAV to {written}.")

    def refresh_providers(self) -> None:
        providers = provider_names(self.manager)
        current = self.provider_var.get().strip()
        default_provider = self.manager.settings.voice_conductor.default_provider
        self.provider_combo["values"] = providers
        if current in providers:
            self.provider_var.set(current)
        elif default_provider in providers:
            self.provider_var.set(default_provider)
        elif providers:
            self.provider_var.set(providers[0])
        else:
            self.provider_var.set("")
        self.status_var.set("Available providers: " + (", ".join(providers) or "none"))
        self.refresh_voices()


if __name__ == "__main__":
    VoiceConductorApp().mainloop()
