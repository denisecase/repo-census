# AGENTS.md

## Purpose

These are standing instructions for Codex and
other coding agents working in this repository.

## Project Rules

- Use `uv` for Python environment and dependency management.
- Target the version of Python listed in .python-version.
- Use a `src/` project layout.
- Prefer deterministic Python code over LLM reasoning
  for collection, calculation, classification, and reporting.
- Do not clone repositories being measured.
- Do not modify repositories being measured.
- Preserve historical census observations rather than replacing prior records.
- Keep external side effects explicit and limited.
- Add or update tests for implemented behavior.
- Keep implementation readable and maintainable.
- Document important architectural decisions.

## Validation

Before finishing a coding task,
keep the dependencies updated and
run the project's available validation commands.

Expected update and validation will include:

```shell
uv python install
uv lock --upgrade
uv sync

uv run ruff check .
uv run ty check
uv run pytest
```

If a required validation tool is not yet configured,
report that clearly rather than inventing a substitute.

## Scope

This repository may read metadata and
traffic information from GitHub.

It must not write to, clone, or
otherwise modify monitored repositories
unless a future task explicitly changes that policy.
