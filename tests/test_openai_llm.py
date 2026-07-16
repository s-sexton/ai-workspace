from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

import pytest

from common.configuration import OpenAICredentials
from common.openai_llm import (
    OpenAIClientError,
    OpenAIResponsesSummaryProvider,
    UrllibOpenAIResponse,
    build_openai_summary_provider,
)


@dataclass
class FakeOpenAIResponse:
    status_code: int
    payload: Mapping[str, Any]

    def json(self) -> Mapping[str, Any]:
        return self.payload


class FakeOpenAITransport:
    def __init__(self, response: FakeOpenAIResponse):
        self.response = response
        self.calls: list[tuple[str, Mapping[str, str], Mapping[str, Any]]] = []

    def post(
        self,
        url: str,
        headers: Mapping[str, str],
        body: Mapping[str, Any],
    ) -> FakeOpenAIResponse:
        self.calls.append((url, headers, body))
        return self.response


def test_openai_summary_provider_posts_responses_request():
    transport = FakeOpenAITransport(
        FakeOpenAIResponse(200, {"output_text": "Safe summary."})
    )
    provider = OpenAIResponsesSummaryProvider(
        api_key="secret-key",
        model="gpt-test",
        transport=transport,
        base_url="https://openai.example/v1",
    )

    summary = provider.summarize("Bounded Clarity prompt")

    assert summary == "Safe summary."
    assert len(transport.calls) == 1
    url, headers, body = transport.calls[0]
    assert url == "https://openai.example/v1/responses"
    assert headers["Authorization"] == "Bearer secret-key"
    assert body == {
        "model": "gpt-test",
        "input": "Bounded Clarity prompt",
    }
    assert "secret-key" not in repr(provider)


def test_openai_summary_provider_reads_nested_output_text():
    transport = FakeOpenAITransport(
        FakeOpenAIResponse(
            200,
            {
                "output": [
                    {
                        "content": [
                            {"type": "output_text", "text": "Nested summary."},
                        ]
                    }
                ]
            },
        )
    )
    provider = OpenAIResponsesSummaryProvider(
        api_key="secret-key",
        model="gpt-test",
        transport=transport,
    )

    assert provider.summarize("Prompt") == "Nested summary."


def test_openai_summary_provider_rejects_missing_output_text():
    transport = FakeOpenAITransport(FakeOpenAIResponse(200, {"output": []}))
    provider = OpenAIResponsesSummaryProvider(
        api_key="secret-key",
        model="gpt-test",
        transport=transport,
    )

    with pytest.raises(OpenAIClientError):
        provider.summarize("Prompt")


def test_openai_summary_provider_rejects_error_status_without_secret():
    transport = FakeOpenAITransport(FakeOpenAIResponse(401, {"error": "nope"}))
    provider = OpenAIResponsesSummaryProvider(
        api_key="secret-key",
        model="gpt-test",
        transport=transport,
    )

    with pytest.raises(OpenAIClientError) as exc_info:
        provider.summarize("Prompt")

    assert "401" in str(exc_info.value)
    assert "secret-key" not in str(exc_info.value)


def test_build_openai_summary_provider_uses_credentials():
    transport = FakeOpenAITransport(
        FakeOpenAIResponse(200, {"output_text": "Safe summary."})
    )

    provider = build_openai_summary_provider(
        OpenAICredentials(
            api_key="secret-key",
            model="gpt-test",
            base_url="https://openai.example/v1",
        ),
        transport=transport,
    )

    assert provider.model == "gpt-test"
    assert provider.base_url == "https://openai.example/v1"
    assert "secret-key" not in repr(provider)


def test_urllib_openai_response_rejects_non_object_json():
    response = UrllibOpenAIResponse(status_code=200, body=b"[]")

    with pytest.raises(OpenAIClientError):
        response.json()
