# Create a GitHub Token for Repository Census

Repository Census uses a GitHub personal access token to make
authenticated, read-only requests to the GitHub API.

Do **not** put the token in `PROMPT.md`, `AGENTS.md`, the README,
source code, Git, or the Codex prompt.

## 1. Create a Fine-Grained GitHub Token

In GitHub:

1. Click your profile picture.
2. Select **Settings**.
3. Select **Developer settings**.
4. Select **Personal access tokens**.
5. Select **Fine-grained tokens**.
6. Select **Generate new token**.

For an initial census of repositories owned by `denisecase`,
configure the token:

```text
Token name:
repo-census

Expiration:
30 days

Resource owner:
denisecase

Repository access:
All repositories
```

Give the token the read-only repository permissions required
by Repository Census:

```text
Administration: Read-only
Contents: Read-only
Metadata: Read-only
```

GitHub traffic endpoints require read access to repository
administration information.
Do not grant write permissions.

Generate the token and copy it.
Treat the token as a password.

## 2. Exit Codex

The token should be set in the normal PowerShell terminal
that will launch Codex.

If Codex is currently running, exit Codex and return to PowerShell.

For example:

```text
PS C:\Repos\denisecase\repo-census>
```

## 3. Set the Token in PowerShell

In the normal PowerShell terminal, enter:

```powershell
$env:GITHUB_TOKEN = "PASTE_YOUR_TOKEN_HERE"
```

This sets `GITHUB_TOKEN` for the current PowerShell session.

Do not commit the token or save it in a project file.

Verify that the environment variable exists without displaying
the token:

```powershell
if ($env:GITHUB_TOKEN) { "GITHUB_TOKEN is set" }
```

Expected output:

```text
GITHUB_TOKEN is set
```

## 4. Launch Codex from the Same PowerShell Session

Make sure PowerShell is in the destination repository:

```powershell
cd C:\Repos\denisecase\repo-census
```

Then launch Codex:

```powershell
codex
```

Codex inherits `GITHUB_TOKEN` from the PowerShell process
that launched it.

Do not paste the GitHub token into the Codex prompt.

## 5. Ask Codex to Run the Live Smoke Test

At the Codex prompt, provide the task:

```text
Resume the live smoke test only.

Do not modify application code.

Run:

uv run repo-census collect --owner denisecase --repo-pattern "datafun-*"

Then run:

uv run repo-census report --format markdown --output reports/datafun-census.md

After the run, report:

- how many repositories matched,
- which repositories matched,
- whether collection completed successfully or partially,
- any GitHub permission or traffic warnings,
- the path to the generated report,
- and the local repository status.
```

## 6. Remove the Token from the PowerShell Session

When finished, close the PowerShell terminal.

Alternatively, remove the environment variable explicitly:

```powershell
Remove-Item Env:GITHUB_TOKEN
```

The token was set only for the current PowerShell process and
its child processes.
It was not permanently added to the project or system environment.
