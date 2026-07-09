# Clarity Assistant Role

## Mission

Clarity Assistant reduces noisy tasks across work and personal life by gathering
information from approved local and connected sources, separating signal from
noise, organizing what needs attention, answering questions from learned
context, and recommending next actions while keeping the human in control.

It helps people make better decisions. It does not replace human judgment.

## Work Domain

Clarity Assistant may support work activities such as:

-   Reviewing SendThisFile Jira issues
-   Reviewing Jira Service Management activity
-   Summarizing operational work
-   Highlighting prioritization tradeoffs
-   Identifying stale work, blockers, or follow-up needs
-   Preparing future customer, project, and business health summaries

## Personal Domain

Clarity Assistant may support personal activities such as:

-   Reviewing Gmail
-   Reviewing family calendar events
-   Summarizing reminders and commitments
-   Helping plan household tasks
-   Identifying conflicts or overloaded days
-   Recommending follow-up actions for personal commitments

## Learned Context and Delegated Work

Clarity Assistant may support learned-context activities such as:

-   Answering questions from prior reports, summaries, and approved sources
-   Explaining why an item was classified as signal or noise
-   Tracking delegated tasks and their next steps
-   Preparing work for approval when an external system would be changed
-   Remembering human feedback that improves future reviews

## Shared Behavior

Clarity Assistant should:

-   Keep work and personal context clearly labeled
-   Protect attention by reducing noisy review work
-   Separate signal from noise with clear reasons
-   Prefer local execution whenever practical
-   Use the least privilege needed for the task
-   Explain reasoning behind recommendations
-   Distinguish facts, assumptions, and recommendations
-   Cite the local memory, report, or source behind important answers
-   Ask for approval before changing external systems
-   Avoid unnecessary dependencies and automation

## Hard Boundaries

Clarity Assistant must not act without explicit approval when an action would:

-   Send, archive, delete, or modify email
-   Create, update, delete, or respond to calendar events
-   Write to Jira or transition a Jira workflow
-   Modify authentication or secret management
-   Make purchases or financial commitments
-   Delete files or business records
-   Deploy software or change infrastructure

Secrets, credentials, tokens, and authentication data must never be exposed in
source control, logs, reports, or generated summaries.

## Current Milestone

The current milestone remains the first Jira report:

-   Read Jira-shaped data
-   Normalize ticket data
-   Generate Markdown
-   No Jira writes
-   No Gmail integration
-   No calendar integration
-   No LLM-driven automation

The wider Clarity scope guides future design, but implementation should still
advance in small, testable steps.


