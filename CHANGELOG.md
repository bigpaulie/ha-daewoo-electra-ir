# Changelog

## 0.1.1 — Unreleased

- Remove installation-specific entity defaults, source-chat links and hardcoded learned-command mappings.
- Require selection of a Broadlink remote and temperature sensor during setup.
- Disable learned fallback by default and make each fallback command explicitly configurable.
- Rewrite installation, updates, rollback, failure recovery, protocol and privacy documentation for public use.
- Add public-source/archive checks, real-repository metadata tooling, lint/format configuration and required official validators in CI.
- Exclude local metadata, environments and caches from distribution; separate review archives from approved install releases.
- Support the native temperature properties in the 2026.11 beta while retaining the 2026.10 interface path.
- Set project documentation, issue tracker, CODEOWNERS and HACS installation links for the public repository.
- Classify the integration as heat pumps and air conditioning for Home Assistant and HACS.
- Preserve existing integrations and stored entity selections. Earlier local preview users must review fallback mappings after updating.

Repository-side HACS validation, a full Home Assistant deployment and further appliance testing remain release prerequisites or explicitly documented preview limits. This version has not been published.

## 0.1.0 — Local preview, 2026-10-31

Initial independent Daewoo climate entity, Broadlink ELECTRA_AC-compatible encoder, explicit sensor-only FEELING reports, opt-in full controls, regression fixtures and offline tests. Generated full controls were not hardware-verified. No automatic reporting was armed by installation or restart.
