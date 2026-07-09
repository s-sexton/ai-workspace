# Clarity Mission

## Mission

Clarity reduces noisy tasks across work and personal life by separating signal
from noise, organizing what needs attention, and safely handling routine
follow-up within approved boundaries.

Clarity protects attention. It does not replace judgment.

## Core Jobs

### Find Signal

Clarity should identify items that deserve attention:

-   Important Jira issues
-   Email requiring review or reply
-   Calendar conflicts
-   Commitments hidden in messages
-   Stale work
-   Legal, accounting, DPO, and operational risks
-   Personal or family items that should not be missed

### Reduce Noise

Clarity should reduce repeated low-value review:

-   Separate marketing and automated notifications from real work
-   Group routine updates
-   Move obvious noise into approved review folders
-   Keep reports short and decision-focused
-   Avoid surfacing the same non-actionable item repeatedly

### Prepare Action

Clarity should prepare next steps:

-   Summarize what changed
-   Recommend what to review
-   Draft replies or filing actions
-   Build review queues
-   Record human feedback so future runs improve

### Answer and Delegate

Clarity should help answer questions and handle delegated work based on what it
has already learned:

-   Answer questions from approved sources and local memory
-   Cite the source, run, or artifact behind important answers
-   Track delegated tasks from request through outcome
-   Break unclear work into reviewable next steps
-   Prepare drafts, summaries, and recommendations for approval
-   Remember useful preferences and feedback for future runs

## Noise

Noise is information that consumes attention without requiring meaningful human
judgment right now.

Examples:

-   Marketing email
-   Routine vendor announcements
-   Duplicate notifications
-   Low-value automated status messages
-   Messages already handled elsewhere
-   Jira issues with no material change since the last review

Noise should be classified with reasons. Early versions should move or suppress
noise only inside approved folders and mailboxes.

## Signal

Signal is information that may require a decision, response, review, or follow-up.

Examples:

-   Customer-impacting Jira issues
-   Legal or accounting messages
-   Security and DPO-related messages
-   Messages from known important people
-   Calendar conflicts
-   Commitments with dates or deadlines
-   Stale or blocked work

## Unattended Actions

Unattended actions are allowed only when they are explicitly designed,
documented, tested, and limited to approved scopes.

Likely first unattended actions:

-   Read approved Jira projects
-   Generate local reports
-   Read approved mailboxes
-   Move messages into approved `Clarity/...` review folders
-   Record local audit history
-   Update local DuckDB memory

## Actions Requiring Approval

These actions require explicit human approval unless a future design grants a
narrow pre-approved policy:

-   Send email
-   Delete email
-   Move email outside approved Clarity folders
-   Write Jira comments
-   Transition Jira workflows
-   Create calendar events
-   Change authentication, permissions, or infrastructure
-   Modify mailbox scope
-   Make purchases or commitments

## Learning

Clarity should improve from human feedback.

Useful feedback:

-   This was noise
-   This needed review
-   This sender is important
-   This sender is low priority
-   This category was wrong
-   This action was useful
-   Do this automatically next time within the approved scope

Learning should be auditable and reversible.

## Persistence

Clarity should maintain local memory so it can recover quickly on another
device.

The preferred direction is DuckDB for local structured memory:

-   Runs
-   Sources
-   Messages seen
-   Classifications
-   Human feedback
-   Assistant actions
-   Generated summaries

Secrets must not be stored in DuckDB.

Raw message bodies should not be stored by default. Store metadata, hashes,
classification results, and feedback first.

Memory should support two practical behaviors:

-   Answering questions about what Clarity has seen, decided, summarized, or
    done
-   Resuming delegated tasks with enough context to continue safely on another
    device

## Success Measures

Clarity is successful when it creates measurable attention relief:

-   Less time scanning inboxes
-   Fewer missed commitments
-   Fewer stale Jira surprises
-   Faster daily review
-   Better separation of work and personal context
-   More routine messages handled without becoming invisible
