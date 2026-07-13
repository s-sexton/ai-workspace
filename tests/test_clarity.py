from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from pathlib import Path

import pytest

from assistant.src.clarity import answer_clarity_request, main
from common.memory import DuckDbMemoryStore


@dataclass(frozen=True)
class FakeEmailReviewResult:
    memory_path: Path
    brief_path: Path
    run_id: str
    mailbox: str
    message_count: int
    review_count: int
    noise_count: int
    trash_count: int
    proposed_action_count: int


@dataclass(frozen=True)
class FakeCalendarReviewResult:
    memory_path: Path
    brief_path: Path
    run_id: str
    calendar: str
    review_date: str
    event_count: int


def test_clarity_answers_emails_needing_attention(tmp_path):
    memory_path = tmp_path / "logs" / "memory.duckdb"
    _seed_memory(memory_path)

    answer = answer_clarity_request(
        "What emails need immediate attention?",
        root=tmp_path,
        memory_path=memory_path,
    )

    assert "# Items Marked For Review" in answer
    assert "Review vendor terms [review]" in answer


def test_clarity_answers_pending_approval_question(tmp_path):
    memory_path = tmp_path / "logs" / "memory.duckdb"
    _seed_memory(memory_path)

    answer = answer_clarity_request(
        "What needs approval?",
        root=tmp_path,
        memory_path=memory_path,
    )

    assert "# Pending Actions" in answer
    assert "propose_email_move_review - Review vendor terms [required]" in answer
    assert "Action:" in answer


def test_clarity_answers_what_did_you_do(tmp_path):
    memory_path = tmp_path / "logs" / "memory.duckdb"
    _seed_memory(memory_path)

    answer = answer_clarity_request(
        "What did you do?",
        root=tmp_path,
        memory_path=memory_path,
    )

    assert "# Recent Actions" in answer
    assert "read_email_metadata [not_required]" in answer


def test_clarity_answers_last_run_question(tmp_path):
    memory_path = tmp_path / "logs" / "memory.duckdb"
    _seed_memory(memory_path)
    _seed_cycle_run(memory_path)

    answer = answer_clarity_request(
        "When did Clarity last run?",
        root=tmp_path,
        memory_path=memory_path,
    )

    assert "# Latest Clarity Cycle" in answer
    assert "- Workflow: clarity-cycle" in answer


def test_clarity_answers_latest_llm_brief_question(tmp_path):
    memory_path = tmp_path / "logs" / "memory.duckdb"
    _seed_memory(memory_path)
    _seed_fake_llm_brief_run(memory_path)

    answer = answer_clarity_request(
        "When was the latest fake LLM brief?",
        root=tmp_path,
        memory_path=memory_path,
    )

    assert "# Latest Fake LLM Brief" in answer
    assert "- Workflow: fake-llm-brief" in answer


def test_clarity_answers_attention_brief_question(tmp_path):
    memory_path = tmp_path / "logs" / "memory.duckdb"
    _seed_memory(memory_path)
    _seed_cycle_run(memory_path)

    answer = answer_clarity_request(
        "What needs my attention?",
        root=tmp_path,
        memory_path=memory_path,
    )

    assert "# Clarity Attention Brief" in answer
    assert "Review vendor terms" in answer
    assert "propose_email_move_review - Review vendor terms" in answer


def test_clarity_answers_focus_question(tmp_path):
    memory_path = tmp_path / "logs" / "memory.duckdb"
    _seed_memory(memory_path)

    answer = answer_clarity_request(
        "What should I focus on?",
        root=tmp_path,
        memory_path=memory_path,
    )

    assert "# Clarity Focus Plan" in answer
    assert "1. Review pending approvals" in answer
    assert "Review vendor terms" in answer
    assert "3. Review approved email moves" in answer


