#!/usr/bin/env python

import os
import tempfile
import pytest
from unittest.mock import patch, MagicMock
from yaoc.openai_cli import parse_image, get_model_name, print_response


class TestParseImage:
    def test_text_only(self):
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
            f.write(b"\x89PNG\r\n\x1a\n")  # PNG header bytes
            f.flush()
            path = f.name
        try:
            text, url = parse_image(f"What is this? @image:{path}")
            assert text == "What is this?"
            assert url.startswith("data:image/png;base64,")
        finally:
            os.unlink(path)

    def test_no_text(self):
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
            f.write(b"\x89PNG\r\n\x1a\n")
            f.flush()
            path = f.name
        try:
            text, url = parse_image(f"@image:{path}")
            assert text == ""
            assert url.startswith("data:image/png;base64,")
        finally:
            os.unlink(path)

    def test_image_not_at_end(self):
        # When text follows the image path, the path includes that text,
        # which makes mime type detection fail
        with pytest.raises(ValueError, match="Unsupported image type"):
            parse_image("@image:/path/image.png more text")

    def test_multiple_images(self):
        with pytest.raises(ValueError):  # splits into >2 parts
            parse_image("@image:a.png @image:b.png")

    def test_nonexistent_file(self):
        with pytest.raises(ValueError, match="file not found"):
            parse_image("@image:/nonexistent/path/image.png")

    def test_unsupported_type(self):
        with tempfile.NamedTemporaryFile(suffix=".xyz", delete=False) as f:
            f.write(b"test")
            f.flush()
            path = f.name
        try:
            with pytest.raises(ValueError, match="Unsupported image type"):
                parse_image(f"@image:{path}")
        finally:
            os.unlink(path)


class TestGetModelName:
    @patch("yaoc.openai_cli.requests.get")
    def test_returns_first_model_if_not_specified(self, mock_get):
        mock_get.return_value.json.return_value = {
            "data": [{"id": "model-a"}, {"id": "model-b"}]
        }
        result = get_model_name("http://api", "key", "")
        assert result == "model-a"

    @patch("yaoc.openai_cli.requests.get")
    def test_returns_specified_model(self, mock_get):
        mock_get.return_value.json.return_value = {
            "data": [{"id": "model-a"}, {"id": "model-b"}]
        }
        result = get_model_name("http://api", "key", "model-b")
        assert result == "model-b"

    @patch("yaoc.openai_cli.requests.get")
    def test_model_not_found(self, mock_get):
        mock_get.return_value.json.return_value = {
            "data": [{"id": "model-a"}]
        }
        with pytest.raises(ValueError, match="not found"):
            get_model_name("http://api", "key", "nonexistent")


class TestPrintResponse:
    def test_simple_content(self):
        console = MagicMock()
        response = {"content": "Hello world"}
        print_response(console, response, hide_thinking=False)
        console.print.assert_called_once()

    def test_reasoning_content_field(self):
        console = MagicMock()
        response = {
            "content": "The answer",
            "reasoning_content": "Let me think..."
        }
        with patch("yaoc.openai_cli.cprint") as mock_cprint:
            print_response(console, response, hide_thinking=False)
            mock_cprint.assert_called_once()
            assert "Let me think" in mock_cprint.call_args[0][0]

    def test_hide_thinking(self):
        console = MagicMock()
        response = {
            "content": "The answer",
            "reasoning_content": "Let me think..."
        }
        with patch("yaoc.openai_cli.cprint") as mock_cprint:
            print_response(console, response, hide_thinking=True)
            mock_cprint.assert_not_called()

    def test_answer_marker(self):
        console = MagicMock()
        response = {"content": "Thinking...\n<answer>The real answer"}
        with patch("yaoc.openai_cli.cprint") as mock_cprint:
            print_response(console, response, hide_thinking=False)
            # Should split on <answer> marker
            mock_cprint.assert_called_once()


