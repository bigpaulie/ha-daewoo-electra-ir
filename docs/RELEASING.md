# First publication and releases

Repository: [bigpaulie/ha-daewoo-electra-ir](https://github.com/bigpaulie/ha-daewoo-electra-ir).

## First source push

The project directory is the repository root: it must contain `hacs.json`, `README.md`, `.github/` and `custom_components/` directly. Do not add an extra enclosing `daewoo-electra-ir` directory to the GitHub tree. The prepared checkout uses branch `main` and the supplied HTTPS `origin`.

From that directory, review and publish the source yourself:

```sh
git status --short
git add .
git diff --cached --stat
git diff --cached
git commit -m "Prepare Daewoo ELECTRA IR preview integration"
git push -u origin main
```

No Git author name/email is set by this package. Use the identity already configured for your GitHub account, optionally with GitHub's no-reply address if you want commit-email privacy. Do not paste a token into repository files or the remote URL.

In the GitHub repository settings:

1. Keep the repository public for HACS and enable Issues.
2. Add a description, for example: “Home Assistant Daewoo ELECTRA_AC-compatible climate integration using Broadlink IR and an external temperature sensor.”
3. Suggested topics: `home-assistant`, `hacs`, `broadlink`, `daewoo`, `electra-ac`, `custom-integration`.
4. Check **Actions → Validate integration**. Offline tests, hassfest, HACS and the pinned runtime smoke job must all pass. Resolve failures before recommending installation. No action suppresses HACS checks or auto-publishes a release.
5. Enable private vulnerability reporting if desired, then verify the Security reporting instructions match the available channel.

The first push makes the README, issue tracker and workflow links resolve. Local checks cannot establish that the future repository-side HACS job will pass.

## Publish the preview release

1. Review [publication status](../PUBLICATION.md) and [validation scope](../VALIDATION.md).
2. Verify the integration on a staging Home Assistant instance, including HACS installation, reload, update and rollback. Keep the documented hardware limits explicit.
3. Use tag **`v0.1.1`** for manifest version **`0.1.1`**. Tag the exact tested commit, not a moving branch.
4. On GitHub, create a Release from that tag with title **“v0.1.1 — preview”** and the prepared [release notes](RELEASE_NOTES_0.1.1.md). A Git tag alone is not the published-release update workflow used here.
5. HACS installs the integration from repository source. Manual ZIP assets are optional; do not enable `zip_release` for the full source-review archive.
6. If publishing as a GitHub prerelease, check its visibility in the target HACS version before giving install instructions; prereleases may require explicit selection.

To create manual archives locally:

```sh
python3 tools/build_zip.py
python3 tools/build_zip.py --release
```

Both validate the current public contents and run offline tests. `--release` also requires repository metadata. It creates a versioned manual install archive and SHA256 checksum beside the repository; no release is uploaded. Neither command replaces repository-side HACS validation, full deployment tests or hardware verification.

## Later updates

Change source, add meaningful tests for behavior changes, increment manifest version and update the changelog. Run the same checks, push the reviewed commit, and publish a matching release after CI passes. HACS can then offer that release as an update. Users must restart Home Assistant and explicitly re-arm reporting after an update.
