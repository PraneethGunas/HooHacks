"""Unit tests for backend/agents/_helpers.py — JSON extraction, tool records, summarizer."""

import pytest
from backend.agents._helpers import _extract_json_block, _parse_json_lenient


# ---------------------------------------------------------------------------
# _extract_json_block
# ---------------------------------------------------------------------------

class TestExtractJsonBlock:
    def test_fenced_json(self):
        text = 'Some text\n```json\n{"key": "value"}\n```\nMore text'
        result = _extract_json_block(text)
        assert result == {"key": "value"}

    def test_unfenced_json(self):
        text = 'Here is the result: {"count": 42, "items": [1, 2, 3]}'
        result = _extract_json_block(text)
        assert result["count"] == 42
        assert result["items"] == [1, 2, 3]

    def test_gemini_list_of_parts(self):
        """Gemini returns content as list of dicts with 'text' keys."""
        text = [
            {"type": "text", "text": '```json\n{"action": "test"}'},
            {"type": "text", "text": '\n```'},
        ]
        result = _extract_json_block(text)
        assert result["action"] == "test"

    def test_plain_string_list(self):
        text = ['{"a": 1}']
        result = _extract_json_block(text)
        assert result["a"] == 1

    def test_non_string_non_list(self):
        text = 42
        with pytest.raises(ValueError, match="No JSON found"):
            _extract_json_block(text)

    def test_no_json_raises(self):
        with pytest.raises(ValueError, match="No JSON found"):
            _extract_json_block("Just some plain text with no JSON")

    def test_empty_fence_falls_through(self):
        text = '```json\n\n```\nBut here: {"fallback": true}'
        result = _extract_json_block(text)
        assert result["fallback"] is True

    def test_nested_json(self):
        text = '```json\n{"a": {"b": [1, 2, {"c": 3}]}}\n```'
        result = _extract_json_block(text)
        assert result["a"]["b"][2]["c"] == 3


# ---------------------------------------------------------------------------
# _parse_json_lenient
# ---------------------------------------------------------------------------

class TestParseJsonLenient:
    def test_valid_json(self):
        result = _parse_json_lenient('{"key": "value"}')
        assert result["key"] == "value"

    def test_trailing_comma_object(self):
        result = _parse_json_lenient('{"a": 1, "b": 2,}')
        assert result["a"] == 1
        assert result["b"] == 2

    def test_trailing_comma_array(self):
        result = _parse_json_lenient('{"items": [1, 2, 3,]}')
        assert result["items"] == [1, 2, 3]

    def test_none_to_null(self):
        result = _parse_json_lenient('{"value": None}')
        assert result["value"] is None

    def test_still_raises_on_garbage(self):
        with pytest.raises(Exception):
            _parse_json_lenient("not json at all")
