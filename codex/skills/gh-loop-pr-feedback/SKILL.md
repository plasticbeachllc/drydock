---
name: gh-loop-pr-feedback
description: Loop on automated GitHub pull request feedback by monitoring bot review threads and GitHub Actions, implementing clear low-risk fixes, validating, committing, pushing, and repeating until the PR is green and quiet or a stop condition is reached. Use when the user asks Codex to keep iterating on a pull request, address recurring bot feedback, shepherd a PR through automated review, or continue fixing CI and automated reviewer feedback without approval after every cycle.
---

# Loop on Automated PR Feedback

Run a bounded feedback loop against one existing GitHub pull request. Treat invocation as standing approval for the scoped local edits, validation, commits, and pushes described below; retain the stop conditions and GitHub write boundaries.

## Defaults

- Resolve the PR from an explicit URL or number, then from the current branch or bookmark.
- Limit the run to five fix-and-push cycles or 30 minutes unless the user specifies another bound.
- Declare the PR quiet only after two clean snapshots at least 60 seconds apart for the same head revision.
- Follow repository instructions and use its required VCS. Preserve unrelated working-copy changes.

## Establish the Baseline

1. Read the repository instructions and inspect the working-copy state, current branch or bookmark, remote, and VCS.
2. Confirm GitHub CLI authentication with `gh auth status`. Stop and request authentication if it fails.
3. Resolve the PR and record its URL, base, head branch, and head SHA. Verify that the local work belongs to that head before editing or pushing.
4. Record the initial checks and review-thread state. Keep every later observation tied to a head SHA so stale feedback does not drive new edits.
5. Report the PR and loop bounds before the first edit. Call out unrelated local changes or an unexpected branch mapping.

## Collect a Feedback Snapshot

Use the GitHub app for PR metadata and patch context when available. Use `gh` for thread-aware review state and Actions logs.

1. Fetch unresolved review threads with their resolution state, outdated state, file and line anchors, comments, and author types. Prefer the thread-aware workflow from `github:gh-address-comments` when available; otherwise query `reviewThreads` with `gh api graphql` and paginate.
2. Treat an author as automation when GitHub identifies it as a Bot, its login ends in `[bot]`, or the account is explicitly known to be automation. Never infer that an unfamiliar human account is a bot.
3. Ignore resolved, outdated, superseded, and duplicate threads. Keep human-authored requests visible but outside the automatic edit scope.
4. Inspect PR checks with the workflow from `github:gh-fix-ci` when available, or use `gh pr checks` and `gh run view` directly. Fetch GitHub Actions logs for failures on the current head.
5. Label non-GitHub Actions checks as external and report their links. Do not claim they are green when their status or logs cannot be inspected.
6. Separate pending work from failures. Do not change code merely because a check is still running, queued, skipped, or neutral.

## Triage One Cycle

Cluster current automated feedback by underlying behavior and classify each item:

- **Fix now:** Clear, reproducible, low-risk, related to the PR diff, and verifiable locally.
- **Wait:** Pending checks or automation that has not reported on the current head.
- **No code change:** Duplicate, stale, transient, unsupported, or demonstrably incorrect feedback. Preserve the rationale for the final report.
- **Stop:** Ambiguous or conflicting guidance; product, API, security, dependency-policy, or workflow-design decisions; failures unrelated to the PR; or changes that overlap unrelated local work.

Do not broaden the PR to satisfy speculative advice. Keep every edit traceable to a current automated thread or failing check.

## Fix, Validate, and Push

1. Implement all compatible **Fix now** items for the cycle as one coherent batch.
2. Inspect the resulting diff and run the most relevant local checks required by the repository. Do not push when validation fails; diagnose it within scope or stop with evidence.
3. Commit only the intended files with a concise message. Use Git or Jujutsu according to repository instructions and preserve the existing PR branch or bookmark.
4. Push normally to the existing PR head. Never force-push, create a replacement PR, or move an unrelated branch or bookmark without explicit authorization.
5. Resolve the PR again after pushing and verify that its head SHA matches the intended revision. Count the push as one loop cycle.

## Wait and Repeat

1. Wait for automation on the new head, using the product's monitoring or wait mechanism when available. Keep user-facing progress updates no more than 60 seconds apart during active work.
2. Resample checks and review threads against the current head. Restart the cycle when new actionable automated feedback appears.
3. Reset the quiet-window timer whenever a check changes state, a new automated comment arrives, or the PR head changes.
4. Stop if another actor changes the head unexpectedly; report the old and new SHAs rather than overwriting concurrent work.
5. Finish successfully only when the same head has no failing or pending GitHub Actions checks, no unresolved actionable automated threads, and two clean snapshots satisfy the quiet window.

## GitHub Write Boundaries

The loop authorizes scoped commits and normal pushes to the existing PR head. It does not authorize any of the following unless the user asks explicitly:

- Replying to, resolving, dismissing, or editing review threads or comments
- Submitting a review or approval
- Rerunning or canceling workflows
- Editing branch protection or repository settings
- Opening, merging, or closing a pull request
- Acting on human-authored review requests

Never expose credentials or paste sensitive log content into the final report.

## Stop and Report

Stop at the first safety condition or when either loop bound is reached. Report:

- The PR URL and final head SHA
- The number of fix-and-push cycles
- Automated feedback fixed, rejected with rationale, or still pending
- Commits or changes pushed and local validation run
- Final GitHub Actions and automated-thread state
- The exact success or stop condition and the next decision needed, if any
