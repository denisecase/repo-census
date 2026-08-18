# Repository Census Usage

## Authentication

Set `GITHUB_TOKEN` to a token authenticated as `denisecase`. The collector verifies the
authenticated login before creating a collection run. The token is sent only to GitHub and is
not stored in SQLite or reports.

Repository metadata and commits require read access. GitHub's traffic endpoints generally
require push access. A repository remains in the census when traffic is forbidden or otherwise
unavailable; views and clones each receive a separate availability result.

## Collect

```powershell
uv run repo-census collect
uv run repo-census collect --database data/census.sqlite3 --lookback-days 365
uv run repo-census collect --owner denisecase --owner toy-gpt
```

Without `--owner`, collection uses the complete explicit allowlist: `denisecase` and the 21
configured organizations. The option only selects from that allowlist; it cannot introduce an
unconfigured organization.

The initial commit query looks back 365 days by default. Later successful collections begin at
the previous successful collection with a one-day overlap, while still respecting the requested
maximum lookback. Commits are deduplicated by repository and SHA.

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
owner and show maintainer commit counts over 30, 90, and 365 days, along with GitHub traffic.
The latest completed collection is the report's implicit selected run. Metadata and traffic are
read only from that run. There is no earlier-run traffic fallback in Version 1.

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

Authentication and identity verification happen before run creation, so authentication failures
do not create collection-run records.

## Limitations

- GitHub traffic covers a rolling window, currently limited by GitHub rather than this project.
- Private repositories and traffic are visible only when allowed by the token.
- The commits API associates commits with the requested GitHub author identity. Unlinked commit
  email identities may not be attributed to `denisecase`.
- Version 1 does not classify repositories or collect issues, pull requests, releases, popular
  paths, or popular referrers.
