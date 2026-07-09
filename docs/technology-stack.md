# Technology Stack

## Primary Language

Python is the primary implementation language.

Minimum supported version:

``` text
Python 3.12+
```

Python is used for:

-   API clients
-   Business logic
-   Data processing
-   Report generation
-   Future LLM integration
-   Testing

------------------------------------------------------------------------

## Runtime Environment

The workspace uses **Windows-native Python** as the default runtime.

PowerShell is the default shell for:

-   Local development
-   Codex App terminals
-   Workspace orchestration
-   Setup scripts
-   Windows automation

WSL is optional and should only be used when a task clearly benefits
from Linux tooling. It is **not** the default runtime for this project.

Rule:

``` text
Python = assistant logic
PowerShell = orchestration
WSL = optional
```

------------------------------------------------------------------------

## Package Management

The workspace uses **uv**.

Expected project files:

``` text
pyproject.toml
uv.lock
```

One Python environment is shared across the workspace.

------------------------------------------------------------------------

## Testing

The workspace uses **pytest**.

Every meaningful implementation should include new or updated tests
before it is considered complete.

------------------------------------------------------------------------

## Logging

Use the standard Python logging framework.

Logs are written locally and ignored by Git.

Logs must never contain secrets, API tokens, credentials, or
authentication data.

------------------------------------------------------------------------

## Setup Scripts

Workspace setup and prerequisite validation should be implemented using
PowerShell scripts under:

``` text
scripts/
```

The initial setup script will be:

``` text
scripts/setup.ps1
```

Responsibilities include verifying:

-   Python 3.12+
-   uv
-   Git
-   Required folder structure
-   Local configuration templates
-   Environment readiness
