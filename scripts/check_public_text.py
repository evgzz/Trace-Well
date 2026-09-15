#!/usr/bin/env python3
"""Fail when tracked public text contains private-context leakage patterns.

The built-in scan is intentionally generic and must work in a fresh clone.
If `.private/sensitive_terms.txt` exists locally, its one-term-per-line entries
augment the scan. That file is never required for CI and must never be tracked.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
import subprocess
import sys
from typing import Iterable

ROOT = Path(__file__).resolve().parents[1]
SELF = Path(__file__).resolve()
PRIVATE_TERMS_PATH = ROOT / ".private" / "sensitive_terms.txt"

TEXT_SUFFIXES = {"", ".md", ".txt", ".py", ".toml", ".yaml", ".yml", ".json", ".ini", ".cfg", ".rst", ".csv"}
FALLBACK_EXCLUDED_PARTS = {".git", ".private", "local-notes", ".venv", "venv", "__pycache__", ".pytest_cache", "build", "dist"}


@dataclass(frozen=True)
class GenericRule:
    name: str
    pattern: re.Pattern[str]


GENERIC_RULES = (
    GenericRule("requisition identifier", re.compile(r"\b(?:requisition|req)\s*(?:id|number|no\.?|#)\s*[:#-]?\s*[A-Za-z0-9_-]+", re.I)),
    GenericRule("private hiring workflow language", re.compile(r"\b(?:recruiter\s+(?:screen|call)|hiring\s+manager|interview\s+(?:prep|preparation|strategy)|application\s+status)\b", re.I)),
    GenericRule("role-targeting language", re.compile(r"\balign(?:ed|ment)?\s+to\s+[^\n.]{1,100}\b(?:role|interview|job)\b", re.I)),
    GenericRule("job-posting URL", re.compile(r"https?://[^\s)\]>]+/(?:jobs?|careers?|candidateexperience|jobsearch|job-details?)(?:/|\?|$)", re.I)),
    GenericRule("unresolved private-context placeholder", re.compile(r"\[(?:EMPLOYER|BUSINESS_UNIT|ROLE|REQ_ID|RECRUITER|INTERVIEWER|JOB_URL)\]", re.I)),
)


def _git_output(*args: str) -> str | None:
    try:
        proc = subprocess.run(["git", "-C", str(ROOT), *args], check=True, capture_output=True, text=True)
    except (OSError, subprocess.CalledProcessError):
        return None
    return proc.stdout


def _tracked_files() -> list[Path] | None:
    output = _git_output("ls-files", "-z")
    if output is None:
        return None
    return [(ROOT / item).resolve() for item in output.split("\0") if item]


def _fallback_files() -> list[Path]:
    files: list[Path] = []
    for path in ROOT.rglob("*"):
        if path.is_file() and not any(part in FALLBACK_EXCLUDED_PARTS for part in path.parts):
            files.append(path.resolve())
    return files


def _candidate_files() -> list[Path]:
    paths = _tracked_files() or _fallback_files()
    return sorted(path for path in paths if path.exists() and path.is_file() and path.suffix.lower() in TEXT_SUFFIXES)


def _read_text(path: Path) -> str | None:
    try:
        return path.read_text(encoding="utf-8")
    except (UnicodeDecodeError, OSError):
        return None


def _load_private_terms() -> list[str]:
    if not PRIVATE_TERMS_PATH.exists():
        return []
    terms: list[str] = []
    for raw in PRIVATE_TERMS_PATH.read_text(encoding="utf-8").splitlines():
        term = raw.strip()
        if term and not term.startswith("#"):
            terms.append(term)
    return terms


def _line_number(text: str, offset: int) -> int:
    return text.count("\n", 0, offset) + 1


def _scan_generic(path: Path, text: str) -> list[str]:
    if path == SELF:
        return []
    findings: list[str] = []
    for rule in GENERIC_RULES:
        for match in rule.pattern.finditer(text):
            findings.append(f"{path.relative_to(ROOT)}:{_line_number(text, match.start())}: {rule.name}: {match.group(0)!r}")
    return findings


def _scan_private_terms(path: Path, text: str, terms: Iterable[str]) -> list[str]:
    findings: list[str] = []
    lowered = text.casefold()
    for term in terms:
        needle = term.casefold()
        start = 0
        while True:
            index = lowered.find(needle, start)
            if index < 0:
                break
            findings.append(f"{path.relative_to(ROOT)}:{_line_number(text, index)}: local sensitive term matched: {term!r}")
            start = index + max(1, len(needle))
    return findings


def _scan_git_surfaces(terms: list[str]) -> list[str]:
    findings: list[str] = []
    surfaces = {
        "branch names": _git_output("for-each-ref", "--format=%(refname:short)", "refs/heads", "refs/remotes"),
        "commit messages": _git_output("log", "--format=%B"),
    }
    for label, text in surfaces.items():
        if not text:
            continue
        for rule in GENERIC_RULES:
            for match in rule.pattern.finditer(text):
                findings.append(f"git {label}: {rule.name}: {match.group(0)!r}")
        lowered = text.casefold()
        for term in terms:
            if term.casefold() in lowered:
                findings.append(f"git {label}: local sensitive term matched: {term!r}")
    return findings


def main() -> int:
    private_terms = _load_private_terms()
    findings: list[str] = []
    for path in _candidate_files():
        text = _read_text(path)
        if text is None:
            continue
        findings.extend(_scan_generic(path, text))
        findings.extend(_scan_private_terms(path, text, private_terms))
    findings.extend(_scan_git_surfaces(private_terms))
    if findings:
        print("Public-text scan failed:\n", file=sys.stderr)
        for finding in findings:
            print(f"- {finding}", file=sys.stderr)
        if not private_terms:
            print("\nNote: no local .private/sensitive_terms.txt was present. Generic CI cannot prove absence of arbitrary private proper nouns.", file=sys.stderr)
        return 1
    print("Public-text scan passed.")
    if private_terms:
        print(f"Applied {len(private_terms)} local sensitive-term entries.")
    else:
        print("No local sensitive-term file present; generic scan only. Publication review remains a maintainer responsibility.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
