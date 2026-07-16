from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

import pytest

from assistant.src.generate_llm_brief import (
    DEFAULT_CODEX_HANDOFF_PATH,
    DEFAULT_LLM_BRIEF_PATH,
    generate_codex_handoff,
    generate_fake_llm_brief,
    generate_openai_llm_brief,
    main,
)
from common.memory import DuckDbMemoryStore


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


def test_generate_fake_llm_brief_writes_safe_report(tmp_path):
    memory_path = tmp_path / "logs" / "memory.duckdb"
    output_path = tmp_path / "reports" / "llm.md"
    _seed_memory(memory_path)

    report = generate_fake_llm_brief(
        root=tmp_path,
        memory_path=memory_path,
        output_path=output_path,
    )

    assert "# Clarity Fake LLM Brief" in report
    assert "No LLM was called." in report
    assert "Review items: 1" in report
    assert "Pending approvals: 1" in report
    assert output_path.read_text(encoding="utf-8") == report
    store = DuckDbMemoryStore(memory_path)
    try:
        latest_run = store.latest_run(workflow="fake-llm-brief")
        artifacts = store.list_generated_artifacts(run_id=latest_run.run_id)
        actions = store.recent_actions()
    finally:
        store.close()

    assert latest_run is not None
    assert latest_run.status == "completed"
    assert latest_run.summary == "Generated local deterministic fake LLM brief."
    assert artifacts[0].path == str(output_path)
    assert artifacts[0].artifact_type == "markdown_fake_llm_brief"
    assert actions[0].action_type == "generate_fake_llm_brief"


def test_generate_fake_llm_brief_can_skip_write(tmp_path):
    memory_path = tmp_path / "logs" / "memory.duckdb"
    output_path = tmp_path / "reports" / "llm.md"
    _seed_memory(memory_path)

    report = generate_fake_llm_brief(
        root=tmp_path,
        memory_path=memory_path,
        output_path=output_path,
        write=False,
    )

    assert "Clarity Fake LLM Brief" in report
    assert not output_path.exists()
    store = DuckDbMemoryStore(memory_path)
    try:
        latest_run = store.latest_run(workflow="fake-llm-brief")
    finally:
        store.close()

    assert latest_run is None


def test_generate_openai_llm_brief_writes_validated_report(tmp_path):
    _write_config(tmp_path)
    memory_path = tmp_path / "logs" / "memory.duckdb"
    output_path = tmp_path / "reports" / "llm.md"
    _seed_memory(memory_path)
    transport = FakeOpenAITransport(
        FakeOpenAIResponse(
            200,
            {
                "output_text": (
                    "1. What matters now\n"
                    "- Review vendor terms needs attention.\n\n"
                    "2. Why it matters\n"
                    "- It may require a human decision.\n\n"
                    "3. What needs approval\n"
                    "- Action approval remains pending.\n\n"
                    "4. Safe next commands\n"
                    "- Review pending actions locally."
                )
            },
        )
    )

    report = generate_openai_llm_brief(
        root=tmp_path,
        memory_path=memory_path,
        output_path=output_path,
        transport=transport,
    )

    assert "# Clarity LLM Brief" in report
    assert "bounded local Clarity context" in report
    assert "Review vendor terms needs attention" in report
    assert output_path.read_text(encoding="utf-8") == report
    assert len(transport.calls) == 1
    assert transport.calls[0][1]["Authorization"] == "Bearer test-openai-key"
    assert transport.calls[0][2]["model"] == "gpt-test"
    store = DuckDbMemoryStore(memory_path)
    try:
        latest_run = store.latest_run(workflow="llm-brief")
        artifacts = store.list_generated_artifacts(run_id=latest_run.run_id)
        actions = store.recent_actions()
    finally:
        store.close()

    assert latest_run is not None
    assert latest_run.status == "completed"
    assert latest_run.summary == "Generated validated OpenAI LLM brief."
    assert artifacts[0].artifact_type == "markdown_llm_brief"
    assert actions[0].action_type == "generate_llm_brief"


def test_generate_openai_llm_brief_rejects_unsafe_output(tmp_path):
    _write_config(tmp_path)
    memory_path = tmp_path / "logs" / "memory.duckdb"
    _seed_memory(memory_path)
    transport = FakeOpenAITransport(
        FakeOpenAIResponse(200, {"output_text": "I moved the email."})
    )

    with pytest.raises(ValueError):
        generate_openai_llm_brief(
            root=tmp_path,
            memory_path=memory_path,
            transport=transport,
        )


def test_generate_codex_handoff_writes_prompt_for_codex(tmp_path):
    memory_path = tmp_path / "logs" / "memory.duckdb"
    output_path = tmp_path / "reports" / "handoff.md"
    _seed_memory(memory_path)

    report = generate_codex_handoff(
        root=tmp_path,
        memory_path=memory_path,
        output_path=output_path,
        user_request="Help me prioritize my morning",
    )

    assert "# Clarity Codex Handoff" in report
    assert "No API call was made." in report
    assert "Instructions for Codex:" in report
    assert "# Clarity LLM Prompt" in report
    assert "Human request:" in report
    assert "Help me prioritize my morning" in report
    assert output_path.read_text(encoding="utf-8") == report
    store = DuckDbMemoryStore(memory_path)
    try:
        latest_run = store.latest_run(workflow="codex-handoff")
        artifacts = store.list_generated_artifacts(run_id=latest_run.run_id)
        actions = store.recent_actions()
    finally:
        store.close()

    assert latest_run is not None
    assert latest_run.summary == "Generated Codex-ready Clarity handoff."
    assert artifacts[0].artifact_type == "markdown_codex_handoff"
    assert actions[0].action_type == "generate_codex_handoff"


