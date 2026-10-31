"""Build sanitized source-review or manual-install archives without publishing."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import zipfile
from pathlib import Path

from check_publication import check_archive, check_release, check_source

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--release", action="store_true", help="Require release metadata and build install archive"
    )
    args = parser.parse_args()
    errors = check_source() + (check_release() if args.release else [])
    if errors:
        for error in errors:
            print(f"FAIL: {error}")
        return 1
    subprocess.run(
        [sys.executable, "-B", "-m", "unittest", "discover", "-s", "tests", "-q"],
        cwd=ROOT,
        check=True,
    )
    manifest = json.loads((ROOT / "custom_components/daewoo_electra_ir/manifest.json").read_text())
    version = manifest["version"]
    kind = "" if args.release else "-source-review"
    archive = ROOT.parent / f"daewoo-electra-ir-{version}{kind}.zip"
    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED) as output:
        for path in sorted(ROOT.rglob("*")):
            relative = path.relative_to(ROOT)
            if not path.is_file() or path.is_symlink() or path.suffix == ".pyc":
                continue
            if any(
                part
                in {".git", ".venv", "__pycache__", ".ruff_cache", ".pytest_cache", ".DS_Store"}
                for part in relative.parts
            ):
                continue
            if any(part.startswith(".") for part in relative.parts) and relative.parts[0] not in {
                ".github",
                ".gitignore",
                ".gitattributes",
            }:
                continue
            if args.release and relative.parts[0] not in {
                "custom_components",
                "README.md",
                "LICENSE",
                "NOTICE.md",
                "PRIVACY.md",
                "CHANGELOG.md",
                "VALIDATION.md",
                "validation",
                "validation-report.json",
                "docs",
                "MAINTAINING.md",
                "PUBLICATION.md",
                "SECURITY.md",
            }:
                continue
            info = zipfile.ZipInfo(relative.as_posix(), date_time=(2026, 10, 31, 12, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            output.writestr(info, path.read_bytes())
    errors = check_archive(archive)
    if errors:
        archive.unlink()
        raise RuntimeError("Archive checks failed: " + "; ".join(errors))
    digest = hashlib.sha256(archive.read_bytes()).hexdigest()
    archive.with_suffix(".zip.sha256").write_text(f"{digest}  {archive.name}\n")
    print(f"Created {archive.name}; {archive.stat().st_size} bytes; SHA256 {digest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
