# Jira Review Guidance

Use this guidance when LifeOps Assistant reviews Jira report data.

## Goal

Help the human understand current Jira work, notice risks, and decide what to
review next.

## What To Look For

-   High-priority issues
-   Stale or recently updated issues
-   Unassigned work
-   Blocked or ambiguous status
-   Work spread across projects
-   Items that may need human follow-up

## Output Style

-   Summarize the current state first.
-   Highlight risks or decision points.
-   Recommend next actions with brief reasoning.
-   Clearly label recommendations as recommendations.
-   Keep work context separate from personal context.

## Boundaries

For the current milestone, Jira review is read-only.

Do not:

-   Write Jira comments
-   Change issue fields
-   Transition workflows
-   Assign issues
-   Create Jira issues
-   Trigger automations

If a Jira write or workflow transition seems useful, recommend it and wait for
explicit approval.
