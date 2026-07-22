"""Generate a numbered email cleanup batch from Clarity memory."""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Sequence

from assistant.src.run_jira_report import DEFAULT_MEMORY_PATH
from common.configuration import find_workspace_root, load_workspace_config
from common.memory import DuckDbMemoryStore, SourceMemoryRecord


DEFAULT_EMAIL_CLEANUP_BATCH_PATH = Path("reports") / "email-cleanup-batch.md"


@dataclass(frozen=True)
class EmailCleanupBatchResult:
    """Safe details from a generated email cleanup batch."""

    output_path: Path
    manifest_path: Path
    memory_path: Path
    mailbox: str
    item_count: int


@dataclass(frozen=True)
class FolderMemoryRecommendation:
    """A prior cleanup folder decision that can guide the current batch."""

    target_folder: str
    reason: str


@dataclass(frozen=True)
class BatchRecommendation:
    """A rendered cleanup recommendation for one batch item."""

    target_folder: str
    reason: str
    group: str


@dataclass(frozen=True)
class FolderMemoryRule:
    """One remembered folder-routing decision from cleanup feedback."""

    target_folder: str
    subject: str
    sender_or_owner: str | None
    created_at: str


_GMAIL_SPECIFIC_FOLDER_RULES: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("Clarity/Monarch", ("monarch",)),
    ("Clarity/Experian", ("experian",)),
    ("Clarity/USPS", ("usps", "informed delivery")),
    ("Clarity/Travelers Insurance", ("travelers",)),
    ("Clarity/VW", ("volkswagen", "vw", "eddy's volkswagen", "eddys volkswagen")),
    ("Clarity/Garmin", ("garmin",)),
    ("Clarity/K-State", ("k-state", "kansas state")),
    ("Clarity/Sedgwick HS", ("sedgwick hs", "district negative balance")),
    ("Clarity/Fiddlers Creek", ("fiddlers creek", "fiddler's creek")),
    ("Clarity/Smith Orthodontics", ("smith orthodontics",)),
)


def generate_email_cleanup_batch(
    *,
    root: Path | str | None = None,
    memory_path: Path | str = DEFAULT_MEMORY_PATH,
    output_path: Path | str = DEFAULT_EMAIL_CLEANUP_BATCH_PATH,
    mailbox: str | None = None,
    limit: int = 25,
    generated_at: datetime | None = None,
) -> EmailCleanupBatchResult:
    """Generate a local numbered email cleanup batch for one mailbox."""

    if limit < 1:
        raise ValueError("limit must be positive.")

    workspace_root = Path(root).resolve() if root is not None else find_workspace_root()
    config = load_workspace_config(workspace_root, include_process_env=False)
    email_settings = config.email_settings
    selected_mailbox = mailbox or email_settings.default_mailbox
    if selected_mailbox not in email_settings.approved_mailboxes:
        raise ValueError(f"Mailbox is not approved: {selected_mailbox}")

    resolved_memory_path = _resolve_path(workspace_root, Path(memory_path))
    resolved_output_path = _resolve_path(workspace_root, Path(output_path))
    resolved_manifest_path = resolved_output_path.with_suffix(".json")
    resolved_generated_at = generated_at or datetime.now()

    records: tuple[SourceMemoryRecord, ...] = ()
    folder_recommendations: dict[str, FolderMemoryRecommendation] = {}
    if resolved_memory_path.is_file():
        store = DuckDbMemoryStore(resolved_memory_path)
        try:
            records = _mailbox_records(store, mailbox=selected_mailbox, limit=limit)
            folder_recommendations = _folder_memory_recommendations(
                store,
                mailbox=selected_mailbox,
                records=records,
                folder_namespace=email_settings.folder_namespace,
            )
        finally:
            store.close()

    content = render_email_cleanup_batch(
        mailbox=selected_mailbox,
        records=records,
        folder_namespace=email_settings.folder_namespace,
        folder_policy=email_settings.folder_policy,
        folder_recommendations=folder_recommendations,
        generated_at=resolved_generated_at,
    )
    resolved_output_path.parent.mkdir(parents=True, exist_ok=True)
    resolved_output_path.write_text(content, encoding="utf-8")
    _write_manifest(
        resolved_manifest_path,
        manifest=_batch_manifest(
            mailbox=selected_mailbox,
            records=records,
            folder_policy=email_settings.folder_policy,
            folder_recommendations=folder_recommendations,
            generated_at=resolved_generated_at,
        ),
    )
    return EmailCleanupBatchResult(
        output_path=resolved_output_path,
        manifest_path=resolved_manifest_path,
        memory_path=resolved_memory_path,
        mailbox=selected_mailbox,
        item_count=len(records),
    )


