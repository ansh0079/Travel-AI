"""
Unit tests for ChatService internals (parser + streaming fallback behavior).
"""

from types import SimpleNamespace

from app.services.chat_service import ChatService, ChatSession


class _FakeChunk:
    def __init__(self, content: str):
        self.choices = [SimpleNamespace(delta=SimpleNamespace(content=content))]


class _FakeStream:
    def __init__(self, parts):
        self._parts = list(parts)
        self._idx = 0

    def __aiter__(self):
        self._idx = 0
        return self

    async def __anext__(self):
        if self._idx >= len(self._parts):
            raise StopAsyncIteration
        part = self._parts[self._idx]
        self._idx += 1
        return _FakeChunk(part)


async def _noop_async(*_args, **_kwargs):
    return None


def test_parse_combined_stream_output_tagged_blocks():
    service = ChatService()
    raw = (
        "<assistant_response>Hello there</assistant_response>"
        "<extracted_json>{\"origin\":\"London\",\"intent\":\"discover\"}</extracted_json>"
    )

    response, extracted = service._parse_combined_stream_output(raw)

    assert response == "Hello there"
    assert extracted["origin"] == "London"
    assert extracted["intent"] == "discover"


async def test_streaming_falls_back_to_legacy_when_combined_call_fails_early(monkeypatch):
    service = ChatService()

    class _FailingCompletions:
        async def create(self, *args, **kwargs):
            raise RuntimeError("forced stream failure")

    service.ai_provider = SimpleNamespace(
        client=SimpleNamespace(chat=SimpleNamespace(completions=_FailingCompletions())),
        model="gpt-3.5-turbo",
    )

    async def _fake_legacy_stream(_session, _grounding):
        yield "legacy-response"

    update_called = {"value": False}

    async def _fake_update_context(_session, _msg):
        update_called["value"] = True

    monkeypatch.setattr(service, "_generate_response_stream", _fake_legacy_stream)
    monkeypatch.setattr(service, "_update_context", _fake_update_context)
    monkeypatch.setattr(service, "_save_session", _noop_async)
    monkeypatch.setattr(service, "_hydrate_from_user_profile", _noop_async)
    monkeypatch.setattr(service, "_should_run_grounding", lambda *_args, **_kwargs: False)

    chunks = []
    async for token in service.send_message_streaming(
        session_id="test-session",
        user_message="plan a trip",
        user_id=None,
    ):
        chunks.append(token)

    full = "".join(chunks)
    assert "legacy-response" in full
    assert update_called["value"] is True


async def test_streaming_passthrough_handles_short_non_tagged_output(monkeypatch):
    service = ChatService()

    class _Completions:
        async def create(self, *args, **kwargs):
            return _FakeStream(["Short reply"])

    service.ai_provider = SimpleNamespace(
        client=SimpleNamespace(chat=SimpleNamespace(completions=_Completions())),
        model="gpt-3.5-turbo",
    )

    monkeypatch.setattr(service, "_save_session", _noop_async)
    monkeypatch.setattr(service, "_hydrate_from_user_profile", _noop_async)
    monkeypatch.setattr(service, "_should_run_grounding", lambda *_args, **_kwargs: False)

    chunks = []
    async for token in service.send_message_streaming(
        session_id="test-session-2",
        user_message="hello",
        user_id=None,
    ):
        chunks.append(token)

    full = "".join(chunks)
    assert "Short reply" in full
