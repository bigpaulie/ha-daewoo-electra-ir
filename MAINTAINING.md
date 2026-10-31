# Maintaining and releasing

The repository root contains one integration in `custom_components/daewoo_electra_ir`. HACS installs that directory. Tests, developer tools and fixture provenance stay outside it. The package adds no runtime dependencies beyond Home Assistant and its Broadlink integration.

## Publication status

Repository: [bigpaulie/ha-daewoo-electra-ir](https://github.com/bigpaulie/ha-daewoo-electra-ir). Maintainer: `@bigpaulie`. The manifest and GitHub CODEOWNERS use that explicit public attribution. The local Git checkout uses `main` and points `origin` to the supplied repository. No commit or push is performed by the preparation tools.

Run `python3 tools/check_publication.py --release` to check source/privacy and metadata consistency. The release metadata gate checks syntax and links within the package; it does not establish HACS catalog acceptance or physical device behavior.

If the repository is ever moved, update local metadata with:

```sh
python3 tools/set_repository.py ACTUAL_OWNER/ACTUAL_REPOSITORY --maintainer ACTUAL_MAINTAINER
```

Do not add private account details, email addresses, source-chat URLs, household entities, IP/MAC addresses or credentials. Confirm Issues are enabled and review the final diff before publishing.

See [first publication and release steps](docs/RELEASING.md). The HACS action and full HACS installation checks still require the source to be pushed to the actual public repository.

## Release checks

1. Read the diff, update `CHANGELOG.md`, and keep hardware evidence separate from protocol tests.
2. Run the configured Ruff lint/format checks, unit tests, protocol validator and publication checker.
3. Run the official Home Assistant **hassfest** and **HACS action**. The GitHub workflow requires them; no checks are ignored. HACS needs the actual repository/GitHub context. Resolve every failure before claiming HACS compatibility.
4. Test setup, options, restart, unload and the intended controls on a supported Home Assistant instance. The offline doubles do not cover real HA startup or dispatcher/registry lifecycle.
5. Verify local brand assets against the current custom-integration branding requirements. If a target HACS version also requires external brand registration, complete it; do not suppress the validator.
6. Increment manifest `version`, record validation scope/results, and publish a matching GitHub Release tag (for example `v0.1.1` for manifest `0.1.1`). A tag alone is not the versioned-release workflow described here.
7. For a public preview release, clearly state unverified hardware functions. Test HACS install, update and rollback on a staging instance before relying on this workflow.

The workflow runs on pushes and pull requests. It has read-only repository permissions, does not publish releases, and does not post comments. Development dependency versions are pinned in `requirements-dev.txt`; they are not Home Assistant runtime requirements.

Custom integrations do not receive official Home Assistant quality-scale tiers. Follow applicable guidance without claiming a core certification or every optional quality rule is satisfied.

## Build packages

```sh
python3 tools/build_zip.py
python3 tools/build_zip.py --release
```

Default mode creates a sanitized **source-review archive**, including a clear publication status. Release mode requires real repository metadata and creates a manual install archive. Building an archive does not itself approve or publish a release; complete the remaining checks recorded in `PUBLICATION.md`. Both run tests and source/privacy checks first, derive the version from the manifest, and write SHA256 checksums. They exclude hidden local metadata, caches and environments. Source-review archives include the GitHub workflow and `.gitignore` explicitly.

HACS installs repository source, not these ZIPs. Never point HACS's `zip_release` setting at the full source-review archive.

## Update or roll back

Stop reports, install the desired release through HACS and restart Home Assistant. Read migration notes before a rollback. Reconfirm the sensor and appliance state, then re-arm reporting explicitly. Keep the physical remote available; a source rollback cannot confirm or reset the AC's state.

For an installation made from an earlier local preview, existing entity selections remain in Home Assistant's config entry. Version 0.1.1 ships no personal defaults and requires explicit learned-command mappings. Review fallback settings after updating. No existing entity is renamed or removed by the source update.

References checked 2026-10-31:

- [Custom repositories](https://hacs.dev/docs/faq/custom_repositories/)
- [HACS publication and versioning](https://hacs.dev/docs/publish/start/)
- [Home Assistant custom integration publication](https://contributors.home-assistant.io/marketplace/guides/integrations/)
- [Integration manifest](https://contributors.home-assistant.io/core/integrations/manifest/)
- [Local custom integration brand assets](https://contributors.home-assistant.io/core/integrations/brands/)
