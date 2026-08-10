import importlib.util
import subprocess
import unittest
from pathlib import Path
from unittest import mock


REPO_ROOT = Path(__file__).resolve().parents[1]
WATCH_PATH = (
    REPO_ROOT
    / "codex"
    / "skills"
    / "gh-loop-pr-feedback"
    / "scripts"
    / "watch_pr.py"
)


def load_watch_module():
    spec = importlib.util.spec_from_file_location("watch_pr", WATCH_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def graphql_result():
    return {
        "data": {
            "repository": {
                "pullRequest": {
                    "number": 7,
                    "url": "https://github.com/acme/widgets/pull/7",
                    "state": "OPEN",
                    "headRefName": "topic",
                    "headRefOid": "abc123",
                    "headRepository": {"nameWithOwner": "acme/widgets"},
                    "comments": {
                        "pageInfo": {"hasPreviousPage": False},
                        "nodes": [
                            {
                                "id": "old",
                                "body": "stale",
                                "createdAt": "2026-01-01T00:00:00Z",
                                "updatedAt": "2026-01-01T00:00:00Z",
                                "url": "https://example.test/old",
                                "author": {"login": "review-bot", "__typename": "Bot"},
                            },
                            {
                                "id": "current",
                                "body": "fix this",
                                "createdAt": "2026-01-02T00:01:00Z",
                                "updatedAt": "2026-01-02T00:01:00Z",
                                "url": "https://example.test/current",
                                "author": {"login": "review-bot", "__typename": "Bot"},
                            },
                        ],
                    },
                    "reviews": {
                        "pageInfo": {"hasPreviousPage": False},
                        "nodes": [],
                    },
                    "reviewThreads": {
                        "pageInfo": {"hasNextPage": False},
                        "nodes": [
                            {
                                "id": "thread-active",
                                "isResolved": False,
                                "isOutdated": False,
                                "path": "src/main.py",
                                "line": 12,
                                "comments": {
                                    "pageInfo": {"hasPreviousPage": False},
                                    "nodes": [
                                        {
                                            "id": "inline",
                                            "body": "add a test",
                                            "createdAt": "2026-01-01T00:00:00Z",
                                            "updatedAt": "2026-01-01T00:00:00Z",
                                            "url": "https://example.test/inline",
                                            "author": {
                                                "login": "review-bot",
                                                "__typename": "Bot",
                                            },
                                            "commit": {"oid": "older"},
                                        }
                                    ],
                                },
                            },
                            {
                                "id": "thread-resolved",
                                "isResolved": True,
                                "isOutdated": False,
                                "path": "src/main.py",
                                "line": 3,
                                "comments": {
                                    "pageInfo": {"hasPreviousPage": False},
                                    "nodes": [
                                        {
                                            "id": "resolved",
                                            "body": "done",
                                            "createdAt": "2026-01-01T00:00:00Z",
                                            "updatedAt": "2026-01-01T00:00:00Z",
                                            "url": "https://example.test/resolved",
                                            "author": {
                                                "login": "review-bot",
                                                "__typename": "Bot",
                                            },
                                            "commit": {"oid": "older"},
                                        }
                                    ],
                                },
                            },
                        ],
                    },
                    "commits": {
                        "nodes": [
                            {
                                "commit": {
                                    "oid": "abc123",
                                    "committedDate": "2026-01-02T00:00:00Z",
                                    "statusCheckRollup": {
                                        "contexts": {
                                            "pageInfo": {"hasNextPage": False},
                                            "nodes": [
                                                {
                                                    "__typename": "CheckRun",
                                                    "name": "tests",
                                                    "status": "COMPLETED",
                                                    "conclusion": "SUCCESS",
                                                    "detailsUrl": "https://example.test/tests",
                                                },
                                                {
                                                    "__typename": "StatusContext",
                                                    "context": "lint",
                                                    "state": "PENDING",
                                                    "targetUrl": "https://example.test/lint",
                                                },
                                            ],
                                        }
                                    },
                                }
                            }
                        ]
                    },
                }
            }
        }
    }


class WatchPrTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module = load_watch_module()

    def test_normalize_includes_current_conversation_and_active_inline_comments(self):
        snapshot = self.module.normalize(graphql_result(), set())

        self.assertEqual(
            [item["id"] for item in snapshot["feedback"]],
            ["current", "inline"],
        )
        self.assertEqual(snapshot["feedback"][0]["author_type"], "Bot")
        self.assertEqual(snapshot["feedback"][1]["thread_id"], "thread-active")
        self.assertEqual(snapshot["pr"]["head_repo"], "acme/widgets")

    def test_required_check_query_accepts_pending_exit_code(self):
        result = subprocess.CompletedProcess(
            args=[],
            returncode=8,
            stdout='[{"name":"tests","link":"https://example.test/tests"}]',
            stderr="",
        )
        with mock.patch.object(self.module.subprocess, "run", return_value=result):
            checks = self.module.required_keys("acme/widgets", 7)

        self.assertEqual(checks, {("tests", "https://example.test/tests")})

    def test_normalize_marks_required_checks_and_pending_blocks_quiet(self):
        required = {("tests", "https://example.test/tests")}
        snapshot = self.module.normalize(graphql_result(), required)

        checks = {check["name"]: check for check in snapshot["checks"]}
        self.assertTrue(checks["tests"]["required"])
        self.assertEqual(checks["tests"]["bucket"], "pass")
        self.assertEqual(checks["lint"]["bucket"], "pending")
        self.assertFalse(self.module.quiet_ready(snapshot))

    def test_quiet_requires_no_feedback_and_passing_checks(self):
        snapshot = self.module.normalize(graphql_result(), set())
        snapshot["feedback"] = []
        for check in snapshot["checks"]:
            check["bucket"] = "pass"

        self.assertTrue(self.module.quiet_ready(snapshot))

    def test_missing_required_check_blocks_quiet(self):
        required = {("security", "https://example.test/security")}
        snapshot = self.module.normalize(graphql_result(), required)
        snapshot["feedback"] = []
        for check in snapshot["checks"]:
            check["bucket"] = "pass"

        self.assertEqual(snapshot["missing_required"], ["security"])
        self.assertFalse(self.module.quiet_ready(snapshot))

    def test_delta_omits_unchanged_feedback_bodies(self):
        previous = self.module.normalize(graphql_result(), set())
        current = self.module.normalize(graphql_result(), set())
        current["checks"][0]["state"] = "FAILURE"
        current["checks"][0]["bucket"] = "fail"

        change = self.module.delta(previous, current)

        self.assertIn("checks", change)
        self.assertNotIn("feedback", change)

    def test_truncation_is_visible_and_blocks_quiet(self):
        raw = graphql_result()
        raw["data"]["repository"]["pullRequest"]["comments"]["pageInfo"][
            "hasPreviousPage"
        ] = True
        snapshot = self.module.normalize(raw, set())
        snapshot["feedback"] = []
        for check in snapshot["checks"]:
            check["bucket"] = "pass"

        self.assertEqual(snapshot["truncated"], ["conversation_comments"])
        self.assertFalse(self.module.quiet_ready(snapshot))


if __name__ == "__main__":
    unittest.main()
