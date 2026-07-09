"""Microsoft Graph email transport boundary for AI Workspace."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Mapping, Protocol
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen

from common.configuration import GraphCredentials
from common.email import (
    EmailClientError,
    SequenceEmailMessages,
    graph_message_to_email_payload,
)


GRAPH_BASE_URL = "https://graph.microsoft.com/v1.0"


class GraphClientError(RuntimeError):
    """Raised when Microsoft Graph email operations fail."""


class GraphTransport(Protocol):
    """Minimal HTTP transport interface used by Graph email adapters."""

    def get(self, url: str, headers: Mapping[str, str]) -> GraphResponse:
        """Send a GET request and return a response."""

    def post(
        self,
        url: str,
        headers: Mapping[str, str],
        body: Mapping[str, Any],
    ) -> GraphResponse:
        """Send a POST request and return a response."""


class GraphTokenTransport(Protocol):
    """Minimal HTTP transport interface for Graph token acquisition."""

    def post_form(
        self,
        url: str,
        headers: Mapping[str, str],
        form: Mapping[str, str],
    ) -> GraphResponse:
        """Send a form-encoded POST request and return a response."""


class GraphResponse(Protocol):
    """Minimal Graph response interface."""

    status_code: int

    def json(self) -> Mapping[str, Any]:
        """Return the response body as JSON data."""


@dataclass(frozen=True)
class UrllibGraphResponse:
    """Graph response backed by a standard-library HTTP response."""

    status_code: int
    body: bytes = field(repr=False)

    def json(self) -> Mapping[str, Any]:
        """Decode the response body as JSON."""

        if not self.body:
            return {}
        try:
            payload = json.loads(self.body.decode("utf-8"))
        except json.JSONDecodeError as exc:
            raise GraphClientError("Graph response body was not valid JSON.") from exc

        if not isinstance(payload, Mapping):
            raise GraphClientError("Graph response body must be a JSON object.")

        return payload


@dataclass(frozen=True)
class UrllibGraphTransport:
    """Microsoft Graph transport using Python's standard library."""

    timeout_seconds: float = 30.0

    def get(self, url: str, headers: Mapping[str, str]) -> UrllibGraphResponse:
        """Send a GET request to Microsoft Graph."""

        return self._send("GET", url, headers=headers)

    def post(
        self,
        url: str,
        headers: Mapping[str, str],
        body: Mapping[str, Any],
    ) -> UrllibGraphResponse:
        """Send a POST request to Microsoft Graph."""

        return self._send("POST", url, headers=headers, body=body)

    def _send(
        self,
        method: str,
        url: str,
        *,
        headers: Mapping[str, str],
        body: Mapping[str, Any] | None = None,
    ) -> UrllibGraphResponse:
        data = None
        request_headers = dict(headers)
        if body is not None:
            data = json.dumps(body).encode("utf-8")
            request_headers.setdefault("Content-Type", "application/json")
        request = Request(url, headers=request_headers, data=data, method=method)

        try:
            with urlopen(request, timeout=self.timeout_seconds) as response:
                status_code = int(response.status)
                response_body = response.read()
        except HTTPError as exc:
            return UrllibGraphResponse(status_code=int(exc.code), body=exc.read())
        except URLError as exc:
            raise GraphClientError("Microsoft Graph request failed.") from exc

        return UrllibGraphResponse(status_code=status_code, body=response_body)


@dataclass(frozen=True)
class UrllibGraphTokenTransport:
    """Microsoft identity token transport using Python's standard library."""

    timeout_seconds: float = 30.0

    def post_form(
        self,
        url: str,
        headers: Mapping[str, str],
        form: Mapping[str, str],
    ) -> UrllibGraphResponse:
        """Send a form-encoded POST request."""

        body = urlencode(form).encode("utf-8")
        request_headers = dict(headers)
        request_headers.setdefault(
            "Content-Type",
            "application/x-www-form-urlencoded",
        )
        request = Request(url, headers=request_headers, data=body, method="POST")

        try:
            with urlopen(request, timeout=self.timeout_seconds) as response:
                status_code = int(response.status)
                response_body = response.read()
        except HTTPError as exc:
            return UrllibGraphResponse(status_code=int(exc.code), body=exc.read())
        except URLError as exc:
            raise GraphClientError("Microsoft identity token request failed.") from exc

        return UrllibGraphResponse(status_code=status_code, body=response_body)


