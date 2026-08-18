# Response: Version 1 complete

Version 1 acceptance changes are complete.

## Implemented

- Reports now constrain repository metadata and traffic to the same latest completed run.
- No stale traffic fallback or --run-id option was added.
- Repository observations now snapshot owner, name, full name, HTML URL, and API URL.
- Existing databases migrate non-destructively to schema version 2.
- Authentication still occurs before collection-run creation.
- Maintainer activity remains based on GitHub’s author=denisecase filter,
  consistent with the
  [official commits API](https://docs.github.com/en/rest/commits/commits).

- Documentation now defines default-branch coverage, author/committer distinctions, committed_at windows, traffic limitations,
  and all collection statuses.

- Malformed traffic responses are recorded as errors rather than aborting unexpectedly.
- No out-of-scope collection was added.

Key changes:

- src/repo_census/persistence.py:35
- src/repo_census/reporting.py:24
- src/repo_census/github.py:88
- docs/architecture.md
- docs/usage.md

## Test expansion

The suite now has 27 passing tests, including:

- Exact 21-organization allowlist and complete default traversal
- Repository pagination
- Incremental collection with one-day overlap
- Owner and repository failure continuation
- Traffic errors producing partial runs
- 30/90/365-day boundaries
- Selected-run inventory
- No cross-run traffic fallback
- Historical repository identity
- Deterministic multi-owner/repository ordering
- Malformed traffic responses

## Validation

The complete required workflow passed:

uv python install PASS — Python 3.14 already installed
uv lock --upgrade PASS — 15 packages resolved
uv sync PASS — 15 packages checked
uv run ruff check . PASS
uv run ty check PASS
uv run pytest PASS — 27 tests
git diff --check PASS

docs/08-request.md remains untracked and was not modified as part of the implementation.