def render_email_cleanup_batch(
    *,
    mailbox: str,
    records: Sequence[SourceMemoryRecord],
    folder_namespace: str,
    folder_policy: dict[str, str] | Any,
    folder_recommendations: dict[str, FolderMemoryRecommendation] | None = None,
    generated_at: datetime,
) -> str:
    """Render a numbered email cleanup batch as compact Markdown."""

    lines = [
        "# Email Cleanup Batch",
        "",
        f"Mailbox: {mailbox}",
        f"Generated: {generated_at.isoformat(timespec='seconds')}",
        f"Items: {len(records)}",
        "",
        "## Routing",
        "",
        f"- Review: {folder_policy.get('review', f'{folder_namespace}/Review')}",
        f"- Noise: {folder_policy.get('noise', f'{folder_namespace}/Noise')}",
        f"- Delete: {folder_policy.get('trash', 'Deleted Items')}",
        f"- Specific folders: {folder_namespace}/<Folder Name>",
        "",
    ]
    if not records:
        lines.extend(("## Emails", ""))
        lines.append("Nothing found for this mailbox.")
        return "\n".join(lines).rstrip() + "\n"

    batch_recommendations = _batch_recommendations(
        mailbox=mailbox,
        records=records,
        folder_policy=folder_policy,
        folder_recommendations=folder_recommendations or {},
    )
    if _is_gmail_mailbox(mailbox):
        lines.extend(
            _gmail_grouped_record_lines(
                records=records,
                batch_recommendations=batch_recommendations,
            )
        )
    else:
        lines.extend(("## Emails", ""))
        for index, record in enumerate(records, 1):
            lines.extend(
                _record_lines(
                    index,
                    record,
                    recommendation=batch_recommendations[record.item_id],
                )
            )
            lines.append("")

    lines.extend(
        (
            "## Example Directions",
            "",
            "- Move 1 to Noise",
            "- Move 2 to Review",
            f"- Move 3 to {folder_namespace}/Vendor Name",
            "- Delete 4",
        )
    )
    return "\n".join(lines).rstrip() + "\n"


def _gmail_grouped_record_lines(
    *,
    records: Sequence[SourceMemoryRecord],
    batch_recommendations: dict[str, BatchRecommendation],
) -> list[str]:
    lines: list[str] = []
    groups = (
        ("specific_folder", "Move To Specific Clarity Folders"),
        ("delete", "Likely Delete"),
        ("review", "Review"),
    )
    numbered_records = tuple(enumerate(records, 1))
    for group, title in groups:
        group_records = tuple(
            (index, record)
            for index, record in numbered_records
            if batch_recommendations[record.item_id].group == group
        )
        if not group_records:
            continue
        lines.extend((f"## {title}", ""))
        for index, record in group_records:
            lines.extend(
                _record_lines(
                    index,
                    record,
                    recommendation=batch_recommendations[record.item_id],
                )
            )
            lines.append("")
    return lines


def _batch_recommendations(
    *,
    mailbox: str,
    records: Sequence[SourceMemoryRecord],
    folder_policy: dict[str, str] | Any,
    folder_recommendations: dict[str, FolderMemoryRecommendation],
) -> dict[str, BatchRecommendation]:
    return {
        record.item_id: _batch_recommendation(
            mailbox=mailbox,
            record=record,
            folder_policy=folder_policy,
            folder_recommendation=folder_recommendations.get(record.item_id),
        )
        for record in records
    }


