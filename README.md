# Repository Census

> Collect and preserve repository activity and traffic data
> for a fleet of GitHub repositories.

## Agentic AI Application

This repository is a **worked example** of delegating a bounded
software-engineering task to **Codex**.

Rather than pair-programming in chat,
I started with a core set of initial files and
delegated implementation of the code and project
to a generative AI agent (OpenAI Codex).

The process is described in:

- [Delegate Coding to an Agent](docs/01-delegate-to-agent.md)
- [First Agent Response and Plan](docs/02-response-plan.md)
- [First Review and Update](docs/03-review-update.md)
- [Second Agent Response and Plan](docs/04-response-plan.md)
- [Second Review and Update](docs/05-review-update.md)
- [Request Post-Implementation Check](docs/06-request-post-impl-check.md)
  
## Goal

Build a deterministic Python application that:

- uses the GitHub API,
- records repository activity and traffic statistics,
- preserves historical observations,
- does not clone the repositories being measured,
- generates a useful report,
- and can later be scheduled with GitHub Actions.

Version 1 focuses on two questions: how actively `denisecase` maintains each repository,
and whether GitHub traffic indicates continuing external use. It collects maintainer commits,
views, visitors, clones, and cloners without cloning or modifying any monitored repository.

## Quick Start

The application requires Python 3.14, `uv`, and a GitHub token authenticated as
`denisecase`. The token needs repository read access; GitHub traffic endpoints generally
require push access.

```powershell
uv python install
uv sync
$env:GITHUB_TOKEN = "..."
uv run repo-census collect
uv run repo-census report --format markdown
```

The default database is `data/census.sqlite3`. Collection covers repositories visible to the
authenticated user that are owned by `denisecase` or an organization in the explicit project
allowlist. See [Usage](docs/usage.md) and [Architecture](docs/architecture.md).

## Codex Workflow

1. Read `docs/01-delegate-to-agent.md`.
2. Review `AGENTS.md`.
3. Review `PROMPT.md`.
4. Open this destination repository in Codex.
5. Copy the task from `PROMPT.md` into Codex.
6. Review the proposed plan before implementation.
7. Review the resulting changes before accepting them.
