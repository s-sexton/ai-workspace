# AI Workspace Instructions

These instructions apply to every AI coding assistant working in this repository.

---

# Mission

Help people make better decisions.

Gather information.

Analyze information.

Recommend actions.

Explain reasoning.

Do not replace human judgment.

---

# Local First

Prefer local execution whenever practical.

Never recommend cloud execution for proprietary business data unless explicitly requested.

Assume this repository contains confidential company information.

---

# Security

Follow the principle of least privilege.

Never introduce secrets into source control.

Never expose credentials.

Never log authentication data.

Never modify environment configuration without approval.

Security takes priority over convenience.

---

# Working Style

Before implementing significant work:

1. Read the repository documentation.
2. Explain your understanding.
3. Present a plan.
4. Wait for approval if the work changes architecture.
5. Implement small reviewable changes.
6. Add or update tests.
7. Update necessary documentation or create new documentation as needed.
8. Explain what changed.

---

## Runtime Environment

The default development runtime for this workspace is Windows-native Python executed from PowerShell.

WSL may be used when a task clearly benefits from Linux tooling, but it should not be assumed.

When running commands, prefer standard PowerShell-compatible commands unless the human operator requests WSL.

---

# Development Philosophy

Favor maintainability over cleverness.

Reuse existing functionality whenever practical.

Avoid unnecessary dependencies.

Keep solutions simple.

Avoid duplication.

If functionality could reasonably be shared, place it in the shared platform.

---

# Repository Organization

Each top-level assistant directory represents a business role.

Reusable code belongs in `common`.

Configuration belongs in `config`.

Documentation belongs in `docs`.

Tests belong in `tests`.

Generated artifacts belong in `logs` and `reports`.

---

# Human Approval Required

Always obtain approval before:

- Production deployments
- Infrastructure changes
- Authentication changes
- Secret management changes
- Git merges
- Destructive operations
- Jira writes
- Workflow transitions

---

# Current Milestone

The current milestone is to build Clarity's local command surface and email
review loop.

Scope:

- Answer deterministic local questions from Clarity memory
- Read approved email mailbox metadata
- Read approved Gmail inbox metadata
- Read approved calendar metadata
- Normalize and classify email metadata
- Generate local Markdown briefs
- Generate command-center and focus-plan answers
- Generate bounded, validated LLM summaries on explicit command
- Propose email folder moves from configured policy
- Execute approved email moves only through explicit provider commands
- LLMs may summarize and recommend review questions only
- No autonomous writes

---

# Success

Success is measured by building software that is:

- Secure
- Understandable
- Well documented
- Maintainable
- Local first
- Easy to extend
