#!/usr/bin/env bash
# cli_notify.sh — speak a message through Voicebox from the command line
#
# USAGE
#   source cli_notify.sh          # load the vb_notify function into your shell
#   vb_notify "Build passed"      # speak a message
#
# Or use the pipeline helper directly:
#   make build && vb_notify "Build passed" || vb_notify "Build failed"
#
# INSTALLATION  (add to ~/.zshrc or ~/.bashrc)
#   source /path/to/cli_notify.sh
#
# ENVIRONMENT
#   VOICEBOX_URL        default: http://127.0.0.1:17493
#   VOICEBOX_PROFILE    voice profile name/id (optional — uses app default)
#   VOICEBOX_CLIENT_ID  X-Voicebox-Client-Id header  (default: cli-notify)

VOICEBOX_URL="${VOICEBOX_URL:-http://127.0.0.1:17493}"
VOICEBOX_PROFILE="${VOICEBOX_PROFILE:-}"
VOICEBOX_CLIENT_ID="${VOICEBOX_CLIENT_ID:-cli-notify}"

# ── core speak helper ─────────────────────────────────────────────────────────

vb_notify() {
    local text="${*}"
    if [[ -z "$text" ]]; then
        echo "Usage: vb_notify <message>" >&2
        return 1
    fi

    # Build JSON payload
    local payload
    if [[ -n "$VOICEBOX_PROFILE" ]]; then
        payload=$(printf '{"text":"%s","profile":"%s"}' \
            "$(echo "$text" | sed 's/"/\\"/g')" \
            "$(echo "$VOICEBOX_PROFILE" | sed 's/"/\\"/g')")
    else
        payload=$(printf '{"text":"%s"}' "$(echo "$text" | sed 's/"/\\"/g')")
    fi

    local tmp_wav
    tmp_wav=$(mktemp /tmp/vb_notify_XXXXXX.wav)

    # POST to /speak; save WAV to temp file
    local http_code
    http_code=$(curl -s -o "$tmp_wav" -w "%{http_code}" \
        -X POST "${VOICEBOX_URL}/speak" \
        -H "Content-Type: application/json" \
        -H "X-Voicebox-Client-Id: ${VOICEBOX_CLIENT_ID}" \
        -d "$payload")

    if [[ "$http_code" != "200" ]]; then
        echo "[vb_notify] Voicebox returned HTTP $http_code — is the app running?" >&2
        rm -f "$tmp_wav"
        return 1
    fi

    # Play audio (platform-aware)
    case "$(uname -s)" in
        Darwin)  afplay "$tmp_wav" ;;
        Linux)   aplay -q "$tmp_wav" 2>/dev/null || mpv --no-terminal "$tmp_wav" 2>/dev/null ;;
        MINGW*|CYGWIN*|MSYS*)
            powershell -c "Start-Process '$tmp_wav'" ;;
        *)
            echo "[vb_notify] Unsupported OS — WAV saved to $tmp_wav" >&2
            return 0
            ;;
    esac

    rm -f "$tmp_wav"
}

# ── pipeline convenience wrappers ─────────────────────────────────────────────

# Run a command; speak pass/fail result.
#
# Usage:  vb_run "npm run build" "Build passed" "Build failed"
vb_run() {
    local cmd="${1:?command required}"
    local ok_msg="${2:-Done}"
    local fail_msg="${3:-Failed}"

    if eval "$cmd"; then
        vb_notify "$ok_msg"
    else
        vb_notify "$fail_msg"
        return 1
    fi
}

# ── quick self-test ────────────────────────────────────────────────────────────
# Run directly to verify Voicebox is reachable:
#   bash cli_notify.sh

if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    echo "Testing Voicebox connection at ${VOICEBOX_URL} …"
    health=$(curl -sf "${VOICEBOX_URL}/health")
    if [[ -z "$health" ]]; then
        echo "ERROR: Voicebox is not running or not reachable at ${VOICEBOX_URL}"
        echo "Download from https://voicebox.sh/download and launch the app."
        exit 1
    fi
    echo "Connection OK — $(echo "$health" | python3 -c "import sys,json; h=json.load(sys.stdin); print(f\"status={h['status']} gpu={h.get('gpu_type','none')} backend={h.get('backend_type','?')}\")" 2>/dev/null || echo "$health")"
    vb_notify "Voicebox is connected and ready."
fi
