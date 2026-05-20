# Speech & Text Analyzer

**TM471 Final Year Project** — Ali Yasser Ali Mohammed (21510864)

A local, privacy-friendly assistant that turns spoken or written input into contextual replies. Audio and text go through a three-stage pipeline (speech-to-text → NLP → LLM), with optional desktop GUI, REST API, and a React Native mobile client that talks to the API over Wi‑Fi.

Everything runs on your machine: Whisper for transcription, spaCy for intent/entities, and **LLaMA 3** via [Ollama](https://ollama.com/) for generation. No cloud API keys are required.

## How it works

```
audio / text  →  Whisper (faster-whisper)  →  spaCy NLP  →  Ollama (llama3)  →  reply
```

| Stage | Technology | Role |
|-------|------------|------|
| Speech-to-text | [faster-whisper](https://github.com/SYSTRAN/faster-whisper) | Microphone or uploaded audio → transcript |
| NLP | [spaCy](https://spacy.io/) (`en_core_web_sm`) | Intent, keywords, named entities |
| LLM | [Ollama](https://ollama.com/) (`llama3`) | Multi-turn replies with rolling conversation memory |

The NLP layer attaches structured context (intent, keywords, entities) to the current turn only, so follow-up questions stay natural without polluting the chat history.

## Repository layout

```
speech-and-text-/
├── analyzer.py          # Core pipeline (STT, NLP, LLM)
├── gui.py               # Desktop Tkinter UI
├── api.py               # Flask REST API for mobile / HTTP clients
├── requirements.txt     # Python dependencies (pinned)
├── Makefile             # install, run, and dev targets
├── mobile/              # Expo / React Native app
│   ├── App.js           # UI + API client (set API_BASE here)
│   ├── package.json
│   └── package-lock.json
└── README.md
```

## Prerequisites

1. **Python 3.10+** (tested on 3.12)
2. **Ollama** installed and running, with the model pulled:
   ```bash
   ollama pull llama3
   ```
3. **PortAudio** (for microphone capture in `gui.py` and CLI `mic` mode):
   - Ubuntu/Debian: `sudo apt install libportaudio2`
   - macOS: usually available via Homebrew `portaudio` if needed
4. **Node.js 18+** and npm (for the mobile app only)

## Quick start (Makefile)

```bash
make help          # list targets
make install       # Python venv + mobile npm deps
make dev           # API server + Expo (mobile workflow)
make gui           # desktop UI only
make cli           # terminal REPL
```

`make dev` runs `api.py` and `npx expo start` in parallel. Set `API_BASE` in `mobile/App.js` to the LAN URL printed by the API.

## Python setup

```bash
make install-python
# or manually:
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

`requirements.txt` includes the `en_core_web_sm` spaCy model as a wheel URL, so you do not need a separate `python -m spacy download` step.

First run downloads Whisper weights automatically (default size: `base` on CPU).

### Configuration

Tunable settings live in the `Config` class in `analyzer.py` (Whisper size/device, silence detection, spaCy model, Ollama model name, history length, etc.).

## Usage

### Desktop GUI

```bash
python gui.py
```

Dark-themed chat window: type messages, use **Speak** for microphone input, **New chat** to clear LLM memory. NLP metadata (intent, keywords, entities) appears below the transcript.

### REST API + mobile app

Start the API server (listens on all interfaces, port 5000):

```bash
python api.py
```

The terminal prints your LAN URL, e.g. `http://192.168.1.5:5000`. Use that IP in the mobile app:

1. Edit `mobile/App.js` and set `API_BASE` to your PC’s address.
2. Install mobile dependencies and start Expo:

   ```bash
   make mobile
   # or: cd mobile && npm ci && npx expo start
   ```

3. Open the project in **Expo Go** on your phone (same Wi‑Fi as the PC).

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Liveness check |
| `/chat` | POST | JSON `{"text": "..."}` → full pipeline result |
| `/voice` | POST | Multipart `audio` file → transcribe + pipeline |
| `/reset` | POST | Clear conversation history |

### CLI (no GUI)

```bash
python analyzer.py
```

Commands: type text, `mic` to speak, `reset` to clear memory, `quit` to exit.

## Mobile app

Built with **Expo 51** and React Native. Features mirror the desktop experience: text chat, voice recording (uploaded to `/voice`), health check on startup, and **New chat** wired to `/reset`.

Locked dependencies: `mobile/package-lock.json` — install with `npm ci` for reproducible builds.

## System notes

- **GPU**: Set `STT_DEVICE = "cuda"` and `STT_COMPUTE_TYPE = "float16"` in `Config` if you have a CUDA-capable GPU and want faster Whisper.
- **Firewall**: Allow inbound TCP **5000** on the PC when using the mobile app.
- **Android emulator**: Use `10.0.2.2` instead of your LAN IP to reach the host machine’s API.
- **tkinter**: Ships with many Python installs; on minimal Linux distros install the `python3-tk` package.

## Author

Ali Yasser Ali Mohammed — TM471, 21510864
