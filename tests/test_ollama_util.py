"""Ollama health helper tests."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from ollama_util import check_ollama


def test_check_ollama_ok_when_model_listed():
    mock_model = MagicMock()
    mock_model.model = "llama3:latest"
    mock_response = MagicMock()
    mock_response.models = [mock_model]
    mock_client = MagicMock()
    mock_client.list.return_value = mock_response

    with patch("ollama.Client", return_value=mock_client):
        assert check_ollama("llama3") is True


def test_check_ollama_down_on_connection_error():
    with patch("ollama.Client", side_effect=ConnectionError("refused")):
        assert check_ollama("llama3") is False
