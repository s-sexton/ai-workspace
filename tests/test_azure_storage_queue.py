from __future__ import annotations

import base64
import json
from typing import Mapping

from common.azure_storage_queue import (
    AzureQueueHttpResponse,
    AzureStorageTeamsRelayQueue,
)


def test_azure_queue_enqueue_posts_base64_json_xml():
    transport = RecordingAzureTransport(
        responses=[AzureQueueHttpResponse(status_code=201)]
    )
    queue = AzureStorageTeamsRelayQueue(
        inbound_queue_url="https://acct.queue.core.windows.net/clarity-inbound?sas=1",
        deadletter_queue_url="https://acct.queue.core.windows.net/clarity-deadletter?sas=1",
        transport=transport,
    )

    queue.enqueue({"schemaVersion": 1, "source": "teams"})

    method, url, headers, body = transport.calls[0]
    assert method == "POST"
    assert url == "https://acct.queue.core.windows.net/clarity-inbound/messages?sas=1"
    assert headers["Content-Type"] == "application/xml"
    assert body is not None
    encoded = body.decode("utf-8").split("<MessageText>", 1)[1].split("</MessageText>", 1)[0]
    assert json.loads(base64.b64decode(encoded).decode("utf-8")) == {
        "schemaVersion": 1,
        "source": "teams",
    }


def test_azure_queue_receive_parses_messages():
    payload = {"schemaVersion": 1, "source": "teams", "commandId": "cmd-1"}
    encoded = base64.b64encode(json.dumps(payload).encode("utf-8")).decode("ascii")
    body = f"""
    <QueueMessagesList>
      <QueueMessage>
        <MessageId>message-1</MessageId>
        <PopReceipt>receipt-1</PopReceipt>
        <MessageText>{encoded}</MessageText>
        <DequeueCount>2</DequeueCount>
      </QueueMessage>
    </QueueMessagesList>
    """.encode("utf-8")
    transport = RecordingAzureTransport(
        responses=[AzureQueueHttpResponse(status_code=200, body=body)]
    )
    queue = AzureStorageTeamsRelayQueue(
        inbound_queue_url="https://acct.queue.core.windows.net/clarity-inbound?sas=1",
        deadletter_queue_url="https://acct.queue.core.windows.net/clarity-deadletter?sas=1",
        transport=transport,
    )

    messages = queue.receive(limit=1)

    assert messages[0].queue_message_id == "message-1|receipt-1"
    assert messages[0].payload["commandId"] == "cmd-1"
    assert messages[0].dequeue_count == 2
    method, url, _, _ = transport.calls[0]
    assert method == "GET"
    assert url.startswith(
        "https://acct.queue.core.windows.net/clarity-inbound/messages?"
    )
    assert "numofmessages=1" in url
    assert "visibilitytimeout=60" in url


def test_azure_queue_receive_accepts_plain_json_messages():
    payload = {"schemaVersion": 1, "source": "teams", "commandId": "plain-json"}
    body = f"""
    <QueueMessagesList>
      <QueueMessage>
        <MessageId>message-1</MessageId>
        <PopReceipt>receipt-1</PopReceipt>
        <MessageText>{json.dumps(payload)}</MessageText>
      </QueueMessage>
    </QueueMessagesList>
    """.encode("utf-8")
    transport = RecordingAzureTransport(
        responses=[AzureQueueHttpResponse(status_code=200, body=body)]
    )
    queue = AzureStorageTeamsRelayQueue(
        inbound_queue_url="https://acct.queue.core.windows.net/clarity-inbound?sas=1",
        deadletter_queue_url="https://acct.queue.core.windows.net/clarity-deadletter?sas=1",
        transport=transport,
    )

    messages = queue.receive(limit=1)

    assert messages[0].payload["commandId"] == "plain-json"


def test_azure_queue_complete_deletes_message_with_pop_receipt():
    transport = RecordingAzureTransport(
        responses=[AzureQueueHttpResponse(status_code=204)]
    )
    queue = AzureStorageTeamsRelayQueue(
        inbound_queue_url="https://acct.queue.core.windows.net/clarity-inbound?sas=1",
        deadletter_queue_url="https://acct.queue.core.windows.net/clarity-deadletter?sas=1",
        transport=transport,
    )

    queue.complete("message-1|receipt-1")

    method, url, _, _ = transport.calls[0]
    assert method == "DELETE"
    assert url == (
        "https://acct.queue.core.windows.net/clarity-inbound/messages/message-1"
        "?popreceipt=receipt-1&sas=1"
    )


class RecordingAzureTransport:
    def __init__(self, *, responses):
        self.responses = list(responses)
        self.calls: list[tuple[str, str, Mapping[str, str], bytes | None]] = []

    def request(self, method, url, *, headers, body=None):
        self.calls.append((method, url, headers, body))
        return self.responses.pop(0)
