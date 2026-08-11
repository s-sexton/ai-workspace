# RRE Guidelines

RRE means roles, responsibilities, and expectations.

Every role or agent should have an RRE when it is created or materially
enhanced. The RRE is the role's living job description and decision-rights
contract.

## When An RRE Is Required

Create or update an RRE when:

- A new role or agent is created.
- A role receives a new data source, communication surface, or scheduled task.
- A role receives new write capability.
- A role's decision rights change.
- A role's escalation rules change.
- A role starts handling a new personal, business, legal, compliance, financial,
  security, or family domain.
- A recurring behavior becomes a standing policy.

## Management Model

RREs should be guided by these market-based management-inspired dimensions:

- Vision: where the role can create the most long-term value.
- Values and capability: the principles, skills, and tool access needed for the
  role to be trusted.
- Knowledge processes: how the role gathers, stores, shares, applies, and audits
  information.
- Decision rights: what the role may decide or do without further approval.
- Incentives and feedback: how success, errors, learning, and behavior changes
  are measured.

Decision rights are the controlling dimension. If a decision or action is not
inside a documented decision right, escalation or human approval is required.

## Required Sections

Each RRE should include:

- Role
- Management model
- Primary outcomes
- Responsibilities
- Expectations
- Current work surfaces
- Current scheduled work, if any
- Decision rights
- Escalation rules
- Security and privacy
- Communication style
- Incentives and feedback
- Knowledge processes
- Open questions

## Decision Rights

Decision rights should be explicit and bounded.

Each RRE should separate:

- Standing decision rights: what the role may do without asking again.
- Conditional decision rights: what the role may do only when specific
  conditions are satisfied.
- Reserved human decision rights: what remains with the human unless a future
  RRE update grants a narrow right.

Decision rights should be assigned where the role has comparative advantage,
such as speed, consistency, memory, pattern recognition, or repetitive execution.
They should stay with the human where judgment, accountability, relationship
context, legal risk, financial commitment, or ambiguous tradeoffs matter more
than speed.

## Configuration Changes

Until the human operator changes this instruction, every role or agent
configuration change should reference the RRE dimensions.

When proposing or explaining a configuration change, answer:

- Vision: what value does this create?
- Values and capability: what principle, skill, or tool access does this depend
  on?
- Knowledge processes: what information will be gathered, stored, or audited?
- Decision rights: what decision right is granted, preserved, narrowed, or
  revoked?
- Incentives and feedback: what signal tells us whether this is working?

## Escalation

Escalate when:

- The requested action is outside documented decision rights.
- The request is ambiguous enough that a reasonable human might disagree.
- The action could delete, move, publish, send, transition, purchase, commit, or
  externally change state and no applicable approval exists.
- Identity, authentication, authorization, or source legitimacy is uncertain.
- Provider errors, stale manifests, missing memory, or conflicting instructions
  make the intended action uncertain.

An escalation should include the recommended action, the reason, the affected
source, and the minimum approval needed to proceed.

## File Naming

Store role RREs in `docs` using a clear role name:

- `docs/clarity-rre.md`
- `docs/<role-name>-rre.md`

If a top-level assistant directory has its own README, link the RRE from that
README and from the repository README when the role is user-facing.
