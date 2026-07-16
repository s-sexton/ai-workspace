# AI Workspace

## Purpose

AI Workspace is a local-first engineering platform for building AI-powered assistants that support work and personal decision making, including SendThisFile operations and personal life coordination.

The goal is **not** to replace human decision making.

The goal is to help people make better decisions by gathering information, analyzing data, making recommendations, and automating repetitive work while maintaining human oversight.

The workspace is designed to grow over time by adding specialized assistants that share a common platform rather than duplicating functionality.

---

# Design Principles

The following principles guide every architectural and implementation decision.

## Local First

Whenever practical, assistants execute locally.

Cloud execution is never assumed.

## Human In Control

Assistants assist.

Humans decide.

Production changes, infrastructure changes, security changes, and destructive actions always require human approval.

## Security First

Security is preferred over convenience.

Least privilege is the default.

Secrets are never committed to source control.

## Build Once, Reuse Everywhere

Common functionality belongs in the shared platform.

Avoid duplicated implementations.

## Small, Understandable Components

Each assistant should have a clear responsibility.

Complexity should emerge through composition rather than large monolithic applications.

---

# Repository Layout

```
ai-workspace/
â”‚
â”œâ”€â”€ assistant/
â”œâ”€â”€ developer/
â”œâ”€â”€ analytics/
â”œâ”€â”€ security/
â”œâ”€â”€ documentation/
â”œâ”€â”€ research/
â”‚
â”œâ”€â”€ common/
â”œâ”€â”€ config/
â”œâ”€â”€ docs/
â”œâ”€â”€ scripts/
â”œâ”€â”€ tests/
â”œâ”€â”€ logs/
â””â”€â”€ reports/
```

---

# Directory Responsibilities

## assistant/

Clarity Assistant for work and personal decision support.

Initial responsibilities include:

- Jira review
- Jira Service Management review
- Operational summaries
- Prioritization recommendations

Future capabilities may include:

- Gmail review
- Family calendar review
- Personal reminders
- Household planning
- Customer health monitoring
- Daily briefings

---

## developer/

Software engineering assistant.

Examples:

- Jira implementation
- Code generation
- Code review
- Pull request summaries
- Architecture analysis

---

## analytics/

Business analytics assistant.

Examples:

- PostgreSQL analysis
- Power BI
- Chargebee
- QuickBooks
- Business metrics
- Customer trends

---

## security/

Security engineering assistant.

Examples:

- Authentication review
- Secret scanning
- Dependency review
- Security recommendations
- Code review

---

## documentation/

Documentation assistant.

Examples:

- README maintenance
- Architecture documentation
- Release notes
- User documentation
- Architecture Decision Records

---

## research/

Research assistant.

Examples:

- Technology evaluations
- Product comparisons
- Design alternatives
- Best practices

---

## common/

Shared platform used by every assistant.

Examples include:

- Authentication
- Configuration
- Logging
- Shared API clients
- Prompt management
- Reporting
- Utility functions

---

## config/

Workspace configuration.

Contains:

- Environment templates
- Shared configuration

Local secrets are never committed.

---

## docs/

Architecture and design documentation.

Every significant architectural decision should be documented.

---

## scripts/

Workspace utility scripts.

These scripts support the workspace.

They should not contain reusable business logic.

---

## tests/

Workspace testing.

Includes:

- Unit tests
- Integration tests
- Shared component tests

---

## logs/

Runtime logs.

Ignored by Git.

---

## reports/

Generated assistant output.

Ignored by Git.

Reports may contain sensitive business information.

---

# Current Milestone

Build Clarity's local command surface and email review loop.

Current scope:

- Deterministic local question answering from Clarity memory
- Read-only Jira Cloud reporting
- Approved email mailbox metadata review
- Approved Gmail inbox metadata review
- Approved calendar metadata review
- Local memory and Markdown briefs
- Daily command-center and focus-plan answers
- Proposed email folder moves with local approval records
- Approved Gmail archive/trash execution through explicit commands
- Scheduler-friendly local cycle commands
- Bounded, validated LLM summaries on explicit command
- No Jira writes
- No LLM tool/action authority
- No autonomous writes

---

# Long-Term Vision

Create a reusable local-first AI engineering platform where specialized assistants collaborate through a shared platform while maintaining consistent architecture, security, and development practices.