def test_clarity_answers_command_center_with_email_cleanup(tmp_path):
    memory_path = tmp_path / "logs" / "memory.duckdb"
    _write_config(tmp_path)
    _seed_memory(memory_path)

    answer = answer_clarity_request(
        "Give me my command center",
        root=tmp_path,
        memory_path=memory_path,
    )

    assert "# Clarity Command Center" in answer
    assert "# Email Cleanup" in answer
    assert "Approved moves ready for cleanup review: 1" in answer
    assert "Proposed moves needing approval: 1" in answer


def test_clarity_answers_email_move_plan(tmp_path):
    memory_path = tmp_path / "logs" / "memory.duckdb"
    _seed_memory(memory_path)

    answer = answer_clarity_request(
        "Show my email move plan",
        root=tmp_path,
        memory_path=memory_path,
    )

    assert "# Email Move Plan" in answer
    assert "email-noise-1 to Clarity/Noise" in answer


def test_clarity_answers_email_cleanup_plan(tmp_path):
    memory_path = tmp_path / "logs" / "memory.duckdb"
    _write_config(tmp_path)
    _seed_memory(memory_path)

    answer = answer_clarity_request(
        "show my email cleanup plan",
        root=tmp_path,
        memory_path=memory_path,
    )

    assert "# Email Cleanup Plan" in answer
    assert "Review vendor terms" in answer
    assert "Monthly newsletter" in answer


def test_clarity_records_feedback_from_natural_language(tmp_path):
    memory_path = tmp_path / "logs" / "memory.duckdb"
    _seed_memory(memory_path)

    answer = answer_clarity_request(
        "mark email-review-1 as noise because this is promotional",
        root=tmp_path,
        memory_path=memory_path,
    )

    assert "Recorded feedback" in answer
    assert "email-review-1: noise" in answer

    store = DuckDbMemoryStore(memory_path)
    try:
        feedback = store.recent_feedback()
    finally:
        store.close()

    assert feedback[0].external_id == "email-review-1"
    assert feedback[0].feedback_type == "noise"
    assert feedback[0].feedback_text == "this is promotional"


def test_clarity_records_default_feedback_note(tmp_path):
    memory_path = tmp_path / "logs" / "memory.duckdb"
    _seed_memory(memory_path)

    answer = answer_clarity_request(
        "mark email-review-1 as review",
        root=tmp_path,
        memory_path=memory_path,
    )

    assert "Recorded feedback" in answer

    store = DuckDbMemoryStore(memory_path)
    try:
        feedback = store.recent_feedback()
    finally:
        store.close()

    assert feedback[0].feedback_type == "review"
    assert feedback[0].feedback_text == "Marked for review from the Clarity command surface."


def test_clarity_records_sender_preference_from_natural_language(tmp_path):
    memory_path = tmp_path / "logs" / "memory.duckdb"
    _write_config(tmp_path)

    answer = answer_clarity_request(
        "always mark emails from Promo@Example.Invalid as noise",
        root=tmp_path,
        memory_path=memory_path,
        mailbox="inbox@example.invalid",
    )

    store = DuckDbMemoryStore(memory_path)
    try:
        preferences = store.list_email_sender_preferences()
    finally:
        store.close()

    assert "Recorded noise email preference" in answer
    assert preferences[0].match_type == "sender"
    assert preferences[0].pattern == "promo@example.invalid"


def test_clarity_records_domain_preference_from_natural_language(tmp_path):
    memory_path = tmp_path / "logs" / "memory.duckdb"
    _write_config(tmp_path)

    answer = answer_clarity_request(
        "always mark emails from example.invalid as review",
        root=tmp_path,
        memory_path=memory_path,
        mailbox="inbox@example.invalid",
    )

    store = DuckDbMemoryStore(memory_path)
    try:
        preferences = store.list_email_sender_preferences()
    finally:
        store.close()

    assert "Recorded review email preference" in answer
    assert preferences[0].match_type == "domain"
    assert preferences[0].pattern == "example.invalid"


