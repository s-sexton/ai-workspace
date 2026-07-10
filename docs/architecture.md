# Architecture

## Overview

AI Workspace is composed of specialized assistants that share a common
platform.

Each top-level assistant directory represents a role or assistant domain.

Reusable functionality belongs in `common`.

## Shared Platform

The `common` package contains reusable platform code shared by assistants.

Current shared components:

-   `common.configuration`: loads committed workspace settings and ignored
    local environment values, validates the Jira report settings needed for the
    current milestone, and avoids exposing secret values in object
    representations or errors.
-   `common.jira`: builds the read-only Jira report query, calls an injected
    transport, optionally uses a standard-library live Jira transport, and
    normalizes Jira issue JSON into report-friendly objects.
-   `common.email`: defines the read-only email metadata boundary, normalizes
    mailbox message metadata, and provides deterministic first-pass
    classifications using fake transports.
-   `common.calendar`: defines the read-only calendar metadata boundary,
    normalizes event metadata, and provides a fake local transport for calendar
    workflow tests.
-   `common.graph_calendar`: provides the Microsoft Graph calendar read adapter
    behind the shared calendar boundary.
-   `common.google_calendar`: provides the Google Calendar read adapter behind
    the shared calendar boundary.
-   `common.memory`: provides the first local Clarity memory boundary, backed by
    DuckDB, for recording runs, approved sources, items seen, classifications,
    human feedback, and delegated tasks without storing secrets.

## Assistant Structure

``` text
assistant/
|-- README.md
|-- prompts/
|-- src/
|-- tests/
`-- docs/
```

Current assistant components:

-   `assistant/`: contains Clarity Assistant, which covers work and personal
    decision support while keeping implementation steps small and testable.
-   `assistant.src.jira_report`: formats normalized Jira issues into Markdown
    for the first read-only Jira report.
-   `assistant.src.run_jira_report`: wires configuration, a static Jira
    transport or explicit live read-only transport, Jira normalization, and
    Markdown generation into an end-to-end report check.
-   `assistant.src.ask_memory`: reads the local DuckDB memory file and answers a
    small deterministic set of questions without network access, LLM calls, or
    external writes.
-   `assistant.src.record_feedback`: records human feedback for remembered
    local memory items without writing to source systems.
-   `assistant.src.delegate_task`: records delegated work in local memory so it
    can be surfaced by summary and open-task questions.
-   `assistant.src.update_task`: updates local delegated task status without
    modifying external systems.
-   `assistant.src.generate_brief`: composes deterministic local memory answers
    into a Markdown brief artifact.
-   `assistant.src.run_email_review`: reads email metadata from a fake local
    transport, records message metadata and classifications in local memory, and
    generates the Clarity brief without live mailbox access or external writes.
-   `assistant.src.run_calendar_review`: reads sample calendar metadata through
    the shared calendar boundary, records event metadata in local memory, and
    can explicitly read approved Graph or Google calendar metadata without
    external writes.
-   Local assistant actions are recorded in `common.memory` so Clarity can
    answer what it did recently without inspecting logs.

