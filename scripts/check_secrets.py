#!/usr/bin/env python3
"""High-confidence repository secret scan for CI gate G7."""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

PATTERNS = {
    "private-key": re.compile(
        r"-----BEGIN (?:RSA |EC |DSA |OPENSSH )?PRIVATE KEY-----"
    ),
    "aws-access-key": re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    "github-token": re.compile(r"\bgh[pousr]_[A-Za-z0-9]{30,}\b"),
    "openai-or-anthropic-key": re.compile(
        r"\bsk-(?:proj-|ant-)?[A-Za-z0-9_-]{20,}\b"
    ),
    "slack-token": re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{20,}\b"),
}

TEXT_SUFFIXES = {
    ".py", ".md", ".json", ".yaml", ".yml", ".toml", ".txt", ".ini",
    ".cfg", ".csv", ".xml", ".html", ".js", ".ts", ".tsx", ".jsx", ".sh",
}


def tracked_files() -> list[Path]:
    output = subprocess.check_output(["git", "ls-files", "-z"])
    return [Path(item.decode()) for item in output.split(b"\0") if item]


def scan() -> list[str]:
    findings: list[str] = []
    for path in tracked_files():
        if path.suffix.lower() not in TEXT_SUFFIXES and path.name not in {
            ".env",
            ".env.example",
        }:
            continue
        try:
            text = path.read_text(errors="replace")
        except OSError:
            continue
        for line_number, line in enumerate(text.splitlines(), start=1):
            for label, pattern in PATTERNS.items():
                if pattern.search(line):
                    findings.append(f"{path}:{line_number}: {label}")
    return findings


def main() -> int:
    findings = scan()
    if findings:
        print("Secret scan failed:", file=sys.stderr)
        for finding in findings:
            print(f"  {finding}", file=sys.stderr)
        return 1
    print("Secret scan passed: no high-confidence credential material detected.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