def test_clarity_answers_email_preferences_question(tmp_path):
    memory_path = tmp_path / "logs" / "memory.duckdb"
    _write_config(tmp_path)
    answer_clarity_request(
        "always mark emails from promo@example.invalid as noise",
        root=tmp_path,
        memory_path=memory_path,
        mailbox="inbox@example.invalid",
    )

    answer = answer_clarity_request(
        "show email preferences",
        root=tmp_path,
        memory_path=memory_path,
    )

    assert "# Email Preferences" in answer
    assert "inbox@example.invalid: sender promo@example.invalid -> noise" in answer


def test_clarity_removes_email_preference_from_natural_language(tmp_path):
    memory_path = tmp_path / "logs" / "memory.duckdb"
    _write_config(tmp_path)
    answer_clarity_request(
        "always mark emails from promo@example.invalid as noise",
        root=tmp_path,
        memory_path=memory_path,
        mailbox="inbox@example.invalid",
    )
    store = DuckDbMemoryStore(memory_path)
    try:
        preference = store.list_email_sender_preferences()[0]
    finally:
        store.close()

    answer = answer_clarity_request(
        f"remove email preference {preference.preference_id}",
        root=tmp_path,
        memory_path=memory_path,
    )

    store = DuckDbMemoryStore(memory_path)
    try:
        preferences = store.list_email_sender_preferences()
    finally:
        store.close()

    assert "Removed noise email preference" in answer
    assert preferences == ()


def test_clarity_answers_calendar_question_from_memory(tmp_path):
    memory_path = tmp_path / "logs" / "memory.duckdb"
    _seed_memory(memory_path)

    answer = answer_clarity_request(
        "What is on my family calendar today?",
        root=tmp_path,
        memory_path=memory_path,
        current_date=date(2026, 7, 10),
    )

    assert "# Calendar Items" in answer
    assert "- Date: 2026-07-10" in answer
    assert "- Source filter: family" in answer
    assert "Family dinner" in answer
    assert "Start: 2026-07-10T18:00:00-05:00" in answer


def test_clarity_can_refresh_calendar_before_answering(tmp_path, monkeypatch):
    memory_path = tmp_path / "logs" / "memory.duckdb"
    calls = []

    def fake_run_calendar_review(**kwargs):
        calls.append(kwargs)
        _seed_memory(memory_path)
        return FakeCalendarReviewResult(
            memory_path=memory_path,
            brief_path=tmp_path / "reports" / "brief.md",
            run_id="run-1",
            calendar="family",
            review_date="2026-07-10",
            event_count=1,
        )

    monkeypatch.setattr(
        "assistant.src.clarity.run_calendar_review",
        fake_run_calendar_review,
    )

    answer = answer_clarity_request(
        "What is on my family calendar today?",
        root=tmp_path,
        memory_path=memory_path,
        refresh_calendar=True,
        current_date=date(2026, 7, 10),
    )

    assert "# Calendar Items" in answer
    assert "Family dinner" in answer
    assert calls[0]["calendar"] == "family"
    assert calls[0]["review_date"] == "2026-07-10"
    assert calls[0]["memory_path"] == memory_path


def test_main_prints_clarity_answer(tmp_path, monkeypatch, capsys):
    memory_path = tmp_path / "logs" / "memory.duckdb"
    _seed_memory(memory_path)
    monkeypatch.chdir(tmp_path)

    main(["What emails need immediate attention?", "--memory", str(memory_path)])

    output = capsys.readouterr().out
    assert "# Items Marked For Review" in output


def test_main_runs_local_prompt(tmp_path, monkeypatch, capsys):
    memory_path = tmp_path / "logs" / "memory.duckdb"
    _seed_memory(memory_path)
    requests = iter(["What did you do?", "quit"])
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr("builtins.input", lambda _prompt: next(requests))

    main(["--memory", str(memory_path)])

    output = capsys.readouterr().out
    assert "Clarity local prompt" in output
    assert "# Recent Actions" in output


