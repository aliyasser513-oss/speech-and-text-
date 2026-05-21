"""Lazy Whisper loading — STT not constructed until first audio path."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import analyzer as analyzer_mod


def test_analyzer_init_does_not_load_whisper():
    with patch.object(analyzer_mod, "SpeechToText") as mock_stt:
        mock_stt.return_value = MagicMock()
        with patch.object(analyzer_mod, "NLPProcessor") as mock_nlp:
            mock_nlp.return_value = MagicMock()
            with patch.object(analyzer_mod, "LLMResponder") as mock_llm:
                mock_llm.return_value = MagicMock()
                a = analyzer_mod.SpeechTextAnalyzer()
                mock_stt.assert_not_called()
                assert not a.whisper_ready


def test_process_audio_file_loads_whisper_once():
    with patch.object(analyzer_mod, "SpeechToText") as mock_stt:
        instance = MagicMock()
        instance.from_file.return_value = "hello"
        mock_stt.return_value = instance
        with patch.object(analyzer_mod, "NLPProcessor") as mock_nlp:
            nlp_instance = MagicMock()
            nlp_result = MagicMock()
            nlp_result.text = "hello"
            nlp_result.intent = "greeting"
            nlp_result.keywords = []
            nlp_result.entities = []
            nlp_instance.analyze.return_value = nlp_result
            mock_nlp.return_value = nlp_instance
            with patch.object(analyzer_mod, "LLMResponder") as mock_llm:
                llm_instance = MagicMock()
                llm_instance.generate.return_value = "Hi"
                mock_llm.return_value = llm_instance
                a = analyzer_mod.SpeechTextAnalyzer()
                a.process_audio_file("/tmp/fake.wav")
                mock_stt.assert_called_once()
                assert a.whisper_ready
