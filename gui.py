"""
Speech and Text Analyzer - Desktop GUI
TM471 Final Year Project | Ali Yasser Ali Mohammed | 21510864

A Tkinter front-end for the SpeechTextAnalyzer pipeline.

Design notes
------------
* The pipeline is heavy (Whisper + spaCy + LLaMA 3), so every call to
  it runs in a background daemon thread. All GUI updates from those
  threads are marshalled back to the main thread via ``root.after``,
  which is the canonical thread-safe pattern in Tkinter.
* Three colour-coded message roles (you / assistant / system) keep
  the transcript readable. A separate metadata strip exposes the NLP
  internals (intent, keywords, entities) for transparency.
"""

from __future__ import annotations

import threading
import tkinter as tk
from tkinter import scrolledtext

from analyzer import PipelineResult, SpeechTextAnalyzer


# ---------------------------------------------------------------------------
# Theme
# ---------------------------------------------------------------------------

class Theme:
    BG       = "#0f1117"   # window background
    PANEL    = "#1a1d27"   # cards / chat surface
    BORDER   = "#2d3148"
    USER     = "#4f8ef7"   # blue
    ASSIST   = "#34d399"   # green
    META     = "#a78bfa"   # purple
    WARN     = "#fbbf24"   # amber
    ERROR    = "#f87171"   # red
    FG       = "#e2e8f0"
    FG_MUTED = "#64748b"

    FONT_UI  = ("Segoe UI", 10)
    FONT_BIG = ("Segoe UI", 16, "bold")
    FONT_CHAT = ("Consolas", 11)
    FONT_META = ("Consolas", 9)


# ---------------------------------------------------------------------------
# Application
# ---------------------------------------------------------------------------

