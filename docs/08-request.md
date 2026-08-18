# Request for Modifications After Check

The acceptance review is good.
Make the following changes before Version 1 acceptance.

1. Reports must not silently combine observations from different runs.
   Repository metadata and traffic in a report must come from the
   report's selected run. Do not implement stale-data fallback in
   Version 1.

2. Preserve repository identity as observed historically.
   Repository observations must retain the owner, name, full name,
   and relevant URLs as they existed for that observation.

3. Keep the current GitHub `author=denisecase` attribution behavior.
   Do not add an independent `author.login` requirement.
   Document precisely what "maintainer activity" means, including:
   - GitHub author filtering,
   - default-branch-only coverage,
   - author versus committer semantics,
   - use of `committed_at` for the 30/90/365-day windows.

4. Explicitly document that GitHub views and clones are evidence of
   continuing repository traffic, but do not prove that the traffic
   came from external users rather than the maintainer.

5. Define successful, partial, failed, forbidden, and unavailable
   collection semantics in the documentation.

6. Expand tests for the approved Version 1 behavior, prioritizing:
   - exact configured owner/default traversal,
   - pagination,
   - incremental collection and overlap,
   - 30/90/365-day boundaries,
   - owner/repository failure continuation,
   - traffic error causing partial status,
   - selected-run inventory,
   - traffic constrained to the report run,
   - deterministic multi-owner/repository report ordering.

Do not add `--run-id` in Version 1.
Do not add stale-data fallback.
Do not create collection runs for authentication failures.

After making these changes, run the complete update and validation
workflow from AGENTS.md and provide a final acceptance summary.
