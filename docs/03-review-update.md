# Review and Update after Plan

The overall architecture is approved with the following scope corrections.

1. Do not add `.python-version`. I already did, you were correct at 3.14.

2. Keep Version 1 focused on the original census question:
   - how actively I maintain each repository, and
   - whether the repository appears to have continuing external use.

For Version 1, collect only the information necessary to answer those
questions reliably.

Include:

- repository identity and basic metadata,
- archived/fork/visibility status,
- relevant repository timestamps,
- my commit activity,
- views and unique visitors,
- clones and unique cloners,
- enough collection metadata to preserve historical observations and
  identify unavailable traffic data.

Do not collect issues, pull requests, releases, popular paths, or
popular referrers in Version 1 unless you can justify that they are
necessary for those two questions.

SQLite, deterministic reporting, read-only GitHub access, historical
observations, Markdown/JSON reporting, tests, and the CLI architecture
are approved.

Please revise the plan to this narrower Version 1 scope before
implementation.

Repository discovery requirements:

- Start with all repositories owned by the authenticated user `denisecase`.
- Also collect repositories from the following GitHub organizations
  owned by `denisecase`:
  - `aauw-ely`
  - `adaptive-interfaces`
  - `analytics-toolworks`
  - `applied-models`
  - `civic-interconnect`
  - `composable-data`
  - `denisecase-org`
  - `ely-has-pride`
  - `ely-monday`
  - `elytc`
  - `genealogy-clusiau`
  - `genealogy-hall`
  - `genealogy-johnson`
  - `genealogy-kokkinen`
  - `humanity-lab`
  - `kapsch-genealogy`
  - `mn-area35-d08`
  - `pup-pack`
  - `structural-explainability`
  - `toy-gpt`
  - `wmnlp-materials`

- For each listed owner or organization, collect every repository
  visible to the authenticated user.
- Keep results organized by repository owner.
- Preserve the authenticated user's repository permission level when
  available.
- If repository traffic data cannot be read because of permissions,
  keep the repository in the census and record traffic availability
  as unavailable or forbidden rather than excluding the repository.
