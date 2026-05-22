"""
Agent voice notifier demo.

Demonstrates the "voice as the agent's observability channel" pattern from
the blog:  when an agent finishes a long-running task it speaks the result
instead of logging to stderr.

Usage
-----
    python agent_notifier.py

The script simulates three long-running jobs (build, tests, deploy), announces
each result aloud via Voicebox, and plays the audio on macOS using `afplay`.
On Linux/Windows substitute the PLAY_CMD constant for your audio player.

Requires
--------
    pip install -r requirements.txt
    Voicebox desktop app running  →  http://127.0.0.1:17493
"""

import subprocess
import sys
import time
import random
from dataclasses import dataclass
from typing import Callable

from client import VoiceboxClient, VoiceboxError

# ── audio playback ────────────────────────────────────────────────────────────
# macOS: afplay   Linux: aplay / mpv   Windows: powershell Start-Process
import platform

_os = platform.system()
if _os == "Darwin":
    PLAY_CMD = ["afplay"]
elif _os == "Linux":
    PLAY_CMD = ["aplay", "-q"]
else:
    # Windows: play WAV via PowerShell
    PLAY_CMD = ["powershell", "-c", "Start-Process"]


def play_wav(path: str) -> None:
    """Play a WAV file using the platform-appropriate command."""
    try:
        subprocess.run([*PLAY_CMD, str(path)], check=True)
    except FileNotFoundError:
        print(f"[audio player not found — saved to {path}]")
    except subprocess.CalledProcessError as exc:
        print(f"[playback error: {exc}]")


# ── simulated jobs ─────────────────────────────────────────────────────────────


@dataclass
class Job:
    name: str
    duration: float          # simulated wall-clock seconds
    fail_chance: float       # 0.0 → always succeeds, 1.0 → always fails
    success_msg: str
    failure_msg: str

    def run(self) -> bool:
        """Simulate the job.  Returns True on success."""
        print(f"  ▶  {self.name} … ", end="", flush=True)
        time.sleep(self.duration)
        success = random.random() >= self.fail_chance
        print("✓ passed" if success else "✗ failed")
        return success


def ensure_profile(client: VoiceboxClient, prefer: str | None = None) -> str:
    """
    Return a usable profile name.

    Resolution order:
      1. Explicit *prefer* name (passed via --profile CLI arg)
      2. First Kokoro-backed profile (stable on MPS, no GPU crash risk)
      3. Any other existing profile
      4. Create a new Kokoro preset (Michael) if no profiles exist
    """
    profiles = client.list_profiles()

    if prefer:
        for p in profiles:
            if p.get("name", "").lower() == prefer.lower():
                return p["name"]
        print(f"  [warning: profile '{prefer}' not found — falling back to default]")

    if profiles:
        # Prefer Kokoro-backed profiles — they use the 82M model and never
        # crash the MPS backend, unlike Qwen 1.7B on Apple Silicon.
        kokoro = next(
            (p for p in profiles if "kokoro" in p.get("engine", "").lower()
             or "kokoro" in p.get("tts_engine", "").lower()),
            None,
        )
        return (kokoro or profiles[0])["name"]

    print("  No profiles found — creating a Kokoro preset voice (Michael) …")
    profile = client.create_preset_profile(
        name="Michael",
        preset_engine="kokoro",
        preset_voice_id="am_michael",
        language="en",
    )
    print(f"  Created profile '{profile['name']}' (id: {profile['id']})")
    return profile["name"]


def ensure_light_model(client: VoiceboxClient) -> None:
    """
    Unload Qwen TTS 1.7B if it is present so Voicebox falls back to the
    lighter 0.6B model.  The winning model loads on-demand when the first
    generation request fires.
    """
    models = {m["model_name"]: m for m in client.list_models()}
    heavy = models.get("qwen-tts-1.7B", {})
    if heavy.get("downloaded"):
        print("  Unloading Qwen TTS 1.7B (too heavy for MPS) … ", end="", flush=True)
        client.unload_model("qwen-tts-1.7B")
        print("done")
    light = models.get("qwen-tts-0.6B") or models.get("kokoro")
    if light:
        print(f"  Will use: {light['display_name']}")



def wait_for_reconnect(client: VoiceboxClient, timeout: float = 120.0) -> None:
    """
    After a backend crash, wait until Voicebox is accepting connections again.
    """
    print("  [Voicebox crashed — waiting for restart … ]", end="", flush=True)
    deadline = time.time() + timeout
    while time.time() < deadline:
        if client.is_running():
            print(" back online")
            ensure_light_model(client)
            return
        time.sleep(2)
    raise RuntimeError("Voicebox did not restart within timeout.")