def _batch_recommendation(
    *,
    mailbox: str,
    record: SourceMemoryRecord,
    folder_policy: dict[str, str] | Any,
    folder_recommendation: FolderMemoryRecommendation | None,
) -> BatchRecommendation:
    if _is_gmail_mailbox(mailbox):
        specific_folder = _gmail_specific_folder(record)
        if specific_folder is not None:
            return BatchRecommendation(
                target_folder=specific_folder,
                reason="Matched known Gmail cleanup folder.",
                group="specific_folder",
            )
        if folder_recommendation is not None:
            return BatchRecommendation(
                target_folder=folder_recommendation.target_folder,
                reason=folder_recommendation.reason,
                group="specific_folder",
            )
        label = (record.label or "review").lower()
        if label in {"noise", "trash"}:
            return BatchRecommendation(
                target_folder=folder_policy.get("trash", "Deleted Items"),
                reason=record.reason or "Looks safe to delete from Gmail cleanup.",
                group="delete",
            )
        return BatchRecommendation(
            target_folder=folder_policy.get("review", "Clarity/Review"),
            reason=record.reason or "Needs human review.",
            group="review",
        )

    if folder_recommendation is not None:
        return BatchRecommendation(
            target_folder=folder_recommendation.target_folder,
            reason=folder_recommendation.reason,
            group="specific_folder",
        )
    label = (record.label or "review").lower()
    if label == "trash":
        return BatchRecommendation(
            target_folder=folder_policy.get("trash", "Deleted Items"),
            reason=record.reason or "Marked for trash.",
            group="delete",
        )
    if label == "noise":
        return BatchRecommendation(
            target_folder=folder_policy.get("noise", "Clarity/Noise"),
            reason=record.reason or "Looks like noise.",
            group="noise",
        )
    return BatchRecommendation(
        target_folder=folder_policy.get("review", "Clarity/Review"),
        reason=record.reason or "Needs human review.",
        group="review",
    )


def _gmail_specific_folder(record: SourceMemoryRecord) -> str | None:
    haystack = _normalize_text(
        " ".join(
            value
            for value in (record.subject, record.sender_or_owner or "")
            if value
        )
    )
    for target_folder, markers in _GMAIL_SPECIFIC_FOLDER_RULES:
        if any(marker in haystack for marker in markers):
            return target_folder
    return None


def _is_gmail_mailbox(mailbox: str) -> bool:
    return mailbox.lower().endswith("@gmail.com")


def main(argv: Sequence[str] | None = None) -> None:
    """Generate a numbered email cleanup batch."""

    args = _parse_args(argv)
    result = generate_email_cleanup_batch(
        memory_path=args.memory,
        output_path=args.output,
        mailbox=args.mailbox,
        limit=args.limit,
    )
    print(f"Wrote {result.output_path}")
    print(f"Manifest: {result.manifest_path}")
    print(f"Mailbox: {result.mailbox}")
    print(f"Items: {result.item_count}")


def _mailbox_records(
    store: DuckDbMemoryStore,
    *,
    mailbox: str,
    limit: int,
) -> tuple[SourceMemoryRecord, ...]:
    latest_records = _latest_mailbox_run_records(store, mailbox=mailbox, limit=limit)
    if latest_records is not None:
        return latest_records
    records = store.recent_memory_by_source_type("email", limit=limit * 5)
    filtered = (
        record
        for record in records
        if record.scope_label == mailbox and record.item_type == "email_message"
    )
    return _unique_records(tuple(filtered))[:limit]


