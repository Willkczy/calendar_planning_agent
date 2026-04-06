# =============================================================================
# tests/test_llm_client.py — LLM client module tests
# =============================================================================
# Tests that the LLM client correctly handles retries, JSON parsing, and
# error cases.  Uses mocking — does NOT make real Anthropic API calls.
#
# STEPS TO COMPLETE:
# 1. Mock the anthropic.Anthropic client.
# 2. Test successful JSON parsing.
# 3. Test retry on JSON parse failure.
# 4. Test retry on API error.
# 5. Test exhausted retries raise the expected exception.
# =============================================================================

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest


class TestCallLlmJson:
    """Tests for call_llm_json."""

    def test_valid_json_response_parsed(self):
        """A well-formed JSON response should be parsed and returned.

        STEPS:
        1. Mock _call_anthropic to return '[{"name": "task1"}]'.
        2. Call call_llm_json("some prompt").
        3. Assert result == [{"name": "task1"}].
        """
        pass  # TODO: implement

    def test_retry_on_invalid_json(self):
        """If the first response is not valid JSON, the client should retry.

        STEPS:
        1. Mock _call_anthropic to return "Here is the JSON: [...]" on the
           first call, then valid '[]' on the second call.
        2. Call call_llm_json.
        3. Assert _call_anthropic was called twice.
        4. Assert result is [].
        """
        pass  # TODO: implement

    def test_exhausted_retries_raises(self):
        """After MAX_RETRIES + 1 failed attempts, ValueError should be raised.

        STEPS:
        1. Mock _call_anthropic to always return invalid JSON.
        2. Call call_llm_json.
        3. Assert ValueError is raised.
        """
        pass  # TODO: implement

    def test_retry_on_api_error(self):
        """An anthropic.APIError should trigger a retry.

        STEPS:
        1. Mock _call_anthropic to raise anthropic.APIError on the first
           call, then return valid JSON on the second.
        2. Assert call_llm_json returns the valid result.
        """
        pass  # TODO: implement


class TestCallLlmText:
    """Tests for call_llm_text."""

    def test_returns_text(self):
        """A normal response should be returned as-is.

        STEPS:
        1. Mock _call_anthropic to return "Some rationale text."
        2. Call call_llm_text("some prompt").
        3. Assert result == "Some rationale text."
        """
        pass  # TODO: implement

    def test_exhausted_retries_raises_runtime_error(self):
        """After all retries fail, RuntimeError should be raised.

        STEPS:
        1. Mock _call_anthropic to always raise APIError.
        2. Assert RuntimeError is raised.
        """
        pass  # TODO: implement
