#!/usr/bin/env python3
"""Timestamped console logging helpers shared by the modding scripts."""

import sys
from datetime import datetime


def log2(level, color, message):
    now = datetime.now().strftime("%H:%M:%S")
    print(f"\033[1;{color}m[{now}] [{level}] {message}\033[0m")


def info2(message):
    log2("INFO", "36", message)   # cyan


def warn2(message):
    log2("WARN", "33", message)   # yellow


def error2(message):
    log2("ERROR", "31", message)   # red
    sys.exit(1)
