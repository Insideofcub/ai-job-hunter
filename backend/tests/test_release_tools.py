from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.check_release import find_forbidden_files  # noqa: E402


def test_release_audit_accepts_example_env_and_source_files(tmp_path):
    (tmp_path / ".env.example").write_text("API_KEY=\n", encoding="utf-8")
    (tmp_path / "README.md").write_text("safe public docs", encoding="utf-8")
    (tmp_path / "backend").mkdir()
    (tmp_path / "backend" / "app.py").write_text("print('hello')", encoding="utf-8")

    assert find_forbidden_files(tmp_path) == []


def test_release_audit_flags_env_database_and_private_resume(tmp_path):
    (tmp_path / ".env").write_text("SECRET=not-for-git", encoding="utf-8")
    (tmp_path / "candidate.db").write_bytes(b"sqlite")
    resume_dir = tmp_path / "backend" / "data" / "resumes"
    resume_dir.mkdir(parents=True)
    (resume_dir / "candidate_resume.pdf").write_bytes(b"sample")

    findings = find_forbidden_files(tmp_path)
    assert any(".env" in finding for finding in findings)
    assert any("candidate.db" in finding for finding in findings)
    assert any("candidate_resume.pdf" in finding for finding in findings)


from scripts.validate_release import relative_markdown_link_findings  # noqa: E402
from scripts.package_release import should_include  # noqa: E402


def test_markdown_link_validator_passes_valid_relative_link(tmp_path):
    docs = tmp_path / "docs"
    docs.mkdir()
    target = docs / "guide.md"
    target.write_text("# Guide\n", encoding="utf-8")
    (tmp_path / "README.md").write_text("[Guide](docs/guide.md)\n", encoding="utf-8")
    assert relative_markdown_link_findings(tmp_path) == []


def test_markdown_link_validator_finds_broken_link(tmp_path):
    (tmp_path / "README.md").write_text("[Missing](docs/not-there.md)\n", encoding="utf-8")
    findings = relative_markdown_link_findings(tmp_path)
    assert any("Broken Markdown link" in finding for finding in findings)


def test_release_packager_excludes_secret_and_local_artifacts(tmp_path):
    root = tmp_path / "project"
    root.mkdir()
    safe = root / "README.md"
    safe.write_text("safe", encoding="utf-8")
    secret = root / ".env"
    secret.write_text("API_KEY=secret", encoding="utf-8")
    data = root / "backend" / "data" / "resumes"
    data.mkdir(parents=True)
    resume = data / "candidate_resume.pdf"
    resume.write_bytes(b"private")
    cache = root / "backend" / "__pycache__"
    cache.mkdir(parents=True)
    bytecode = cache / "main.pyc"
    bytecode.write_bytes(b"cache")

    output = tmp_path / "candidate.zip"
    assert should_include(safe, root, output)
    assert not should_include(secret, root, output)
    assert not should_include(resume, root, output)
    assert not should_include(bytecode, root, output)
