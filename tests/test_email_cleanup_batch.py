from __future__ import annotations

import json
from datetime import datetime

import pytest

from assistant.src.email_cleanup_batch import generate_email_cleanup_batch, main
from common.memory import DuckDbMemoryStore


def test_generate_email_cleanup_batch_numbers_current_mailbox_items(tmp_path):
    memory_path = tmp_path / "logs" / "memory.duckdb"
    output_path = tmp_path / "reports" / "email-cleanup-batch.md"
    _write_config(tmp_path)
    _seed_email_memory(memory_path)

    result = generate_email_cleanup_batch(
        root=tmp_path,
        memory_path=memory_path,
        output_path=output_path,
        mailbox="scott.sexton@sendthisfile.com",
        generated_at=datetime(2026, 7, 17, 8, 15),
    )

    batch = output_path.read_text(encoding="utf-8")
    manifest = json.loads(output_path.with_suffix(".json").read_text(encoding="utf-8"))
    assert result.output_path == output_path
    assert result.manifest_path == output_path.with_suffix(".json")
    assert result.mailbox == "scott.sexton@sendthisfile.com"
    assert result.item_count == 2
    assert "# Email Cleanup Batch" in batch
    assert "Mailbox: scott.sexton@sendthisfile.com" in batch
    assert "Generated: 2026-07-17T08:15:00" in batch
    assert "- Review: Clarity/Review" in batch
    assert "- Noise: Clarity/Noise" in batch
    assert "- Specific folders: Clarity/<Folder Name>" in batch
    assert "1. Date: 2026-07-17T08:00:00-05:00" in batch
    assert "From: vendor@example.invalid" in batch
    assert "Subject: SaaS tax webinar" in batch
    assert "Recommendation: Move to Clarity/Noise" in batch
    assert "2. Date: 2026-07-17T07:55:00-05:00" in batch
    assert "Subject: Customer escalation" in batch
    assert "Recommendation: Move to Clarity/Review" in batch
    assert "other-mailbox-message" not in batch
    assert "duplicate older copy" not in batch
    assert "## Example Directions" in batch
    assert manifest["mailbox"] == "scott.sexton@sendthisfile.com"
    assert manifest["items"][0]["number"] == 1
    assert manifest["items"][0]["externalId"] == "message-noise"
    assert manifest["items"][1]["number"] == 2
    assert manifest["items"][1]["externalId"] == "message-review"


def test_generate_email_cleanup_batch_recommends_prior_specific_folder(tmp_path):
    memory_path = tmp_path / "logs" / "memory.duckdb"
    output_path = tmp_path / "reports" / "email-cleanup-batch.md"
    _write_config(tmp_path)
    _seed_folder_learning_memory(memory_path)

    generate_email_cleanup_batch(
        root=tmp_path,
        memory_path=memory_path,
        output_path=output_path,
        mailbox="scott.sexton@sendthisfile.com",
        generated_at=datetime(2026, 7, 17, 8, 15),
    )

    batch = output_path.read_text(encoding="utf-8")
    manifest = json.loads(output_path.with_suffix(".json").read_text(encoding="utf-8"))
    assert "Subject: Azure Reserved VM Instances update" in batch
    assert "Recommendation: Move to Clarity/Azure" in batch
    assert "Why: Matched prior folder move by sender and subject." in batch
    assert manifest["items"][0]["folderRecommendation"] == {
        "targetFolder": "Clarity/Azure",
        "reason": "Matched prior folder move by sender and subject.",
    }


def test_generate_email_cleanup_batch_honors_latest_empty_mailbox_refresh(tmp_path):
    memory_path = tmp_path / "logs" / "memory.duckdb"
    output_path = tmp_path / "reports" / "email-cleanup-batch.md"
    _write_config(tmp_path)
    _seed_email_memory(memory_path)
    _seed_empty_mailbox_refresh(
        memory_path,
        mailbox="scott.sexton@sendthisfile.com",
    )

    result = generate_email_cleanup_batch(
        root=tmp_path,
        memory_path=memory_path,
        output_path=output_path,
        mailbox="scott.sexton@sendthisfile.com",
        generated_at=datetime(2026, 7, 17, 8, 15),
    )

    batch = output_path.read_text(encoding="utf-8")
    manifest = json.loads(output_path.with_suffix(".json").read_text(encoding="utf-8"))
    assert result.item_count == 0
    assert "Nothing found for this mailbox." in batch
    assert manifest["items"] == []


