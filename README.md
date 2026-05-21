# Speech & Text Analyzer

**TM471 Final Year Project** — Ali Yasser Ali Mohammed (21510864)

A local, privacy-friendly assistant that turns spoken or written input into contextual replies. Audio and text go through a three-stage pipeline (speech-to-text → NLP → LLM), with optional desktop GUI, REST API, and a React Native mobile client that talks to the API over Wi‑Fi.

Everything runs on your machine: Whisper for transcription, spaCy for intent/entities, and **LLaMA 3** via [Ollama](https://ollama.com/) for generation. No cloud API keys are required.

---

## Quick start: zero to hero

> **Goal:** Install once, run the API + Expo on your PC, open the app on your phone over Wi‑Fi, and send a message. First run is ~15 minutes (plus model downloads).

| | |
|---|---|
| **You need** | Python 3.10+, [Ollama](https://ollama.com/), [GNU Make](https://gnuwin32.sourceforge.net/) (Windows: `choco install make`), Node 18+ (mobile only), phone + PC on **same Wi‑Fi** |
| **Windows** | Use `make mobile` (not raw `npx expo start`) so your **192.168.x.x** IP is written to `mobile/.env` — see [Windows notes](#windows-notes) |

### 1 — Install (one time)

```bash
git clone <your-repo-url>
cd speech-and-text-

make install          # Python venv + npm in mobile/
ollama pull llama3    # LLM weights (~4 GB, once)
make check-ollama     # must print: ollama: ok
```

### 2 — Run (two terminals, every demo)

**Terminal 1 — API** (keep running):

```bash
make api
```

Wait for **`API ready`** and a banner like `http://192.168.x.x:5000` (not `127.0.0.1` on the phone path).

**Terminal 2 — mobile** (keep running):

```bash
make mobile
```

You should see `EXPO_PUBLIC_API_BASE=http://192.168.x.x:5000`. Scan the QR code with **Expo Go** (Android/iOS).

**Or one terminal:** `make dev` (API + Expo together).

### 3 — On the phone

1. Same Wi‑Fi as the PC.
2. App status **Ready** (green).
3. Type a message → **Send** → assistant reply + NLP strip under the bubble.

**Voice (optional):** Hold **mic**, speak, release. First voice request loads Whisper on the PC (can take a minute).

### You’re done when

- [ ] `make check-ollama` → `ollama: ok`
- [ ] `make api` banner shows a **192.168.x.x** (or **10.x**) URL
- [ ] `make mobile` printed `EXPO_PUBLIC_API_BASE=http://192.168…`
- [ ] Expo Go shows **Ready**, then a real reply (not `[LLM error]…`)

### Quick fixes

| Problem | Fix |
|---------|-----|
| App shows **127.0.0.1** or can’t connect | Run **`make mobile`** again; reload app. Or Settings (gear) → paste URL from `make api` banner. |
| **Ollama not running on PC** (yellow) | Start Ollama app, then `make check-ollama`, restart `make api`. |
| Red / no connection | Same Wi‑Fi; firewall allow **5000** (API) and **8081** (Expo). Linux: `sudo ufw allow 5000/tcp` and `8081/tcp`. |
| No LLM reply but NLP works | `ollama pull llama3` and keep Ollama running. |

More detail: [V2 demo](#v2-demo-full-stack--text--voice) · [First phone demo](#first-phone-demo-android--expo-go) · [Makefile commands](#makefile-commands)

---

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
├── api.py               # Flask REST API (debug + mobile request logs)
├── host_util.py         # LAN IP helper (used by api.py)
├── ollama_util.py       # Ollama health probe (used by api.py)
├── requirements.txt     # Python dependencies (pinned)
├── requirements-dev.txt # pytest (make test)
├── Makefile             # install, run, dev, and test targets
├── scripts/             # check_mobile.sh, test_api_live.sh
├── tests/               # automated setup tests
├── mobile/              # Expo / React Native app
│   ├── App.js           # UI + API client (auto-detect API URL in dev)
│   ├── assets/          # app icon (required by app.json)
│   ├── package.json
│   └── package-lock.json
└── README.md
```

## Prerequisites

1. **Python 3.10+** (tested on 3.12)
2. **Ollama** (required for real assistant replies):
   ```bash
   ollama pull llama3
   make check-ollama   # should print: ollama: ok
   ```
3. **PortAudio** (for microphone capture in `gui.py` and CLI `mic` mode):
   - Ubuntu/Debian: `sudo apt install libportaudio2`  
     (or `portaudio19-dev` if you build audio tools from source)
4. **Node.js 18+** and npm (for the mobile app only)

## Makefile commands

Works on **Linux, macOS, and Windows** (`choco install make` on Windows; use `python` not `python3` if needed). **Start here:** [Quick start: zero to hero](#quick-start-zero-to-hero).

```bash
make help          # list all targets
make install       # Python venv + mobile npm deps
make api           # Flask API on :5000 (Terminal 1)
make mobile        # writes mobile/.env + Expo LAN QR (Terminal 2)
make dev           # API + Expo together
make gui           # desktop UI only
make cli           # terminal REPL
make test          # automated checks (no server required)
```

## Ollama setup (Windows + Linux)

1. Install [Ollama](https://ollama.com/download) and start the app / service.
2. Pull the model (matches `Config.LLM_MODEL` in `analyzer.py`):
   ```bash
   ollama pull llama3
   ```
3. Verify:
   ```bash
   make check-ollama
   # ollama: ok
   ```
4. Start the API **after** Ollama is running: `make api`

## V2 demo (full stack — text + voice)

**Fast startup:** The API loads spaCy + LLM config immediately; **Whisper loads only on the first `/voice` request** (or first desktop mic use). Text chat works within seconds of `make api`.

### Text chat on phone

1. `make install` (once)
2. Start **Ollama**, then **Terminal 1:** `make api` — wait for `API ready`
3. **Terminal 2:** `make mobile` → scan QR with Expo Go (same Wi‑Fi)
4. App status **Ready** (or yellow **Ollama not running on PC** if Ollama is down)
5. Type a message → **Send** → real reply when Ollama is OK

### Voice on phone (hold mic)

1. With `make api` already running, hold the **mic** button, speak, release.
2. **First voice request** downloads/loads Whisper on the PC (can take a minute) — watch the API terminal.
3. You should see a user bubble with the transcript and an assistant reply.

`GET /health` returns:

```json
{
  "status": "ok",
  "model": "llama3",
  "ollama": "ok",
  "whisper": "not_loaded",
  "ready_for_chat": true
}
```

(`whisper` becomes `"ready"` after the first voice upload.)

## First phone demo (Android + Expo Go)

Same flow as [Quick start: zero to hero](#quick-start-zero-to-hero) — extra troubleshooting below.

**Order matters** — start Ollama and the API before opening the app on your phone.

**API URL on the phone:** `make mobile` writes `EXPO_PUBLIC_API_BASE` in `mobile/.env`; Settings (gear) is the fallback.

**Without Ollama:** NLP still works; `reply` will be `[LLM error]…` and status shows **Ollama not running on PC**.

**Firewall (Linux):**

```bash
sudo ufw allow 8081/tcp   # Metro / Expo
sudo ufw allow 5000/tcp   # Flask API
```

### Watching mobile traffic in the API terminal

`make api` runs Flask in **debug mode** (tracebacks on errors) with **INFO** logs for every request from the phone:

```
MOBILE IN  | 192.168.1.102 | POST /chat | message='hello'
MOBILE OUT | 192.168.1.102 | POST /chat | message='hello' | intent=greeting | keywords=[] | reply='...'
```

- **MOBILE IN** — what the phone sent (message text, voice filename, health check, reset).
- **MOBILE OUT** — pipeline result (message repeated, intent, keywords, reply preview).

Disable Flask debug (keep INFO logs):

```bash
FLASK_DEBUG=0 make api
```

## Testing

| Command | What it checks |
|---------|----------------|
| `make test` | Pytest (`tests/`) + `scripts/check_mobile.sh` — no running server |
| `make test-setup` | Mobile layout / Expo entry point only |
| `make test-api` | Live `curl` against `/health` and `/chat` — **requires `make api` in another terminal** |

```bash
make test

# With API running in another terminal:
make test-api

# From another machine on the LAN:
API_URL=http://192.168.1.115:5000 make test-api
```

## Python setup

```bash
make install-python
```

Or manually:

```bash
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
pip install -r requirements-dev.txt   # optional, for make test
```

`requirements.txt` includes the `en_core_web_sm` spaCy model as a wheel URL, so you do not need a separate `python -m spacy download` step.

First run downloads Whisper weights automatically (default size: `base` on CPU).

### Configuration

Tunable settings live in the `Config` class in `analyzer.py` (Whisper size/device, silence detection, spaCy model, Ollama model name, history length, etc.).

## Usage

### Desktop GUI

```bash
make gui
```

Dark-themed chat window: type messages, use **Speak** for microphone input, **New chat** to clear LLM memory. NLP metadata (intent, keywords, entities) appears below the transcript.

### REST API + mobile app

```bash
make api      # Terminal 1
make mobile   # Terminal 2 — Expo Go, scan QR
```

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Liveness check (mobile pings on startup) |
| `/chat` | POST | JSON `{"text": "..."}` → full pipeline result |
| `/voice` | POST | Multipart `audio` file → transcribe + pipeline |
| `/reset` | POST | Clear conversation history |

Example `curl` (replace IP with your LAN address):

```bash
curl http://192.168.1.115:5000/health
curl -X POST http://192.168.1.115:5000/chat \
  -H 'Content-Type: application/json' \
  -d '{"text":"hello"}'
```

### CLI (no GUI)

```bash
make cli
```

Commands: type text, `mic` to speak, `reset` to clear memory, `quit` to exit.

## Mobile app

Built with **Expo 51** and React Native. Features:

- Text chat via `/chat`
- Hold-to-talk voice via `/voice` (v2 polish)
- Health check on startup
- NLP metadata strip (intent, keywords, entities)
- **New chat** → `/reset`
- **Settings** → override API base URL

Locked dependencies: `mobile/package-lock.json` — install with `npm ci` (or `make install-npm`).

## Windows notes

- The Makefile detects `OS=Windows_NT` and uses `.venv\Scripts\python.exe` instead of `.venv/bin/python`.
- `npm` / `npx` are invoked as `npm.cmd` / `npx.cmd` when needed.
- `make dev` runs `scripts/dev.py` (no Bash `trap` required).
- `make test-setup` / `make test-api` use Python scripts, not `.sh` files.
- **WSL** is treated as Linux (uses `bin/` paths); run the whole stack inside WSL for the closest match to Linux.
- **Phone API URL shows `127.0.0.1`**: Expo on Windows often reports `debuggerHost` as localhost. Always start the app with **`make mobile`** (not raw `npx expo start`) — it runs `scripts/write_mobile_env.py`, which detects your Wi‑Fi IPv4 via `ipconfig` and writes `mobile/.env` with `EXPO_PUBLIC_API_BASE=http://192.168.x.x:5000`. Restart Expo after changing networks. If detection still fails, paste the URL from the `make api` banner into Settings (gear).

## System notes

- **GPU**: Set `STT_DEVICE = "cuda"` and `STT_COMPUTE_TYPE = "float16"` in `Config` for faster Whisper.
- **Firewall**: Allow inbound TCP **5000** (API) and **8081** (Metro) on the PC.
- **Android emulator**: Use `http://10.0.2.2:5000` as the API URL in Settings.
- **Physical phone**: Same Wi‑Fi as the PC; `make mobile` writes that IP into `mobile/.env`, or use the URL from the `make api` banner in Settings.
- **tkinter**: On minimal Linux, install `python3-tk` if `make gui` fails.

## Author

Ali Yasser Ali Mohammed — TM471, 21510864
