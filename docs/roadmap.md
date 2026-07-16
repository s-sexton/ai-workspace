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
- Read approved Gmail inbox metadata
- Normalize Microsoft Graph-shaped email payloads
- Apply allowed-sender and authentication checks
- Classify messages as review, noise, or trash
- Propose folder moves from configured policy
- Create approved Clarity folders on explicit command
- Execute approved email moves only through explicit Graph commands
- Execute approved Gmail archive/trash actions only through explicit commands
- Keep all moves scoped to the source mailbox
- Learn future review/noise email classification from local human feedback
- Learn from sanitized subject/preview content terms without storing raw bodies
- Apply mailbox-specific sender/domain preferences
- Review and remove mailbox-specific sender/domain preferences
- Review proposed and approved cleanup before executing Gmail filing
- Summarize Gmail filing dry-runs and executions by count, mailbox, and destination
- Surface email cleanup status in the daily command center
- Bulk-approve matching pending email move suggestions in local memory
- Review and approve mailbox cleanup suggestions in bounded batches
- Summarize cleanup approval batches by sender and domain

Next useful slices:

- Add command-center filtering for "today" views
- Add cleanup batch summaries by learned preference matches

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
- Copy-ready local commands for feedback, approvals, and filing dry-runs
- Compact remembered calendar agenda with source, start/end, and location
- Date-aware calendar questions for today, tomorrow, and explicit ISO dates
- Source-aware calendar questions for family, work, and personal calendars
- Explicit read-only calendar refresh before answering calendar questions
- Combined email and calendar refresh in scheduled-friendly Clarity cycles
- Schedule-printer support for optional calendar refresh flags
- Email-ready daily brief generation with Outlook attention, calendar, Jira,
  pending approval counts, and reply guidance
- Explicit-only Microsoft Graph daily brief send command with dry-run preview
- Daily brief JSON manifest for stable reply item resolution
- Deterministic local daily brief reply command processor
- Graph-backed daily brief reply poller with allowed-sender/auth checks and
  duplicate skipping
- Windows schedule-printer support for daily brief send and reply poll
  workflows

## Phase 4: Calendar Awareness

Status: read-only Graph and Google wiring started.

Calendar support begins as read-only metadata:

- Read sample, approved Microsoft Graph, or approved Google Calendar event
  metadata
- Store event title, source, start/end, location, organizer, and hash
- Surface calendar items in the command center as a compact remembered agenda
- Filter remembered calendar items by simple requested date
- Filter remembered calendar items by simple requested source
- Refresh approved read-only calendar metadata before answering when requested
- Avoid creating, updating, deleting, or responding to calendar events

Live calendar providers require a separate design and approval before use.

## Phase 5: LLM Summarization

Status: live provider wiring started behind explicit commands.

The LLM may summarize only bounded local context. It may not approve, execute,
send, move, delete, or modify anything.

Current implementation:

- `ask_memory llm-context`
- `ask_memory llm-prompt`
- fake deterministic LLM brief generation
- live OpenAI LLM brief generation through the Responses API
- optional LLM brief generation after a Clarity cycle
- Codex-ready handoff generation for ChatGPT/Codex Pro summarization without API
  credits
- local output validation

Next useful slices:

- Add LLM-backed answers for selected local questions without granting tool
  execution authority
- Add eval fixtures for brief quality and safety boundaries
- Add per-run prompt/report artifact links in the command center

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
- Scheduled email-ready daily brief generation
- Approved email filing inside configured Clarity folders
- Local audit history

Actions that send messages, write Jira, change calendars, alter permissions, or
make commitments require explicit human approval unless a future narrow policy
is designed and approved.

## Phase 8: Daily Email And Reply Loop

Status: started with local brief generation.

Clarity should eventually send a scheduled "Day in a Glance" email and process
authenticated replies from approved senders. This work should proceed in small
slices:

- Generate the daily brief locally without sending
- Add a bounded Graph `sendMail` transport for `clarity@sendthisfile.ai`
- Send only to configured recipients on explicit command
- Read replies from the Clarity mailbox
- Require allowed sender and SPF/DKIM/DMARC checks before interpreting replies
- Parse deterministic reply commands into local actions
- Keep destructive or external writes behind approval unless a narrow standing
  policy is explicitly approved
