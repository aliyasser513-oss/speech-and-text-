"""
Speech and Text Analyzer - Core Pipeline
TM471 Final Year Project | Ali Yasser Ali Mohammed | 21510864

A three-stage pipeline that turns spoken or written input into a
contextual reply:

    audio / text  ->  Whisper STT  ->  spaCy NLP  ->  LLaMA 3 LLM  ->  reply

Each stage is a self-contained class so that any one of them can be
swapped (e.g. a different Whisper size, a multilingual spaCy model,
or another Ollama model) without touching the rest of the system.
"""

from __future__ import annotations

import json
import logging
import platform
import re
import sys
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

import numpy as np
import ollama
import sounddevice as sd
import spacy
from faster_whisper import WhisperModel

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(name)-8s | %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("analyzer")


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

class Config:
    """Single source of truth for tunable parameters."""

    # --- Speech-to-text -----------------------------------------------------
    STT_MODEL_SIZE: str = "base"           # tiny | base | small | medium | large-v3
    STT_DEVICE: str = "cpu"                # "cpu" or "cuda"
    STT_COMPUTE_TYPE: str = "int8"         # int8 for CPU, float16 for GPU
    STT_LANGUAGE: Optional[str] = "en"     # set None to auto-detect

    # --- Microphone capture -------------------------------------------------
    SAMPLE_RATE: int = 16_000              # Whisper expects 16 kHz mono
    CHUNK_SECONDS: float = 0.1             # length of each audio frame
    MAX_RECORD_SECONDS: float = 15.0       # hard cap on a single utterance
    SILENCE_RMS: float = 0.01              # frame quieter than this = silent
    SILENCE_PATIENCE_SEC: float = 1.5      # stop after this much silence

    # --- NLP ----------------------------------------------------------------
    SPACY_MODEL: str = "en_core_web_sm"

    # --- LLM ----------------------------------------------------------------
    LLM_MODEL: str = "llama3"
    LLM_MAX_TOKENS: int = 300
    LLM_TEMPERATURE: float = 0.7

    # --- Conversation memory -----------------------------------------------
    # Number of past (user, assistant) exchanges kept in the LLM prompt.
    # Each turn is two messages, so 8 turns = 16 messages of context.
    # Older messages are dropped FIFO; the system prompt is always kept.
    MAX_HISTORY_TURNS: int = 8


# ---------------------------------------------------------------------------
# Data containers
# ---------------------------------------------------------------------------

@dataclass
class NLPResult:
    """Structured output of the NLP stage."""
    text: str
    intent: str
    keywords: list[str] = field(default_factory=list)
    entities: list[tuple[str, str]] = field(default_factory=list)


@dataclass
class PipelineResult:
    """Everything one full pipeline pass produces."""
    user_input: str
    nlp: Optional[NLPResult]
    reply: str


# ---------------------------------------------------------------------------
# Module 1 - Speech-to-Text
# ---------------------------------------------------------------------------