def test_clarity_can_refresh_email_before_answering(tmp_path, monkeypatch):
    memory_path = tmp_path / "logs" / "memory.duckdb"
    calls = []

    def fake_run_email_review(**kwargs):
        calls.append(kwargs)
        _seed_memory(memory_path)
        return FakeEmailReviewResult(
            memory_path=memory_path,
            brief_path=tmp_path / "reports" / "brief.md",
            run_id="run-1",
            mailbox="clarity@sendthisfile.ai",
            message_count=1,
            review_count=1,
            noise_count=0,
            trash_count=0,
            proposed_action_count=1,
        )

    monkeypatch.setattr("assistant.src.clarity.run_email_review", fake_run_email_review)

    answer = answer_clarity_request(
        "What emails need immediate attention?",
        root=tmp_path,
        memory_path=memory_path,
        refresh_email=True,
        mailbox="clarity@sendthisfile.ai",
    )

    assert "# Items Marked For Review" in answer
    assert calls[0]["mailbox"] == "clarity@sendthisfile.ai"
    assert calls[0]["memory_path"] == memory_path


def test_main_can_refresh_email_with_graph_transport(tmp_path, monkeypatch, capsys):
    memory_path = tmp_path / "logs" / "memory.duckdb"
    graph_calls = []
    review_calls = []

    def fake_build_graph_read_transport_from_config(*, use_bearer_auth=False, **_):
        graph_calls.append(use_bearer_auth)
        return object()

    def fake_run_email_review(**kwargs):
        review_calls.append(kwargs)
        _seed_memory(memory_path)
        return FakeEmailReviewResult(
            memory_path=memory_path,
            brief_path=tmp_path / "reports" / "brief.md",
            run_id="run-1",
            mailbox="clarity@sendthisfile.ai",
            message_count=1,
            review_count=1,
            noise_count=0,
            trash_count=0,
            proposed_action_count=1,
        )

    monkeypatch.setattr(
        "assistant.src.clarity.build_graph_read_transport_from_config",
        fake_build_graph_read_transport_from_config,
    )
    monkeypatch.setattr("assistant.src.clarity.run_email_review", fake_run_email_review)
    monkeypatch.chdir(tmp_path)

    main(
        [
            "What emails need immediate attention?",
            "--refresh-email",
            "--mailbox",
            "clarity@sendthisfile.ai",
            "--graph",
            "--graph-bearer",
            "--memory",
            str(memory_path),
        ]
    )

    output = capsys.readouterr().out
    assert graph_calls == [True]
    assert review_calls[0]["transport"] is not None
    assert "# Items Marked For Review" in output


def test_main_can_refresh_calendar_with_google_transport(tmp_path, monkeypatch, capsys):
    memory_path = tmp_path / "logs" / "memory.duckdb"
    google_calls = []
    review_calls = []

    def fake_build_google_calendar_read_transport_from_config(
        *,
        use_bearer_auth=False,
        **_,
    ):
        google_calls.append(use_bearer_auth)
        return object()

    def fake_run_calendar_review(**kwargs):
        review_calls.append(kwargs)
        _seed_memory(memory_path)
        return FakeCalendarReviewResult(
            memory_path=memory_path,
            brief_path=tmp_path / "reports" / "brief.md",
            run_id="run-1",
            calendar="family",
            review_date="2026-07-10",
            event_count=1,
        )

    monkeypatch.setattr(
        "assistant.src.clarity.build_google_calendar_read_transport_from_config",
        fake_build_google_calendar_read_transport_from_config,
    )
    monkeypatch.setattr(
        "assistant.src.clarity.run_calendar_review",
        fake_run_calendar_review,
    )
    monkeypatch.chdir(tmp_path)

    main(
        [
            "What is on my family calendar 2026-07-10?",
            "--refresh-calendar",
            "--calendar",
            "family",
            "--google",
            "--google-bearer",
            "--memory",
            str(memory_path),
        ]
    )

    output = capsys.readouterr().out
    assert google_calls == [True]
    assert review_calls[0]["transport"] is not None
    assert review_calls[0]["use_google"] is True
    assert "Family dinner" in output


