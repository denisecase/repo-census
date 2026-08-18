# Request: Clarification on V2 Request

The architecture, schema, historical semantics, Dependabot identification,
failure handling, migration plan, and testing plan are approved.

Make one reporting change before implementation.

Version 2's purpose is to make repositories needing PR attention visible
across the fleet.
The full report contains hundreds of repositories, so
repository-level PR details alone are not sufficient.

Add a fleet-level "Open Pull Request Summary" near the top of the
Markdown report, before the owner/repository detail.

Include only repositories with one or more open pull requests.

For each repository show:

- owner/repository
- total open PRs
- open Dependabot PRs
- oldest open PR age

Make the repository name link to the repository or its pull-request page.

Use deterministic ordering. Prefer:

1. repositories with Dependabot PRs first,
2. then oldest open PR age descending,
3. then owner/repository name for deterministic ties.

Also provide equivalent fleet-level summary data in JSON.

Do not add scoring, recommendations, categories, or any other
maintenance capability.

The detailed per-repository reporting described in the plan should
remain.

Otherwise proceed with the proposed Version 2 architecture.