def _latest_mailbox_run_records(
    store: DuckDbMemoryStore,
    *,
    mailbox: str,
    limit: int,
) -> tuple[SourceMemoryRecord, ...] | None:
    row = store._connection.execute(
        """
        SELECT r.run_id
        FROM runs r
        JOIN assistant_actions a ON a.run_id = r.run_id
        WHERE r.workflow = 'email-review'
          AND a.action_type = 'read_email_metadata'
          AND a.result LIKE ?
        ORDER BY r.started_at DESC, r.run_id DESC
        LIMIT 1
        """,
        [f"Read % message(s) from {mailbox}."],
    ).fetchone()
    if row is None:
        return None
    rows = store._connection.execute(
        """
        SELECT i.item_id, i.external_id, s.source_type, s.display_name,
               s.scope_label, i.item_type, i.subject, i.sender_or_owner,
               i.updated_at, c.label, c.reason
        FROM items_seen i
        JOIN sources s ON s.source_id = i.source_id
        LEFT JOIN classifications c ON c.item_id = i.item_id
        WHERE i.first_seen_run_id = ?
          AND s.scope_label = ?
          AND i.item_type = 'email_message'
        ORDER BY COALESCE(i.updated_at, '') DESC, i.item_id DESC
        LIMIT ?
        """,
        [row[0], mailbox, limit],
    ).fetchall()
    return tuple(SourceMemoryRecord(*record) for record in rows)


def _unique_records(
    records: Sequence[SourceMemoryRecord],
) -> tuple[SourceMemoryRecord, ...]:
    unique_records: list[SourceMemoryRecord] = []
    seen: set[tuple[str, str]] = set()
    for record in records:
        key = (record.scope_label, record.external_id)
        if key in seen:
            continue
        seen.add(key)
        unique_records.append(record)
    return tuple(unique_records)


def _folder_memory_recommendations(
    store: DuckDbMemoryStore,
    *,
    mailbox: str,
    records: Sequence[SourceMemoryRecord],
    folder_namespace: str,
) -> dict[str, FolderMemoryRecommendation]:
    rules = _folder_memory_rules(
        store,
        mailbox=mailbox,
        folder_namespace=folder_namespace,
        limit=250,
    )
    recommendations: dict[str, FolderMemoryRecommendation] = {}
    for record in records:
        recommendation = _folder_memory_recommendation(record, rules=rules)
        if recommendation is not None:
            recommendations[record.item_id] = recommendation
    return recommendations


def _folder_memory_rules(
    store: DuckDbMemoryStore,
    *,
    mailbox: str,
    folder_namespace: str,
    limit: int,
) -> tuple[FolderMemoryRule, ...]:
    folder_prefix = f"Filed to {folder_namespace}/"
    rows = store._connection.execute(
        """
        SELECT f.feedback_text, i.subject, i.sender_or_owner, f.created_at
        FROM human_feedback f
        JOIN items_seen i ON i.item_id = f.item_id
        JOIN sources s ON s.source_id = i.source_id
        WHERE s.source_type = 'email'
          AND s.scope_label = ?
          AND f.feedback_type = 'review'
          AND f.feedback_text LIKE ?
        ORDER BY f.created_at DESC, f.feedback_id DESC
        LIMIT ?
        """,
        [mailbox, f"{folder_prefix}%", limit],
    ).fetchall()
    rules: list[FolderMemoryRule] = []
    for feedback_text, subject, sender_or_owner, created_at in rows:
        target_folder = _folder_from_feedback_text(
            feedback_text,
            folder_namespace=folder_namespace,
        )
        if target_folder is None:
            continue
        rules.append(
            FolderMemoryRule(
                target_folder=target_folder,
                subject=subject,
                sender_or_owner=sender_or_owner,
                created_at=created_at,
            )
        )
    return tuple(rules)


def _folder_from_feedback_text(
    feedback_text: str,
    *,
    folder_namespace: str,
) -> str | None:
    match = re.match(
        rf"^Filed to ({re.escape(folder_namespace)}/.+?) during email cleanup\.$",
        feedback_text,
    )
    if not match:
        return None
    target_folder = match.group(1)
    if target_folder in {
        f"{folder_namespace}/Review",
        f"{folder_namespace}/Noise",
    }:
        return None
    return target_folder


