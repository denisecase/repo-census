# Request Parameter Match

Add an optional repository-name filter for focused diagnostic collection.

Use a CLI option:

```text
--repo-pattern
```

It should support shell-style patterns such as:

```text
--repo-pattern "datafun-*"
```

Requirements:

- Apply the filter after repository discovery.
- Match repository names, not owner/full-name strings.
- Use deterministic standard-library pattern matching.
- Do not change the default behavior when the option is omitted.
- The default full census must still include all configured repositories.
- Record the filter in the collection run metadata so the historical database shows that the run was intentionally scoped.
- Add tests for matching, nonmatching, and omitted patterns.
- Update usage documentation.
- Do not modify the existing full-census semantics or owner allowlist.

Do not make any other functional changes.

After implementing the feature, run the complete project validation.

Then run a live smoke test against my `denisecase/datafun-*` repositories.

Use the existing `GITHUB_TOKEN` from the environment.

Run:

```shell
uv run repo-census collect --owner denisecase --repo-pattern "datafun-*"
```

Then run:

```shell
uv run repo-census report --format markdown --output reports/datafun-census.md
```

Do not modify monitored repositories.

After implementing and validating the requested `--repo-pattern` feature,
do not make further application-code changes during the live smoke test.

If the live commands fail because of an application defect,
stop and report the defect before making additional changes.

After the run, report:

- how many repositories matched,
- which repositories matched,
- whether collection completed successfully or partially,
- any GitHub permission or traffic warnings,
- the path to the generated report,
- and the validation/status of the local repo.
