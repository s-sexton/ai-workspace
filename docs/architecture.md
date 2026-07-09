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

