# Publication readiness

The source is prepared for the first commit and push to [bigpaulie/ha-daewoo-electra-ir](https://github.com/bigpaulie/ha-daewoo-electra-ir). Local release-metadata checks and the official Home Assistant hassfest validator pass. **A published install release is not yet approved:** repository-side HACS validation and deployment verification remain outstanding.

## Completed locally

- Actual project documentation and issue URLs, maintainer `@bigpaulie`, and GitHub CODEOWNERS are configured.
- The local checkout uses `main` with the supplied HTTPS repository as `origin`. No author identity, commit or push was created by the preparation tools.
- Installation-specific entity defaults, learned-command names, source-chat URLs and household references are removed from public contents.
- Setup requires explicit remote/sensor selection. Learned fallbacks are disabled by default and require explicit mappings.
- Source/privacy, relative documentation-link, JSON/Python, duplicate-fixture and translation checks pass.
- Ruff lint/format checks and 26 offline protocol/behavior/configuration/privacy tests pass.
- Four real Home Assistant beta runtime smoke tests pass with fake services; their scope is narrower than deployment testing.
- Original local integration icons are supplied without vendor or Home Assistant trademark artwork.
- CI requires offline checks, release metadata, hassfest, the HACS action and pinned beta runtime checks. No validator checks are suppressed, and nothing auto-publishes releases.
- Documentation includes concrete HACS installation links, updates, rollback, recovery, unsupported functions, privacy, security reporting and release steps/notes.

## After the first push

1. Verify **Actions → Validate integration** passes every job. HACS requires the actual public repository and source tree; its repository-side result has not been established locally.
2. Keep the repository public, enable Issues, set the description/topics, and confirm the documentation links resolve. Verify the available private security reporting channel.
3. Verify HACS installation/update/rollback and full integration setup/reload on a staging Home Assistant instance.
4. Review the final commit and publish an explicitly labeled preview release from the exact tested commit. Follow [release instructions](docs/RELEASING.md).

Source commits and GitHub Releases are separate. The source preparation and manual ZIP builder do not publish either one or certify HACS catalog acceptance.

## Hardware limits that remain explicit in a preview

Generated full controls, IFeel enable/disable, mode-specific restrictions, retained unknown fields and the AC's lost-report fallback still need appliance verification. Reported sensor-update observations on one unit do not establish every command's physical behavior. The integration remains opt-in and uses assumed state.

Home Assistant's core quality-scale tiers are not certifications available to custom integrations. No blanket standards or security certification is claimed.

See [validation results](VALIDATION.md) for executed checks and [maintainer instructions](MAINTAINING.md) for future updates.
