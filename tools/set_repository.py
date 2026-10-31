"""Set real publication metadata without publishing or contacting GitHub."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("repository", help="Actual GitHub owner/repository")
    parser.add_argument("--maintainer", required=True, help="Consenting maintainer's GitHub handle")
    args = parser.parse_args()
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9-]*/[A-Za-z0-9_.-]+", args.repository):
        parser.error("Use an actual GitHub owner/repository")
    maintainer = args.maintainer.removeprefix("@")
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9-]*", maintainer):
        parser.error("Invalid GitHub maintainer handle")
    path = ROOT / "custom_components/daewoo_electra_ir/manifest.json"
    manifest = json.loads(path.read_text())
    manifest.update(
        {
            "documentation": f"https://github.com/{args.repository}#readme",
            "issue_tracker": f"https://github.com/{args.repository}/issues",
            "codeowners": [f"@{maintainer}"],
        }
    )
    manifest = {
        key: manifest[key]
        for key in ["domain", "name", *sorted(set(manifest) - {"domain", "name"})]
    }
    path.write_text(json.dumps(manifest, indent=2) + "\n")
    print(
        "Repository metadata set locally. Verify the repository exists, Issues are enabled, and the maintainer consents before publication."
    )


if __name__ == "__main__":
    main()