def test_generate_email_cleanup_batch_groups_gmail_recommendations(tmp_path):
    memory_path = tmp_path / "logs" / "memory.duckdb"
    output_path = tmp_path / "reports" / "email-cleanup-batch.md"
    _write_config(tmp_path)
    _seed_gmail_cleanup_memory(memory_path)

    generate_email_cleanup_batch(
        root=tmp_path,
        memory_path=memory_path,
        output_path=output_path,
        mailbox="sesexton@gmail.com",
        generated_at=datetime(2026, 7, 18, 9, 30),
    )

    batch = output_path.read_text(encoding="utf-8")
    manifest = json.loads(output_path.with_suffix(".json").read_text(encoding="utf-8"))
    assert "Mailbox: sesexton@gmail.com" in batch
    assert "## Move To Specific Clarity Folders" in batch
    assert "## Likely Delete" in batch
    assert "## Review" in batch
    assert "1. Date: 2026-07-18T09:00:00-05:00" in batch
    assert "Subject: USPS Informed Delivery Daily Digest" in batch
    assert "Recommendation: Move to Clarity/USPS" in batch
    assert "3. Date: 2026-07-18T08:50:00-05:00" in batch
    assert "Subject: Monarch found a recurring merchant" in batch
    assert "Recommendation: Move to Clarity/Monarch" in batch
    assert "4. Date: 2026-07-18T08:45:00-05:00" in batch
    assert "Subject: Your Experian score changed" in batch
    assert "Recommendation: Move to Clarity/Experian" in batch
    assert "5. Date: 2026-07-18T08:40:00-05:00" in batch
    assert "Subject: Eddy's Volkswagen vehicle value" in batch
    assert "Recommendation: Move to Clarity/VW" in batch
    assert "2. Date: 2026-07-18T08:55:00-05:00" in batch
    assert "Subject: Flash sale ends tonight" in batch
    assert "Recommendation: Delete (Deleted Items)" in batch
    assert "6. Date: 2026-07-18T08:35:00-05:00" in batch
    assert "Subject: School registration reminder" in batch
    assert "Recommendation: Move to Clarity/Review" in batch
    assert manifest["items"][0]["recommendation"] == {
        "targetFolder": "Clarity/USPS",
        "reason": "Matched known Gmail cleanup folder.",
        "group": "specific_folder",
    }
    assert manifest["items"][1]["recommendation"]["group"] == "delete"
    assert manifest["items"][5]["recommendation"]["group"] == "review"


def test_generate_email_cleanup_batch_handles_missing_memory(tmp_path):
    memory_path = tmp_path / "logs" / "missing.duckdb"
    output_path = tmp_path / "reports" / "email-cleanup-batch.md"
    _write_config(tmp_path)

    result = generate_email_cleanup_batch(
        root=tmp_path,
        memory_path=memory_path,
        output_path=output_path,
        generated_at=datetime(2026, 7, 17, 8, 15),
    )

    batch = output_path.read_text(encoding="utf-8")
    manifest = json.loads(output_path.with_suffix(".json").read_text(encoding="utf-8"))
    assert result.item_count == 0
    assert "Nothing found for this mailbox." in batch
    assert manifest["items"] == []
    assert not memory_path.exists()


def test_generate_email_cleanup_batch_rejects_unapproved_mailbox(tmp_path):
    _write_config(tmp_path)

    with pytest.raises(ValueError, match="Mailbox is not approved"):
        generate_email_cleanup_batch(
            root=tmp_path,
            mailbox="unknown@example.invalid",
        )


