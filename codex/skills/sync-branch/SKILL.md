---
name: sync-branch
description: Synchronize a current feature or topic branch with newer development from its mainline or downstream branch, such as main, master, trunk, or develop. Use when asked to sync, update, catch up, rebase, or merge a working branch with recent development while preserving local work, selecting a safe rebase or merge, and handling conflicts in Git or Jujutsu repositories.
---

# Sync Branch

Bring the latest development-line changes into the current working branch without losing local work or rewriting shared history unexpectedly.

## Workflow

1. Read the repository's active instructions and inspect the working state. Use the repository's required VCS; do not substitute Git history commands in a repo that requires `jj`.
2. Identify and state before changing anything:
   - the topic change or branch to move, including its bookmark when present;
   - the intended development line and authoritative remote-tracking ref;
   - the scope of the topic stack and of incoming work;
   - unresolved conflicts, a detached or ambiguous target, or another condition that makes integration unsafe.
3. Fetch the selected remote unless the user explicitly requests a local-only sync. Do not treat a local `main` or `master` as current without checking its remote-tracking counterpart.
4. Preview the incoming commits and report before integrating if the histories are unrelated, the divergence is unexpectedly large, or the destination is uncertain.
5. Select an integration method.

| Situation | Method |
| --- | --- |
| Private topic stack; linear history is customary | Rebase the topic stack onto the fetched development ref. |
| Existing branch history or repository convention retains integration commits | Create or preserve a merge. |
| Published topic branch and no documented convention | Ask whether rewriting it is acceptable before rebasing. |

6. Integrate only the intended topic stack into the fetched development ref. Do not force-push, discard changes, reset destructively, or rewrite shared work merely to complete the sync.
7. Resolve conflicts only when nearby code, tests, and repository guidance support the result. Preserve meaningful changes from both sides. Stop and explain when resolution requires a product decision.
8. Confirm the resulting history, diff, bookmark placement, and conflict-free state. Run focused checks for touched areas and the repository-required validation when practical.
9. Summarize the source ref and fetched revision, target scope, integration method, conflicts and resolutions, validation, and any remaining push. Do not push unless asked.

## Git Guidance

Inspect with read-only commands such as `git status`, `git branch --show-current`, `git remote -v`, and `git log`. Fetch the selected remote, preview both sides of the divergence, then merge the remote-tracking ref or rebase only a private topic branch onto it. Review `git status`, `git log`, and `git diff` after integrating.

## Jujutsu Guidance

Use Jujutsu exclusively for repository history when the repository requires it, even in a colocated repository.

1. Inspect with `jj status`, `jj log -r '@ | @-'`, `jj bookmark list`, and `jj git remote list`. Identify whether `@` is an empty working-copy change and whether the topic stack starts at `@` or `@-`.
2. Fetch with `jj git fetch --remote <remote>` and use the resulting remote bookmark explicitly, for example `main@origin`. Do not silently substitute the local `main` bookmark.
3. Preview each direction with revsets appropriate to the identified topic change: `<upstream>..<topic>` for topic-only work and `<topic>..<upstream>` for incoming work. Inspect the full graph when either result is surprising.
4. For a private, linear topic, use `jj rebase` with the identified topic root or bookmark as the source and the fetched remote bookmark as the destination. Include the whole topic stack; do not rebase only its tip when it has descendants.
5. For merge-preserving history, create a merge with the topic change and fetched remote change as parents, then ensure the topic bookmark points to the new merge change. Do not create an unbookmarked merge and assume the topic branch moved.
6. After integration, use `jj status`, `jj log`, and `jj diff` to verify the graph, content, and bookmark placement. Resolve all conflict markers before reporting success.

Use explicit change IDs when bookmarks resolve ambiguously. Remember that `@` is the working-copy change; after committing, committed content is normally at `@-`.

## Safety Rules

- Keep pre-existing uncommitted work intact. If the selected VCS cannot safely integrate around it, pause and state what must be committed, described, or otherwise protected.
- Treat `main`, `master`, `trunk`, and `develop` as candidates, not interchangeable facts. Confirm the actual development line from repository configuration, remote default, history, or user direction.
- Treat a topic bookmark, its change ID, and the working-copy change as distinct until inspection proves they coincide.
- Never resolve conflicts wholesale with “ours” or “theirs” unless the user explicitly wants one side discarded.
- Never use destructive cleanup commands to make the status look clean.
- Do not move, create, or delete bookmarks outside the requested topic without explicit user direction.
- Separate syncing from publishing. A successful local integration does not imply permission to push.
