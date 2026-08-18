# Repository Census Usage

## Authentication

Set `GITHUB_TOKEN` to a token authenticated as `denisecase`. The collector verifies the
authenticated login before creating a collection run. The token is sent only to GitHub and is
not stored in SQLite or reports.

Repository metadata, commits, and open pull requests require read access. GitHub's traffic
endpoints generally require push access. A repository remains in the census when traffic or
pull-request data is forbidden or otherwise unavailable; each request receives a separate
availability result.

## Collect

```powershell
uv run repo-census collect
uv run repo-census collect --database data/census.sqlite3 --lookback-days 365
uv run repo-census collect --owner denisecase --owner toy-gpt
uv run repo-census collect --owner denisecase --repo-pattern "datafun-*"
```

Without `--owner`, collection uses the complete explicit allowlist: `denisecase` and the 21
configured organizations. The option only selects from that allowlist; it cannot introduce an
unconfigured organization.

`--repo-pattern` applies a deterministic, case-sensitive shell-style pattern to repository names
after each owner has been discovered. It does not match owner/full-name strings. Omitting the
option preserves the full-census behavior and includes every visible repository for the selected
configured owners. Scoped runs retain the pattern in collection-run metadata so reports and the
historical database show that the inventory was intentionally filtered.

The initial commit query looks back 365 days by default. Later successful collections begin at
the previous successful collection with a one-day overlap, while still respecting the requested
maximum lookback. Commits are deduplicated by repository and SHA.

For every included repository, Version 2 also reads all pages of GitHub's pull-request endpoint
with `state=open`. This is strictly read-only: the application cannot approve, merge, close,
comment on, review, or otherwise modify a pull request. A failure for one repository is recorded
and collection continues with the remaining repositories.

Dependabot is identified only by case-insensitive exact GitHub author login
(`dependabot[bot]` or legacy `dependabot-preview[bot]`). The title is never used for
classification, and the actual author login is retained.

For Version 1, "maintainer activity" has a precise API-level meaning:

- GitHub's commits endpoint is queried with `author=denisecase`.
- The query is restricted to the repository's current default branch. Work that exists only on
  another branch is not included.
- `author` is GitHub's commit-author filter, not its committer filter. A commit authored by
  `denisecase` may count even when another identity committed it; merely committing or merging a
  commit authored by someone else does not make it a `denisecase` author commit.
- GitHub performs the author attribution. The collector does not independently require the
  returned `author.login` field to equal `denisecase`.
- GitHub may associate an author email with the account. Commits made with an email GitHub does
  not associate with `denisecase` may be absent.
- Reports place commits in the 30-, 90-, and 365-day windows using the commit's `committed_at`
  timestamp, not its authored timestamp.

These rules also apply to merge, squash, automated, and bot-created commits: inclusion depends on
the commit author identity GitHub returns for the `author=denisecase` query, not who clicked merge
or initiated an automation.

## Report

```powershell
uv run repo-census report --format markdown
uv run repo-census report --format json --output reports/census.json
```

Markdown and JSON are generated deterministically from SQLite. Reports group repositories by
owner and show maintainer commit counts over 30, 90, and 365 days, GitHub traffic, and detailed
open pull requests. A fleet-level open-PR summary appears near the top and includes only
repositories with observed open PRs. It orders repositories with Dependabot PRs first, then by
oldest open PR age descending, then by full repository name.

The latest completed collection is the report's implicit selected run. Metadata, traffic, and
pull-request observations are read only from that run. An earlier open PR is not carried into a
later report when it is absent from that run's successful response.

GitHub returns both an aggregate unique count and unique counts for individual days. These are
not additive: one person may appear on multiple days. The census stores both forms and reports
GitHub's aggregate value. It never produces a multi-day unique count by summing daily uniques.
Views and clones show continuing traffic, but GitHub does not say whether it came from external
users or the maintainer. Treat these values as evidence of continuing external use, not proof.

## Collection Statuses

- `successful`: owner and commit collection completed without execution errors. Forbidden or
  unavailable traffic was recorded normally.
- `partial`: collection continued after an owner/commit error or a traffic `error` result.
- `failed`: an unexpected error stopped a run after authentication and run creation.
- `forbidden`: GitHub returned HTTP 403 for one traffic endpoint.
- `unavailable`: GitHub returned HTTP 404 or 422 for one traffic endpoint.
- `error`: another transport, HTTP, or response-processing failure affected a traffic endpoint.

For pull requests, `available` plus a stored count distinguishes a successful zero result from
one or more open PRs. `forbidden`, `unavailable`, and `error` mean the PR inventory could not be
collected and make the run partial; they never appear as zero.

Authentication and identity verification happen before run creation, so authentication failures
do not create collection-run records.

## Limitations

- GitHub traffic covers a rolling window, currently limited by GitHub rather than this project.
- Private repositories and traffic are visible only when allowed by the token.
- The commits API associates commits with the requested GitHub author identity. Unlinked commit
  email identities may not be attributed to `denisecase`.
- Version 2 collects only open pull requests. It does not collect issues, closed pull requests,
  reviews, comments, workflows, security alerts, releases, popular paths, or popular referrers,
  and it does not classify repository maintenance health.