def test_main_prints_email_cleanup_batch_summary(tmp_path, monkeypatch, capsys):
    memory_path = tmp_path / "logs" / "memory.duckdb"
    output_path = tmp_path / "reports" / "email-cleanup-batch.md"
    _write_config(tmp_path)
    _seed_email_memory(memory_path)
    monkeypatch.chdir(tmp_path)

    main(
        [
            "--memory",
            str(memory_path),
            "--output",
            str(output_path),
            "--mailbox",
            "scott.sexton@sendthisfile.com",
        ]
    )

    output = capsys.readouterr().out
    assert f"Wrote {output_path}" in output
    assert f"Manifest: {output_path.with_suffix('.json')}" in output
    assert "Mailbox: scott.sexton@sendthisfile.com" in output
    assert "Items: 2" in output


def _write_config(root):
    config_dir = root / "config"
    config_dir.mkdir()
    (config_dir / "config.json").write_text(
        """
        {
          "assistant": {
            "email": {
              "approvedMailboxes": [
                {"address": "scott.sexton@sendthisfile.com", "accessMode": "read_write"},
                {"address": "sesexton@gmail.com", "accessMode": "read_write"},
                {"address": "legal@example.invalid", "accessMode": "read"}
              ],
              "defaultMailbox": "scott.sexton@sendthisfile.com",
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


def _seed_email_memory(memory_path):
    memory_path.parent.mkdir(parents=True, exist_ok=True)
    store = DuckDbMemoryStore(memory_path)
    try:
        store.initialize_schema()
        older_run = store.start_run(workflow="email-review")
        source = store.record_source(
            source_type="email",
            display_name="scott.sexton@sendthisfile.com",
            scope_label="scott.sexton@sendthisfile.com",
        )
        older_duplicate = store.record_item_seen(
            source_id=source.source_id,
            external_id="message-review",
            item_type="email_message",
            subject="duplicate older copy",
            sender_or_owner="old@example.invalid",
            updated_at="2026-07-16T06:00:00-05:00",
            first_seen_run_id=older_run.run_id,
        )
        store.record_classification(
            item_id=older_duplicate.item_id,
            run_id=older_run.run_id,
            label="review",
            reason="Older duplicate should be hidden.",
        )
        run = store.start_run(workflow="email-review")
        noise_item = store.record_item_seen(
            source_id=source.source_id,
            external_id="message-noise",
            item_type="email_message",
            subject="SaaS tax webinar",
            sender_or_owner="vendor@example.invalid",
            updated_at="2026-07-17T08:00:00-05:00",
            first_seen_run_id=run.run_id,
        )
        store.record_classification(
            item_id=noise_item.item_id,
            run_id=run.run_id,
            label="noise",
            reason="Looks like vendor marketing.",
        )
        review_item = store.record_item_seen(
            source_id=source.source_id,
            external_id="message-review",
            item_type="email_message",
            subject="Customer escalation",
            sender_or_owner="customer@example.invalid",
            updated_at="2026-07-17T07:55:00-05:00",
            first_seen_run_id=run.run_id,
        )
        store.record_classification(
            item_id=review_item.item_id,
            run_id=run.run_id,
            label="review",
            reason="Looks operational.",
        )
        legal_source = store.record_source(
            source_type="email",
            display_name="legal@example.invalid",
            scope_label="legal@example.invalid",
        )
        legal_item = store.record_item_seen(
            source_id=legal_source.source_id,
            external_id="other-mailbox-message",
            item_type="email_message",
            subject="Legal item",
            first_seen_run_id=run.run_id,
        )
        store.record_classification(
            item_id=legal_item.item_id,
            run_id=run.run_id,
            label="review",
            reason="Other mailbox.",
        )
    finally:
        store.close()


def _seed_empty_mailbox_refresh(memory_path, *, mailbox):
    store = DuckDbMemoryStore(memory_path)
    try:
        store.initialize_schema()
        run = store.start_run(workflow="email-review")
        store.record_assistant_action(
            run_id=run.run_id,
            action_type="read_email_metadata",
            approval_status="not_required",
            result=f"Read 0 message(s) from {mailbox}.",
        )
        store.finish_run(
            run.run_id,
            status="completed",
            summary=f"Reviewed 0 email message(s) from {mailbox}.",
        )
    finally:
        store.close()


def _seed_folder_learning_memory(memory_path):
    memory_path.parent.mkdir(parents=True, exist_ok=True)
    store = DuckDbMemoryStore(memory_path)
    try:
        store.initialize_schema()
        learning_run = store.start_run(workflow="email-cleanup-learning")
        source = store.record_source(
            source_type="email",
            display_name="scott.sexton@sendthisfile.com",
            scope_label="scott.sexton@sendthisfile.com",
        )
        learned_item = store.record_item_seen(
            source_id=source.source_id,
            external_id="learned-azure",
            item_type="email_message",
            subject="Azure Reserved VM Instances",
            sender_or_owner="azure-noreply@microsoft.com",
            first_seen_run_id=learning_run.run_id,
        )
        store.record_feedback(
            item_id=learned_item.item_id,
            run_id=learning_run.run_id,
            feedback_type="review",
            feedback_text="Filed to Clarity/Azure during email cleanup.",
        )
        run = store.start_run(workflow="email-review")
        current_item = store.record_item_seen(
            source_id=source.source_id,
            external_id="current-azure",
            item_type="email_message",
            subject="Azure Reserved VM Instances update",
            sender_or_owner="azure-noreply@microsoft.com",
            updated_at="2026-07-17T08:00:00-05:00",
            first_seen_run_id=run.run_id,
        )
        store.record_classification(
            item_id=current_item.item_id,
            run_id=run.run_id,
            label="review",
            reason="Default review before folder memory.",
        )
    finally:
        store.close()


def _seed_gmail_cleanup_memory(memory_path):
    memory_path.parent.mkdir(parents=True, exist_ok=True)
    store = DuckDbMemoryStore(memory_path)
    try:
        store.initialize_schema()
        run = store.start_run(workflow="email-review")
        source = store.record_source(
            source_type="email",
            display_name="sesexton@gmail.com",
            scope_label="sesexton@gmail.com",
        )
        for external_id, subject, sender, updated_at, label, reason in (
            (
                "gmail-usps",
                "USPS Informed Delivery Daily Digest",
                "USPSInformeddelivery@email.informeddelivery.usps.com",
                "2026-07-18T09:00:00-05:00",
                "noise",
                "Daily digest.",
            ),
            (
                "gmail-promo",
                "Flash sale ends tonight",
                "promo@example.invalid",
                "2026-07-18T08:55:00-05:00",
                "noise",
                "Looks like marketing.",
            ),
            (
                "gmail-monarch",
                "Monarch found a recurring merchant",
                "email@email.monarch.com",
                "2026-07-18T08:50:00-05:00",
                "review",
                "Default review before folder routing.",
            ),
            (
                "gmail-experian",
                "Your Experian score changed",
                "support@e.usa.experian.com",
                "2026-07-18T08:45:00-05:00",
                "review",
                "Default review before folder routing.",
            ),
            (
                "gmail-vw",
                "Eddy's Volkswagen vehicle value",
                "EddysVolkswagen@send.outsellplatform.com",
                "2026-07-18T08:40:00-05:00",
                "review",
                "Default review before folder routing.",
            ),
            (
                "gmail-review",
                "School registration reminder",
                "school@example.invalid",
                "2026-07-18T08:35:00-05:00",
                "review",
                "Looks personal.",
            ),
        ):
            item = store.record_item_seen(
                source_id=source.source_id,
                external_id=external_id,
                item_type="email_message",
                subject=subject,
                sender_or_owner=sender,
                updated_at=updated_at,
                first_seen_run_id=run.run_id,
            )
            store.record_classification(
                item_id=item.item_id,
                run_id=run.run_id,
                label=label,
                reason=reason,
            )
    finally:
        store.close()
