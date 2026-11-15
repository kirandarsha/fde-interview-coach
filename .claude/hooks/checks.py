"""PostToolUse hook: lint and type-check after every Edit / Write / MultiEdit.

Runs, from the project root:
    ruff check app tests
    mypy app

All pass -> exit 0 (silent).
Any fail -> print their output to stderr and exit 2, which Claude Code feeds back
            to the agent so it sees the problem and fixes it straight away.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parents[2]  # .claude/hooks/checks.py -> project root

CHECKS: list[list[str]] = [
    ["ruff", "check", "app", "tests"],
    ["mypy", "app"],
]


def project_python() -> str:
    """The venv's Python (where ruff and mypy are installed), else the current one."""
    for candidate in (".venv/Scripts/python.exe", ".venv/bin/python"):
        path = PROJECT_DIR / candidate
        if path.exists():
            return str(path)
    return sys.executable


def run_check(python: str, command: list[str]) -> tuple[bool, str]:
    """Run one check as `python -m <tool> ...`; return (passed, combined output)."""
    result = subprocess.run(
        [python, "-m", *command],
        cwd=PROJECT_DIR,
        capture_output=True,
        text=True,
    )
    return result.returncode == 0, (result.stdout + result.stderr).strip()


def main() -> int:
    sys.stdin.read()  # the tool-call JSON; we check the whole project, so it isn't needed
    python = project_python()
    failures = []
    for command in CHECKS:
        passed, output = run_check(python, command)
        if not passed:
            failures.append(f"$ {' '.join(command)}\n{output}")
    if failures:
        print("Checks failed after this edit:\n\n" + "\n\n".join(failures), file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
