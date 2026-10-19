#!/usr/bin/env python3
"""Audit a working tree for common private/local files before publishing to GitHub."""
from __future__ import annotations

import argparse
from pathlib import Path
import sys

SKIP_DIRS = {".git", ".venv", "venv", "node_modules", "__pycache__", ".pytest_cache", "dist", ".vite"}
ALLOWED_ENV_NAMES = {".env.example"}
FORBIDDEN_NAMES = {
    ".env", ".env.local", ".env.development", ".env.production",
    "id_rsa", "id_ed25519", "credentials.json", "token.json",
}
FORBIDDEN_DIRS = {"browser-profile", "applications-private", "secrets", "credentials"}
FORBIDDEN_SUFFIXES = {".db", ".sqlite", ".sqlite3", ".db-wal", ".db-shm", ".pem", ".key"}


def find_forbidden_files(root: Path) -> list[str]:
    findings: list[str] = []
    if not root.exists() or not root.is_dir():
        return [f"Project root is missing or not a directory: {root}"]

    for path in root.rglob("*"):
        try:
            rel = path.relative_to(root)
        except ValueError:
            continue
        parts = set(rel.parts)
        if parts.intersection(SKIP_DIRS):
            continue
        if path.is_dir():
            if path.name.lower() in FORBIDDEN_DIRS:
                findings.append(f"Private directory present: {rel.as_posix()}")
            continue
        name = path.name.lower()
        if name in FORBIDDEN_NAMES and name not in ALLOWED_ENV_NAMES:
            findings.append(f"Private/credential file present: {rel.as_posix()}")
            continue
        if name.startswith(".env.") and name not in ALLOWED_ENV_NAMES:
            findings.append(f"Non-example environment file present: {rel.as_posix()}")
            continue
        if path.suffix.lower() in FORBIDDEN_SUFFIXES:
            findings.append(f"Database/key material present: {rel.as_posix()}")
            continue
        if rel.as_posix().lower().startswith(("backend/data/", "data/")):
            findings.append(f"Local candidate/application data present: {rel.as_posix()}")
            continue
        if path.suffix.lower() in {".pdf", ".doc", ".docx", ".rtf"} and any(token in name for token in ("resume", "cv", "candidate")):
            findings.append(f"Potential personal document present: {rel.as_posix()}")
    return sorted(set(findings))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    findings = find_forbidden_files(args.root.resolve())
    if findings:
        print("RELEASE AUDIT FAILED — remove these private/local items before publishing:")
        for finding in findings:
            print(f" - {finding}")
        return 1
    print("RELEASE AUDIT PASSED — no common private/local files detected.")
    print("Review staged changes and run GitHub secret scanning before publishing.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