class SpeechToText:
    """Microphone or file -> transcribed text, using faster-whisper."""

    def __init__(self, cfg: type[Config] = Config) -> None:
        self.cfg = cfg
        log.info("[STT] loading Whisper '%s' (%s/%s) ...",
                 cfg.STT_MODEL_SIZE, cfg.STT_DEVICE, cfg.STT_COMPUTE_TYPE)
        self._model = WhisperModel(
            cfg.STT_MODEL_SIZE,
            device=cfg.STT_DEVICE,
            compute_type=cfg.STT_COMPUTE_TYPE,
        )
        log.info("[STT] ready.")

    # -- microphone ----------------------------------------------------------

    def _record_until_silence(self) -> np.ndarray:
        """Capture audio until the user stops speaking (or the hard cap)."""
        cfg = self.cfg
        frames_per_chunk = int(cfg.SAMPLE_RATE * cfg.CHUNK_SECONDS)
        max_chunks       = int(cfg.MAX_RECORD_SECONDS / cfg.CHUNK_SECONDS)
        silence_limit    = int(cfg.SILENCE_PATIENCE_SEC / cfg.CHUNK_SECONDS)

        chunks: list[np.ndarray] = []
        silent_in_a_row = 0
        spoke_at_least_once = False

        log.info("[STT] listening ...")
        with sd.InputStream(samplerate=cfg.SAMPLE_RATE,
                            channels=1, dtype="float32") as stream:
            for _ in range(max_chunks):
                chunk, _ = stream.read(frames_per_chunk)
                chunks.append(chunk.flatten())
                rms = float(np.sqrt(np.mean(np.square(chunk))))
                if rms < cfg.SILENCE_RMS:
                    silent_in_a_row += 1
                    # don't stop on the leading silence before speech begins
                    if spoke_at_least_once and silent_in_a_row >= silence_limit:
                        break
                else:
                    silent_in_a_row = 0
                    spoke_at_least_once = True

        return np.concatenate(chunks) if chunks else np.zeros(0, dtype="float32")

    def from_microphone(self) -> str:
        audio = self._record_until_silence()
        if audio.size == 0:
            return ""
        return self._transcribe(audio)

    # -- file ----------------------------------------------------------------

    def from_file(self, path: str) -> str:
        return self._transcribe(path)

    # -- shared internals ----------------------------------------------------

    def _transcribe(self, audio) -> str:
        segments, _ = self._model.transcribe(
            audio, beam_size=5, language=self.cfg.STT_LANGUAGE,
        )
        text = " ".join(seg.text.strip() for seg in segments).strip()
        log.info("[STT] transcript: %r", text)
        return text


# ---------------------------------------------------------------------------
# Module 2 - NLP
# ---------------------------------------------------------------------------

class NLPProcessor:
    """Cleans text, detects intent, extracts keywords + named entities."""

    # Ordered: first match wins. Specific action verbs are checked
    # before the more generic greeting / question patterns so that
    # e.g. "translate hello to French" is classified as 'translate'
    # rather than 'greeting'.
    _INTENT_PATTERNS: list[tuple[str, re.Pattern]] = [
        ("translate", re.compile(r"\b(translate|translation|in\s+(arabic|french|spanish|german|italian))\b", re.I)),
        ("summarize", re.compile(r"\b(summari[sz]e|summary|tl;?dr|brief|shorten)\b", re.I)),
        ("define",    re.compile(r"\b(define|definition|meaning\s+of|explain|what\s+is|what\s+are)\b", re.I)),
        ("calculate", re.compile(r"\b(calculate|compute|how\s+much|add|subtract|multiply|divide)\b", re.I)),
        ("command",   re.compile(r"\b(open|close|start|stop|run|play|pause|search\s+for)\b", re.I)),
        ("farewell",  re.compile(r"\b(bye|goodbye|see\s+you|exit|quit)\b", re.I)),
        ("greeting",  re.compile(r"^\s*(hello|hi|hey|good\s+(morning|afternoon|evening))\b", re.I)),
        ("question",  re.compile(r"\?\s*$|\b(who|when|where|why|how|which)\b", re.I)),
    ]

    def __init__(self, cfg: type[Config] = Config) -> None:
        self.cfg = cfg
        log.info("[NLP] loading spaCy model '%s' ...", cfg.SPACY_MODEL)
        try:
            self._nlp = spacy.load(cfg.SPACY_MODEL)
        except OSError:
            log.error("[NLP] spaCy model '%s' not found.", cfg.SPACY_MODEL)
            log.error("       Run:  python -m spacy download %s", cfg.SPACY_MODEL)
            sys.exit(1)
        log.info("[NLP] ready.")

    # -- public --------------------------------------------------------------

    def analyze(self, raw_text: str) -> NLPResult:
        cleaned = self._clean(raw_text)
        doc = self._nlp(cleaned)

        keywords = [
            tok.lemma_
            for tok in doc
            if tok.pos_ in ("NOUN", "PROPN") and not tok.is_stop and tok.is_alpha
        ]
        entities = [(ent.text, ent.label_) for ent in doc.ents]
        intent = self._detect_intent(cleaned)

        result = NLPResult(text=cleaned, intent=intent,
                           keywords=keywords, entities=entities)
        log.info("[NLP] intent=%s | keywords=%s | entities=%s",
                 intent, keywords, entities)
        return result

    # -- internals -----------------------------------------------------------

    @staticmethod
    def _clean(text: str) -> str:
        text = text.strip()
        text = re.sub(r"[^\x00-\x7f]", "", text)   # drop non-ASCII
        text = re.sub(r"\s+", " ", text)
        return text

    @classmethod
    def _detect_intent(cls, text: str) -> str:
        for label, pattern in cls._INTENT_PATTERNS:
            if pattern.search(text):
                return label
        return "general"


