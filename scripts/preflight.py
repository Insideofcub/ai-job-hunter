#!/usr/bin/env python3
"""Check local prerequisites for AI Job Hunter without exposing secret values."""
from __future__ import annotations

import importlib.util
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
REQUIRED_MODULES = {
    "fastapi": "fastapi",
    "uvicorn": "uvicorn",
    "sqlalchemy": "sqlalchemy",
    "pydantic-settings": "pydantic_settings",
    "httpx": "httpx",
    "pypdf": "pypdf",
    "python-docx": "docx",
    "Pillow": "PIL",
    "openpyxl": "openpyxl",
    "playwright": "playwright",
}


def check(name: str, ok: bool, detail: str, required: bool = True) -> tuple[bool, str]:
    state = "OK" if ok else ("FAIL" if required else "WARN")
    print(f"[{state}] {name}: {detail}")
    return ok or not required, state


def main() -> int:
    failures = 0
    print("AI Job Hunter local preflight")
    print(f"Project: {ROOT}")
    print(f"Python: {sys.executable}")
    py_ok = sys.version_info >= (3, 11)
    if not check("Python version", py_ok, platform.python_version() + (" (3.11+ required)" if not py_ok else ""))[0]:
        failures += 1

    missing = []
    for distribution, module in REQUIRED_MODULES.items():
        if importlib.util.find_spec(module) is None:
            missing.append(distribution)
    if not check("Backend dependencies", not missing, ", ".join(missing) if missing else "required imports are available")[0]:
        failures += 1

    env_file = BACKEND / ".env"
    check("Backend .env", env_file.exists(), str(env_file) if env_file.exists() else "not found; copy backend/.env.example to backend/.env", required=False)

    try:
        req = urllib.request.Request("http://127.0.0.1:11434/api/tags", headers={"Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=1.2) as response:
            payload = json.loads(response.read().decode("utf-8", errors="replace"))
        names = {str(model.get("name", "")) for model in payload.get("models", [])}
        has_embed = any(name.startswith("nomic-embed-text") for name in names)
        has_qwen = any(name.startswith("qwen2.5:3b-instruct") for name in names)
        check("Ollama service", True, "reachable on localhost:11434", required=False)
        check("Ollama language model", has_qwen, "qwen2.5:3b-instruct installed" if has_qwen else "qwen2.5:3b-instruct not found", required=False)
        check("Ollama embedding model", has_embed, "nomic-embed-text installed" if has_embed else "nomic-embed-text not found", required=False)
    except Exception:
        check("Ollama service", False, "not reachable at localhost:11434; optional if using a cloud provider", required=False)

    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            executable = Path(p.chromium.executable_path)
            present = executable.exists()
            check("Playwright Chromium", present, str(executable) if present else "Chromium is not installed; run `python -m playwright install chromium`", required=False)
    except Exception as exc:
        check("Playwright Chromium", False, f"browser readiness unavailable ({type(exc).__name__}); install dependencies and Chromium if browser automation is needed", required=False)

    if failures:
        print("\nPreflight found required dependencies to fix before starting the backend.")
        return 1
    print("\nRequired checks passed. Optional services may still need configuration.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
