# Create the GitHub Actions Census Token

Repository Census needs a GitHub credential that can read repository
metadata, commits, views, and clones across the configured repository owners.

For the scheduled GitHub Action, create a dedicated
**personal access token (classic)** and save it as a GitHub Actions secret.

GitHub recommends fine-grained tokens when possible, but a fine-grained
personal access token is associated with a single resource owner.
Repository Census spans the `denisecase` account and multiple separately
owned GitHub organizations, so a dedicated classic token is more practical
for this specific cross-owner census.

GitHub classic personal access tokens can access repositories in
organizations that the authenticated user can access, subject to each
organization's personal-access-token policy.

## 1. Create a Personal Access Token (Classic)

In GitHub:

1. Click your profile picture.
2. Select **Settings**.
3. Select **Developer settings**.
4. Select **Personal access tokens**.
5. Select **Tokens (classic)**.
6. Select **Generate new token**.
7. Select **Generate new token (classic)** if prompted.

Configure the token:

```text
Note:
repo-census GitHub Action

Expiration:
Choose an appropriate expiration date.
```

An expiration date is recommended so a forgotten credential does not
remain valid indefinitely.

## 2. Select the Required Scope

Select:

```text
repo
```

The `repo` scope allows the token to access repositories that the
`denisecase` account is authorized to access, including private
repositories.

Repository Census uses the credential only for read-only GitHub API
requests.
The application does not implement GitHub mutation operations.

**Do not select unrelated scopes.**

## 3. Generate and Copy the Token

Select **Generate token**.
Copy the generated token immediately.
GitHub will not show the complete token again.
Treat the token like a password.
Do not put it in any files or prompts or terminal commands.

## 4. Add the Token as a Repository Secret

Open the GitHub repository: `denisecase/repo-census`

In the repository, go to:
**Settings / Secrets and variables / Actions / New repository secret**
and create the secret (must not start with GITHUB):

```text
Name:
ACTIONS_CENSUS_TOKEN

Secret:
PASTE_THE_GENERATED_TOKEN_HERE
```

Select **Add secret**.

The workflow can now reference the credential as:

```yaml
${{ secrets.GITHUB_CENSUS_TOKEN }}
```

For example:

```yaml
env:
  GITHUB_TOKEN: ${{ secrets.GITHUB_CENSUS_TOKEN }}
```

This makes the existing Repository Census application see the secret
through the `GITHUB_TOKEN` environment variable without placing the
credential in source code.

## 5. Check Organization Token Policies

A classic personal access token can access organization repositories
only when the organization's personal-access-token policy permits it.

If Repository Census reports `forbidden` or cannot see repositories for
one of the configured organizations, check that organization's settings:

```text
Organization
/ Settings
/ Personal access tokens
/ Settings
/ Tokens (classic)
```

Confirm that classic personal access tokens are allowed for that
organization.

Do not broaden the token with additional scopes merely to resolve an
organization policy restriction.

## 6. Test the GitHub Action Manually First

The Repository Census workflow should include:

```yaml
on:
  workflow_dispatch:
```

After the workflow and secret are configured:

1. Open the `repo-census` repository on GitHub.
2. Select **Actions**.
3. Select **Repository Census**.
4. Select **Run workflow**.
5. Run it manually.

Verify that the workflow:

- authenticates as `denisecase`,
- discovers the configured owners,
- collects repository activity,
- collects views and clones where available,
- preserves the census database,
- generates the census report,
- and commits only the intended census artifacts.

Only after the manual workflow succeeds should the scheduled execution
be relied upon.

## Security Model

Two different GitHub credentials are involved in the workflow:

```text
GITHUB_CENSUS_TOKEN
    ↓
read monitored repositories
    ↓
GitHub REST API
```

and:

```text
GitHub Actions GITHUB_TOKEN
    ↓
write generated census artifacts
    ↓
repo-census repository only
```

Keep these responsibilities separate.

`GITHUB_CENSUS_TOKEN` is the census credential.

The workflow's built-in `GITHUB_TOKEN`, with explicitly configured
`contents: write` permission, is used only to commit the updated census
database and report back to `repo-census`.