@dataclass(frozen=True)
class GraphClientCredentialsTokenProvider:
    """Acquire Microsoft Graph app-only tokens with client credentials."""

    credentials: GraphCredentials = field(repr=False)
    transport: GraphTokenTransport = field(repr=False)
    authority_base_url: str = "https://login.microsoftonline.com"
    scope: str = "https://graph.microsoft.com/.default"

    def access_token(self) -> str:
        """Return a Graph access token from Microsoft identity platform."""

        tenant_id = _required_text(self.credentials.tenant_id, "tenant_id")
        client_id = _required_text(self.credentials.client_id, "client_id")
        client_secret = _required_text(
            self.credentials.client_secret,
            "client_secret",
        )
        response = self.transport.post_form(
            self._token_url(tenant_id),
            headers={"Accept": "application/json"},
            form={
                "client_id": client_id,
                "client_secret": client_secret,
                "grant_type": "client_credentials",
                "scope": self.scope,
            },
        )
        if response.status_code != 200:
            raise GraphClientError(
                f"Microsoft identity token request failed with status {response.status_code}"
            )
        payload = response.json()
        token = payload.get("access_token")
        if not isinstance(token, str) or not token.strip():
            raise GraphClientError(
                "Microsoft identity token response missing access_token."
            )
        return token.strip()

    def _token_url(self, tenant_id: str) -> str:
        return (
            f"{self.authority_base_url.rstrip('/')}/"
            f"{quote(tenant_id, safe='')}/oauth2/v2.0/token"
        )


def build_graph_email_move_transport(
    credentials: GraphCredentials,
    *,
    graph_transport: GraphTransport | None = None,
    token_transport: GraphTokenTransport | None = None,
    use_bearer_auth: bool = False,
) -> GraphEmailMoveTransport:
    """Build a Graph email move transport from local credentials."""

    if use_bearer_auth:
        access_token = _required_text(credentials.access_token, "access_token")
    else:
        provider = GraphClientCredentialsTokenProvider(
            credentials=credentials,
            transport=token_transport or UrllibGraphTokenTransport(),
        )
        access_token = provider.access_token()

    return GraphEmailMoveTransport(
        access_token=access_token,
        transport=graph_transport or UrllibGraphTransport(),
    )


def build_graph_email_read_transport(
    credentials: GraphCredentials,
    *,
    graph_transport: GraphTransport | None = None,
    token_transport: GraphTokenTransport | None = None,
    use_bearer_auth: bool = False,
) -> GraphEmailReadTransport:
    """Build a Graph email read transport from local credentials."""

    if use_bearer_auth:
        access_token = _required_text(credentials.access_token, "access_token")
    else:
        provider = GraphClientCredentialsTokenProvider(
            credentials=credentials,
            transport=token_transport or UrllibGraphTokenTransport(),
        )
        access_token = provider.access_token()

    return GraphEmailReadTransport(
        access_token=access_token,
        transport=graph_transport or UrllibGraphTransport(),
    )


@dataclass(frozen=True)
class GraphEmailMoveTransport:
    """Move email messages inside a mailbox using Microsoft Graph."""

    access_token: str = field(repr=False)
    transport: GraphTransport = field(repr=False)
    base_url: str = GRAPH_BASE_URL

    def move_message(
        self,
        *,
        mailbox: str,
        message_id: str,
        target_folder: str,
    ) -> None:
        """Move one message inside the specified mailbox."""

        clean_mailbox = _required_text(mailbox, "mailbox")
        clean_message_id = _required_text(message_id, "message_id")
        destination_id = self._destination_id(
            mailbox=clean_mailbox,
            target_folder=target_folder,
        )
        response = self.transport.post(
            self._message_move_url(clean_mailbox, clean_message_id),
            headers=self._json_headers(),
            body={"destinationId": destination_id},
        )
        if response.status_code not in (200, 201):
            raise GraphClientError(
                f"Microsoft Graph message move failed with status {response.status_code}"
            )

    def _destination_id(self, *, mailbox: str, target_folder: str) -> str:
        clean_target = _required_text(target_folder, "target_folder")
        if clean_target == "Deleted Items":
            return "deleteditems"

        segments = _folder_segments(clean_target)
        folder_id = self._find_child_folder_id(
            mailbox=mailbox,
            parent_folder_id=None,
            display_name=segments[0],
        )
        for segment in segments[1:]:
            folder_id = self._find_child_folder_id(
                mailbox=mailbox,
                parent_folder_id=folder_id,
                display_name=segment,
            )
        return folder_id

    def _find_child_folder_id(
        self,
        *,
        mailbox: str,
        parent_folder_id: str | None,
        display_name: str,
    ) -> str:
        payload = self._get_json(
            self._mail_folders_url(mailbox, parent_folder_id=parent_folder_id)
        )
        folders = payload.get("value")
        if not isinstance(folders, list):
            raise GraphClientError("Microsoft Graph mailFolders response missing value.")
        for folder in folders:
            if not isinstance(folder, Mapping):
                raise GraphClientError(
                    "Microsoft Graph mailFolders response item must be an object."
                )
            if folder.get("displayName") == display_name:
                folder_id = folder.get("id")
                if not isinstance(folder_id, str) or not folder_id.strip():
                    raise GraphClientError(
                        "Microsoft Graph mail folder missing id."
                    )
                return folder_id
        raise GraphClientError(f"Microsoft Graph folder was not found: {display_name}")

    def _get_json(self, url: str) -> Mapping[str, Any]:
        response = self.transport.get(url, headers=self._json_headers())
        if response.status_code != 200:
            raise GraphClientError(
                f"Microsoft Graph mail folder lookup failed with status {response.status_code}"
            )
        return response.json()

    def _json_headers(self) -> dict[str, str]:
        token = _required_text(self.access_token, "access_token")
        return {
            "Accept": "application/json",
            "Authorization": f"Bearer {token}",
        }

    def _mail_folders_url(
        self,
        mailbox: str,
        *,
        parent_folder_id: str | None,
    ) -> str:
        encoded_mailbox = quote(mailbox, safe="")
        query = urlencode({"$top": "100"})
        if parent_folder_id is None:
            return f"{self._base_url()}/users/{encoded_mailbox}/mailFolders?{query}"
        encoded_folder_id = quote(parent_folder_id, safe="")
        return (
            f"{self._base_url()}/users/{encoded_mailbox}/mailFolders/"
            f"{encoded_folder_id}/childFolders?{query}"
        )

    def _message_move_url(self, mailbox: str, message_id: str) -> str:
        encoded_mailbox = quote(mailbox, safe="")
        encoded_message_id = quote(message_id, safe="")
        return (
            f"{self._base_url()}/users/{encoded_mailbox}/messages/"
            f"{encoded_message_id}/move"
        )

    def _base_url(self) -> str:
        return self.base_url.rstrip("/")


