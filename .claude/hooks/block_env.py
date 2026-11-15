"""PreToolUse hook: stop Claude Code from reading .env files.

Claude Code pipes the tool call to this script as JSON on stdin, e.g.
    {"tool_name": "Read", "tool_input": {"file_path": "C:/.../my-coach/.env"}, ...}

Exit 0 -> allow the call.
Exit 2 -> block it; whatever we print to stderr is shown to Claude as the reason.
"""
from __future__ import annotations

import json
import sys

ALLOWED_SUFFIX = ".env.example"


def is_blocked(file_path: str) -> bool:
    """True if the path refers to a .env file (but .env.example is fine)."""
    path = file_path.lower()  # Windows paths are case-insensitive
    return ".env" in path and not path.endswith(ALLOWED_SUFFIX)


def main() -> int:
    try:
        # utf-8-sig tolerates a leading byte-order mark (Windows PowerShell adds one).
        payload = json.loads(sys.stdin.buffer.read().decode("utf-8-sig"))
    except (json.JSONDecodeError, UnicodeDecodeError):
        return 0  # not something we understand; don't get in the way

    file_path = str(payload.get("tool_input", {}).get("file_path", ""))
    if is_blocked(file_path):
        print(
            f"Blocked: reading '{file_path}' is not allowed. .env files hold secrets "
            "(see CLAUDE.md guardrails). Use .env.example instead.",
            file=sys.stderr,
        )
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
