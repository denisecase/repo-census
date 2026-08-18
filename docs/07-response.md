# Response: Check Summary

Overall assessment:
strong Version 1 foundation, but I recommend changes before
final acceptance.
No files were modified, and the worktree remains clean.

## PASS items

### 1. Scope compliance

- Collection is limited to repository metadata, denisecase commits, views, and
  clones.

- No issue, PR, release, referrer, or popular-path endpoints exist.
- No scheduling, classification, or maintenance automation was added.
- Reports remain factual rather than assigning activity/use labels.

### 2. Repository discovery

- denisecase repositories use authenticated /user/repos?affiliation=owner.
- Organization repositories use /orgs/{owner}/repos?type=all.
- The configured allowlist contains exactly the required 21 organizations.
- Arbitrary owners are rejected by both the CLI and GitHub client.
- No organization-membership discovery is performed.
- Repository permission role and individual permission flags are retained when
  GitHub supplies them.

See src/repo_census/constants.py:5 and src/repo_census/github.py:59.

### 3. Safety

- All GitHub calls use httpx.Client.get; no write methods exist.
- No clone command or Git library exists.
- There is no monitored-repository mutation capability.
- GITHUB_TOKEN is read from the environment and used only in the HTTP
  authorization header.

- The token is not included in persistence models, reports, or ordinary output.
- Local side effects are explicit: SQLite database creation and optional report-
  file output.

### 4. Historical traffic semantics

- Collection runs, owner results, repository observations, traffic responses, and
  daily traffic rows are retained.

- Repeated rolling-window observations create new records rather than replacing
  earlier records.

- GitHub’s returned aggregate count and aggregate unique count are stored
  separately from daily rows.

- Reports use aggregate_uniques; they do not sum daily uniques.
- Tests deliberately use daily uniques totaling 9 while GitHub’s aggregate is 7,
  confirming the distinction.

