# Architecture

## Version 1 Decision

The application uses a read-only GitHub REST client, an orchestration layer, append-oriented
SQLite persistence, and deterministic Markdown/JSON reporting. This separation keeps external
effects in the client and database boundary and makes later classification possible without
putting subjective reasoning in collection code.

## Collection Boundary

The configured owner set is deliberately closed: the authenticated owner `denisecase` and 21
named organizations in `constants.py`. The collector does not discover organization membership.
It calls the authenticated user's owned-repository endpoint and each allowlisted organization's
repository endpoint, retaining every repository visible to the token.

Only HTTP `GET` operations are implemented. The application has no clone, update, issue, pull
request, release, or repository-maintenance capability.

## Historical Model

After authentication succeeds, each attempt creates a collection run. Authentication failures
do not create runs. Owner results make partial discovery visible. Stable GitHub repository IDs
live separately from immutable per-run metadata observations. Each observation snapshots the
owner, name, full name, HTML/API URLs, status, permissions, and repository timestamps as they
existed in that run. Commits are immutable facts deduplicated by repository and SHA, with their
first observation retained.

Every traffic request creates a result containing its availability status and GitHub's returned
aggregate count and aggregate unique count. Daily observations belong to that result. A later
request creates another result even when its rolling dates overlap, so older readings are never
replaced. Forbidden traffic is recorded independently for views and clones.

SQLite was selected because transactions, constraints, and indexed historical queries are
available without an external service. The schema has an explicit version marker for future
migrations.

Reports use the latest completed run as their implicit selected run. Repository identity,
metadata, and traffic must all belong to that run. Missing traffic is reported as
`not_collected`; Version 1 never falls back to traffic from an earlier run. Repositories absent
from the selected run are absent from its inventory, while their historical observations remain
in SQLite.

## Collection Statuses

- `successful` means all configured owner and commit requests completed without execution errors.
  Traffic responses of `forbidden` or `unavailable` are successfully recorded outcomes and do
  not make the run partial.
- `partial` means collection continued after at least one owner or commit request error, or after
  a traffic request produced the `error` status.
- `failed` means an unexpected error stopped the run after it was created. Facts committed before
  that failure remain auditable.
- Traffic `forbidden` means GitHub returned HTTP 403, normally because the token lacks sufficient
  repository permission.
- Traffic `unavailable` means GitHub returned HTTP 404 or 422 for that traffic endpoint.
- Traffic `error` means transport, HTTP, or response processing failed for another reason.

## Reporting and Future Classification

Reports use stored commit timestamps to calculate recent maintainer activity. Continuing use is
represented by GitHub's traffic aggregates, daily values, availability, and observation time.
Daily unique values are retained for inspection but never summed into a multi-day unique value.
Views and clones demonstrate continuing repository traffic, but GitHub does not distinguish
external users from the maintainer; they are evidence of external use, not proof of it.

The JSON report exposes factual features for a later deterministic classifier. Version 1 does
not assign labels or thresholds.
