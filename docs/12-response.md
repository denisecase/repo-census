# Proposed Version 2 architecture

The existing separation remains intact:

- src/repo_census/models.py: add typed open-PR and collection-result models.
- src/repo_census/github.py: add one read-only paginated GitHub REST request:
  GET /repos/{owner}/{repo}/pulls?state=open&per_page=100&page=N

- src/repo_census/collector.py: collect PRs independently for every
  included repository and continue after repository-level failures.

- src/repo_census/persistence.py: add append-only, run-scoped PR results and observations.
- src/repo_census/reporting.py: report only PR observations belonging to the selected census run.
- CLI behavior remains unchanged; collect automatically includes open PRs
  and both report formats include them.

Only HTTP GET requests will be used.
No mutation endpoints or monitored-repository changes will be introduced.

## Proposed schema migration

Bump the schema version from 3 to 4 and add two tables.

pull_request_collection_results:

- id
- run_id
- repository_id
- observed_at
- status: available, forbidden, unavailable, or error
- open_count
- error
- unique constraint on (run_id, repository_id)

open_pull_request_observations:

- id
- pull_request_result_id
- repository_id
- owner_login
- repository_name
- number
- title
- author_login
- html_url
- created_at
- updated_at
- is_draft
- is_dependabot
- unique constraint on (pull_request_result_id, number)

The collection result distinguishes:

- available plus open_count = 0: successfully collected, no open PRs
- available plus a positive count: successfully collected with open PRs
- forbidden: HTTP 403
- unavailable: HTTP 404 or 422
- error: transport errors, other HTTP failures, or malformed responses

A non-available PR result will make the overall run partial,
because Version 2’s primary dataset is incomplete, but collection
will continue with all remaining repositories.

The migration will only create tables, indexes, and update the schema marker.
It will not alter or delete Version 1 observations.
Existing Version 1 runs will report PR status as not_collected,
with counts unavailable rather than falsely reporting zero.

## Historical semantics

Open status will be stored as a run-specific observation,
unlike the existing deduplicated commit facts.

For a report’s selected run:

collection run
  → repository observation for that run
    → PR collection result for that run
      → open PR observations returned during that request

There will be no fallback to another run.

Therefore:

- A PR observed open in run 10 remains preserved in run 10.
- If it is absent from run 11’s successful PR response, it does not appear in run 11.
- If run 11’s PR request fails, the report says the data is unavailable;
- it does not show zero and does not carry run 10’s PRs forward.

- Earlier observations are never overwritten or deleted.

Reports will retain the existing “latest completed run” selection behavior.

## Dependabot identification

Dependabot status will be derived exclusively from the GitHub API’s user.login value.

The deterministic rule will use case-insensitive exact matching against:

- dependabot[bot]
- dependabot-preview[bot] for historical legacy Dependabot PRs

No title, branch name, labels, or textual heuristics will be used.
The original author login will always be stored alongside the
derived Boolean.
A missing/deleted author identity will be preserved as null and will not be classified as Dependabot.

Other automated identities, such as Renovate bots or GitHub Actions bots, remain non-Dependabot.

## Reporting design

Each repository’s JSON object will gain an open_pull_requests section containing:

- collection status, observation timestamp, and error
- total open count
- Dependabot open count
- oldest open PR age in whole days
- ordered PR details

Each PR detail will include its number, title, author, URL,
creation/update timestamps, draft status, and Dependabot indicator.

Markdown will show a prominent repository-level line such as:

- Open pull requests: 3 total; 1 Dependabot; oldest: 47 days

Repositories with open PRs will also have an Open pull requests subsection
containing linked PR details.
Repository grouping and ordering by owner will remain unchanged.

PRs will use deterministic ordering by PR number ascending.
Oldest age will be calculated as nonnegative whole days between the
run completion timestamp and the earliest created_at value.

No score, recommendation, or maintenance classification will be added.

## Testing plan

Tests will use fakes, temporary SQLite databases, and httpx.MockTransport;
none will contact or modify a real GitHub repository.

Coverage will include:

- zero open PRs produces available, count zero, and no PR rows
- one open PR
- multiple open PRs
- exact dependabot[bot] recognition
- legacy dependabot-preview[bot] recognition
- non-Dependabot automated author
- human author
- missing author identity
- draft PR
- PR pagination beyond 100 results
- endpoint uses state=open
- oldest-open-PR calculation and boundary behavior
- deterministic owner, repository, and PR ordering
- 403, 404/422, transport, malformed-response, and other API failures
- one repository’s PR failure does not block later repositories
- zero PRs remains distinct from unavailable data
- PR collection failure makes the run partial
- multiple runs preserve separate PR observations
- an earlier open PR disappears from the later successful run
- a later failed request does not carry earlier PRs forward
- Markdown and JSON expose all required facts
- Version 1 database migration to schema 4
- Version 1 reports remain readable and show not_collected
- existing Version 1 behavior remains covered

Documentation changes will be limited to docs/architecture.md, docs/usage.md, and README.md.

If you approve this plan, I’ll implement it and run the full required uv update and validation sequence.
