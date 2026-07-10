# Clarity Persistence and Memory

## Purpose

Clarity needs local memory so it can answer questions from what it has learned,
continue delegated work, and recover quickly on another device.

Memory should make Clarity more useful without making it careless. It should
store enough context to explain recommendations and resume work, while avoiding
unnecessary copies of sensitive source data.

## Goals

-   Keep a local audit trail of what Clarity read, summarized, classified, and
    recommended
-   Support questions such as "what changed", "what needs review", "why was this
    classified as noise", and "what did you do last time"
-   Track delegated tasks from request to completion
-   Record human feedback so future runs can improve
-   Make state portable across devices without storing secrets

## Non-Goals

-   Store credentials, API tokens, session cookies, or refresh tokens
-   Replace source systems such as Jira, Exchange, Gmail, or calendars
-   Store full raw mailbox or ticket bodies by default
-   Make irreversible decisions without human approval
-   Introduce cloud storage as a default requirement

## Storage Direction

DuckDB is the preferred local store for structured memory because it is portable,
queryable, easy to back up, and suitable for local analytics.

The first implementation should keep the schema small and boring. Add tables
only when a real workflow needs them.

## Proposed Tables

### runs

One record per Clarity execution.

Suggested fields:

-   `run_id`
-   `started_at`
-   `completed_at`
-   `assistant_name`
-   `workflow`
-   `status`
-   `summary`

### sources

Approved systems or data sets Clarity may read.

Suggested fields:

-   `source_id`
-   `source_type`
-   `display_name`
-   `scope_label`
-   `access_mode`
-   `created_at`

### items_seen

Metadata about source items Clarity has processed.

Suggested fields:

-   `item_id`
-   `source_id`
-   `external_id`
-   `item_type`
-   `subject`
-   `sender_or_owner`
-   `updated_at`
-   `content_hash`
-   `first_seen_run_id`
-   `last_seen_run_id`

### classifications

Signal, noise, review, and priority judgments.

Suggested fields:

-   `classification_id`
-   `item_id`
-   `run_id`
-   `label`
-   `reason`
-   `confidence`
-   `created_at`

### human_feedback

Corrections and preferences supplied by the human.

Suggested fields:

-   `feedback_id`
-   `item_id`
-   `run_id`
-   `feedback_type`
-   `feedback_text`
-   `created_at`

### email_sender_preferences

Mailbox-scoped sender/domain classification preferences.

Suggested fields:

-   `preference_id`
-   `mailbox`
-   `match_type`
-   `pattern`
-   `label`
-   `created_run_id`
-   `created_at`

### assistant_actions

Actions Clarity prepared or performed.

Suggested fields:

-   `action_id`
-   `run_id`
-   `item_id`
-   `action_type`
-   `approval_status`
-   `action_target`
-   `result`
-   `created_at`

### generated_artifacts

Reports, summaries, drafts, and other local outputs.

Suggested fields:

-   `artifact_id`
-   `run_id`
-   `artifact_type`
-   `path`
-   `summary`
-   `created_at`

### delegated_tasks

Work the human asks Clarity to handle.

Suggested fields:

-   `task_id`
-   `created_run_id`
-   `title`
-   `request`
-   `status`
-   `next_step`
-   `approval_required`
-   `completed_at`

## Question Answering

Answers should come from local memory and approved sources. When an answer
depends on stored memory, Clarity should identify the run, source item, artifact,
or feedback record that supports it.

Early question answering should be narrow:

-   What did the latest Jira report find?
-   Which items were marked as needing review?
-   Which items were treated as noise, and why?
-   What delegated tasks are still open?
-   What did Clarity do in the last run?

If Clarity cannot support an answer from memory or an approved source, it should
say so plainly.

## Delegated Work

Delegated work should be tracked as a task with status and next step.

Useful statuses:

-   `requested`
-   `in_progress`
-   `waiting_for_approval`
-   `waiting_for_external_response`
-   `completed`
-   `blocked`

Clarity may prepare drafts, summaries, filing recommendations, or task plans.
Sending messages, changing calendars, writing Jira, deleting records, changing
permissions, or moving items outside approved folder conventions still requires
approval.

