# Calendar

## Current Milestone

Calendar support starts as local, read-only metadata wiring.

The current implementation:

-   Uses a fake local calendar transport by default
-   Optionally reads approved calendar metadata from Microsoft Graph with
    `--graph`
-   Optionally reads approved calendar metadata from Google Calendar with
    `--google`
-   Requires the calendar to be listed in local approved calendar config
-   Normalizes event metadata into a small shared model
-   Stores event metadata and hashes in local Clarity memory
-   Surfaces calendar items in the command center
-   Does not call live calendar APIs unless `--graph` is explicitly passed
-   Does not create, update, delete, or respond to calendar events

## Shared Boundary

`common.calendar` owns the reusable calendar metadata boundary:

-   `CalendarClient`
-   `CalendarTransport`
-   `CalendarEvent`
-   `CalendarReadResult`
-   `StaticCalendarTransport`
-   `graph_event_to_calendar_payload`

Assistant workflows consume normalized `CalendarEvent` objects. They should not
parse provider-specific payloads directly.

`common.graph_calendar` contains the Microsoft Graph-specific runtime adapter:

-   `GraphCalendarReadTransport` lists event metadata from the Graph
    `calendarView` endpoint.
-   `build_graph_calendar_read_transport()` builds the transport from local
    Graph credentials.

The adapter is isolated from the assistant workflow so it can be tested with
fake transports before live Graph reads are used.

`common.google_calendar` contains the Google Calendar-specific runtime adapter:

-   `GoogleCalendarReadTransport` lists event metadata from the Google Calendar
    `events` endpoint.
-   `build_google_calendar_read_transport()` builds the transport from either a
    local refresh token or a direct access token.

## Local Review Command

To run the first local sample calendar review:

``` powershell
python -m assistant.src.run_calendar_review --calendar family --date 2026-07-10
```

This writes calendar metadata to local Clarity memory and regenerates
`reports/clarity-brief.md`.

To read an approved Graph calendar instead, configure `config/config.json` with
a calendar entry like:

``` json
{
  "assistant": {
    "calendar": {
      "approvedCalendars": [
        {
          "label": "work",
          "provider": "graph",
          "source": "scott.sexton@sendthisfile.com",
          "accessMode": "read"
        }
      ],
      "defaultCalendar": "work",
      "maxEvents": 25
    }
  }
}
```

Then run:

``` powershell
python -m assistant.src.run_calendar_review --calendar work --date 2026-07-10 --graph
```

Use `--graph-bearer` with `--graph` only when intentionally testing a local
`GRAPH_ACCESS_TOKEN`; otherwise the command uses app-only client credentials
from `GRAPH_TENANT_ID`, `GRAPH_CLIENT_ID`, and `GRAPH_CLIENT_SECRET`.

To read an approved Google Calendar instead, configure `config/config.json`
with a calendar entry like:

``` json
{
  "assistant": {
    "calendar": {
      "approvedCalendars": [
        {
          "label": "google-family",
          "provider": "google",
          "source": "your-family-calendar-id@group.calendar.google.com",
          "accessMode": "read"
        }
      ],
      "defaultCalendar": "google-family",
      "maxEvents": 25
    }
  }
}
```

Then run:

``` powershell
python -m assistant.src.run_calendar_review --calendar google-family --date 2026-07-10 --google
```

Use `--google-bearer` with `--google` only when intentionally testing a local
`GOOGLE_ACCESS_TOKEN`; otherwise the command uses refresh-token credentials
from `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, and `GOOGLE_REFRESH_TOKEN`.

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

## Future Calendar Step

Before Google Calendar access or calendar writes are added, create a separate
design proposal covering:

-   Approved calendars
-   Read-only versus write scopes
-   Authentication and token storage
-   Event content boundaries
-   Audit behavior
-   Failure handling
-   Human approval requirements
