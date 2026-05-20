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

import os
import tempfile

from flask import Flask, jsonify, request
from flask_cors import CORS

from analyzer import SpeechTextAnalyzer
from host_util import lan_ip

# ---------------------------------------------------------------------------
app = Flask(__name__)
CORS(app)   # allow the React Native app to POST from any origin

print("[API] Loading pipeline (Whisper + spaCy + LLaMA 3) …")
analyzer = SpeechTextAnalyzer()
print("[API] Pipeline ready.")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

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

@app.get("/health")
def health():
    """Quick liveness check — the mobile app pings this on startup."""
    return jsonify({"status": "ok", "model": "llama3"})


@app.post("/chat")
def chat():
    """
    Body: { "text": "What is photosynthesis?" }
    Returns the full pipeline result as JSON.
    """
    data = request.get_json(force=True, silent=True) or {}
    text = (data.get("text") or "").strip()
    if not text:
        return jsonify({"error": "empty text"}), 400

    result = analyzer.process_text(text)
    return jsonify(_serialize(result))


@app.post("/voice")
def voice():
    """
    Body: multipart/form-data with field 'audio' containing an audio file.
    The file is saved to a temp path, transcribed by Whisper, then the
    full pipeline runs exactly as it does for text input.

    Accepts: .wav, .m4a, .mp4, .webm, .ogg — Whisper handles all of them.
    """
    if "audio" not in request.files:
        return jsonify({"error": "no audio field in request"}), 400

    f = request.files["audio"]
    ext = os.path.splitext(f.filename or "audio.wav")[1] or ".wav"

    with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as tmp:
        f.save(tmp.name)
        tmp_path = tmp.name

    try:
        result = analyzer.process_audio_file(tmp_path)
    finally:
        os.unlink(tmp_path)

    return jsonify(_serialize(result))


@app.post("/reset")
def reset():
    """Clear conversation history — wired to the 'New chat' button."""
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

    app.run(host="0.0.0.0", port=5000, debug=False)
