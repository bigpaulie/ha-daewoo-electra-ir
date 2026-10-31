# Validation record

Version **0.1.1**, reviewed **2026-10-31**. Public-source cleanup is complete for the current package. Project repository metadata is assigned and passes the local release gate. Publication approval still depends on repository-side HACS checks and deployment verification.

| Check | Actual result |
|---|---|
| Offline unit tests | **26 passed**; protocol, behavior, setup validation, privacy/release guards |
| Real HA runtime smoke tests | **4 passed** on **2026.11.0b2**, Python **3.14.10**, in the official hassfest image with networking disabled and a fake remote service |
| Runtime deprecation warnings | None in the final smoke run; native temperature compatibility added after the initial beta findings |
| Ruff lint and formatting | Passed with the repository's configured rules |
| YAML / JSON / Python syntax | Parsed successfully |
| Source privacy / relative documentation links | Passed |
| Official hassfest | **Passed** with final project metadata: one integration checked, zero invalid integrations |
| HACS action | Configured in CI, **not run** against a real repository yet |
| Full Home Assistant deployment / HACS installation | **Not tested** |
| New hardware transmissions | **None** |

The runtime test environment came from the official image digest `sha256:a6a695921327230c07ba89ebbb48778737bc1dda30b00cb60c9276585687fc6d`. Its HA source is a beta; these results do not certify every supported stable or future release. The 2026.10 compatibility path is retained and covered by offline interface tests, but was not exercised in a full 2026.10 runtime.

## Protocol checks

- All four anonymized contributed captures decode as 13-byte ELECTRA_AC-compatible frames with valid checksums.
- The contributed 21°C regression waveform matches the generated 21°C payload. Normalized generated timings can differ from captured Base64 while representing the same payload.
- The 28°C payload is calculated from the same template; its original transmitted waveform is not available for direct comparison.
- All 51 whole sensor temperatures 0–50°C encode/decode, changing only bytes 7 and 12 of the sensor template.
- All 1,360 mode/fan/target/power/IFeel combinations encode/decode with expected documented fields and checksum. This is protocol validation, not 1,360 appliance tests.
- Independent upstream recorded-frame interpretation and an independent LSB bit-string decoder support the round-trip tests.
- Broadlink payload length, extended durations, rounding, malformed frames, invalid readings and preserved fields are covered.

## Behavioral checks

Offline tests cover setup silence, unknown initial mode, explicit arming, cached target/fan behavior, sensor validity/freshness/units, report throttling/refresh, stop/unload, remote-outage disarming, failed sends and explicitly configured learned fallbacks. Existing climate state is not altered by commands to the new integration.

The real-runtime smoke checks use real Home Assistant schema, state, registry, climate, restore-state and service interfaces with temporary storage and fake send services. They cover required entity selection, validation, sensor-only reporting, full-state property updates and lifecycle hooks. State writes are replaced in that narrow suite; the full loader, frontend, config-entry lifecycle, real entity-action dispatch and HACS install/update paths are not certified by it.

## Privacy and packaging checks

Installation-specific defaults, hardcoded learned mappings, source-chat URLs, household labels and personal filesystem references have been removed. Public fixtures retain protocol bytes without source identities or device/network identifiers. Local caches and operating-system metadata are removed or excluded. Archive CRC, path safety and content scans run during packaging.

The scanner detects common private paths, source-chat URLs, email addresses, local network addresses, MAC addresses and credential patterns without echoing matched data. This is a guard against accidental disclosure, not a general security certification or proof about arbitrary future contributions.

## Contributor-reported physical evidence

An anonymized contributor reported that, in HEAT at 24°C, a generated 28°C sensor update stopped the compressor without a beep, and a generated 21°C update allowed heating to resume. These observations support the sensor-update path on one unit; they have not been independently repeated during this audit.

Generated power/mode/target/fan controls, IFeel enable/disable, mode-specific limits, retained unknown fields, FEELING timeout and internal-sensor fallback remain hardware-verification limits. Read [failure behavior](docs/SAFETY.md) before use.

## Remaining publication checks

The manifest now contains actual project documentation/issue URLs and maintainer attribution, and the release metadata gate plus hassfest pass. After the first source push, run the HACS action against the actual repository. Verify HACS installation/update/rollback and full integration setup/reload in a staging Home Assistant instance. No official quality-scale tier or catalog acceptance is claimed.

See [publication readiness](PUBLICATION.md).