def test_generate_codex_handoff_can_skip_write(tmp_path):
    memory_path = tmp_path / "logs" / "memory.duckdb"
    output_path = tmp_path / "reports" / "handoff.md"
    _seed_memory(memory_path)

    report = generate_codex_handoff(
        root=tmp_path,
        memory_path=memory_path,
        output_path=output_path,
        write=False,
    )

    assert "Clarity Codex Handoff" in report
    assert not output_path.exists()
    store = DuckDbMemoryStore(memory_path)
    try:
        latest_run = store.latest_run(workflow="codex-handoff")
    finally:
        store.close()

    assert latest_run is None


def test_main_prints_and_writes_report(tmp_path, monkeypatch, capsys):
    memory_path = tmp_path / "logs" / "memory.duckdb"
    output_path = tmp_path / "reports" / "llm.md"
    _seed_memory(memory_path)
    monkeypatch.chdir(tmp_path)

    main(["--memory", str(memory_path), "--output", str(output_path)])

    output = capsys.readouterr().out
    assert "# Clarity Fake LLM Brief" in output
    assert "Wrote" in output
    assert output_path.is_file()


def test_main_can_generate_codex_handoff(tmp_path, monkeypatch, capsys):
    memory_path = tmp_path / "logs" / "memory.duckdb"
    output_path = tmp_path / "reports" / "handoff.md"
    _seed_memory(memory_path)
    monkeypatch.chdir(tmp_path)

    main(
        [
            "--codex-handoff",
            "--memory",
            str(memory_path),
            "--output",
            str(output_path),
            "--request",
            "Help me prioritize my morning",
        ]
    )

    output = capsys.readouterr().out
    assert "# Clarity Codex Handoff" in output
    assert "Wrote" in output
    assert output_path.is_file()
    assert not DEFAULT_LLM_BRIEF_PATH.is_file()


def test_main_can_use_openai_provider(tmp_path, monkeypatch, capsys):
    _write_config(tmp_path)
    memory_path = tmp_path / "logs" / "memory.duckdb"
    output_path = tmp_path / "reports" / "llm.md"
    _seed_memory(memory_path)
    monkeypatch.chdir(tmp_path)

    def fake_build_openai_summary_provider(credentials, *, transport=None):
        assert credentials.api_key == "test-openai-key"
        assert credentials.model == "gpt-test"

        class StaticProvider:
            def summarize(self, prompt):
                assert "# Clarity LLM Prompt" in prompt
                return (
                    "1. What matters now\n"
                    "- Review vendor terms needs attention.\n\n"
                    "2. Why it matters\n"
                    "- It may require a human decision.\n\n"
                    "3. What needs approval\n"
                    "- Action approval remains pending.\n\n"
                    "4. Safe next commands\n"
                    "- Review pending actions locally."
                )

        return StaticProvider()

    monkeypatch.setattr(
        "assistant.src.generate_llm_brief.build_openai_summary_provider",
        fake_build_openai_summary_provider,
    )

    main(
        [
            "--openai",
            "--memory",
            str(memory_path),
            "--output",
            str(output_path),
        ]
    )

    output = capsys.readouterr().out
    assert "# Clarity LLM Brief" in output
    assert "Wrote" in output
    assert output_path.is_file()


def _seed_memory(memory_path):
    memory_path.parent.mkdir(parents=True, exist_ok=True)
    store = DuckDbMemoryStore(memory_path)
    try:
        store.initialize_schema()
        run = store.start_run(workflow="clarity-cycle")
        source = store.record_source(
            source_type="email",
            display_name="clarity@sendthisfile.ai",
            scope_label="clarity@sendthisfile.ai",
        )
        item = store.record_item_seen(
            source_id=source.source_id,
            external_id="email-review-1",
            item_type="email_message",
            subject="Review vendor terms",
            first_seen_run_id=run.run_id,
        )
        store.record_classification(
            item_id=item.item_id,
            run_id=run.run_id,
            label="review",
            reason="No safe noise rule matched; keep for human review.",
        )
        store.record_assistant_action(
            run_id=run.run_id,
            item_id=item.item_id,
            action_type="propose_email_move_review",
            approval_status="required",
            action_target="Clarity/Review",
            result="Proposed moving message metadata.",
        )
        store.finish_run(
            run.run_id,
            status="completed",
            summary="Read 1 message(s) from clarity@sendthisfile.ai.",
        )
    finally:
        store.close()


def _write_config(root):
    config_dir = root / "config"
    config_dir.mkdir()
    (config_dir / "config.json").write_text(
        """
        {
          "assistant": {
            "email": {
              "approvedMailboxes": [
                {"address": "clarity@sendthisfile.ai", "accessMode": "read"}
              ],
              "defaultMailbox": "clarity@sendthisfile.ai",
              "folderNamespace": "Clarity",
              "folderPolicy": {
                "review": "Clarity/Review",
                "noise": "Clarity/Noise",
                "trash": "Deleted Items"
              },
              "maxMessages": 25
            }
          }
        }
        """,
        encoding="utf-8",
    )
    (config_dir / ".env").write_text(
        """
        OPENAI_API_KEY=test-openai-key
        OPENAI_MODEL=gpt-test
        OPENAI_BASE_URL=https://openai.example/v1
        """,
        encoding="utf-8",
    )
