# Repository Census

[![Repo](https://img.shields.io/badge/repo-GitHub-black?logo=github)](https://github.com/denisecase/repo-census)
[![Python 3.14](https://img.shields.io/badge/python-3.14%2B-blue?logo=python)](./pyproject.toml)
[![uv](https://img.shields.io/badge/uv-managed-DE5FE9?logo=uv)](https://docs.astral.sh/uv/)
[![License](https://img.shields.io/badge/license-MIT-yellow.svg)](./LICENSE)

[![CI](https://github.com/denisecase/repo-census/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/denisecase/repo-census/actions/workflows/ci.yml)
[![Census](https://github.com/denisecase/repo-census/actions/workflows/census.yml/badge.svg?branch=main)](https://github.com/denisecase/repo-census/actions/workflows/census.yml)
[![Links](https://github.com/denisecase/repo-census/actions/workflows/links.yml/badge.svg?branch=main)](https://github.com/denisecase/repo-census/actions/workflows/links.yml)
[![Dependabot](https://img.shields.io/badge/Dependabot-enabled-brightgreen.svg)](https://github.com/denisecase/repo-census/security)

> Collect and preserve repository activity, traffic, and open pull-request data
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
- [1st Agent Response and Plan](docs/02-response-plan.md)
- [1st Review and Update](docs/03-review-update.md)
- [2nd Agent Response and Plan](docs/04-response-plan.md)
- [2nd Review and Update](docs/05-review-update.md)
- [3rd Request Post-Implementation Check](docs/06-request-post-impl-check.md)
- [3rd Response: Check Results](docs/07-response.md)
- [4th Request: Updates](docs/08-request.md)
- [4th Response: Version 1](docs/09-response-complete.md)
- [5th Request: Parameter match](docs/10-request-param-match.md)
- [6th Request: V2 active PRs](docs/11-request-v2.md)
- [6th Response: V2 draft](docs/12-response.md)
- [7th Request: V2 update](docs/13-request.md)

## Goal

Build a deterministic Python application that:

- uses the GitHub API,
- records repository activity and traffic statistics,
- preserves historical observations,
- does not clone the repositories being measured,
- generates a useful report,
- runs periodically with GitHub Actions.

Version 1 focuses on two questions:
how actively `denisecase` maintains each repository,
and whether GitHub traffic indicates continuing external use.
It collects maintainer commits,
views, visitors, clones, and cloners
without cloning or modifying any monitored repository.
Traffic is evidence that a repository continues to be used,
but GitHub does not identify whether
that traffic came from external users or from the maintainer.

Version 2 identifies repositories with open maintenance pull requests across the fleet. It calls
out Dependabot pull requests separately, preserves run-specific historical observations, and
reports factual PR details without scoring or taking maintenance action. Collection is strictly
read-only and never modifies a monitored repository or pull request.

## Quick Start

The application requires Python 3.14, `uv`, and a GitHub token authenticated as
`denisecase`.
The token needs repository read access.
GitHub traffic endpoints require repository Administration permission (read)
for fine-grained tokens.

```powershell
uv python install
uv sync
$env:GITHUB_TOKEN = "..."
uv run repo-census collect
uv run repo-census report --format markdown --output reports/full-census.md
```

The default database is `data/census.sqlite3`.
Collection covers repositories visible to the
authenticated user that are owned by `denisecase`
or an organization in the explicit project allowlist.
See [Usage](docs/usage.md) and [Architecture](docs/architecture.md).

## Codex Workflow

1. Read `docs/01-delegate-to-agent.md`.
2. Review `AGENTS.md`.
3. Review `PROMPT.md`.
4. Open this destination repository in Codex.
5. Copy the task from `PROMPT.md` into Codex.
6. Review the proposed plan before implementation.
7. Review the resulting changes before accepting them.

## Development

This project uses:

- `uv` for Python and dependency management,
- Ruff for linting and formatting,
- ty for static type checking,
- pytest for testing,
- pre-commit for local validation,
- GitHub Actions for continuous integration and scheduled census collection.

## Update Professional Project Scaffolding

```pwsh
uvx pup-up@latest --write `
  .annotations/annotations.md `
  .editorconfig `
  .gitattributes `
  .github/.yamllint.yml `
  .github/dependabot.yml `
  .github/lychee.toml `
  .github/workflows/links.yml `
  .gitignore `
  .markdownlint-cli2.yaml `
  AI_USE.md `
  LICENSE `
  .pre-commit-config.yaml `
  sit.ps1 `
  shape.ps1
```