@dataclass(frozen=True)
class GraphEmailReadTransport:
    """Read email message metadata from Microsoft Graph."""

    access_token: str = field(repr=False)
    transport: GraphTransport = field(repr=False)
    base_url: str = GRAPH_BASE_URL

    def list_messages(self, mailbox: str, limit: int) -> SequenceEmailMessages:
        """Return normalized email payloads for messages in one mailbox."""

        clean_mailbox = _required_text(mailbox, "mailbox")
        if limit < 1:
            raise EmailClientError("limit must be positive.")

        payload = self._get_json(self._messages_url(clean_mailbox, limit=limit))
        raw_messages = payload.get("value")
        if not isinstance(raw_messages, list):
            raise GraphClientError("Microsoft Graph messages response missing value.")

        messages = []
        for raw_message in raw_messages:
            if not isinstance(raw_message, Mapping):
                raise GraphClientError(
                    "Microsoft Graph messages response item must be an object."
                )
            message_id = raw_message.get("id")
            if not isinstance(message_id, str) or not message_id.strip():
                raise GraphClientError("Microsoft Graph message missing id.")
            enriched_message = dict(raw_message)
            enriched_message["internetMessageHeaders"] = self._message_headers(
                mailbox=clean_mailbox,
                message_id=message_id,
            )
            messages.append(
                graph_message_to_email_payload(enriched_message, mailbox=clean_mailbox)
            )

        return tuple(messages)

    def _message_headers(self, *, mailbox: str, message_id: str) -> list[Mapping[str, Any]]:
        payload = self._get_json(self._message_headers_url(mailbox, message_id))
        headers = payload.get("internetMessageHeaders", [])
        if not isinstance(headers, list):
            raise GraphClientError(
                "Microsoft Graph internetMessageHeaders response must be a list."
            )
        return headers

    def _get_json(self, url: str) -> Mapping[str, Any]:
        response = self.transport.get(url, headers=self._json_headers())
        if response.status_code != 200:
            raise GraphClientError(
                f"Microsoft Graph email read failed with status {response.status_code}"
            )
        return response.json()

    def _json_headers(self) -> dict[str, str]:
        token = _required_text(self.access_token, "access_token")
        return {
            "Accept": "application/json",
            "Authorization": f"Bearer {token}",
        }

    def _messages_url(self, mailbox: str, *, limit: int) -> str:
        encoded_mailbox = quote(mailbox, safe="")
        query = urlencode(
            {
                "$top": str(limit),
                "$orderby": "receivedDateTime desc",
                "$select": ",".join(
                    (
                        "id",
                        "subject",
                        "from",
                        "sender",
                        "receivedDateTime",
                        "bodyPreview",
                        "categories",
                    )
                ),
            }
        )
        return f"{self._base_url()}/users/{encoded_mailbox}/messages?{query}"

    def _message_headers_url(self, mailbox: str, message_id: str) -> str:
        encoded_mailbox = quote(mailbox, safe="")
        encoded_message_id = quote(message_id, safe="")
        query = urlencode({"$select": "internetMessageHeaders"})
        return (
            f"{self._base_url()}/users/{encoded_mailbox}/messages/"
            f"{encoded_message_id}?{query}"
        )

    def _base_url(self) -> str:
        return self.base_url.rstrip("/")


def _folder_segments(folder_path: str) -> tuple[str, ...]:
    segments = tuple(segment.strip() for segment in folder_path.split("/"))
    if not segments or any(not segment for segment in segments):
        raise EmailClientError("Email folder path must contain non-empty segments.")
    return segments


def _required_text(value: str, key: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise EmailClientError(f"Microsoft Graph email value is required: {key}")
    return value.strip()
