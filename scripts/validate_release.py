#!/usr/bin/env python3
"""Pre-release validation for AI Job Hunter source trees.

Default mode is offline/static: versions, required files, Markdown links, and
private-data scan. Optional flags run the backend suite and/or frontend build.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re
import subprocess
import sys
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parents[1]
VERSION_PATTERN = re.compile(r"^\s*APP_VERSION\s*=\s*[\"']([^\"']+)[\"']", re.MULTILINE)
MARKDOWN_LINK_PATTERN = re.compile(r"\[[^\]]*\]\(([^)]+)\)")
REQUIRED_FILES = (
    "README.md", "LICENSE", "SECURITY.md", "CONTRIBUTING.md", "CHANGELOG.md",
    "VERSION", "ASSET_NOTICES.md", "backend/app/main.py", "backend/requirements.txt",
    "backend/run_server.py", "frontend/package.json", "frontend/index.html",
    "docs/public-release-checklist.md", "scripts/check_release.py", ".github/workflows/ci.yml",
)
SKIP_LINK_DIRS = {".git", ".venv", "venv", "node_modules", "__pycache__", ".pytest_cache", "dist", ".vite"}


def relative_markdown_link_findings(root: Path) -> list[str]:
    findings: list[str] = []
    for md_path in root.rglob("*.md"):
        if any(part in SKIP_LINK_DIRS for part in md_path.relative_to(root).parts):
            continue
        try:
            text = md_path.read_text(encoding="utf-8", errors="replace")
        except OSError as exc:
            findings.append(f"Cannot read Markdown file {md_path.relative_to(root)}: {exc}")
            continue
        for raw_target in MARKDOWN_LINK_PATTERN.findall(text):
            target = unquote(raw_target.strip().split()[0].strip("<>"))
            target = target.split("#", 1)[0]
            if not target or target.startswith(("#", "//")) or re.match(r"^[a-zA-Z][a-zA-Z0-9+.-]*:", target):
                continue
            target_path = (md_path.parent / target).resolve()
            try:
                target_path.relative_to(root.resolve())
            except ValueError:
                # Do not allow repository docs to use local paths outside the tree.
                findings.append(f"Relative Markdown link escapes repository: {md_path.relative_to(root)} -> {raw_target}")
                continue
            if not target_path.exists():
                findings.append(f"Broken Markdown link: {md_path.relative_to(root)} -> {raw_target}")
    return sorted(set(findings))


def inspect_release(root: Path) -> tuple[list[str], list[str]]:
    """Return (errors, warnings); does not run npm/network operations by default."""
    errors: list[str] = []
    warnings: list[str] = []
    if not root.exists() or not root.is_dir():
        return [f"Project root does not exist: {root}"], warnings

    for rel in REQUIRED_FILES:
        if not (root / rel).is_file():
            errors.append(f"Required release file is missing: {rel}")

    version_file = root / "VERSION"
    package_file = root / "frontend" / "package.json"
    main_file = root / "backend" / "app" / "main.py"
    readme_file = root / "README.md"
    changelog_file = root / "CHANGELOG.md"
    try:
        version = version_file.read_text(encoding="utf-8").strip()
        package_version = json.loads(package_file.read_text(encoding="utf-8")).get("version")
        backend_text = main_file.read_text(encoding="utf-8")
        backend_match = VERSION_PATTERN.search(backend_text)
        backend_version = backend_match.group(1) if backend_match else None
        readme_text = readme_file.read_text(encoding="utf-8")
        changelog_text = changelog_file.read_text(encoding="utf-8")
        if not version:
            errors.append("VERSION is empty.")
        for label, value in (("frontend/package.json", package_version), ("backend APP_VERSION", backend_version)):
            if value != version:
                errors.append(f"Version mismatch: VERSION={version}, {label}={value!r}.")
        readme_lines = readme_text.splitlines()
        current_release_line = readme_lines[2] if len(readme_lines) > 2 else ""
        if f"v{version}" not in current_release_line:
            errors.append(f"README current release line does not identify v{version}.")
        if f"v{version}" not in changelog_text[:500]:
            errors.append(f"CHANGELOG does not start with a v{version} entry.")
    except (OSError, ValueError, TypeError, json.JSONDecodeError) as exc:
        errors.append(f"Could not verify release version metadata: {exc}")

    errors.extend(relative_markdown_link_findings(root))

    try:
        # Import from this source tree instead of depending on cwd/sys.path.
        sys.path.insert(0, str(root))
        from scripts.check_release import find_forbidden_files
        errors.extend(find_forbidden_files(root))
    except Exception as exc:
        errors.append(f"Private-data audit could not run: {type(exc).__name__}: {exc}")

    asset_notice = root / "ASSET_NOTICES.md"
    if asset_notice.exists():
        content = asset_notice.read_text(encoding="utf-8", errors="replace").lower()
        if "confirm redistribution rights before public release" in content:
            warnings.append("Theme artwork redistribution rights still require human confirmation; see ASSET_NOTICES.md.")
    if not (root / "frontend" / "node_modules").is_dir():
        warnings.append("Frontend dependencies are not installed in this working tree; run npm install then npm run build before tagging a release.")
    return sorted(set(errors)), sorted(set(warnings))


def run_command(command: list[str], cwd: Path, env: dict[str, str] | None = None) -> int:
    print(f"\n$ {' '.join(command)}  (cwd: {cwd})")
    try:
        completed = subprocess.run(command, cwd=cwd, env=env, check=False)
    except FileNotFoundError:
        print(f"ERROR: Command not found: {command[0]}")
        return 127
    return completed.returncode


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--run-tests", action="store_true", help="Run the backend test suite after static checks.")
    parser.add_argument("--build-frontend", action="store_true", help="Run npm run build (requires installed frontend dependencies).")
    args = parser.parse_args()
    root = args.root.resolve()
    print(f"AI Job Hunter release validation\nProject: {root}")
    errors, warnings = inspect_release(root)
    if errors:
        print("\nERRORS:")
        for item in errors:
            print(f"  [FAIL] {item}")
    else:
        print("\n[PASS] Required files, version metadata, Markdown links, and private-data audit.")
    for item in warnings:
        print(f"  [WARN] {item}")

    if errors:
        return 1

    if args.run_tests:
        test_env = os.environ.copy()
        test_env["PYTHONPATH"] = "."
        if run_command([sys.executable, "-m", "pytest", "-q"], root / "backend", test_env):
            return 1
    if args.build_frontend:
        if run_command(["npm", "run", "build"], root / "frontend"):
            return 1
    print("\nStatic release validation passed. Review warnings and complete manual checklist before publishing.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
