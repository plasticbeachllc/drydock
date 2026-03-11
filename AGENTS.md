# Repository Instructions

Use this file as the repo-local working agreement for agents and automation.

## Priorities

- Keep `README.md` as the canonical documentation for the live workflow.
- Treat files under `docs/archive/` as historical context, not active guidance.
- Preserve the repo-owned symlink model driven by `setup.py`.
- Do not commit secrets, machine-local tokens, or generated state.

## Editing Rules

- Prefer minimal, targeted changes over wide rewrites.
- Keep bootstrap logic small; put durable provisioning behavior in `setup.py`.
- Add or update tests when changing `setup.py` behavior.
- Prefer Python stdlib in tests unless a dependency is clearly justified.

## Validation

- Run `python3 -m unittest discover -s tests -p 'test_*.py'` after test changes.
- Run `bash -n bootstrap.sh` after shell script changes.

## Version Control

- This repo uses `jj`; do not use `git` for repo history operations.