# ---------------------------------------------------------------------------
# Module 3 - LLM (LLaMA 3 via Ollama)
# ---------------------------------------------------------------------------

_SYSTEM_PROMPT = """\
You are a concise, helpful AI assistant embedded inside a Speech and Text Analyzer.
Follow these rules in every reply:
- Answer in 2 to 4 sentences unless the user explicitly asks for more detail.
- If the user is just greeting you, greet back briefly.
- If asked to summarize, return a short bullet list.
- If asked to define something, give one clear paragraph.
- If you are uncertain, say so plainly instead of inventing facts.
- Reply in the same language the user used.
"""


class LLMResponder:
    """
    Generates a reply from the NLP result using a local Ollama model,
    and keeps a rolling conversation history so multi-turn dialogue
    works (e.g. follow-up questions, pronouns, "what about ...?").

    The history stores natural user/assistant exchanges. The structured
    NLP metadata (intent, keywords, entities) is only attached to the
    current turn, so past structured prompts don't pollute future
    context windows.
    """

    def __init__(self, cfg: type[Config] = Config) -> None:
        self.cfg = cfg
        # Each entry is {"role": "user"|"assistant", "content": str}.
        self._history: list[dict[str, str]] = []
        log.info("[LLM] using Ollama model '%s'.", cfg.LLM_MODEL)

    # -- public --------------------------------------------------------------

    def generate(self, nlp: NLPResult) -> str:
        current_user_msg = self._build_user_prompt(nlp)

        messages: list[dict[str, str]] = [
            {"role": "system", "content": _SYSTEM_PROMPT},
            *self._history,
            {"role": "user", "content": current_user_msg},
        ]

        try:
            response = ollama.chat(
                model=self.cfg.LLM_MODEL,
                messages=messages,
                options={
                    "num_predict": self.cfg.LLM_MAX_TOKENS,
                    "temperature": self.cfg.LLM_TEMPERATURE,
                },
            )
            reply = response["message"]["content"].strip()
        except Exception as exc:
            # Warning only — full traceback drowns API/mobile request logs during dev
            log.warning("[LLM] generation failed: %s", exc)
            return (f"[LLM error] {exc}\n"
                    f"Check that Ollama is running and that "
                    f"`ollama pull {self.cfg.LLM_MODEL}` has been done.")

        # Remember the natural exchange for future turns - NOT the
        # structured prompt, which would confuse later context.
        self._remember(user_text=nlp.text, assistant_reply=reply)

        log.info("[LLM] reply: %s | history=%d turns",
                 reply.replace("\n", " ")[:120], len(self._history) // 2)
        return reply

    def reset(self) -> None:
        """Forget all prior turns - start a fresh conversation."""
        self._history.clear()
        log.info("[LLM] conversation history cleared.")

    def history_size(self) -> int:
        """Return the number of complete (user, assistant) turns stored."""
        return len(self._history) // 2

    # -- internals -----------------------------------------------------------

    def _remember(self, *, user_text: str, assistant_reply: str) -> None:
        self._history.append({"role": "user",      "content": user_text})
        self._history.append({"role": "assistant", "content": assistant_reply})
        self._trim_history()

    def _trim_history(self) -> None:
        """Keep only the most recent N turns (each turn = 2 messages)."""
        max_messages = self.cfg.MAX_HISTORY_TURNS * 2
        if len(self._history) > max_messages:
            drop = len(self._history) - max_messages
            del self._history[:drop]

    @staticmethod
    def _build_user_prompt(nlp: NLPResult) -> str:
        keywords = ", ".join(nlp.keywords) or "none"
        entities = "; ".join(f"{t} ({lbl})" for t, lbl in nlp.entities) or "none"
        return (
            f"[NLP context for this turn]\n"
            f"  intent   : {nlp.intent}\n"
            f"  keywords : {keywords}\n"
            f"  entities : {entities}\n\n"
            f"User said: {nlp.text}"
        )


# ---------------------------------------------------------------------------
# Pipeline orchestrator
# ---------------------------------------------------------------------------

class SpeechTextAnalyzer:
    """High-level facade that wires the three modules together."""

    def __init__(self, cfg: type[Config] = Config) -> None:
        self.cfg = cfg
        self._stt: Optional[SpeechToText] = None
        self.nlp = NLPProcessor(cfg)
        self.llm = LLMResponder(cfg)

    def _get_stt(self) -> SpeechToText:
        """Load Whisper on first voice/file request (keeps API startup fast)."""
        if self._stt is None:
            self._stt = SpeechToText(self.cfg)
        return self._stt

    @property
    def whisper_ready(self) -> bool:
        return self._stt is not None

    # -- public entry points -------------------------------------------------

    def process_text(self, text: str) -> PipelineResult:
        if not text.strip():
            return PipelineResult(user_input=text, nlp=None,
                                  reply="(empty input - please type something.)")
        nlp_result = self.nlp.analyze(text)
        reply = self.llm.generate(nlp_result)
        return PipelineResult(user_input=text, nlp=nlp_result, reply=reply)

    def process_voice(self) -> PipelineResult:
        transcript = self._get_stt().from_microphone()
        if not transcript:
            return PipelineResult(user_input="", nlp=None,
                                  reply="I didn't catch any speech. Please try again.")
        return self.process_text(transcript)

    def process_audio_file(self, path: str) -> PipelineResult:
        transcript = self._get_stt().from_file(path)
        return self.process_text(transcript)

    def reset_conversation(self) -> None:
        """Clear the LLM's memory of past turns."""
        self.llm.reset()


# ---------------------------------------------------------------------------
# CLI entry point (text-only fallback if Tkinter is unavailable)
# ---------------------------------------------------------------------------

def _print_result(result: PipelineResult) -> None:
    if result.nlp:
        print(f"  intent   : {result.nlp.intent}")
        print(f"  keywords : {', '.join(result.nlp.keywords) or '-'}")
        print(f"  entities : {', '.join(f'{t}({l})' for t,l in result.nlp.entities) or '-'}")
    print(f"Assistant: {result.reply}\n")


def _cli() -> None:
    analyzer = SpeechTextAnalyzer()
    print("\n=== Speech & Text Analyzer (CLI) ===")
    print("Type a message, 'mic' to speak, 'reset' to clear memory, 'quit' to exit.\n")
    while True:
        try:
            line = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if not line:
            continue
        cmd = line.lower()
        if cmd in ("quit", "exit", "bye"):
            print("Goodbye!")
            break
        if cmd in ("reset", "clear", "new"):
            analyzer.reset_conversation()
            print("[conversation cleared]\n")
            continue
        if cmd == "mic":
            result = analyzer.process_voice()
            if result.user_input:
                print(f"You (voice): {result.user_input}")
        else:
            result = analyzer.process_text(line)
        _print_result(result)


if __name__ == "__main__":
    _cli()
