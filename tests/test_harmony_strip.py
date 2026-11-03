"""Harmony/reasoning token stripping (gpt-oss style channel leaks)."""
from backend.llm_client import _clean_content


def test_final_channel_kept():
    raw = (
        "<|start|>assistant<|channel|>commentary<|message|>The user says hi."
        "<|channel|>final<|message|>At your service, Sir.<|end|>"
    )
    assert _clean_content(raw) == "At your service, Sir."


def test_malformed_single_bracket_stripped():
    raw = "<|channel|>thought <channel|>*nods.* At your service, Sir. Shall we begin?"
    out = _clean_content(raw)
    assert "<|" not in out and "|>" not in out
    assert "At your service, Sir." in out


def test_think_block_dropped():
    raw = "<think>Let me reason about this.</think>Certainly."
    assert _clean_content(raw) == "Certainly."


def test_plain_text_untouched():
    raw = "Hello. I am James."
    assert _clean_content(raw) == raw


def test_parse_strips_channels():
    from backend.llm_client import RawLLMClient
    data = {"choices": [{"message": {
        "content": "<|channel|>final<|message|>Hi there.<|end|>",
        "tool_calls": [],
    }}]}
    content, calls = RawLLMClient._parse(data)
    assert content == "Hi there."
    assert calls == []
