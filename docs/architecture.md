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

Each attempt creates a collection run. Owner results make partial discovery visible. Stable
repository identity lives separately from immutable per-run metadata observations. Commits are
immutable facts deduplicated by repository and SHA, with their first observation retained.

Every traffic request creates a result containing its availability status and GitHub's returned
aggregate count and aggregate unique count. Daily observations belong to that result. A later
request creates another result even when its rolling dates overlap, so older readings are never
replaced. Forbidden traffic is recorded independently for views and clones.

SQLite was selected because transactions, constraints, and indexed historical queries are
available without an external service. The schema has an explicit version marker for future
migrations.

## Reporting and Future Classification

Reports use stored commit timestamps to calculate recent maintainer activity. Continuing use is
represented by GitHub's traffic aggregates, daily values, availability, and observation time.
Daily unique values are retained for inspection but never summed into a multi-day unique value.

The JSON report exposes factual features for a later deterministic classifier. Version 1 does
not assign labels or thresholds.
