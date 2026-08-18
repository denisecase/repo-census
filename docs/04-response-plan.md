# Agent Response: Plan

No files have been modified. Here is the revised Version 1 plan.

## Version 1 scope

The census will answer only:

1. How actively does denisecase maintain each repository?
2. Does the repository appear to have continuing external use?

Issues, pull requests, releases, popular paths, and popular referrers are excluded.

## Repository discovery

The collector will authenticate with GITHUB_TOKEN and verify that the authenticated login
is denisecase. It will then discover every repository visible to that token for:

- The authenticated user denisecase
- All 21 listed organizations

Authenticated API endpoints will be used so private repositories are included when the
token permits access.

Repositories will be grouped by their actual owner. Each repository observation will
preserve GitHub’s permission information when provided, including fields such as admin,
maintain, push, triage, and pull, plus the effective role name when available.

Discovery failure for one organization will be recorded without discarding successfully
collected owners.

## Data collected

### Repository identity and metadata

- GitHub repository ID and node ID
- Owner ID, login, and owner type
- Repository name and full name
- HTML/API URL
- Visibility and private/public status
- Archived, disabled, and fork status
- Default branch
- Created, updated, and pushed timestamps
- Collection-time permission level
- Relevant collection status and error information

### Maintainer activity

Use the commits API with author=denisecase, restricted to the repository’s default branch.

For each matching commit:

- SHA
- GitHub author identity when available
- authored and committed timestamps
- repository and default branch
- collection run in which it was first observed

Reports will calculate deterministic activity measures such as:

- most recent maintainer commit
- commits in the last 30, 90, and 365 days
- days since the most recent maintainer commit

The initial collection will default to a 365-day lookback, configurable through the CLI.
Later collections will continue from the last successful collection with a small overlap to
avoid boundary misses. Commit SHAs will be deduplicated.

### External-use signals

Collect GitHub’s daily traffic series:

- views
- unique visitors
- clones
- unique cloners

GitHub exposes only a rolling traffic window, so every returned reading will be retained
with both:

- the traffic date
- the collection run and observation time

Repeated readings for the same traffic date will not overwrite older observations.

Views and clones will have independent availability states such as:

- available
- forbidden
- unavailable
- error

A traffic permission failure will never remove the repository from the census.

## SQLite persistence

The schema will contain:

- collection_runs
- owner_collection_results
- repositories
- repository_observations
- maintainer_commits
- traffic_collection_results
- traffic_observations
- schema_metadata

Repository observations and traffic readings will be append-oriented. Stable repository IDs
and commit SHAs will prevent accidental duplication while retaining when facts were
observed.

Failed or partial runs will remain auditable but will not become incremental-collection
baselines.

## CLI

The initial commands will be:

repo-census collect --database data/census.sqlite3
repo-census collect --lookback-days 365
repo-census report --database data/census.sqlite3 --format markdown
repo-census report --database data/census.sqlite3 --format json

The default owner set will be denisecase plus the supplied organizations. Optional owner
filters will support focused diagnostic runs without changing the default census
definition.

All GitHub operations will be authenticated, read-only GET requests. Tokens will not be
persisted or logged.

## Reports

Markdown and JSON reports will organize repositories first by owner and then by repository
name.

For each repository they will show:

- visibility, archived, and fork status
- latest relevant repository timestamps
- authenticated user’s permission level
- last maintainer commit
- maintainer commits over 30, 90, and 365 days
- latest available traffic window totals
- views, unique visitors, clones, and unique cloners
- traffic availability or failure reason
- census freshness

The report will present factual signals rather than assign activity/use classifications in
Version 1. Its structured output will make later deterministic classification
straightforward.

## Implementation and tests

The package will retain the previously approved separation:

src/repo_census/
├── **main**.py
├── cli.py
├── collector.py
├── github.py
├── models.py
├── persistence.py
└── reporting.py

Tests will cover:

- authenticated identity verification
- user and organization discovery
- pagination and owner grouping
- private and public repository metadata
- permission preservation
- maintainer-only commit filtering
- initial and incremental commit collection
- commit deduplication and overlap handling
- independent views/clones availability
- forbidden traffic access
- immutable overlapping traffic observations
- partial owner and repository failures
- deterministic Markdown and JSON reports
- CLI behavior and exit codes

Documentation will explain architecture, token permissions, data limitations, historical
semantics, and usage.

After implementation I will run the complete required uv update and validation workflow.
I’ll begin modifying files only after you approve this revised plan.