- This matches GitHub’s API structure, which provides aggregate totals plus a
  daily breakdown for the rolling traffic window.
  [GitHub traffic API documentation](https://docs.github.com/en/rest/metrics/traffic)

### 5. Inventory behavior

- Repository metadata rows in a report are constrained to the chosen—currently
  implicit latest—run.

- A repository absent from that run is not silently carried into its inventory.
- Failed owner discovery is exposed through owner collection warnings.
- A repository remains present when traffic is forbidden.

See src/repo_census/reporting.py:13.

### 6. Failure handling

- HTTP 409 from the commits endpoint is treated as an empty repository with zero
  commits.

- A recognized owner discovery failure produces an owner error and collection
  continues.

- Traffic 403 becomes forbidden; 404/422 becomes unavailable.
- Traffic transport and other HTTP failures become error data.
- Traffic errors mark the run partial; forbidden/unavailable traffic does not.
- Unexpected exceptions after a run starts mark it failed before being re-raised.
- Failed and partial runs are excluded as incremental baselines.

### 7. Reporting

- Repositories are sorted and headed by owner, then repository name.
- Commit thresholds are calculated relative to the report run’s completion time.
- Markdown labels traffic uniques as GitHub aggregates.
- JSON includes aggregate and daily traffic values.
- Run status, completion time, owner errors, repository observation time, and
  traffic observation time are available.

### 8. General project rules

- Python 3.14 and the src/ layout are used.
- Dependency management uses uv.
- Collection, calculation, persistence, and reporting are deterministic Python.
- SQLite persistence, architectural decisions, usage, and limitations are
  documented.

- The existing .python-version was not modified.

## CONCERNS

### 1. Historical report selection and stale traffic

This is the most important acceptance concern.

build_report() always selects the latest non-running run; the CLI has no --run-id
option. Therefore historical runs are auditable in SQLite but cannot actually be
selected through the supported report interface.

More importantly, repository inventory is restricted to that run, but
\_latest_traffic() selects the newest traffic result for the repository across all
runs:

WHERE repository_id=? AND kind=?
ORDER BY run_id DESC LIMIT 1

Normally every observed repository gets both traffic results. However, if a failed
run records repository metadata and then stops before one traffic call, the report
can combine:

- repository metadata from the failed run, and
- traffic from an earlier run.

Available traffic includes observed_at, so a careful reader can notice the older
timestamp, but it is not explicitly labeled stale and contains no traffic run ID.
This falls short of making stale data unambiguous.

### 2. Repository identity is not fully historical

repositories is updated in place for owner, name, full name, and URLs. Historical
repository_observations preserve status and timestamps but not these identity
fields.

After a rename or owner transfer, an older observation will join against the
current name/owner. Historical runs therefore do not fully preserve the identity
presentation that was observed at that time.

### 3. Exact maintainer-commit meaning

A qualifying commit is currently:

- reachable from the repository’s current default branch,
- returned by GitHub’s commits endpoint with author=denisecase,
- after the incremental since timestamp,
- and counted using its Git committer timestamp.

GitHub documents author as a GitHub username or email filter, distinct from
committer.
[GitHub commits API documentation](https://docs.github.com/en/rest/commits/commits)

Consequences:

- Commits authored with an email GitHub associates with denisecase should qualify.
- Commits using an unlinked or unverified author email may be omitted.
- Commits existing only on unmerged/non-default branches are omitted.
- A commit authored by denisecase but committed or merged by someone else can
  count.

- A merge performed by denisecase does not necessarily count if its commit author
  is someone else.

- Squash and merge commits depend on the author identity GitHub assigns to the
  resulting commit.

- Bot-authored commits do not count merely because denisecase initiated the
  workflow.

- The implementation trusts GitHub’s filtered response; it does not independently
  require returned author.login == "denisecase".

- Activity windows use committed_at, not authored_at. Rebases, cherry-picks, and
  delayed commits can therefore place activity in a different window than the
  original authoring work.

These semantics are defensible, but not documented precisely enough for
acceptance.

### 4. Traffic is only a proxy for external use

GitHub traffic does not distinguish maintainer traffic from external traffic.
Views and clones therefore indicate apparent continuing use, but cannot prove that
use is external. The report’s factual presentation is appropriate, but this
limitation should be explicit.

### 5. Run-status semantics need clarification

A run with forbidden or unavailable traffic can still be successful; only traffic
error, owner failure, or commit failure makes it partial.

That may be the correct design—“successful collection of an unavailable status”—
but documentation does not define the distinction. Also, architecture says “each
attempt creates a collection run,” while identity verification occurs before
start_run(). Authentication or identity failures leave no auditable run.

### 6. Failed runs are reportable by default

The latest non-running run can be failed, and it becomes the default report
source. The status is visible in the header, but this may expose only a partially
collected inventory. The desired behavior—latest completed run versus latest
successful/partial run—should be explicitly decided.

### 7. Test coverage is narrower than the approved plan

Important missing tests include:

- Exact 21-organization allowlist and full default traversal
- Pagination beyond 100 repositories or commits
- Private/public metadata parsing
- Persistence of all permission flags
- Initial versus incremental since calculation and one-day overlap
- 30-, 90-, and 365-day boundary cases
- days_since_last_commit
- Commit collection failure followed by continued repository/owner collection
- Owner failure followed by a later successful owner
- Traffic error causing a partial run
- Unexpected exception causing and persisting a failed run
- Views and clones having different availability states
- Reporting only the selected run’s inventory after deletion/disappearance
- Stale traffic behavior across failed runs
- Historical repository rename/owner-transfer semantics
- CLI owner restrictions, JSON output, and output-file handling
- Token non-persistence/non-output
- Deterministic report ordering with multiple owners/repositories

The approved plan explicitly promised pagination, incremental collection,
permission preservation, partial repository failures, owner grouping, and broader
CLI tests; those are not all covered.

### 8. Documentation discrepancies

README commands and basic usage match the application. Architecture and usage are
generally accurate, but should be corrected or expanded for:

- authentication failures not creating runs,
- exact successful/partial/failed semantics,
- lack of historical run selection,
- potential cross-run traffic fallback,
- mutable repository identity fields,
- precise author-versus-committer behavior,
- default-branch-only commit coverage,
- traffic being an imperfect proxy for external use.

## RECOMMENDED CHANGES

Before final acceptance, I recommend:

1. Add explicit report selection, such as --run-id, while retaining latest-run
   default behavior.

2. Restrict traffic lookup to the selected run. If fallback is intentionally
   supported, include source_run_id, age, and an explicit stale: true marker in
   JSON and Markdown.

3. Preserve observed repository owner/name/full-name/URLs in each repository
   observation.

4. Document and test the exact maintainer attribution rule, including the use of
   committed_at for time windows.

5. Decide whether to verify returned author.login, or explicitly trust GitHub’s
   author=denisecase filter.

6. Define successful, partial, failed, forbidden, and unavailable semantics.
7. Decide whether authentication failures should create auditable failed runs.
8. Add the missing tests listed above, prioritizing pagination, incremental
   boundaries, selected-run inventory, stale traffic, and failed-run behavior.

9. State explicitly that GitHub traffic suggests but does not prove external use.
10. Align the architecture and usage documentation with the final decisions.

## Validation

During this acceptance review, I ran non-mutating equivalents because you
prohibited file changes:

uv python install PASS — Python 3.14 already installed
uv lock --check PASS — 15 packages resolved
uv sync --locked PASS — 15 packages checked
uv run ruff check . PASS
uv run ty check PASS
uv run pytest PASS — 15 tests
git diff --check PASS
git status --short clean

During implementation, the exact required update workflow was also run:

uv python install
uv lock --upgrade
uv sync
uv run ruff check .
uv run ty check
uv run pytest

All passed; the final test run reported 15 passing tests.