JOBS: list[Job] = [
    Job(
        name="Build",
        duration=2.0,
        fail_chance=0.15,
        success_msg="Build passed. All artifacts compiled cleanly.",
        failure_msg="Build failed. Check the compiler output for details.",
    ),
    Job(
        name="Tests",
        duration=1.5,
        fail_chance=0.2,
        success_msg="All tests passed. Coverage above ninety percent.",
        failure_msg="Test suite failed. One or more assertions did not hold.",
    ),
    Job(
        name="Deploy",
        duration=1.0,
        fail_chance=0.1,
        success_msg="Deploy complete. Service is live.",
        failure_msg="Deploy failed. Rolling back to the previous version.",
    ),
]


# ── main loop ─────────────────────────────────────────────────────────────────


def run_pipeline(
    client: VoiceboxClient,
    profile: str | None = None,
    max_retries: int = 3,
) -> None:
    """Run each job in sequence and speak the result.

    Each speak attempt is retried up to *max_retries* times.  If Voicebox
    crashes mid-generation (MLX stream error on first model load), the
    function waits for the app to restart and tries again.
    """
    print("\n=== Voicebox Agent Notifier Demo ===\n")

    for job in JOBS:
        success = job.run()
        message = job.success_msg if success else job.failure_msg

        print(f"  🔊 Speaking: '{message}'")
        for attempt in range(1, max_retries + 1):
            try:
                wav_path = client.speak_to_temp(message, profile=profile)
                info = client.last_generation_info
                engine = info.get("engine", "?")
                size = info.get("model_size") or ""
                print(f"     engine: {engine}{' ' + size if size else ''}")
                play_wav(wav_path)
                break  # success — move to next job
            except VoiceboxError as exc:
                print(f"  [attempt {attempt}/{max_retries} failed: {exc}]")
                if attempt < max_retries:
                    if not client.is_running():
                        wait_for_reconnect(client)
                    else:
                        time.sleep(2)

        time.sleep(0.4)

    print("\nPipeline complete.\n")


# ── voice-driven transcript demo ──────────────────────────────────────────────


def transcribe_demo(client: VoiceboxClient, audio_path: str) -> None:
    """
    Transcribe a local audio file and print the result.

    Mirrors the dictation → coding-agent pattern described in the blog:
    Whisper cleans up the raw transcript before it reaches the agent.
    """
    print(f"\n=== Transcribe Demo: {audio_path} ===\n")
    try:
        text = client.transcribe(audio_path)
        print(f"Transcript: {text}\n")
    except VoiceboxError as exc:
        print(f"Transcription error: {exc}\n")
    except FileNotFoundError:
        print(f"File not found: {audio_path}\n")


# ── entry point ───────────────────────────────────────────────────────────────


def main() -> None:
    import argparse
    parser = argparse.ArgumentParser(description="Voicebox Agent Notifier Demo")
    parser.add_argument(
        "--profile", "-p",
        default=None,
        help="Voice profile name to use (default: auto-select stable Kokoro profile)",
    )
    parser.add_argument(
        "--transcribe", "-t",
        default=None,
        metavar="AUDIO_FILE",
        help="Also run the transcription demo on this audio file",
    )
    args = parser.parse_args()

    client = VoiceboxClient()

    if not client.is_running():
        print(
            "ERROR: Voicebox is not running.\n"
            "Download from https://voicebox.sh/download, launch the app, and retry."
        )
        sys.exit(1)

    try:
        h = client.health()
        print(f"Backend:   {h.get('backend_type', '?')} | GPU: {h.get('gpu_type', 'none')}")
        profiles = client.list_profiles()
        print(f"Profiles:  {[p.get('name', p.get('id', p)) for p in profiles] or '(none yet)'}")
        models = client.list_models()
        loaded = [m['display_name'] for m in models if m.get('loaded')]
        downloaded = [m['display_name'] for m in models if m.get('downloaded') and not m.get('loaded')]
        print(f"Loaded:    {loaded or '(none)'}")
        print(f"Downloaded:{downloaded or '(none)'}")
    except VoiceboxError as exc:
        print(f"[discovery warning: {exc}]")

    profile = ensure_profile(client, prefer=args.profile)
    print(f"  Using voice profile: '{profile}'\n")
    ensure_light_model(client)
    run_pipeline(client, profile=profile)

    if args.transcribe:
        transcribe_demo(client, args.transcribe)


if __name__ == "__main__":
    main()
