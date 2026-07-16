"""OpenAI Responses API summarizer boundary."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Mapping, Protocol
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from common.configuration import OpenAICredentials


OPENAI_BASE_URL = "https://api.openai.com/v1"


class OpenAIClientError(RuntimeError):
    """Raised when OpenAI summarization fails."""


class OpenAITransport(Protocol):
    """Minimal HTTP transport interface for OpenAI API calls."""

    def post(
        self,
        url: str,
        headers: Mapping[str, str],
        body: Mapping[str, Any],
    ) -> OpenAIResponse:
        """Send a POST request and return a response."""


class OpenAIResponse(Protocol):
    """Minimal OpenAI response interface."""

    status_code: int

    def json(self) -> Mapping[str, Any]:
        """Return the response body as JSON data."""


@dataclass(frozen=True)
class UrllibOpenAIResponse:
    """OpenAI response backed by a standard-library HTTP response."""

    status_code: int
    body: bytes = field(repr=False)

    def json(self) -> Mapping[str, Any]:
        """Decode the response body as JSON."""

        if not self.body:
            return {}
        try:
            payload = json.loads(self.body.decode("utf-8"))
        except json.JSONDecodeError as exc:
            raise OpenAIClientError("OpenAI response body was not valid JSON.") from exc
        if not isinstance(payload, Mapping):
            raise OpenAIClientError("OpenAI response body must be a JSON object.")
        return payload


@dataclass(frozen=True)
class UrllibOpenAITransport:
    """OpenAI transport using Python's standard library."""

    timeout_seconds: float = 60.0

    def post(
        self,
        url: str,
        headers: Mapping[str, str],
        body: Mapping[str, Any],
    ) -> UrllibOpenAIResponse:
        request_headers = dict(headers)
        request_headers.setdefault("Content-Type", "application/json")
        request = Request(
            url,
            headers=request_headers,
            data=json.dumps(body).encode("utf-8"),
            method="POST",
        )
        try:
            with urlopen(request, timeout=self.timeout_seconds) as response:
                status_code = int(response.status)
                response_body = response.read()
        except HTTPError as exc:
            return UrllibOpenAIResponse(status_code=int(exc.code), body=exc.read())
        except URLError as exc:
            raise OpenAIClientError("OpenAI request failed.") from exc

        return UrllibOpenAIResponse(status_code=status_code, body=response_body)


@dataclass(frozen=True)
class OpenAIResponsesSummaryProvider:
    """Summarize Clarity prompts with the OpenAI Responses API."""

    api_key: str = field(repr=False)
    model: str
    transport: OpenAITransport = field(repr=False)
    base_url: str = OPENAI_BASE_URL

    def summarize(self, prompt: str) -> str:
        """Return summary text for a Clarity prompt."""

        clean_prompt = _required_text(prompt, "prompt")
        response = self.transport.post(
            self._responses_url(),
            headers=self._json_headers(),
            body={
                "model": _required_text(self.model, "model"),
                "input": clean_prompt,
            },
        )
        if response.status_code != 200:
            raise OpenAIClientError(
                f"OpenAI Responses API request failed with status {response.status_code}"
            )
        return _response_text(response.json())

    def _json_headers(self) -> dict[str, str]:
        token = _required_text(self.api_key, "api_key")
        return {
            "Accept": "application/json",
            "Authorization": f"Bearer {token}",
        }

    def _responses_url(self) -> str:
        return f"{self.base_url.rstrip('/')}/responses"


def build_openai_summary_provider(
    credentials: OpenAICredentials,
    *,
    transport: OpenAITransport | None = None,
) -> OpenAIResponsesSummaryProvider:
    """Build an OpenAI Responses API summarizer from local credentials."""

    return OpenAIResponsesSummaryProvider(
        api_key=_required_text(credentials.api_key, "api_key"),
        model=_required_text(credentials.model, "model"),
        base_url=credentials.base_url or OPENAI_BASE_URL,
        transport=transport or UrllibOpenAITransport(),
    )


def _response_text(payload: Mapping[str, Any]) -> str:
    output_text = payload.get("output_text")
    if isinstance(output_text, str) and output_text.strip():
        return output_text.strip()

    parts = []
    output = payload.get("output")
    if isinstance(output, list):
        for item in output:
            if not isinstance(item, Mapping):
                continue
            content = item.get("content")
            if not isinstance(content, list):
                continue
            for content_item in content:
                if not isinstance(content_item, Mapping):
                    continue
                text = content_item.get("text")
                if isinstance(text, str) and text.strip():
                    parts.append(text.strip())
    if parts:
        return "\n".join(parts)

    raise OpenAIClientError("OpenAI response did not contain output text.")


def _required_text(value: str | None, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise OpenAIClientError(f"OpenAI value is required: {name}")
    return value.strip()
