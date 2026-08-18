# Agent Response: Plan

I read AGENTS.md and inspected the repository.
No files were modified.
The worktree is clean and currently contains only the
initial scaffold.

One configuration gap exists:
.python-version is missing, although
pyproject.toml and the setup documentation specify Python 3.14.
I propose adding .python-version with 3.14.

## Proposed architecture

A deterministic CLI application with four layers:

CLI
├── collect
│ ├── GitHub read-only API client
│ └── SQLite historical store
└── report
├── deterministic calculations
└── Markdown and JSON output

### GitHub collection

Use GitHub’s REST API with token authentication from GITHUB_TOKEN.
All requests will be GET; the application will contain no cloning or
mutation operations.

Repository discovery will default to repositories owned by the
authenticated user. CLI owner/repository filters will make runs
reproducible and allow later expansion to organization repositories.

For each repository, collect:

- Repository metadata:
  - owner, name, visibility, archived/fork status
  - default branch
  - creation, update, and last-push timestamps
  - stars, forks, watchers/subscribers, size, and open-issue count

- Activity:
  - recent commits on the default branch
  - issues
  - pull requests, including merged state
  - releases

- GitHub traffic:
  - daily clone counts and unique cloners
  - daily view counts and unique visitors
  - popular referrers
  - popular paths

Traffic access requires sufficient repository permissions. An
unavailable or forbidden traffic endpoint will be recorded as a
collection warning without discarding the rest of that repository’s
observation.

Collection will use pagination, bounded retries for transient
failures, rate-limit-aware errors, and an explicit configurable
activity lookback. Subsequent runs will use the last successful
observation plus a small overlap to avoid missing updates.

### Historical persistence

Use SQLite from Python’s standard library. It suits append-oriented
historical data, transactions, constraints, and later
classification/reporting without adding a database service.

The schema will separate:

- collection_runs: start/end time, status, parameters, API identity,
  warnings

- repositories: stable GitHub repository identity
- repository_observations: immutable metadata/counter snapshot per
  run

- commits, issues, pull_requests, and releases: GitHub entities
  keyed by stable external IDs

- activity observations for mutable entity state over time
- traffic_observations: daily views/clones as observed during each
  run

- popular_referrer_observations
- popular_path_observations
- schema version metadata

Overlapping traffic windows will not overwrite earlier readings.
Each API reading remains associated with its collection run,
preserving revisions GitHub may make to recent traffic data.

Writes will occur in explicit transactions. Failed runs remain
visible but will not become the baseline for incremental collection.

### Reporting

The report command will read only from SQLite and produce:

- A human-readable Markdown census
- A machine-readable JSON report

The report will include:

- latest repository inventory and metadata
- collection freshness and warnings
- recent commits, issues, pull requests, merges, and releases
- recent views, unique visitors, clones, and unique cloners
- top referrers and paths
- changes from the prior successful census
- data-availability indicators

The stored facts and report model will retain author identities,
timestamps, repository owner, and traffic dimensions needed for
later deterministic classification of maintainer activity versus
external use. Classification itself will not be added in this task.

## Proposed interface

Examples:

repo-census collect --database data/census.sqlite3
repo-census collect --owner denisecase --lookback-days 90
repo-census report --database data/census.sqlite3 --format markdown
repo-census report --database data/census.sqlite3 --format json

Secrets will only come from environment variables and will never be
written to the database, reports, logs, or configuration.

## Proposed implementation layout

.python-version
pyproject.toml
src/repo_census/
├── **init**.py
├── **main**.py
├── cli.py
├── github.py
├── models.py
├── persistence.py
├── collector.py
└── reporting.py
tests/
├── test_github.py
├── test_persistence.py
├── test_collector.py
├── test_reporting.py
└── test_cli.py
docs/
├── architecture.md
└── usage.md
README.md

I propose httpx as the sole runtime dependency for explicit,
testable HTTP behavior. CLI parsing, SQLite persistence, models,
calculations, Markdown, and JSON generation will use the standard
library.

## Testing plan

Tests will use mocked GitHub HTTP responses and temporary SQLite
databases. Coverage will include:

- pagination and authentication
- rate-limit and transient-error handling
- inaccessible traffic endpoints
- repository discovery and filtering
- initial and incremental activity collection
- transaction rollback and failed-run recording
- immutable historical observations across repeated collections
- overlapping traffic windows
- deterministic Markdown and JSON reports
- missing or partial data
- CLI argument and exit-code behavior

No test will call or modify a real monitored repository.

## Documentation plan

- Expand the README with setup and quick-start instructions.
- Add usage documentation covering token permissions, commands, data
  files, and traffic limitations.

- Add an architecture decision document explaining:
  - read-only REST API access
  - SQLite and append-oriented history
  - incremental activity collection
  - separation of collection, persistence, and reporting
  - preparation for later classification

No scheduler or repository-maintenance capability will be
introduced.

## Validation plan

After implementation:

uv python install
uv lock --upgrade
uv sync

uv run ruff check .
uv run ty check
uv run pytest

I’ll also inspect the final diff and report any unavailable tool or
environment issue explicitly. Implementation will begin only after
you approve this plan.