## Security Rules

-   Do not store secrets
-   Do not log authentication headers
-   Do not store raw message bodies by default
-   Store hashes and metadata before storing content
-   Keep work and personal context clearly labeled
-   Make human feedback auditable and reversible
-   Prefer local backups over cloud synchronization unless explicitly approved

## Testing Strategy

The first implementation should use fake records and a temporary local database.

Tests should cover:

-   Creating the schema
-   Recording a run
-   Recording a source item
-   Recording a classification and feedback
-   Recording a delegated task
-   Querying open tasks
-   Querying recent memory for question answering
-   Verifying secrets are not accepted in persisted records

Live connectors should not be required for memory tests.

## First Reusable Component

The smallest reusable component is a local memory store interface in `common`,
backed by DuckDB.

The first version supports:

-   Start and finish a run
-   Record an item seen
-   Record a classification
-   Record human feedback
-   Record and list delegated tasks

That gives Clarity enough memory to begin learning without widening external
permissions.

The Jira report runner now uses this component by default. Each run records the
Jira source, issues seen, content hashes, generated Markdown report artifact,
and a basic `review` classification in `logs/clarity-memory.duckdb`. Use
`--no-memory` when a report should be generated without updating local memory.

The first read-only memory question command is `assistant.src.ask_memory`. It can
answer deterministic questions about the local memory summary, latest Jira
report run, recent items, items marked for review, items marked as noise, recent
human feedback, recent local actions, and open delegated tasks. It does not use
an LLM, network access, or external writes.

The first local feedback command is `assistant.src.record_feedback`. It records
human feedback for remembered items by internal item ID or external ID, such as a
Jira key. Feedback is stored locally and does not write back to Jira, email,
calendar, or any external system.

For email, `noise` and `review` feedback records are also used as local learning
input on later email review runs. Learning is scoped to the mailbox and matching
message metadata. It can correct future review/noise classification for
matching subjects and senders, or for the same sender when sanitized
subject/preview terms overlap enough. It cannot override restricted mailbox
sender allow-list checks or email authentication failures.

Mailbox-specific sender/domain preferences can also guide classification. They
are local, auditable memory records, apply only to the configured mailbox, and
run after restricted mailbox sender/authentication checks. Preferences can be
listed from local memory and removed by preference ID.

The first local delegation command is `assistant.src.delegate_task`. It records
work the human wants Clarity to track, then surfaces it through `ask_memory
open-tasks` and `ask_memory summary`. It only writes to local memory.

Delegated task status is updated with `assistant.src.update_task`. Supported
statuses are `requested`, `in_progress`, `waiting_for_approval`,
`waiting_for_external_response`, `blocked`, and `completed`. Completing a task
removes it from open-task summaries.

Clarity records local assistant actions for report generation, feedback,
delegated task creation, and task status updates. These records provide an audit
trail of what Clarity did locally and whether approval was required. When an
action has a destination, such as a proposed email folder move, the destination
is stored in `action_target` so later planning does not need to parse prose.
Pending and approved action queues include the linked source item's
`external_id`; for email, that is the provider message identifier needed by a
future live move.

The first brief command is `assistant.src.generate_brief`. It composes the local
memory summary, review items, noise items, open delegated tasks, and recent
actions into `reports/clarity-brief.md`, then records the brief as a local
artifact and action.

The first email milestone is `assistant.src.run_email_review`. It reads fake
mailbox metadata through `common.email`, normalizes message metadata, applies
deterministic classifications, stores metadata and hashes in local
memory, and generates the Clarity brief. The requested mailbox must be listed in
local approved mailbox configuration with `read` or `read_write` access. It does
not connect to live Exchange or Gmail, store raw bodies by default, or perform
mailbox writes. It may store sanitized learning terms extracted from subject and
preview/snippet metadata so future feedback can generalize without preserving
raw message content. Proposed folder destinations are stored as structured
`assistant_actions.action_target` values. Non-trash email move targets must live
under the configured folder namespace, such as `Clarity/Review`; trash must use
the system `Deleted Items` folder.