class AnalyzerApp:
    """Top-level Tkinter application."""

    TITLE = "Speech & Text Analyzer - TM471"
    SUBTITLE = "TM471 - Ali Yasser Ali - 21510864"

    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title(self.TITLE)
        self.root.configure(bg=Theme.BG)
        self.root.geometry("900x700")
        self.root.minsize(700, 500)

        self._mic_busy = False
        self._send_busy = False

        # Build UI before instantiating the (slow) analyzer so the
        # window appears immediately; load the pipeline in a thread.
        self._build_ui()
        self.analyzer: SpeechTextAnalyzer | None = None
        self._set_status("Loading models (Whisper, spaCy, Ollama) ...", Theme.WARN)
        threading.Thread(target=self._load_pipeline, daemon=True).start()

    # -- model loading -------------------------------------------------------

    def _load_pipeline(self) -> None:
        try:
            analyzer = SpeechTextAnalyzer()
        except Exception as exc:
            self._dispatch(self._on_load_error, str(exc))
            return
        self._dispatch(self._on_load_ready, analyzer)

    def _on_load_ready(self, analyzer: SpeechTextAnalyzer) -> None:
        self.analyzer = analyzer
        self._set_status("Ready.", Theme.FG_MUTED)
        self._post("assistant", "Assistant",
                   "Hello! Type a message below or click 'Speak' to use your microphone.")

    def _on_load_error(self, message: str) -> None:
        self._set_status("Failed to load pipeline.", Theme.ERROR)
        self._post("error", "System", f"Pipeline failed to load:\n{message}")

    # -- UI construction -----------------------------------------------------

    def _build_ui(self) -> None:
        self._build_header()
        self._build_chat()
        self._build_meta_strip()
        self._build_input_row()
        self._build_status_bar()

    def _build_header(self) -> None:
        header = tk.Frame(self.root, bg=Theme.PANEL, padx=24, pady=14)
        header.pack(fill="x")

        tk.Label(header, text="Speech & Text Analyzer",
                 font=Theme.FONT_BIG, bg=Theme.PANEL, fg=Theme.USER
                 ).pack(side="left")

        tk.Label(header, text=self.SUBTITLE,
                 font=Theme.FONT_UI, bg=Theme.PANEL, fg=Theme.FG_MUTED
                 ).pack(side="right", pady=4)

    def _build_chat(self) -> None:
        wrapper = tk.Frame(self.root, bg=Theme.BG, padx=16, pady=10)
        wrapper.pack(fill="both", expand=True)

        self.chat = scrolledtext.ScrolledText(
            wrapper,
            bg=Theme.PANEL, fg=Theme.FG,
            insertbackground=Theme.FG,
            font=Theme.FONT_CHAT,
            relief="flat", borderwidth=0,
            wrap="word", state="disabled",
            padx=14, pady=12,
        )
        self.chat.pack(fill="both", expand=True)

        # Role-specific text styling.
        self.chat.tag_config("user_label",
                             foreground=Theme.USER,
                             font=("Consolas", 11, "bold"),
                             spacing1=8)
        self.chat.tag_config("assistant_label",
                             foreground=Theme.ASSIST,
                             font=("Consolas", 11, "bold"),
                             spacing1=8)
        self.chat.tag_config("error_label",
                             foreground=Theme.ERROR,
                             font=("Consolas", 11, "bold"),
                             spacing1=8)
        self.chat.tag_config("body",
                             foreground=Theme.FG,
                             lmargin1=16, lmargin2=16, spacing3=4)
        self.chat.tag_config("divider",
                             foreground=Theme.BORDER)

    def _build_meta_strip(self) -> None:
        tk.Frame(self.root, bg=Theme.BORDER, height=1).pack(fill="x")
        self.meta_var = tk.StringVar(
            value="Intent: -    Keywords: -    Entities: -"
        )
        tk.Label(
            self.root, textvariable=self.meta_var,
            bg=Theme.PANEL, fg=Theme.META,
            font=Theme.FONT_META,
            anchor="w", padx=16, pady=6,
        ).pack(fill="x")

    def _build_input_row(self) -> None:
        row = tk.Frame(self.root, bg=Theme.BG, padx=16, pady=10)
        row.pack(fill="x")

        self.entry = tk.Entry(
            row,
            bg=Theme.PANEL, fg=Theme.FG, insertbackground=Theme.FG,
            font=("Consolas", 12),
            relief="flat", bd=0,
        )
        self.entry.pack(side="left", fill="x", expand=True, ipady=10, padx=(0, 8))
        self.entry.bind("<Return>", lambda _e: self._on_send())

        self.send_btn = self._make_button(row, "Send", Theme.USER, self._on_send)
        self.send_btn.pack(side="left")

        self.mic_btn = self._make_button(row, "Speak", Theme.WARN, self._on_mic,
                                         fg_color="#1a1d27")
        self.mic_btn.pack(side="left", padx=(8, 0))

        self.new_btn = self._make_button(row, "New chat", Theme.BORDER, self._on_new_chat)
        self.new_btn.pack(side="left", padx=(8, 0))

    def _build_status_bar(self) -> None:
        self.status_var = tk.StringVar(value="Starting up ...")
        self.status_label = tk.Label(
            self.root, textvariable=self.status_var,
            bg=Theme.BG, fg=Theme.FG_MUTED,
            font=Theme.FONT_META,
            anchor="w", padx=16, pady=4,
        )
        self.status_label.pack(fill="x")

    @staticmethod
    def _make_button(parent, label, bg, cmd, *, fg_color="white"):
        return tk.Button(
            parent, text=label,
            bg=bg, fg=fg_color,
            activebackground=bg,
            font=("Segoe UI", 10, "bold"),
            relief="flat", cursor="hand2",
            padx=18, pady=8, bd=0,
            command=cmd,
        )

    # -- chat helpers --------------------------------------------------------

    def _post(self, role: str, label: str, body: str) -> None:
        tag = {"user": "user_label",
               "assistant": "assistant_label",
               "error": "error_label"}.get(role, "assistant_label")

        self.chat.config(state="normal")
        self.chat.insert("end", f"{label}\n", tag)
        self.chat.insert("end", f"{body}\n", "body")
        self.chat.insert("end", ("-" * 70) + "\n", "divider")
        self.chat.config(state="disabled")
        self.chat.see("end")

    def _show_meta(self, result: PipelineResult) -> None:
        if result.nlp is None:
            self.meta_var.set("Intent: -    Keywords: -    Entities: -")
            return
        kw  = ", ".join(result.nlp.keywords) or "-"
        ent = ", ".join(f"{t}({lbl})" for t, lbl in result.nlp.entities) or "-"
        self.meta_var.set(
            f"Intent: {result.nlp.intent}    Keywords: {kw}    Entities: {ent}"
        )

    def _set_status(self, message: str, color: str = Theme.FG_MUTED) -> None:
        self.status_var.set(message)
        self.status_label.configure(fg=color)

    # -- event handlers ------------------------------------------------------

    def _on_send(self) -> None:
        if self._send_busy or self.analyzer is None:
            return
        text = self.entry.get().strip()
        if not text:
            return
        self.entry.delete(0, "end")
        self._post("user", "You", text)
        self._send_busy = True
        self._set_status("Analysing ...", Theme.WARN)
        threading.Thread(target=self._run_text, args=(text,), daemon=True).start()

    def _on_mic(self) -> None:
        if self._mic_busy or self.analyzer is None:
            return
        self._mic_busy = True
        self.mic_btn.configure(text="Recording ...", state="disabled")
        self._set_status("Listening - speak now ...", Theme.WARN)
        threading.Thread(target=self._run_voice, daemon=True).start()

    def _on_new_chat(self) -> None:
        """Clear the LLM's memory of past turns and reset the visible transcript."""
        if self.analyzer is None or self._send_busy or self._mic_busy:
            return
        self.analyzer.reset_conversation()
        self.chat.config(state="normal")
        self.chat.delete("1.0", "end")
        self.chat.config(state="disabled")
        self.meta_var.set("Intent: -    Keywords: -    Entities: -")
        self._post("assistant", "Assistant",
                   "New chat started - previous context has been cleared.")
        self._set_status("Ready.", Theme.FG_MUTED)

    # -- background workers --------------------------------------------------

    def _run_text(self, text: str) -> None:
        assert self.analyzer is not None
        result = self.analyzer.process_text(text)
        self._dispatch(self._show_text_result, result)

    def _run_voice(self) -> None:
        assert self.analyzer is not None
        result = self.analyzer.process_voice()
        self._dispatch(self._show_voice_result, result)

    # -- main-thread result handlers ----------------------------------------

    def _show_text_result(self, result: PipelineResult) -> None:
        self._show_meta(result)
        self._post("assistant", "Assistant", result.reply)
        self._set_status("Ready.", Theme.FG_MUTED)
        self._send_busy = False

    def _show_voice_result(self, result: PipelineResult) -> None:
        if result.user_input:
            self._post("user", "You (voice)", result.user_input)
        self._show_text_result(result)
        self.mic_btn.configure(text="Speak", state="normal")
        self._mic_busy = False

    # -- thread-safe dispatch -----------------------------------------------

    def _dispatch(self, fn, *args) -> None:
        """Schedule fn(*args) to run on the Tk main thread."""
        self.root.after(0, lambda: fn(*args))


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    root = tk.Tk()
    AnalyzerApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
