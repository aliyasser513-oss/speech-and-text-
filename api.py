"""
Speech and Text Analyzer — REST API Server
TM471 Final Year Project | Ali Yasser Ali Mohammed | 21510864

Wraps the existing SpeechTextAnalyzer pipeline as a JSON REST API
so the Android mobile app (or any HTTP client) can use it over WiFi.

analyzer.py is UNCHANGED — this file only adds a thin HTTP layer.

Endpoints
---------
GET  /health          → liveness check
POST /chat            → {"text": "..."} → pipeline result JSON
POST /voice           → multipart audio file → pipeline result JSON
POST /reset           → clears conversation history

Run:
    python api.py

Then open the printed URL on your phone's browser to confirm it works.
Set the same IP in the mobile app (App.js → API_BASE).
"""

import logging
import os
import tempfile

from flask import Flask, jsonify, request
from flask_cors import CORS

from analyzer import Config, SpeechTextAnalyzer
from host_util import lan_ip
from ollama_util import check_ollama

# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(name)-8s | %(levelname)s | %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("api")
logging.getLogger("werkzeug").setLevel(logging.INFO)

app = Flask(__name__)
CORS(app)   # allow the React Native app to POST from any origin

log.info("Loading pipeline (spaCy + LLM; Whisper loads on first /voice) …")
analyzer = SpeechTextAnalyzer()
log.info("API ready — text chat available; Whisper loads on first voice request.")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _client_ip() -> str:
    return request.remote_addr or "-"


def _reply_preview(reply: str, limit: int = 120) -> str:
    one_line = reply.replace("\n", " ").strip()
    return one_line if len(one_line) <= limit else one_line[: limit - 3] + "..."


def _serialize(result) -> dict:
    """Convert a PipelineResult into a JSON-safe dict."""
    nlp = result.nlp
    return {
        "user_input": result.user_input,
        "reply":      result.reply,
        "intent":     nlp.intent   if nlp else "unknown",
        "keywords":   nlp.keywords if nlp else [],
        "entities": [
            {"text": t, "label": lbl}
            for t, lbl in (nlp.entities if nlp else [])
        ],
    }


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

def _health_payload() -> dict:
    ollama_ok = check_ollama(Config.LLM_MODEL)
    return {
        "status": "ok",
        "model": Config.LLM_MODEL,
        "ollama": "ok" if ollama_ok else "down",
        "whisper": "ready" if analyzer.whisper_ready else "not_loaded",
        "ready_for_chat": ollama_ok,
    }


@app.get("/health")
def health():
    """Liveness + readiness for text chat (Ollama) and voice (Whisper)."""
    log.info("MOBILE IN  | %s | GET /health", _client_ip())
    return jsonify(_health_payload())


@app.post("/chat")
def chat():
    """
    Body: { "text": "What is photosynthesis?" }
    Returns the full pipeline result as JSON.
    """
    data = request.get_json(force=True, silent=True) or {}
    text = (data.get("text") or "").strip()
    client = _client_ip()
    log.info("MOBILE IN  | %s | POST /chat | message=%r", client, text)
    if not text:
        log.info("MOBILE OUT | %s | POST /chat | status=400 | error=empty text", client)
        return jsonify({"error": "empty text"}), 400

    result = analyzer.process_text(text)
    payload = _serialize(result)
    log.info(
        "MOBILE OUT | %s | POST /chat | message=%r | intent=%s | keywords=%s | reply=%r",
        client,
        text,
        payload["intent"],
        payload["keywords"],
        _reply_preview(payload["reply"]),
    )
    return jsonify(payload)


@app.post("/voice")
def voice():
    """
    Body: multipart/form-data with field 'audio' containing an audio file.
    The file is saved to a temp path, transcribed by Whisper, then the
    full pipeline runs exactly as it does for text input.

    Accepts: .wav, .m4a, .mp4, .webm, .ogg — Whisper handles all of them.
    """
    if "audio" not in request.files:
        log.info("MOBILE OUT | %s | POST /voice | status=400 | error=no audio field", _client_ip())
        return jsonify({"error": "no audio field in request"}), 400

    f = request.files["audio"]
    ext = os.path.splitext(f.filename or "audio.wav")[1] or ".wav"
    client = _client_ip()
    log.info(
        "MOBILE IN  | %s | POST /voice | filename=%r ext=%s",
        client,
        f.filename,
        ext,
    )

    tmp_path: str | None = None
    try:
        with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as tmp:
            f.save(tmp.name)
            tmp_path = tmp.name
        # File closed here (required on Windows before Whisper opens it)

        if not analyzer.whisper_ready:
            log.info("Loading Whisper for first voice request …")
        result = analyzer.process_audio_file(tmp_path)
    except Exception as exc:
        log.exception("POST /voice failed")
        return jsonify({"error": str(exc)}), 503
    finally:
        if tmp_path and os.path.exists(tmp_path):
            os.unlink(tmp_path)

    payload = _serialize(result)
    log.info(
        "MOBILE OUT | %s | POST /voice | transcript=%r | intent=%s | reply=%r",
        client,
        payload["user_input"],
        payload["intent"],
        _reply_preview(payload["reply"]),
    )
    return jsonify(payload)


@app.post("/reset")
def reset():
    """Clear conversation history — wired to the 'New chat' button."""
    log.info("MOBILE IN  | %s | POST /reset", _client_ip())
    analyzer.reset_conversation()
    return jsonify({"status": "ok"})


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    local_ip = lan_ip()
    api_url = f"http://{local_ip}:5000"

    print()
    print("=" * 50)
    print("  Speech & Text Analyzer — API Server")
    print("=" * 50)
    print(f"  URL  :  {api_url}")
    print()
    print("  On the phone (Expo Go, same Wi‑Fi):")
    print("    API URL is auto-detected from your PC IP in dev.")
    print("    Or open Settings (gear) and paste:", api_url)
    print()
    print("  Make sure your phone is on the same WiFi network.")
    print("  Press Ctrl+C to stop.")
    print("=" * 50)
    print()

    # debug=True for tracebacks; use_reloader=False avoids loading Whisper twice
    debug = os.getenv("FLASK_DEBUG", "1").lower() in ("1", "true", "yes")
    log.info("Starting Flask (debug=%s, reloader=off)", debug)
    app.run(host="0.0.0.0", port=5000, debug=debug, use_reloader=False)