def _folder_memory_recommendation(
    record: SourceMemoryRecord,
    *,
    rules: Sequence[FolderMemoryRule],
) -> FolderMemoryRecommendation | None:
    record_sender = _normalize_text(record.sender_or_owner or "")
    record_subject_terms = _subject_terms(record.subject)
    for rule in rules:
        rule_sender = _normalize_text(rule.sender_or_owner or "")
        rule_subject_terms = _subject_terms(rule.subject)
        shared_subject_terms = record_subject_terms & rule_subject_terms
        if (
            record_sender
            and rule_sender
            and record_sender == rule_sender
            and shared_subject_terms
        ):
            return FolderMemoryRecommendation(
                target_folder=rule.target_folder,
                reason="Matched prior folder move by sender and subject.",
            )
        folder_terms = _folder_terms(rule.target_folder)
        if folder_terms and folder_terms.issubset(record_subject_terms):
            return FolderMemoryRecommendation(
                target_folder=rule.target_folder,
                reason="Matched prior folder move by subject.",
            )
    return None


def _folder_terms(folder_path: str) -> set[str]:
    folder_name = folder_path.split("/")[-1]
    return {
        term
        for term in _subject_terms(folder_name)
        if len(term) > 2
    }


def _subject_terms(value: str) -> set[str]:
    return {
        token
        for token in re.findall(r"[a-z0-9]+", value.lower())
        if len(token) > 2
    }


def _normalize_text(value: str) -> str:
    return " ".join(value.lower().strip().split())


def _record_lines(
    index: int,
    record: SourceMemoryRecord,
    *,
    recommendation: BatchRecommendation,
) -> list[str]:
    return [
        f"{index}. Date: {record.updated_at or 'Unknown'}",
        f"   From: {record.sender_or_owner or 'Unknown'}",
        f"   Subject: {record.subject}",
        f"   Recommendation: {_recommendation_text(recommendation)}",
        f"   Why: {recommendation.reason}",
    ]


def _recommendation_text(recommendation: BatchRecommendation) -> str:
    if recommendation.group == "delete":
        return f"Delete ({recommendation.target_folder})"
    return f"Move to {recommendation.target_folder}"


def _batch_manifest(
    *,
    mailbox: str,
    records: Sequence[SourceMemoryRecord],
    folder_policy: dict[str, str] | Any,
    folder_recommendations: dict[str, FolderMemoryRecommendation],
    generated_at: datetime,
) -> dict[str, Any]:
    recommendations = _batch_recommendations(
        mailbox=mailbox,
        records=records,
        folder_policy=folder_policy,
        folder_recommendations=folder_recommendations,
    )
    return {
        "mailbox": mailbox,
        "generatedAt": generated_at.isoformat(timespec="seconds"),
        "items": [
            {
                "number": index,
                "itemId": record.item_id,
                "externalId": record.external_id,
                "sourceType": record.source_type,
                "sourceScope": record.scope_label,
                "itemType": record.item_type,
                "subject": record.subject,
                "senderOrOwner": record.sender_or_owner,
                "updatedAt": record.updated_at,
                "label": record.label,
                "reason": record.reason,
                "recommendation": {
                    "targetFolder": recommendations[record.item_id].target_folder,
                    "reason": recommendations[record.item_id].reason,
                    "group": recommendations[record.item_id].group,
                },
                "folderRecommendation": (
                    {
                        "targetFolder": folder_recommendations[record.item_id].target_folder,
                        "reason": folder_recommendations[record.item_id].reason,
                    }
                    if record.item_id in folder_recommendations
                    else None
                ),
            }
            for index, record in enumerate(records, 1)
        ],
    }


def _write_manifest(path: Path, *, manifest: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _resolve_path(root: Path, path: Path) -> Path:
    if path.is_absolute():
        return path
    return root / path


def _parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate a numbered email cleanup batch from Clarity memory.",
    )
    parser.add_argument(
        "--memory",
        default=DEFAULT_MEMORY_PATH,
        type=Path,
        help="DuckDB memory path.",
    )
    parser.add_argument(
        "--output",
        default=DEFAULT_EMAIL_CLEANUP_BATCH_PATH,
        type=Path,
        help="Markdown output path.",
    )
    parser.add_argument(
        "--mailbox",
        help="Approved mailbox to batch. Defaults to assistant.email.defaultMailbox.",
    )
    parser.add_argument(
        "--limit",
        default=25,
        type=int,
        help="Maximum current items to include.",
    )
    return parser.parse_args(argv)


if __name__ == "__main__":
    main()


