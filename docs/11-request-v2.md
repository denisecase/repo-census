# Request: Version 2 Pull Request Census

Extend Repository Census with one new capability:

> Identify repositories with open pull requests that may require maintenance attention.

Keep Version 2 narrowly focused on **open pull requests**.

## Requirements

For every repository included in a census run, collect all open pull requests.

For each open pull request, preserve enough information to report:

- repository owner
- repository name
- pull request number
- pull request title
- pull request author login
- pull request URL
- created timestamp
- updated timestamp
- draft status
- whether the pull request was created by Dependabot
- collection run / observation metadata needed to preserve historical census semantics

Use the GitHub pull-request API.

Collection must remain read-only.

Do not modify, approve, merge, close, comment on,
or otherwise interact with pull requests.

## Dependabot

Dependabot pull requests are particularly important for repository maintenance.

Identify Dependabot pull requests deterministically from the GitHub author identity.

Do not infer Dependabot status from the pull request title.

Preserve the actual author login in addition to the derived Dependabot indicator.

## Historical Semantics

Preserve the existing historical census model.

A report for a particular completed census run must show
the open pull requests observed during that run.

Do not silently carry open pull requests forward from another run.

A pull request that was open in an earlier census but is absent from
a later completed census should no longer appear as open in the later report.

Do not overwrite or destroy earlier census observations.

Existing Version 1 census history must remain readable.

If a schema migration is required, make it non-destructive.

## Collection Failure

Failure to collect pull requests for one repository must not abort
collection for the remaining repositories.

Record pull-request collection availability/status sufficiently
to distinguish:

- successfully collected with zero open pull requests
- successfully collected with one or more open pull requests
- forbidden
- unavailable
- error

Do not confuse "collection failed" with "zero open pull requests."

## Reporting

Extend both Markdown and JSON reports.

Keep repositories organized by owner as they are now.

For each repository, report at minimum:

- total open pull requests
- number of open Dependabot pull requests
- age of the oldest open pull request, when any exist

Also provide enough detail to identify and visit each open pull request:

- PR number
- title
- author
- URL
- created date
- draft status
- Dependabot indicator

Make repositories with open pull requests easy to identify in the
human-readable report.

Do not create an overall maintenance-health score or classification.

The report should expose facts, not decide what action I should take.

## Tests

Add tests covering at least:

- repository with zero open pull requests
- repository with one open pull request
- repository with multiple open pull requests
- Dependabot pull request
- non-Dependabot automated pull request
- human-authored pull request
- draft pull request
- pull-request pagination
- oldest-open-PR calculation
- deterministic report ordering
- pull-request collection failure
- distinction between zero PRs and unavailable PR data
- historical observations across multiple census runs
- an earlier open PR disappearing from the latest completed run
- existing Version 1 database migration

No test may modify a real GitHub repository.

## Documentation

Update the architecture and usage documentation to describe
Version 2 pull-request collection and its read-only semantics.

Update the README to state that Repository Census can identify
open maintenance pull requests, with Dependabot pull requests
called out separately.

## Scope

Do not add:

- issue collection
- workflow or GitHub Actions health
- security alerts
- dependency updating
- automated pull-request handling
- pull-request merging
- pull-request review
- comments
- branch protection inspection
- repository conformance checking
- maintenance scoring

Do not modify monitored repositories.

Do not add any other functional capability.

## Review Gate

Before modifying files:

1. Read `AGENTS.md`.
2. Inspect the existing Version 1 architecture and historical model.
3. Propose the Version 2 architecture and schema changes.
4. Explain how open-PR observations will preserve the existing
   run-specific historical semantics.
5. Explain exactly how Dependabot PRs will be identified.
6. Describe the required migration, if any.
7. Present the testing plan.

Do not modify files until I approve the plan.
