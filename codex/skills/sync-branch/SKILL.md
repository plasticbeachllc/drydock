---
name: sync-branch
description: Synchronize a current feature or topic branch with newer development from its mainline or downstream branch, such as main, master, trunk, or develop. Use when asked to sync, update, catch up, rebase, or merge a working branch with recent development while preserving local work and handling conflicts safely in Git or Jujutsu repositories.
---

# Sync Branch

Bring the latest development-line changes into the current working branch without losing local work or rewriting shared history unexpectedly.

## Workflow

1. Read the repository's active instructions and inspect its status before changing anything. Use the repository's required VCS; do not substitute Git history commands in a repo that requires `jj`.
2. Determine:
   - the current working branch, bookmark, or change;
   - the requested source branch, or the repository's default development branch when none was named;
   - its authoritative remote-tracking ref;
   - whether local edits, unresolved conflicts, detached state, or an in-progress operation make syncing unsafe.
3. Fetch remote state before integrating unless the user explicitly requested a local-only sync. Do not assume a local `main` or `master` is current.
4. Preview the incoming commits and report surprising scope, such as an unrelated history or a very large divergence, before integrating.
5. Choose the integration method from repository instructions and existing history:
   - Preserve an established merge-based workflow with a merge.
   - Use a rebase when the repository uses linear topic branches and the commits are local/private.
   - If either method is equally plausible and rebasing could rewrite published work, ask the user which history shape they want.
6. Integrate the fetched development ref into the current branch. Never force-push, discard changes, reset destructively, or rewrite a shared branch merely to complete the sync.
7. Resolve conflicts only when the intended result is supported by nearby code, tests, and repository guidance. Preserve meaningful changes from both sides. If resolution requires a product decision, stop and explain the conflicting intents.
8. Verify that the working state is conflict-free, inspect the resulting history/diff, and run focused checks for conflict-touched areas. Run the repository's required validation when practical.
9. Summarize the source ref and fetched revision, integration method, conflicts and resolutions, validation, and whether any push remains. Do not push unless the user requested it.

## VCS Guidance

For Git, inspect with read-only commands such as `git status`, `git branch --show-current`, `git remote -v`, and `git log`; fetch the selected remote; then merge its remote-tracking ref or rebase the current private branch onto it.

For Jujutsu, inspect with commands such as `jj status`, `jj log`, `jj bookmark list`, and `jj git remote list`; fetch with `jj git fetch`; then use the repository's preferred `jj rebase` or merge workflow. Refer to the fetched remote bookmark explicitly when a local bookmark may be stale. Remember that a colocated repository can expose Git internals without authorizing Git history operations.

## Safety Rules

- Keep pre-existing uncommitted work intact. If the selected VCS cannot safely integrate around it, pause and state what must be committed, described, or otherwise protected.
- Treat `main`, `master`, `trunk`, and `develop` as candidates, not interchangeable facts. Confirm the actual development line from repository configuration, remote default, history, or user direction.
- Never resolve conflicts wholesale with “ours” or “theirs” unless the user explicitly wants one side discarded.
- Never use destructive cleanup commands to make the status look clean.
- Separate syncing from publishing. A successful local integration does not imply permission to push.
