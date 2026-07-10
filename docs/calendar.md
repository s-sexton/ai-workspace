# Calendar

## Current Milestone

Calendar support starts as local, read-only metadata wiring.

The current implementation:

-   Uses a fake local calendar transport by default
-   Normalizes event metadata into a small shared model
-   Stores event metadata and hashes in local Clarity memory
-   Surfaces calendar items in the command center
-   Does not call Google Calendar, Outlook Calendar, or Microsoft Graph calendar
    APIs
-   Does not create, update, delete, or respond to calendar events

## Shared Boundary

`common.calendar` owns the reusable calendar metadata boundary:

-   `CalendarClient`
-   `CalendarTransport`
-   `CalendarEvent`
-   `CalendarReadResult`
-   `StaticCalendarTransport`

Assistant workflows consume normalized `CalendarEvent` objects. They should not
parse provider-specific payloads directly.

## Local Review Command

To run the first local sample calendar review:

``` powershell
python -m assistant.src.run_calendar_review --calendar family --date 2026-07-10
```

This writes calendar metadata to local Clarity memory and regenerates
`reports/clarity-brief.md`.

To ask from remembered calendar metadata:

``` powershell
python -m assistant.src.clarity "What is on my family calendar today?"
python -m assistant.src.ask_memory calendar-items
```

## Memory Rules

Calendar memory stores:

-   Calendar label
-   Event ID
-   Event title
-   Start and end time
-   Location when available
-   Organizer when available
-   Content hash
-   Classification reason

Calendar memory does not store attachments or provider tokens.

## Live Calendar Step

Before live Google Calendar or Outlook Calendar access is added, create a
separate design proposal covering:

-   Approved calendars
-   Read-only versus write scopes
-   Authentication and token storage
-   Event content boundaries
-   Audit behavior
-   Failure handling
-   Human approval requirements
