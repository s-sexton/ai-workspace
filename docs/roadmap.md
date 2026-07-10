# Clarity Roadmap

Clarity helps the human get organized and focused by gathering approved context,
separating signal from noise, recording local memory, and preparing safe next
steps.

The roadmap advances in small, testable slices. Each slice should preserve the
local-first security model and keep writes behind explicit approval.

## Phase 1: Foundation

Status: implemented.

- Read-only Jira reporting
- Local DuckDB memory
- Local feedback records
- Delegated task tracking
- Deterministic memory questions
- Local Markdown briefs

## Phase 2: Email Review And Filing

Status: in progress.

- Read approved mailbox metadata
- Normalize Microsoft Graph-shaped email payloads
- Apply allowed-sender and authentication checks
- Classify messages as review, noise, or trash
- Propose folder moves from configured policy
- Create approved Clarity folders on explicit command
- Execute approved email moves only through explicit Graph commands
- Keep all moves scoped to the source mailbox

## Phase 3: Daily Command Center

Status: in progress.

The command center is the default organizing surface. It should answer:

- What should I focus on?
- What needs approval?
- What email needs attention?
- What approved filing is ready?
- What delegated work is open?
- What is on the calendar?

Current implementation:

- `ask_memory focus-plan`
- `ask_memory command-center`
- `clarity "What should I focus on?"`
- `clarity "Give me my command center."`

## Phase 4: Calendar Awareness

Status: read-only Graph and Google wiring started.

Calendar support begins as read-only metadata:

- Read sample, approved Microsoft Graph, or approved Google Calendar event
  metadata
- Store event title, source, start/end, location, organizer, and hash
- Surface calendar items in the command center
- Avoid creating, updating, deleting, or responding to calendar events

Live calendar providers require a separate design and approval before use.

## Phase 5: LLM Summarization

Status: bounded local contract implemented, live provider not enabled.

The LLM may summarize only bounded local context. It may not approve, execute,
send, move, delete, or modify anything.

Current implementation:

- `ask_memory llm-context`
- `ask_memory llm-prompt`
- fake deterministic LLM brief generation
- local output validation

Next step is provider wiring through the existing `llm_summary` contract.

## Phase 6: Delegated Workflows

Status: started.

Clarity should track delegated work from request through outcome:

- Record tasks
- Track status and next step
- Include tasks in the focus plan
- Prepare drafts or recommendations for approval
- Cite local memory behind answers

Future work should add richer task history and reminders without changing
external systems unless approved.

## Phase 7: Controlled Autonomy

Status: future.

Unattended work is allowed only when explicitly designed, documented, tested,
and limited to approved scopes.

Likely first candidates:

- Scheduled read-only refresh
- Scheduled local brief generation
- Approved email filing inside configured Clarity folders
- Local audit history

Actions that send messages, write Jira, change calendars, alter permissions, or
make commitments require explicit human approval unless a future narrow policy
is designed and approved.
