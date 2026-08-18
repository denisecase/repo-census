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

## Report

```powershell
uv run repo-census report --format markdown
uv run repo-census report --format json --output reports/census.json
```

Markdown and JSON are generated deterministically from SQLite. Reports group repositories by
owner and show maintainer commit counts over 30, 90, and 365 days, along with GitHub traffic.

GitHub returns both an aggregate unique count and unique counts for individual days. These are
not additive: one person may appear on multiple days. The census stores both forms and reports
GitHub's aggregate value. It never produces a multi-day unique count by summing daily uniques.

## Limitations

- GitHub traffic covers a rolling window, currently limited by GitHub rather than this project.
- Private repositories and traffic are visible only when allowed by the token.
- The commits API associates commits with the requested GitHub author identity. Unlinked commit
  email identities may not be attributed to `denisecase`.
- Version 1 does not classify repositories or collect issues, pull requests, releases, popular
  paths, or popular referrers.
