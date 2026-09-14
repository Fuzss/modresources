#!/usr/bin/env python3
"""Timestamped, ANSI-colored console logging.

Purpose: provide the single set of log helpers used across ``scripts/main/``
so progress and fatal errors are reported consistently.

Entry points: imported by ``main.py`` and the sibling modules as ``info2``,
``warn2``, ``error2``, and ``log2``.

Side effects: every helper writes one line to stdout. ``error2`` additionally
terminates the process with exit code 1.

Constraints: standard library only; colors are hard-coded ANSI escapes (cyan
for info, yellow for warning, red for error).
"""

import sys
from datetime import datetime


def log2(level, color, message):
    """Print one timestamped ANSI-colored log line.

    Args:
        level: Severity label rendered in brackets, e.g. ``"INFO"``.
        color: ANSI SGR color code, e.g. ``"36"``.
        message: Text printed after the level.

    Side effects: writes a line to stdout.
    """
    now = datetime.now().strftime("%H:%M:%S")
    print(f"\033[1;{color}m[{now}] [{level}] {message}\033[0m")


def info2(message):
    """Print an info line in cyan."""
    log2("INFO", "36", message)   # cyan


def warn2(message):
    """Print a warning line in yellow."""
    log2("WARN", "33", message)   # yellow


def error2(message):
    """Print an error line in red, then terminate the process.

    Side effects: writes a line to stdout and raises ``SystemExit(1)``; it
    never returns.
    """
    log2("ERROR", "31", message)   # red
    sys.exit(1)
