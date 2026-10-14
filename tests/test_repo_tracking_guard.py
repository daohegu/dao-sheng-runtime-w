"""Repo tracking guard tests (synthetic temp Git repositories only).

Verifies that tools/repo_tracking_guard.py detects Git TRACKING personal
runtime data paths (config/, log/, instances/) -- the exact condition
under which a plain `git pull` from an upstream that starts tracking the
same path silently overwrites local personal data.

All repositories are created under a temporary directory with synthetic
content. The real working copy is never initialized as Git here.
"""

from __future__ import annotations

import importlib.util
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
GUARD_SCRIPT = REPO_ROOT / "tools" / "repo_tracking_guard.py"

_spec = importlib.util.spec_from_file_location("repo_tracking_guard", GUARD_SCRIPT)
guard = importlib.util.module_from_spec(_spec)
assert _spec.loader is not None
_spec.loader.exec_module(guard)

GIT = shutil.which("git")


def _git(repo: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", "-c", "user.email=guard-test@example.com",
         "-c", "user.name=guard-test", *args],
        cwd=str(repo), capture_output=True, text=True, check=True,
    )


@unittest.skipIf(GIT is None, "git executable not available")
class GuardDetectionTest(unittest.TestCase):
    """The guard must fail exactly when Git tracks a personal-data path."""

    def setUp(self) -> None:
        # TemporaryDirectory (not raw mkdtemp + rmtree): Git writes read-only
        # files under .git/objects, which make plain shutil.rmtree silently
        # leave the temp dir behind on Windows. TemporaryDirectory.cleanup
        # handles the read-only case.
        tmp = tempfile.TemporaryDirectory(prefix="ds-guard-test-")
        self.addCleanup(tmp.cleanup)
        self.tmp = Path(tmp.name)

    def _init_repo(self, name: str) -> Path:
        repo = self.tmp / name
        repo.mkdir(parents=True)
        _git(repo, "init", "-q")
        (repo / ".gitignore").write_text(
            "config/\nlog/\ninstances/\n", encoding="utf-8"
        )
        (repo / "hello.py").write_text("SOURCE = 'synthetic'\n", encoding="utf-8")
        _git(repo, "add", ".gitignore", "hello.py")
        _git(repo, "commit", "-q", "-m", "initial")
        return repo

    def test_clean_repo_passes(self) -> None:
        repo = self._init_repo("clean")
        self.assertEqual(guard.main(["--repo", str(repo)]), 0)

    def test_force_tracked_identity_fails_guard(self) -> None:
        # .gitignore is present, yet the path is force-added -- exactly the
        # upstream "starts tracking the same path" scenario. .gitignore does
        # NOT protect an already-tracked file.
        repo = self._init_repo("tracked")
        personal = repo / "instances" / "default"
        personal.mkdir(parents=True)
        (personal / "identity.json").write_text(
            '{"name": "synthetic-local-personal-data"}\n', encoding="utf-8"
        )
        _git(repo, "add", "-f", "instances/default/identity.json")
        _git(repo, "commit", "-q", "-m", "upstream starts tracking identity path")

        self.assertEqual(guard.main(["--repo", str(repo)]), 1)

    def test_staged_only_violation_is_detected(self) -> None:
        # Even before a commit, a staged personal-data path is in the index.
        repo = self._init_repo("staged")
        (repo / "config").mkdir()
        (repo / "config" / "install-state.json").write_text(
            '{"staged": true}\n', encoding="utf-8"
        )
        _git(repo, "add", "-f", "config/install-state.json")
        self.assertEqual(guard.main(["--repo", str(repo)]), 1)

    def test_all_guarded_prefixes_detected(self) -> None:
        repo = self._init_repo("allprefixes")
        for rel in ("instances/default/faculties.json", "log/runtime.log"):
            path = repo / rel
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("synthetic\n", encoding="utf-8")
            _git(repo, "add", "-f", rel)
        _git(repo, "commit", "-q", "-m", "track personal data dirs")
        tracked = guard.tracked_paths(repo)
        self.assertIsNotNone(tracked)
        bad = guard.violations(tracked or [])
        self.assertEqual(
            sorted(bad),
            ["instances/default/faculties.json", "log/runtime.log"],
        )
        self.assertEqual(guard.main(["--repo", str(repo)]), 1)

    def test_non_repo_directory_passes_vacuously(self) -> None:
        plain = self.tmp / "not-a-repo"
        plain.mkdir()
        (plain / "instances").mkdir()
        (plain / "instances" / "identity.json").write_text(
            '{"untracked": true}\n', encoding="utf-8"
        )
        # No Git index -> nothing tracked -> nothing a pull can overwrite.
        self.assertIsNone(guard.tracked_paths(plain))
        self.assertEqual(guard.main(["--repo", str(plain)]), 0)


class ViolationsUnitTest(unittest.TestCase):
    """Prefix matching is pure logic; no Git needed."""

    def test_prefix_rules(self) -> None:
        paths = [
            "hello.py",
            "dao_sheng/composition.py",
            "tests/test_x.py",
            "instances/default/identity.json",
            "config/install-state.json",
            "log/runtime.log",
            "instance-notes.md",  # must NOT match "instances/"
            "configs/other.json",  # must NOT match "config/"
            "logging/x.log",  # must NOT match "log/"
            "instances",  # bare directory entry matches
        ]
        bad = guard.violations(paths)
        self.assertEqual(
            sorted(bad),
            sorted(
                [
                    "instances/default/identity.json",
                    "config/install-state.json",
                    "log/runtime.log",
                    "instances",
                ]
            ),
        )

    def test_clean_paths_yield_no_violations(self) -> None:
        self.assertEqual(
            guard.violations(["README.md", "dao_sheng/layout.py", ".gitignore"]),
            [],
        )


if __name__ == "__main__":
    unittest.main()
