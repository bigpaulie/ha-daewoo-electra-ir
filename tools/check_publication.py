"""Check public source and optionally require real release metadata.

This is a repository-specific guard, not a replacement for hassfest or HACS.
"""

from __future__ import annotations

import argparse
import ast
import json
import re
import zipfile
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
DOMAIN = "daewoo_electra_ir"
TEXT_SUFFIXES = {".py", ".json", ".md", ".txt", ".yml", ".yaml", ".toml"}
PATTERNS = {
    "home-directory path": re.compile(r"/(?:Users|home)/[^/\s]+/"),
    "source-chat URL": re.compile(r"https?://(?:www\.)?chatgpt\.com/(?:share|c)/[\w-]+"),
    "private IPv4 address": re.compile(
        r"\b(?:10\.(?:\d{1,3}\.){2}\d{1,3}|192\.168\.\d{1,3}\.\d{1,3}|172\.(?:1[6-9]|2\d|3[01])\.\d{1,3}\.\d{1,3})\b"
    ),
    "MAC address": re.compile(r"\b(?:[0-9a-fA-F]{2}:){5}[0-9a-fA-F]{2}\b"),
    "email address": re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"),
    "GitHub credential": re.compile(
        r"\b(?:gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,})\b"
    ),
    "private key": re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
}


def inspect_text(name: str, text: str) -> list[str]:
    return [
        f"{name}: possible {label}" for label, pattern in PATTERNS.items() if pattern.search(text)
    ]


def check_source(root: Path = ROOT) -> list[str]:
    errors = []
    for path in sorted(root.rglob("*")):
        relative = path.relative_to(root)
        if any(
            part in {".git", ".venv", "__pycache__", ".ruff_cache", ".pytest_cache"}
            for part in relative.parts
        ):
            continue
        if not path.is_file():
            continue
        if path.is_symlink():
            errors.append(f"{relative}: do not publish symlinks")
        if path.name == ".DS_Store" or path.suffix == ".pyc":
            errors.append(f"{relative}: local metadata must be removed")
        if path.suffix in TEXT_SUFFIXES or path.name in {"LICENSE", ".gitignore"}:
            text = path.read_text()
            errors.extend(inspect_text(str(relative), text))
            if path.suffix == ".py":
                ast.parse(text, filename=str(relative))
            elif path.suffix == ".json":
                json.loads(text)
            elif path.suffix == ".md":
                for target in re.findall(r"\]\(([^)]+)\)", text):
                    if "://" in target or target.startswith("#"):
                        continue
                    local = target.split("#", 1)[0]
                    if local and not (path.parent / local).is_file():
                        errors.append(f"{relative}: broken relative link {target}")
    integration = root / "custom_components" / DOMAIN
    manifest = json.loads((integration / "manifest.json").read_text())
    if manifest["domain"] != DOMAIN:
        errors.append("manifest domain differs from integration folder")
    if list(manifest) != ["domain", "name", *sorted(set(manifest) - {"domain", "name"})]:
        errors.append("manifest keys must be domain, name, then alphabetical")
    if json.loads((integration / "strings.json").read_text()) != json.loads(
        (integration / "translations/en.json").read_text()
    ):
        errors.append("English translations differ from strings.json")
    if json.loads((root / "fixtures/captures.json").read_text()) != json.loads(
        (integration / "captures.json").read_text()
    ):
        errors.append("fixture copies differ")
    return errors


def check_release(root: Path = ROOT) -> list[str]:
    manifest = json.loads((root / "custom_components" / DOMAIN / "manifest.json").read_text())
    errors = []
    docs = urlparse(manifest.get("documentation", ""))
    issues = urlparse(manifest.get("issue_tracker", ""))
    parts = docs.path.strip("/").split("/")
    if docs.scheme != "https" or docs.netloc != "github.com" or len(parts) < 2:
        errors.append("Set documentation to the actual GitHub repository README URL")
    else:
        repository = "/".join(parts[:2])
        if (
            issues.scheme != "https"
            or issues.netloc != "github.com"
            or issues.path != f"/{repository}/issues"
        ):
            errors.append("Set issue_tracker to the same repository's GitHub Issues URL")
    if not manifest.get("issue_tracker"):
        errors.append("Set issue_tracker to the actual GitHub Issues URL")
    owners = manifest.get("codeowners", [])
    if not owners or any(not re.fullmatch(r"@[A-Za-z0-9][A-Za-z0-9-]*", owner) for owner in owners):
        errors.append("Set codeowners to the real consenting GitHub maintainer handle(s)")
    return errors


def check_archive(path: Path) -> list[str]:
    errors = []
    with zipfile.ZipFile(path) as archive:
        if archive.testzip() is not None:
            errors.append("archive CRC check failed")
        for name in archive.namelist():
            parts = Path(name).parts
            if name.startswith("/") or ".." in parts:
                errors.append(f"{name}: unsafe archive path")
            if any(
                part in {".git", ".venv", "__pycache__", ".DS_Store"} for part in parts
            ) or name.endswith(".pyc"):
                errors.append(f"{name}: excluded local metadata in archive")
            if Path(name).suffix in TEXT_SUFFIXES or Path(name).name == "LICENSE":
                errors.extend(inspect_text(name, archive.read(name).decode()))
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--release", action="store_true", help="Require real repository metadata")
    parser.add_argument("--archive", type=Path, help="Also inspect a ZIP")
    args = parser.parse_args()
    errors = check_source()
    if args.release:
        errors.extend(check_release())
    if args.archive:
        errors.extend(check_archive(args.archive))
    if errors:
        for error in errors:
            print(f"FAIL: {error}")
        return 1
    print(
        "Public-source checks passed"
        + ("; release metadata checked" if args.release else " (release metadata not certified)")
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
