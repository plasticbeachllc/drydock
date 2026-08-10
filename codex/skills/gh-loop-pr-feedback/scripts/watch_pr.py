#!/usr/bin/env python3
"""Watch PR feedback and checks, emitting compact NDJSON state changes."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import time
from typing import Any


QUERY = r"""
query($owner:String!,$name:String!,$number:Int!){
  repository(owner:$owner,name:$name){
    pullRequest(number:$number){
      number url state headRefName headRefOid headRepository{nameWithOwner}
      comments(last:100){pageInfo{hasPreviousPage} nodes{
        id body createdAt updatedAt url author{login __typename}
      }}
      reviews(last:100){pageInfo{hasPreviousPage} nodes{
        id body state submittedAt url author{login __typename} commit{oid}
      }}
      reviewThreads(first:100){pageInfo{hasNextPage} nodes{
        id isResolved isOutdated path line
        comments(last:100){pageInfo{hasPreviousPage} nodes{
          id body createdAt updatedAt url author{login __typename} commit{oid}
        }}
      }}
      commits(last:1){nodes{commit{
        oid committedDate
        statusCheckRollup{contexts(first:100){pageInfo{hasNextPage} nodes{
          __typename
          ... on CheckRun{name status conclusion detailsUrl}
          ... on StatusContext{context state targetUrl}
        }}}
      }}}
    }
  }
}
"""

PR_URL = re.compile(r"^https?://[^/]+/([^/]+)/([^/]+)/pull/(\d+)(?:/.*)?$")
PASS_BUCKETS = {"pass", "skipping"}


class WatchError(RuntimeError):
    pass


def gh_json(args: list[str], *, no_checks_ok: bool = False) -> Any:
    result = subprocess.run(
        ["gh", *args], capture_output=True, text=True, check=False
    )
    if result.returncode:
        message = result.stderr.strip() or result.stdout.strip()
        if no_checks_ok:
            try:
                return json.loads(result.stdout)
            except json.JSONDecodeError:
                if re.search(r"no (?:required )?checks reported", message, re.I):
                    return []
        raise WatchError(message or f"gh exited {result.returncode}")
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError as error:
        raise WatchError("gh returned invalid JSON") from error


def resolve_pr(selector: str | None, repo: str | None) -> tuple[str, int, str]:
    args = ["pr", "view"]
    if selector:
        args.append(selector)
    if repo:
        args.extend(["--repo", repo])
    args.extend(["--json", "number,url"])
    resolved = gh_json(args)
    url = resolved["url"]
    match = PR_URL.match(url)
    if not match:
        raise WatchError(f"cannot parse PR URL: {url}")
    owner, name, url_number = match.groups()
    number = int(resolved.get("number", url_number))
    return f"{owner}/{name}", number, url


def current_by_time(item: dict[str, Any], committed_at: str) -> bool:
    timestamp = item.get("updatedAt") or item.get("submittedAt") or item.get("createdAt")
    return bool(timestamp and timestamp >= committed_at)


def feedback_item(kind: str, item: dict[str, Any], **extra: Any) -> dict[str, Any]:
    author = item.get("author") or {}
    result = {
        "kind": kind,
        "id": item["id"],
        "author": author.get("login"),
        "author_type": author.get("__typename"),
        "url": item.get("url"),
        "body": item.get("body") or "",
    }
    result.update(extra)
    return result


def check_bucket(state: str | None) -> str:
    value = (state or "").upper()
    if value in {"SUCCESS", "NEUTRAL"}:
        return "pass"
    if value == "SKIPPED":
        return "skipping"
    if value in {
        "EXPECTED",
        "QUEUED",
        "PENDING",
        "IN_PROGRESS",
        "WAITING",
        "REQUESTED",
    }:
        return "pending"
    if value == "CANCELLED":
        return "cancel"
    return "fail"


def required_keys(repo: str, number: int) -> set[tuple[str, str]]:
    checks = gh_json(
        [
            "pr",
            "checks",
            str(number),
            "--repo",
            repo,
            "--required",
            "--json",
            "name,link",
        ],
        no_checks_ok=True,
    )
    return {(check["name"], check.get("link") or "") for check in checks}


def mark_required(
    checks: list[dict[str, Any]], required: set[tuple[str, str]]
) -> list[str]:
    required_names = {name for name, _link in required}
    seen_names = {check["name"] for check in checks}
    for check in checks:
        key = (check["name"], check.get("link") or "")
        check["required"] = key in required or check["name"] in required_names
    return sorted(required_names - seen_names)


def normalize(
    raw: dict[str, Any], required: set[tuple[str, str]]
) -> dict[str, Any]:
    pr = raw.get("data", {}).get("repository", {}).get("pullRequest")
    if not pr:
        raise WatchError("pull request not found")
    commits = pr.get("commits", {}).get("nodes", [])
    if not commits:
        raise WatchError("pull request has no head commit")
    commit = commits[0]["commit"]
    head = pr["headRefOid"]
    committed_at = commit["committedDate"]
    truncated: list[str] = []

    comments = pr.get("comments", {})
    if comments.get("pageInfo", {}).get("hasPreviousPage"):
        truncated.append("conversation_comments")
    reviews = pr.get("reviews", {})
    if reviews.get("pageInfo", {}).get("hasPreviousPage"):
        truncated.append("reviews")
    threads = pr.get("reviewThreads", {})
    if threads.get("pageInfo", {}).get("hasNextPage"):
        truncated.append("review_threads")

    feedback: list[dict[str, Any]] = []
    for item in comments.get("nodes", []):
        if current_by_time(item, committed_at):
            feedback.append(feedback_item("conversation_comment", item))
    for item in reviews.get("nodes", []):
        if item.get("body") and (
            item.get("commit", {}).get("oid") == head
            or current_by_time(item, committed_at)
        ):
            feedback.append(
                feedback_item("review", item, review_state=item.get("state"))
            )
    for thread in threads.get("nodes", []):
        thread_comments = thread.get("comments", {})
        if thread_comments.get("pageInfo", {}).get("hasPreviousPage"):
            truncated.append(f"thread:{thread['id']}")
        if thread.get("isResolved") or thread.get("isOutdated"):
            continue
        for item in thread_comments.get("nodes", []):
            feedback.append(
                feedback_item(
                    "inline_comment",
                    item,
                    thread_id=thread["id"],
                    path=thread.get("path"),
                    line=thread.get("line"),
                )
            )

    contexts = (commit.get("statusCheckRollup") or {}).get("contexts", {})
    if contexts.get("pageInfo", {}).get("hasNextPage"):
        truncated.append("checks")
    checks: list[dict[str, Any]] = []
    for item in contexts.get("nodes", []):
        if item["__typename"] == "CheckRun":
            name = item["name"]
            link = item.get("detailsUrl") or ""
            state = item.get("conclusion") or item.get("status")
        else:
            name = item["context"]
            link = item.get("targetUrl") or ""
            state = item.get("state")
        checks.append(
            {
                "name": name,
                "state": state,
                "bucket": check_bucket(state),
                "required": False,
                "link": link or None,
            }
        )

    feedback.sort(key=lambda item: (item["kind"], item["id"]))
    checks.sort(key=lambda item: (item["name"], item["link"] or ""))
    missing_required = mark_required(checks, required)
    return {
        "pr": {
            "number": pr["number"],
            "url": pr["url"],
            "state": pr["state"],
            "head_branch": pr["headRefName"],
            "head_repo": (pr.get("headRepository") or {}).get("nameWithOwner"),
            "head": head,
        },
        "checks": checks,
        "missing_required": missing_required,
        "feedback": feedback,
        "truncated": sorted(set(truncated)),
    }


def fetch_snapshot(repo: str, number: int, required: set[tuple[str, str]]) -> dict[str, Any]:
    owner, name = repo.split("/", 1)
    raw = gh_json(
        [
            "api",
            "graphql",
            "-f",
            f"query={QUERY}",
            "-F",
            f"owner={owner}",
            "-F",
            f"name={name}",
            "-F",
            f"number={number}",
        ]
    )
    return normalize(raw, required)


def signature(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def delta(previous: dict[str, Any], current: dict[str, Any]) -> dict[str, Any]:
    changed: dict[str, Any] = {"pr": current["pr"]}
    for field in ("checks", "missing_required", "feedback", "truncated"):
        if signature(current[field]) != signature(previous[field]):
            changed[field] = current[field]
    return changed


def emit(event: str, **payload: Any) -> None:
    print(json.dumps({"event": event, **payload}, separators=(",", ":")), flush=True)


def quiet_ready(snapshot: dict[str, Any]) -> bool:
    return (
        snapshot["pr"]["state"] == "OPEN"
        and not snapshot["truncated"]
        and not snapshot["missing_required"]
        and not snapshot["feedback"]
        and all(check["bucket"] in PASS_BUCKETS for check in snapshot["checks"])
    )


def watch(args: argparse.Namespace) -> int:
    repo, number, _url = resolve_pr(args.pr, args.repo)
    required: set[tuple[str, str]] = set()
    required_head: str | None = None
    previous: dict[str, Any] | None = None
    quiet_since: float | None = None
    started = time.monotonic()

    while True:
        try:
            snapshot = fetch_snapshot(repo, number, required)
            head = snapshot["pr"]["head"]
            if head != required_head:
                required = required_keys(repo, number)
                required_head = head
                snapshot["missing_required"] = mark_required(
                    snapshot["checks"], required
                )
        except WatchError as error:
            emit("error", message=str(error))
            return 2

        changed = previous is None or signature(snapshot) != signature(previous)
        if previous is None:
            emit("snapshot", **snapshot)
        elif changed:
            if snapshot["pr"]["head"] != previous["pr"]["head"]:
                emit("head", **snapshot)
            else:
                emit("change", **delta(previous, snapshot))

        if snapshot["truncated"]:
            emit("error", message="snapshot truncated", fields=snapshot["truncated"])
            return 2
        if args.once:
            return 0
        if snapshot["pr"]["state"] != "OPEN":
            emit("stopped", reason=f"PR is {snapshot['pr']['state']}", pr=snapshot["pr"])
            return 2

        now = time.monotonic()
        if quiet_ready(snapshot):
            if quiet_since is None or changed:
                quiet_since = now
            elif now - quiet_since >= args.quiet_seconds:
                emit("quiet", pr=snapshot["pr"], checks=snapshot["checks"])
                return 0
        else:
            quiet_since = None
        if args.timeout and now - started >= args.timeout:
            emit("timeout", pr=snapshot["pr"])
            return 3

        previous = snapshot
        time.sleep(args.interval)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("pr", nargs="?", help="PR URL, number, or branch")
    parser.add_argument("-R", "--repo", help="[HOST/]OWNER/REPO")
    parser.add_argument("--interval", type=float, default=15, help="refresh seconds")
    parser.add_argument("--quiet-seconds", type=float, default=60)
    parser.add_argument("--timeout", type=float, default=1800, help="0 disables timeout")
    parser.add_argument("--once", action="store_true", help="emit one snapshot")
    args = parser.parse_args()
    if args.interval <= 0 or args.quiet_seconds < 0 or args.timeout < 0:
        parser.error("interval must be positive; quiet/timeout must be non-negative")
    return args


if __name__ == "__main__":
    try:
        sys.exit(watch(parse_args()))
    except KeyboardInterrupt:
        sys.exit(130)
