# voicebox_agent

A small working project that demonstrates integrating with the [Voicebox](https://github.com/jamiepine/voicebox) local voice stack — REST API, voice notifications for CLI pipelines, and MCP agent configuration.

> **Prerequisite:** Install and launch the Voicebox desktop app from [voicebox.sh/download](https://voicebox.sh/download).
> The API becomes available at `http://127.0.0.1:17493` once the app is running.
> Alternatively, run headless with Docker — see [Running with Docker](#running-with-docker).

---

## Project structure

```
voicebox_agent/
├── client.py           # VoiceboxClient — Python wrapper around the REST API
├── agent_notifier.py   # Demo: simulated CI/CD pipeline with spoken results
├── cli_notify.sh       # Bash helper: speak messages from any shell pipeline
├── mcp_config.json     # MCP server config for Cursor / Windsurf / VS Code
├── requirements.txt
└── README.md
```

---

## Quick start

```bash
# 1. Install Python dependency (only `requests`)
pip install -r requirements.txt

# 2. Confirm Voicebox is running
curl http://127.0.0.1:17493/health

# 3. Run the agent notifier demo
python agent_notifier.py
```

The demo simulates a build → test → deploy pipeline and speaks each result
aloud using Voicebox.

---

## `client.py` — VoiceboxClient

A synchronous Python client for the full Voicebox REST surface.

```python
from client import VoiceboxClient

vb = VoiceboxClient()

# Check the API is up
print(vb.is_running())          # True / False

# Server health (backend type, GPU)
print(vb.health())
# {'status': 'ok', 'backend_type': 'mlx', 'gpu_type': 'MPS (Apple Silicon)'}

# List downloaded/loaded TTS models
print(vb.list_models())

# List cloned voice profiles
print(vb.list_profiles())

# Speak — returns raw WAV bytes
wav = vb.speak("Deploy complete.", profile="Morgan")

# Speak and save to a file
vb.speak_and_save("Tests passing.", "result.wav", profile="Morgan")

# Speak to a temp file (convenient for shell playback)
path = vb.speak_to_temp("Build failed.")
# macOS:  subprocess.run(["afplay", path])

# Transcribe a local audio file
text = vb.transcribe("recording.wav", model="whisper-turbo")
print(text)

# Clone a voice from a reference clip (10–30 s of clean speech)
profile = vb.clone_voice("my_voice.wav", name="MyVoice")

# Unload a model from GPU memory without deleting it
vb.unload_model("qwen-tts-1.7B")

# Create a preset (non-cloned) voice profile
vb.create_preset_profile("Michael", preset_engine="kokoro",
                          preset_voice_id="am_michael", language="en")
```

### Environment variables

| Variable | Default | Purpose |
|---|---|---|
| `VOICEBOX_URL` | `http://127.0.0.1:17493` | API base URL |
| `VOICEBOX_CLIENT_ID` | `voicebox-agent-demo` | `X-Voicebox-Client-Id` header |

---

## `agent_notifier.py` — Pipeline voice notifications

Mirrors the **"CLI tools that talk back"** pattern from the blog.

```bash
# Auto-selects the most stable available profile (prefers Kokoro over Qwen)
python agent_notifier.py

# Use a specific voice profile
python agent_notifier.py --profile Mihir

# Run the pipeline and also transcribe a local audio file
python agent_notifier.py --transcribe notes.wav
```

Example output:

```
Backend:   mlx | GPU: MPS (Apple Silicon)
Profiles:  ['Mihir', 'Michael']
Loaded:    (none)
Downloaded:['Qwen TTS 1.7B', 'Qwen TTS 0.6B', 'Kokoro 82M']
  Using voice profile: 'Michael'

=== Voicebox Agent Notifier Demo ===

  ▶  Build … ✓ passed
  🔊 Speaking: 'Build passed. All artifacts compiled cleanly.'
     engine: kokoro
  ▶  Tests … ✓ passed
  🔊 Speaking: 'All tests passed. Coverage above ninety percent.'
     engine: kokoro
  ▶  Deploy … ✓ passed
  🔊 Speaking: 'Deploy complete. Service is live.'
     engine: kokoro

Pipeline complete.
```

### Profile selection logic

`agent_notifier.py` resolves the voice profile in this order:

1. `--profile <name>` if provided
2. First **Kokoro-backed** profile (82M model, runs on CPU, never crashes the MPS backend)
3. Any other existing profile
4. Creates a Kokoro preset called **Michael** if no profiles exist yet

> **Apple Silicon note:** Qwen TTS 1.7B can crash Voicebox's MLX backend on
> first load (`There is no Stream(gpu, 1) in current thread`).
> The script handles this with automatic retry (up to 3 attempts) and
> reconnect. For a permanently stable experience, delete the 1.7B model from
> **Voicebox → Settings → Models** so only 0.6B is available.

---

## `cli_notify.sh` — Shell voice helper

Source this file to get `vb_notify` and `vb_run` in any shell session.

```bash
# Load functions
source cli_notify.sh

# Speak a message
vb_notify "Build passed"

# Run a command and speak the result
vb_run "npm run build" "Build passed" "Build failed"

# Use in a Makefile pipeline
make test && vb_notify "Tests passed" || vb_notify "Tests failed"
```

Add to `~/.zshrc` for permanent access:

```bash
source /path/to/voicebox_agent/cli_notify.sh
```

Environment overrides:

```bash
export VOICEBOX_PROFILE="Morgan"     # use a specific voice
export VOICEBOX_CLIENT_ID="zshrc"    # label in Voicebox → Settings → MCP
```

---

## MCP server — give your coding agent a voice

Voicebox ships a built-in MCP server that exposes four tools:
`voicebox.speak`, `voicebox.transcribe`, `voicebox.list_captures`, `voicebox.list_profiles`.

### Claude Code

```bash
claude mcp add voicebox \
  --transport http \
  --url http://127.0.0.1:17493/mcp \
  --header "X-Voicebox-Client-Id: claude-code"
```

### Cursor / Windsurf / VS Code

Copy `mcp_config.json` into your project root (or merge into your existing
`.cursor/mcp.json` / `settings.json`) and change the `X-Voicebox-Client-Id`
to your preferred label.

```json
{
  "mcpServers": {
    "voicebox": {
      "url": "http://127.0.0.1:17493/mcp",
      "headers": { "X-Voicebox-Client-Id": "cursor" }
    }
  }
}
```

Restart your editor.  The `voicebox.*` tools appear in the agent's tool list
automatically via the MCP handshake.

### stdio fallback (Claude Desktop)

```json
{
  "mcpServers": {
    "voicebox": {
      "command": "/Applications/Voicebox.app/Contents/MacOS/voicebox-mcp",
      "env": { "VOICEBOX_CLIENT_ID": "claude-desktop" }
    }
  }
}
```

### What agents can do once connected

```javascript
// Agent speaks a result in your cloned voice
await voicebox.speak({ text: "Tests passing. Ready to merge.", profile: "Morgan" });

// Agent narrates through a personality LLM first, then speaks
await voicebox.speak({ text: "All clear.", profile: "Morgan", personality: true });

// Agent transcribes a voice memo you dropped in the repo
await voicebox.transcribe({ audio_path: "notes.wav" });
```

---

## API reference (key endpoints)

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/health` | Server health, backend type, GPU info |
| `GET` | `/models/status` | TTS model catalog with download/load state |
| `GET` | `/profiles` | List voice profiles |
| `POST` | `/profiles` | Create or clone a voice profile |
| `POST` | `/speak` | Agent-style speak (profile by name, async → polls → WAV) |
| `POST` | `/generate` | Full TTS with explicit `profile_id` and `language` |
| `GET` | `/history/{id}` | Poll generation status |
| `GET` | `/audio/{id}` | Fetch completed WAV bytes |
| `POST` | `/models/{name}/unload` | Free GPU memory without deleting model |
| `POST` | `/transcribe` | Whisper STT — multipart audio upload |

> **Async flow:** `POST /speak` returns `{"id": "...", "status": "generating"}`.
> Poll `GET /history/{id}` until `status == "completed"`, then fetch `GET /audio/{id}`.
> `VoiceboxClient.speak()` handles this automatically.

Full interactive docs: `http://127.0.0.1:17493/docs`

---

## Running with Docker

Voicebox ships an official `docker-compose.yml` that runs the full backend
and web UI without the desktop app — same API, same port.

```bash
git clone --depth=1 https://github.com/jamiepine/voicebox.git ~/voicebox-server
cd ~/voicebox-server
mkdir -p output
docker compose up -d        # API + web UI on http://127.0.0.1:17493
```

**Trade-offs vs the desktop app on macOS:**

| | Desktop App | Docker |
|---|---|---|
| MPS / Metal GPU | ✅ | ❌ CPU only (Linux VM) |
| Qwen 1.7B MLX crash | Possible | Not applicable (CPU) |
| Voice management UI | ✅ Desktop | ✅ Web browser |
| Runs headless | Requires login session | ✅ `restart: unless-stopped` |

`client.py` and `agent_notifier.py` work unchanged against either backend.

---

## Latency comparison

| | Cloud TTS (ElevenLabs) | Local Voicebox |
|---|---|---|
| First-token latency | ~800 ms p50 (network-bound) | ~250 ms p50 on M-series (GPU-bound) |
| Cost model | Per-character | Fixed hardware |
| Data residency | Audio transits vendor infra | Never leaves your machine |
| Offline | ✗ | ✓ |
