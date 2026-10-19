#!/usr/bin/env python3
"""Create a clean, source-only ZIP for review or GitHub release preparation."""
from __future__ import annotations

import argparse
from pathlib import Path
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[1]
EXCLUDED_DIRS = {
    ".git", ".venv", "venv", "node_modules", "__pycache__", ".pytest_cache",
    ".mypy_cache", ".ruff_cache", ".vite", "dist", "coverage", "htmlcov",
    "browser-profile", "secrets", "credentials", "applications-private",
}
EXCLUDED_NAMES = {
    ".env", ".env.local", ".env.development", ".env.production",
    "id_rsa", "id_ed25519", "credentials.json", "token.json",
}
EXCLUDED_SUFFIXES = {".pyc", ".pyo", ".db", ".sqlite", ".sqlite3", ".pem", ".key", ".log"}
EXCLUDED_DIR_PREFIXES = ("backend/data/", "data/", "uploads/", "resumes/")


def should_include(path: Path, root: Path, output: Path) -> bool:
    rel = path.relative_to(root).as_posix()
    if path.resolve() == output.resolve():
        return False
    parts = set(path.relative_to(root).parts)
    if parts.intersection(EXCLUDED_DIRS):
        return False
    lower_name = path.name.lower()
    if lower_name in EXCLUDED_NAMES:
        return False
    if lower_name.startswith(".env.") and lower_name != ".env.example":
        return False
    if path.suffix.lower() in EXCLUDED_SUFFIXES:
        return False
    if rel.lower().startswith(EXCLUDED_DIR_PREFIXES):
        return False
    if path.is_file() and path.suffix.lower() in {".pdf", ".doc", ".docx", ".rtf"} and any(w in lower_name for w in ("resume", "cv", "candidate")):
        return False
    return path.is_file()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--output", type=Path, required=True, help="Output ZIP path.")
    args = parser.parse_args()
    root = args.root.resolve()
    output = args.output.resolve()
    sys.path.insert(0, str(root))
    try:
        from scripts.validate_release import inspect_release
    except Exception as exc:
        print(f"Cannot load release validator: {exc}")
        return 1
    errors, warnings = inspect_release(root)
    if errors:
        print("Refusing to package: release validation has errors.")
        for item in errors:
            print(f" - {item}")
        return 1
    for item in warnings:
        print(f"[WARN] {item}")

    output.parent.mkdir(parents=True, exist_ok=True)
    included: list[Path] = []
    for path in root.rglob("*"):
        if should_include(path, root, output):
            included.append(path)
    if not included:
        print("No source files found; refusing to create an empty archive.")
        return 1
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=8) as archive:
        for path in sorted(included):
            archive.write(path, path.relative_to(root).as_posix())
    print(f"Created {output} with {len(included)} files ({output.stat().st_size:,} bytes).")
    print("This is a release candidate. Complete docs/public-release-checklist.md before publishing.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