def test_main_rejects_graph_refresh_without_refresh_mode():
    with pytest.raises(SystemExit):
        main(["What emails need immediate attention?", "--graph"])


def test_main_rejects_graph_bearer_without_graph():
    with pytest.raises(SystemExit):
        main(["What emails need immediate attention?", "--refresh-email", "--graph-bearer"])


def test_main_rejects_google_without_refresh_calendar():
    with pytest.raises(SystemExit):
        main(["What is on my calendar?", "--google"])


def _seed_memory(memory_path):
    memory_path.parent.mkdir(parents=True, exist_ok=True)
    store = DuckDbMemoryStore(memory_path)
    try:
        store.initialize_schema()
        run = store.start_run(workflow="email-review")
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
            result="Proposed moving message metadata to Clarity/Review.",
        )
        approved_item = store.record_item_seen(
            source_id=source.source_id,
            external_id="email-noise-1",
            item_type="email_message",
            subject="Monthly newsletter",
            first_seen_run_id=run.run_id,
        )
        store.record_assistant_action(
            run_id=run.run_id,
            item_id=approved_item.item_id,
            action_type="propose_email_move_noise",
            approval_status="approved",
            action_target="Clarity/Noise",
            result="Proposed moving message metadata to Clarity/Noise.",
        )
        store.record_assistant_action(
            run_id=run.run_id,
            action_type="read_email_metadata",
            approval_status="not_required",
            result="Read 2 message(s) from clarity@sendthisfile.ai.",
        )
        calendar_source = store.record_source(
            source_type="calendar",
            display_name="family calendar",
            scope_label="family",
        )
        calendar_item = store.record_item_seen(
            source_id=calendar_source.source_id,
            external_id="family-dinner",
            item_type="calendar_event",
            subject="Family dinner",
            first_seen_run_id=run.run_id,
            updated_at="2026-07-10T18:00:00-05:00",
        )
        store.record_classification(
            item_id=calendar_item.item_id,
            run_id=run.run_id,
            label="calendar",
            reason="Calendar event starts at 2026-07-10T18:00:00-05:00.",
        )
        store.finish_run(
            run.run_id,
            status="completed",
            summary="Reviewed 2 email message(s).",
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
                {"address": "inbox@example.invalid", "accessMode": "read_write"},
                {"address": "clarity@sendthisfile.ai", "accessMode": "read_write"}
              ],
              "defaultMailbox": "inbox@example.invalid",
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


def _seed_cycle_run(memory_path):
    store = DuckDbMemoryStore(memory_path)
    try:
        store.initialize_schema()
        run = store.start_run(
            workflow="clarity-cycle",
            started_at="2026-07-09T16:00:00+00:00",
        )
        store.record_generated_artifact(
            run_id=run.run_id,
            artifact_type="markdown_cycle_report",
            path="reports/clarity-cycle.md",
            summary="Clarity cycle report for clarity@sendthisfile.ai.",
        )
        store.finish_run(
            run.run_id,
            status="completed",
            summary="Read 1 message(s) from clarity@sendthisfile.ai.",
            completed_at="2026-07-09T16:01:00+00:00",
        )
    finally:
        store.close()


def _seed_fake_llm_brief_run(memory_path):
    store = DuckDbMemoryStore(memory_path)
    try:
        store.initialize_schema()
        run = store.start_run(
            workflow="fake-llm-brief",
            started_at="2026-07-09T16:05:00+00:00",
        )
        store.record_generated_artifact(
            run_id=run.run_id,
            artifact_type="markdown_fake_llm_brief",
            path="reports/clarity-llm-brief.md",
            summary="Local deterministic fake LLM brief.",
        )
        store.finish_run(
            run.run_id,
            status="completed",
            summary="Generated local deterministic fake LLM brief.",
            completed_at="2026-07-09T16:06:00+00:00",
        )
    finally:
        store.close()
