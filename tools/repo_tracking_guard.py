"""Repository tracking guard (upgrade-safety layer).

Purpose
-------
Personal runtime data (role identity, faculties, continuity, Memory,
capability records, install state, runtime logs) must live OUTSIDE the
Git worktree, under the external data home (see INSTALLATION_CONTRACT
and dao-sheng.ps1 / run_dao_sheng.py path resolution).

`.gitignore` alone is NOT protection: it only prevents accidental
`git add`. Once a path is TRACKED -- e.g. an upstream commit starts
tracking `instances/default/identity.json` -- a plain `git pull`
overwrites the local file and exits 0, silently destroying personal
data. This guard makes that state structurally visible: it fails when
Git tracks any path under the guarded personal-data prefixes.

What it checks
--------------
`git ls-files` lists every path in the index (tracked or staged).
Any such path under `config/`, `log/`, or `instances/` is a violation.

Where it runs
-------------
- CI: .github/workflows/repo-guard.yml (every push / pull request).
- Test suite: tests/test_repo_tracking_guard.py (temp Git repos).

Exit codes
----------
0  no tracked personal-data path (or no Git index available at all --
   e.g. this checkout is not a Git repository; a vacuous pass is
   reported explicitly in that case)
1  at least one guarded path is tracked by Git
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

# Forward-slash relative prefixes of personal runtime data inside a
# repository worktree. These must never be tracked by Git.
GUARDED_PREFIXES = ("config/", "log/", "instances/")


def tracked_paths(repo_root: Path) -> list[str] | None:
    """Return tracked/staged paths (forward-slash relative), or None when
    the Git index is unavailable (not a repo, git missing, etc.)."""
    try:
        result = subprocess.run(
            ["git", "-C", str(repo_root), "ls-files", "-z"],
            capture_output=True,
            check=False,
        )
    except OSError:
        return None
    if result.returncode != 0:
        return None
    raw_entries = result.stdout.split(b"\0")
    paths: list[str] = []
    for raw in raw_entries:
        if not raw:
            continue
        path = raw.decode("utf-8", "surrogateescape").replace("\\", "/")
        paths.append(path)
    return paths


def violations(paths: list[str]) -> list[str]:
    """Paths that fall under a guarded personal-data prefix."""
    found: list[str] = []
    for path in paths:
        for prefix in GUARDED_PREFIXES:
            bare = prefix.rstrip("/")
            if path == bare or path.startswith(prefix):
                found.append(path)
                break
    return found


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--repo",
        default=str(Path(__file__).resolve().parent.parent),
        help="repository root to inspect (default: this repo)",
    )
    args = parser.parse_args(argv)
    repo_root = Path(args.repo).resolve()

    paths = tracked_paths(repo_root)
    if paths is None:
        print(
            "[OK] repo tracking guard: no Git index available at "
            f"{repo_root} (not a Git repository or git unavailable); "
            "nothing is tracked, so nothing can be overwritten by a pull"
        )
        return 0

    bad = violations(paths)
    if bad:
        print("[FAIL] repo tracking guard: Git tracks personal-data paths")
        print("       guarded prefixes: " + ", ".join(GUARDED_PREFIXES))
        for path in bad:
            print(f"       tracked: {path}")
        print(
            "       fix: untrack these paths (git rm --cached <path>) and keep "
            "personal runtime data under the external data home; "
            ".gitignore alone does NOT protect already-tracked files"
        )
        return 1

    print(
        f"[OK] repo tracking guard: {len(paths)} tracked path(s), none under "
        + ", ".join(GUARDED_PREFIXES)
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
