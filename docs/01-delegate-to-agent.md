# Delegate Coding to an Agent

This page describes the workflow for delegating implementation work to Codex.

## 1. Create Initial Destination Repository Locally

Create a local repository with these initial files:

```text
repo-census/
├── .github/workflows/ci.yml
├── .vscode/ (with settings.json and extensions.json)
├── docs/01-delegate-to-agent.md
├── src/repo_census/__init__.py
├── tests/__init__.py
├── .python-version
├── AGENTS.md
├── PROMPT.md
├── pyproject.toml
└── README.md
```

Review the human-facing files:

1. **README.md** - Tells the what and why of the project.
2. **AGENTS.md** - Provides standing instructions for
   Codex when working in this repository.
   Examples include the Python version, package manager,
   validation commands, architectural constraints, and forbidden actions.
3. **PROMPT.md** - Records the exact task prompt
   to copy and paste into Codex.
   Kept in the repository to document the delegation.

## 2. Create the GitHub Destination Repository & Sync

Create the repository in GitHub.
The destination repository contains the project context,
standing agent instructions, and the task prompt.
Set up the local repository and do the initial sync.

```shell
git init
git branch -M main
git remote add origin https://github.com/denisecase/repo-census.git

git add .
git commit -m "Initial project setup"
git push -u origin main
```

## 3. Verify the Initial Repository

Before delegating work to Codex,
verify the initial repository
and set up the environment.

```shell
git status

uv self update
uv python pin 3.14
uv python install
uv lock --upgrade
uv sync
```

Resolve any initial issues before asking Codex to implement the task.

## 4. Open the Destination Repository in Codex

Open Codex and select or open the local `repo-census` repository.
Codex should be working against the local destination repository.

## 5. Copy the Recorded Prompt

Open `PROMPT.md`.
Copy the task text and paste it into the Codex prompt box.
Submit the task.
The text in `PROMPT.md` is the canonical record of what was delegated.

## 6. Review the Proposed Plan (Review 1)

The prompt tells Codex to propose an architecture and
implementation plan before modifying files.

Review the plan.
If the plan is correct, approve it.
If it is not correct, give Codex corrections before implementation begins.

## 7. Let Codex Implement the Task

After approval,
Codex can create and modify the necessary
source files, tests, documentation, and configuration
within the destination repository.
Codex should follow `AGENTS.md` while doing the work.

## 8. Review the Implementation (Review 2)

When Codex finishes,
inspect the repository state and changes,
then run validation checks manually.

```shell
# review diffs
git status
git diff --stat
git diff

# if Codex worked on a separate branch
git branch --show-current
git log --oneline --decorate -5
git diff main...HEAD

# run checks
uv run ruff check .
uv run ty check
uv run pytest
```

Do a complete review:

1. Review the changed files.
2. Review the diff.
3. Review the architecture.
4. Confirm the requested requirements were implemented.
5. Confirm prohibited actions were not introduced.
6. Review test coverage.
7. Review validation results.

Do not treat passing tests as the **only approval criterion**.

## 9. Request Corrections in the Same Codex Thread

If changes are needed, continue the Codex conversation.
Examples:

```text
Change the persistence layer to use CSV rather than SQLite.
```

```text
Do not add another dependency for this capability.
```

```text
Add tests for repositories with missing traffic data.
```

```text
Run the complete validation suite and report the results.
```

Continue until the implementation is acceptable.

## 10. Accept the Work

When satisfied, commit and push the accepted changes,
or merge the reviewed Codex branch/PR
using the normal Git and GitHub workflow for the project.

```shell
git status

git add .
git commit -m "Codex contribution"
git push
```

## 11. Automate Only After the Workflow Is Stable

The first goal is to delegate implementation work successfully.
Later, once a recurring process becomes deterministic,
move routine execution into an ordinary script or GitHub Action.

A useful progression is:

```text
DELEGATE
    ↓
STANDARDIZE
    ↓
AUTOMATE
```

Use **Codex** where interpretation and engineering judgment are useful.
Use deterministic **Python and GitHub Actions** where the same inputs
should produce the same procedural response.
