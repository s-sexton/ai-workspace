"""Local Clarity memory store."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

import duckdb


OPEN_TASK_STATUSES = (
    "requested",
    "in_progress",
    "waiting_for_approval",
    "waiting_for_external_response",
    "blocked",
)
TASK_STATUSES = (*OPEN_TASK_STATUSES, "completed")
ACTION_APPROVAL_STATUSES = (
    "required",
    "approved",
    "rejected",
    "executed",
    "not_required",
)

_SECRET_MARKERS = (
    "api_token=",
    "access_token=",
    "authorization:",
    "bearer ",
    "basic ",
    "password=",
)


class MemoryStoreError(RuntimeError):
    """Raised when local memory cannot be read or written safely."""


@dataclass(frozen=True)
class RunRecord:
    """A single Clarity execution."""

    run_id: str
    workflow: str
    assistant_name: str
    status: str
    started_at: str
    completed_at: str | None = None
    summary: str | None = None


@dataclass(frozen=True)
class SourceRecord:
    """An approved source Clarity may remember metadata about."""

    source_id: str
    source_type: str
    display_name: str
    scope_label: str
    access_mode: str
    created_at: str


@dataclass(frozen=True)
class ItemSeenRecord:
    """Metadata for an item Clarity has processed."""

    item_id: str
    source_id: str
    external_id: str
    item_type: str
    subject: str
    sender_or_owner: str | None
    updated_at: str | None
    content_hash: str | None
    first_seen_run_id: str
    last_seen_run_id: str


@dataclass(frozen=True)
class ClassificationRecord:
    """A signal, noise, review, or priority judgment."""

    classification_id: str
    item_id: str
    run_id: str
    label: str
    reason: str
    confidence: float | None
    created_at: str


@dataclass(frozen=True)
class FeedbackRecord:
    """Human feedback that can improve future Clarity runs."""

    feedback_id: str
    item_id: str
    run_id: str
    feedback_type: str
    feedback_text: str
    created_at: str


@dataclass(frozen=True)
class GeneratedArtifactRecord:
    """A local report, summary, draft, or other generated output."""

    artifact_id: str
    run_id: str
    artifact_type: str
    path: str
    summary: str | None
    created_at: str


@dataclass(frozen=True)
class AssistantActionRecord:
    """A local action Clarity prepared or performed."""

    action_id: str
    run_id: str
    item_id: str | None
    action_type: str
    approval_status: str
    action_target: str | None
    result: str | None
    created_at: str


@dataclass(frozen=True)
class PendingActionRecord:
    """An action with approval status and optional item context."""

    action_id: str
    run_id: str
    item_id: str | None
    item_external_id: str | None
    item_subject: str | None
    item_type: str | None
    source_type: str | None
    source_scope_label: str | None
    action_type: str
    approval_status: str
    action_target: str | None
    result: str | None
    created_at: str


@dataclass(frozen=True)
class DelegatedTaskRecord:
    """Work the human has asked Clarity to handle."""

    task_id: str
    created_run_id: str
    title: str
    request: str
    status: str
    next_step: str | None
    approval_required: bool
    completed_at: str | None


@dataclass(frozen=True)
class RecentMemoryRecord:
    """A compact view used for early question answering."""

    item_id: str
    source_type: str
    display_name: str
    subject: str
    label: str | None
    reason: str | None


@dataclass(frozen=True)
class FeedbackSummaryRecord:
    """A compact feedback view used for learning review."""

    feedback_id: str
    external_id: str
    subject: str
    feedback_type: str
    feedback_text: str
    created_at: str


class DuckDbMemoryStore:
    """Small local DuckDB-backed memory store for Clarity."""

    def __init__(self, path: str | Path = ":memory:") -> None:
        self.path = str(path)
        self._connection = duckdb.connect(self.path)

    def close(self) -> None:
        """Close the underlying database connection."""

        self._connection.close()

    def initialize_schema(self) -> None:
        """Create the local memory schema if it does not already exist."""

        self._connection.execute(
            """
            CREATE TABLE IF NOT EXISTS runs (
                run_id VARCHAR PRIMARY KEY,
                started_at VARCHAR NOT NULL,
                completed_at VARCHAR,
                assistant_name VARCHAR NOT NULL,
                workflow VARCHAR NOT NULL,
                status VARCHAR NOT NULL,
                summary VARCHAR
            )
            """
        )
        self._connection.execute(
            """
            CREATE TABLE IF NOT EXISTS sources (
                source_id VARCHAR PRIMARY KEY,
                source_type VARCHAR NOT NULL,
                display_name VARCHAR NOT NULL,
                scope_label VARCHAR NOT NULL,
                access_mode VARCHAR NOT NULL,
                created_at VARCHAR NOT NULL
            )
            """
        )
        self._connection.execute(
            """
            CREATE TABLE IF NOT EXISTS items_seen (
                item_id VARCHAR PRIMARY KEY,
                source_id VARCHAR NOT NULL,
                external_id VARCHAR NOT NULL,
                item_type VARCHAR NOT NULL,
                subject VARCHAR NOT NULL,
                sender_or_owner VARCHAR,
                updated_at VARCHAR,
                content_hash VARCHAR,
                first_seen_run_id VARCHAR NOT NULL,
                last_seen_run_id VARCHAR NOT NULL
            )
            """
        )
        self._connection.execute(
            """
            CREATE TABLE IF NOT EXISTS classifications (
                classification_id VARCHAR PRIMARY KEY,
                item_id VARCHAR NOT NULL,
                run_id VARCHAR NOT NULL,
                label VARCHAR NOT NULL,
                reason VARCHAR NOT NULL,
                confidence DOUBLE,
                created_at VARCHAR NOT NULL
            )
            """
        )
        self._connection.execute(
            """
            CREATE TABLE IF NOT EXISTS human_feedback (
                feedback_id VARCHAR PRIMARY KEY,
                item_id VARCHAR NOT NULL,
                run_id VARCHAR NOT NULL,
                feedback_type VARCHAR NOT NULL,
                feedback_text VARCHAR NOT NULL,
                created_at VARCHAR NOT NULL
            )
            """
        )
        self._connection.execute(
            """
            CREATE TABLE IF NOT EXISTS assistant_actions (
                action_id VARCHAR PRIMARY KEY,
                run_id VARCHAR NOT NULL,
                item_id VARCHAR,
                action_type VARCHAR NOT NULL,
                approval_status VARCHAR NOT NULL,
                action_target VARCHAR,
                result VARCHAR,
                created_at VARCHAR NOT NULL
            )
            """
        )
        self._connection.execute(
            """
            ALTER TABLE assistant_actions
            ADD COLUMN IF NOT EXISTS action_target VARCHAR
            """
        )
        self._connection.execute(
            """
            CREATE TABLE IF NOT EXISTS generated_artifacts (
                artifact_id VARCHAR PRIMARY KEY,
                run_id VARCHAR NOT NULL,
                artifact_type VARCHAR NOT NULL,
                path VARCHAR NOT NULL,
                summary VARCHAR,
                created_at VARCHAR NOT NULL
            )
            """
        )
        self._connection.execute(
            """
            CREATE TABLE IF NOT EXISTS delegated_tasks (
                task_id VARCHAR PRIMARY KEY,
                created_run_id VARCHAR NOT NULL,
                title VARCHAR NOT NULL,
                request VARCHAR NOT NULL,
                status VARCHAR NOT NULL,
                next_step VARCHAR,
                approval_required BOOLEAN NOT NULL,
                completed_at VARCHAR
            )
            """
        )

    def start_run(
        self,
        *,
        workflow: str,
        assistant_name: str = "Clarity",
        started_at: str | None = None,
    ) -> RunRecord:
        """Record the start of a Clarity run."""

        _reject_secret_text(workflow, assistant_name)
        record = RunRecord(
            run_id=_new_id(),
            workflow=_required_text(workflow, "workflow"),
            assistant_name=_required_text(assistant_name, "assistant_name"),
            status="started",
            started_at=started_at or _now(),
        )
        self._connection.execute(
            """
            INSERT INTO runs
            (run_id, started_at, completed_at, assistant_name, workflow, status, summary)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            [
                record.run_id,
                record.started_at,
                record.completed_at,
                record.assistant_name,
                record.workflow,
                record.status,
                record.summary,
            ],
        )
        return record

    def finish_run(
        self,
        run_id: str,
        *,
        status: str,
        summary: str | None = None,
        completed_at: str | None = None,
    ) -> RunRecord:
        """Record the completion status for a Clarity run."""

        _reject_secret_text(run_id, status, summary)
        self._connection.execute(
            """
            UPDATE runs
            SET completed_at = ?, status = ?, summary = ?
            WHERE run_id = ?
            """,
            [completed_at or _now(), _required_text(status, "status"), summary, run_id],
        )
        return self.get_run(run_id)

    def get_run(self, run_id: str) -> RunRecord:
        """Return a run by ID."""

        row = self._connection.execute(
            """
            SELECT run_id, workflow, assistant_name, status, started_at, completed_at, summary
            FROM runs
            WHERE run_id = ?
            """,
            [run_id],
        ).fetchone()
        if row is None:
            raise MemoryStoreError(f"Unknown run: {run_id}")
        return RunRecord(*row)

    def latest_run(self, *, workflow: str | None = None) -> RunRecord | None:
        """Return the most recent run, optionally filtered by workflow."""

        if workflow is None:
            row = self._connection.execute(
                """
                SELECT run_id, workflow, assistant_name, status, started_at,
                       completed_at, summary
                FROM runs
                ORDER BY started_at DESC, run_id DESC
                LIMIT 1
                """
            ).fetchone()
        else:
            _reject_secret_text(workflow)
            row = self._connection.execute(
                """
                SELECT run_id, workflow, assistant_name, status, started_at,
                       completed_at, summary
                FROM runs
                WHERE workflow = ?
                ORDER BY started_at DESC, run_id DESC
                LIMIT 1
                """,
                [_required_text(workflow, "workflow")],
            ).fetchone()
        if row is None:
            return None
        return RunRecord(*row)

    def record_source(
        self,
        *,
        source_type: str,
        display_name: str,
        scope_label: str,
        access_mode: str = "read",
        created_at: str | None = None,
    ) -> SourceRecord:
        """Record an approved source."""

        _reject_secret_text(source_type, display_name, scope_label, access_mode)
        record = SourceRecord(
            source_id=_new_id(),
            source_type=_required_text(source_type, "source_type"),
            display_name=_required_text(display_name, "display_name"),
            scope_label=_required_text(scope_label, "scope_label"),
            access_mode=_required_text(access_mode, "access_mode"),
            created_at=created_at or _now(),
        )
        self._connection.execute(
            """
            INSERT INTO sources
            (source_id, source_type, display_name, scope_label, access_mode, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            [
                record.source_id,
                record.source_type,
                record.display_name,
                record.scope_label,
                record.access_mode,
                record.created_at,
            ],
        )
        return record

    def record_item_seen(
        self,
        *,
        source_id: str,
        external_id: str,
        item_type: str,
        subject: str,
        first_seen_run_id: str,
        sender_or_owner: str | None = None,
        updated_at: str | None = None,
        content_hash: str | None = None,
        last_seen_run_id: str | None = None,
    ) -> ItemSeenRecord:
        """Record metadata for a processed source item."""

        _reject_secret_text(
            source_id,
            external_id,
            item_type,
            subject,
            sender_or_owner,
            updated_at,
            content_hash,
            first_seen_run_id,
            last_seen_run_id,
        )
        record = ItemSeenRecord(
            item_id=_new_id(),
            source_id=_required_text(source_id, "source_id"),
            external_id=_required_text(external_id, "external_id"),
            item_type=_required_text(item_type, "item_type"),
            subject=_required_text(subject, "subject"),
            sender_or_owner=sender_or_owner,
            updated_at=updated_at,
            content_hash=content_hash,
            first_seen_run_id=_required_text(first_seen_run_id, "first_seen_run_id"),
            last_seen_run_id=last_seen_run_id or first_seen_run_id,
        )
        self._connection.execute(
            """
            INSERT INTO items_seen
            (
                item_id, source_id, external_id, item_type, subject, sender_or_owner,
                updated_at, content_hash, first_seen_run_id, last_seen_run_id
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                record.item_id,
                record.source_id,
                record.external_id,
                record.item_type,
                record.subject,
                record.sender_or_owner,
                record.updated_at,
                record.content_hash,
                record.first_seen_run_id,
                record.last_seen_run_id,
            ],
        )
        return record

    def find_item_seen(self, item_reference: str) -> ItemSeenRecord | None:
        """Find an item by internal item ID or external source ID."""

        _reject_secret_text(item_reference)
        reference = _required_text(item_reference, "item_reference")
        row = self._connection.execute(
            """
            SELECT item_id, source_id, external_id, item_type, subject,
                   sender_or_owner, updated_at, content_hash, first_seen_run_id,
                   last_seen_run_id
            FROM items_seen
            WHERE item_id = ? OR external_id = ?
            ORDER BY item_id DESC
            LIMIT 1
            """,
            [reference, reference],
        ).fetchone()
        if row is None:
            return None
        return ItemSeenRecord(*row)

    def record_classification(
        self,
        *,
        item_id: str,
        run_id: str,
        label: str,
        reason: str,
        confidence: float | None = None,
        created_at: str | None = None,
    ) -> ClassificationRecord:
        """Record a signal, noise, review, or priority judgment."""

        _reject_secret_text(item_id, run_id, label, reason)
        if confidence is not None and not 0 <= confidence <= 1:
            raise MemoryStoreError("confidence must be between 0 and 1.")
        record = ClassificationRecord(
            classification_id=_new_id(),
            item_id=_required_text(item_id, "item_id"),
            run_id=_required_text(run_id, "run_id"),
            label=_required_text(label, "label"),
            reason=_required_text(reason, "reason"),
            confidence=confidence,
            created_at=created_at or _now(),
        )
        self._connection.execute(
            """
            INSERT INTO classifications
            (classification_id, item_id, run_id, label, reason, confidence, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            [
                record.classification_id,
                record.item_id,
                record.run_id,
                record.label,
                record.reason,
                record.confidence,
                record.created_at,
            ],
        )
        return record

    def record_feedback(
        self,
        *,
        item_id: str,
        run_id: str,
        feedback_type: str,
        feedback_text: str,
        created_at: str | None = None,
    ) -> FeedbackRecord:
        """Record human feedback for a memory item."""

        _reject_secret_text(item_id, run_id, feedback_type, feedback_text)
        record = FeedbackRecord(
            feedback_id=_new_id(),
            item_id=_required_text(item_id, "item_id"),
            run_id=_required_text(run_id, "run_id"),
            feedback_type=_required_text(feedback_type, "feedback_type"),
            feedback_text=_required_text(feedback_text, "feedback_text"),
            created_at=created_at or _now(),
        )
        self._connection.execute(
            """
            INSERT INTO human_feedback
            (feedback_id, item_id, run_id, feedback_type, feedback_text, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            [
                record.feedback_id,
                record.item_id,
                record.run_id,
                record.feedback_type,
                record.feedback_text,
                record.created_at,
            ],
        )
        return record

    def recent_feedback(self, *, limit: int = 25) -> tuple[FeedbackSummaryRecord, ...]:
        """Return recent human feedback with source item context."""

        if limit < 1:
            raise MemoryStoreError("limit must be positive.")
        rows = self._connection.execute(
            """
            SELECT f.feedback_id, i.external_id, i.subject, f.feedback_type,
                   f.feedback_text, f.created_at
            FROM human_feedback f
            JOIN items_seen i ON i.item_id = f.item_id
            ORDER BY f.created_at DESC, f.feedback_id DESC
            LIMIT ?
            """,
            [limit],
        ).fetchall()
        return tuple(FeedbackSummaryRecord(*row) for row in rows)

    def record_generated_artifact(
        self,
        *,
        run_id: str,
        artifact_type: str,
        path: str | Path,
        summary: str | None = None,
        created_at: str | None = None,
    ) -> GeneratedArtifactRecord:
        """Record a local artifact generated by Clarity."""

        artifact_path = str(path)
        _reject_secret_text(run_id, artifact_type, artifact_path, summary)
        record = GeneratedArtifactRecord(
            artifact_id=_new_id(),
            run_id=_required_text(run_id, "run_id"),
            artifact_type=_required_text(artifact_type, "artifact_type"),
            path=_required_text(artifact_path, "path"),
            summary=summary,
            created_at=created_at or _now(),
        )
        self._connection.execute(
            """
            INSERT INTO generated_artifacts
            (artifact_id, run_id, artifact_type, path, summary, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            [
                record.artifact_id,
                record.run_id,
                record.artifact_type,
                record.path,
                record.summary,
                record.created_at,
            ],
        )
        return record

    def record_assistant_action(
        self,
        *,
        run_id: str,
        action_type: str,
        approval_status: str,
        action_target: str | None = None,
        result: str | None = None,
        item_id: str | None = None,
        created_at: str | None = None,
    ) -> AssistantActionRecord:
        """Record a local action Clarity prepared or performed."""

        _reject_secret_text(
            run_id,
            action_type,
            approval_status,
            action_target,
            result,
            item_id,
        )
        record = AssistantActionRecord(
            action_id=_new_id(),
            run_id=_required_text(run_id, "run_id"),
            item_id=item_id,
            action_type=_required_text(action_type, "action_type"),
            approval_status=_required_text(approval_status, "approval_status"),
            action_target=action_target,
            result=result,
            created_at=created_at or _now(),
        )
        self._connection.execute(
            """
            INSERT INTO assistant_actions
            (
                action_id, run_id, item_id, action_type, approval_status,
                action_target, result, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                record.action_id,
                record.run_id,
                record.item_id,
                record.action_type,
                record.approval_status,
                record.action_target,
                record.result,
                record.created_at,
            ],
        )
        return record

    def recent_actions(self, *, limit: int = 25) -> tuple[AssistantActionRecord, ...]:
        """Return recent local Clarity actions."""

        if limit < 1:
            raise MemoryStoreError("limit must be positive.")
        rows = self._connection.execute(
            """
            SELECT action_id, run_id, item_id, action_type, approval_status,
                   action_target, result, created_at
            FROM assistant_actions
            ORDER BY created_at DESC, action_id DESC
            LIMIT ?
            """,
            [limit],
        ).fetchall()
        return tuple(AssistantActionRecord(*row) for row in rows)

    def pending_actions(self, *, limit: int = 25) -> tuple[PendingActionRecord, ...]:
        """Return local actions that still require human approval."""

        return self.actions_by_approval_status("required", limit=limit)

    def actions_by_approval_status(
        self,
        approval_status: str,
        *,
        limit: int = 25,
    ) -> tuple[PendingActionRecord, ...]:
        """Return local actions with a specific approval status."""

        _reject_secret_text(approval_status)
        clean_status = _required_text(approval_status, "approval_status")
        if clean_status not in ACTION_APPROVAL_STATUSES:
            raise MemoryStoreError(
                "approval_status must be one of: "
                + ", ".join(ACTION_APPROVAL_STATUSES)
            )
        if limit < 1:
            raise MemoryStoreError("limit must be positive.")
        rows = self._connection.execute(
            """
            SELECT a.action_id, a.run_id, a.item_id, i.external_id, i.subject,
                   i.item_type, s.source_type, s.scope_label, a.action_type,
                   a.approval_status, a.action_target, a.result, a.created_at
            FROM assistant_actions a
            LEFT JOIN items_seen i ON i.item_id = a.item_id
            LEFT JOIN sources s ON s.source_id = i.source_id
            WHERE a.approval_status = ?
            ORDER BY a.created_at DESC, a.action_id DESC
            LIMIT ?
            """,
            [clean_status, limit],
        ).fetchall()
        return tuple(PendingActionRecord(*row) for row in rows)

    def update_assistant_action_approval(
        self,
        *,
        action_id: str,
        approval_status: str,
    ) -> AssistantActionRecord:
        """Update the local approval status for an assistant action."""

        _reject_secret_text(action_id, approval_status)
        clean_status = _required_text(approval_status, "approval_status")
        if clean_status not in ACTION_APPROVAL_STATUSES:
            raise MemoryStoreError(
                "approval_status must be one of: "
                + ", ".join(ACTION_APPROVAL_STATUSES)
            )

        existing = self._connection.execute(
            """
            SELECT action_id
            FROM assistant_actions
            WHERE action_id = ?
            """,
            [_required_text(action_id, "action_id")],
        ).fetchone()
        if existing is None:
            raise MemoryStoreError(f"Unknown assistant action: {action_id}")

        self._connection.execute(
            """
            UPDATE assistant_actions
            SET approval_status = ?
            WHERE action_id = ?
            """,
            [clean_status, action_id],
        )
        row = self._connection.execute(
            """
            SELECT action_id, run_id, item_id, action_type, approval_status,
                   action_target, result, created_at
            FROM assistant_actions
            WHERE action_id = ?
            """,
            [action_id],
        ).fetchone()
        return AssistantActionRecord(*row)

    def list_generated_artifacts(
        self,
        *,
        run_id: str,
    ) -> tuple[GeneratedArtifactRecord, ...]:
        """Return generated artifacts for a run."""

        _reject_secret_text(run_id)
        rows = self._connection.execute(
            """
            SELECT artifact_id, run_id, artifact_type, path, summary, created_at
            FROM generated_artifacts
            WHERE run_id = ?
            ORDER BY created_at DESC, artifact_id DESC
            """,
            [_required_text(run_id, "run_id")],
        ).fetchall()
        return tuple(GeneratedArtifactRecord(*row) for row in rows)

    def create_delegated_task(
        self,
        *,
        created_run_id: str,
        title: str,
        request: str,
        next_step: str | None = None,
        approval_required: bool = True,
        status: str = "requested",
    ) -> DelegatedTaskRecord:
        """Record work the human has delegated to Clarity."""

        _reject_secret_text(created_run_id, title, request, next_step, status)
        record = DelegatedTaskRecord(
            task_id=_new_id(),
            created_run_id=_required_text(created_run_id, "created_run_id"),
            title=_required_text(title, "title"),
            request=_required_text(request, "request"),
            status=_required_text(status, "status"),
            next_step=next_step,
            approval_required=approval_required,
            completed_at=None,
        )
        self._connection.execute(
            """
            INSERT INTO delegated_tasks
            (task_id, created_run_id, title, request, status, next_step, approval_required, completed_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                record.task_id,
                record.created_run_id,
                record.title,
                record.request,
                record.status,
                record.next_step,
                record.approval_required,
                record.completed_at,
            ],
        )
        return record

    def get_delegated_task(self, task_id: str) -> DelegatedTaskRecord:
        """Return a delegated task by ID."""

        _reject_secret_text(task_id)
        row = self._connection.execute(
            """
            SELECT task_id, created_run_id, title, request, status, next_step,
                   approval_required, completed_at
            FROM delegated_tasks
            WHERE task_id = ?
            """,
            [_required_text(task_id, "task_id")],
        ).fetchone()
        if row is None:
            raise MemoryStoreError(f"Unknown delegated task: {task_id}")
        return DelegatedTaskRecord(*row)

    def update_delegated_task_status(
        self,
        *,
        task_id: str,
        status: str,
        next_step: str | None = None,
        completed_at: str | None = None,
    ) -> DelegatedTaskRecord:
        """Update the status and optional next step for a delegated task."""

        _reject_secret_text(task_id, status, next_step, completed_at)
        clean_status = _required_text(status, "status")
        if clean_status not in TASK_STATUSES:
            raise MemoryStoreError(
                "status must be one of: " + ", ".join(TASK_STATUSES)
            )

        existing = self.get_delegated_task(task_id)
        resolved_completed_at = (
            completed_at or _now() if clean_status == "completed" else None
        )
        resolved_next_step = next_step if next_step is not None else existing.next_step
        self._connection.execute(
            """
            UPDATE delegated_tasks
            SET status = ?, next_step = ?, completed_at = ?
            WHERE task_id = ?
            """,
            [
                clean_status,
                resolved_next_step,
                resolved_completed_at,
                existing.task_id,
            ],
        )
        return self.get_delegated_task(existing.task_id)

    def list_open_delegated_tasks(self) -> tuple[DelegatedTaskRecord, ...]:
        """Return delegated tasks that still need attention."""

        rows = self._connection.execute(
            """
            SELECT task_id, created_run_id, title, request, status, next_step,
                   approval_required, completed_at
            FROM delegated_tasks
            WHERE status IN (?, ?, ?, ?, ?)
            ORDER BY task_id
            """,
            list(OPEN_TASK_STATUSES),
        ).fetchall()
        return tuple(DelegatedTaskRecord(*row) for row in rows)

    def recent_memory_by_label(
        self,
        label: str,
        *,
        limit: int = 25,
    ) -> tuple[RecentMemoryRecord, ...]:
        """Return recent item memory with a specific classification label."""

        _reject_secret_text(label)
        if limit < 1:
            raise MemoryStoreError("limit must be positive.")
        rows = self._connection.execute(
            """
            SELECT i.item_id, s.source_type, s.display_name, i.subject,
                   c.label, c.reason
            FROM items_seen i
            JOIN sources s ON s.source_id = i.source_id
            JOIN classifications c ON c.item_id = i.item_id
            WHERE c.label = ?
            ORDER BY i.item_id DESC
            LIMIT ?
            """,
            [_required_text(label, "label"), limit],
        ).fetchall()
        return tuple(RecentMemoryRecord(*row) for row in rows)

    def recent_memory(self, *, limit: int = 25) -> tuple[RecentMemoryRecord, ...]:
        """Return recent item memory for early question-answering use cases."""

        if limit < 1:
            raise MemoryStoreError("limit must be positive.")
        rows = self._connection.execute(
            """
            SELECT i.item_id, s.source_type, s.display_name, i.subject,
                   c.label, c.reason
            FROM items_seen i
            JOIN sources s ON s.source_id = i.source_id
            LEFT JOIN classifications c ON c.item_id = i.item_id
            ORDER BY i.item_id DESC
            LIMIT ?
            """,
            [limit],
        ).fetchall()
        return tuple(RecentMemoryRecord(*row) for row in rows)


def _new_id() -> str:
    return uuid4().hex


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _required_text(value: str, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise MemoryStoreError(f"{field_name} must be a non-empty string.")
    return value.strip()


def _reject_secret_text(*values: Any) -> None:
    for value in values:
        if not isinstance(value, str):
            continue
        lower_value = value.lower()
        if any(marker in lower_value for marker in _SECRET_MARKERS):
            raise MemoryStoreError("Memory records must not contain sensitive auth data.")
