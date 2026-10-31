# v0.1.1 — preview

Independent Home Assistant climate integration for the contributed Daewoo ELECTRA_AC-compatible IR profile, using an existing Broadlink transmitter and a room temperature sensor.

- Silent FEELING measurement reports with explicit start/stop, freshness checks and rate limits.
- Opt-in generated power, modes, target and fan controls; configurable existing learned-command fallbacks.
- Setup requires selecting local entities. No household defaults, credentials or source-chat links are included.
- Startup, reload and options changes do not automatically send IR or re-arm reports.
- Existing climate integrations and learned codes remain independent.

## Verification and limits

Offline protocol/behavior tests and isolated real Home Assistant beta interface tests pass; see the repository validation record for scope. Verify the exact release commit's CI result before publishing these notes.

This is a preview. Generated full controls and the appliance's FEELING timeout/internal-sensor fallback still need hardware verification. All AC states are assumed; there is no appliance feedback. Full controls and learned fallback are disabled by default. Unsupported features include swing, turbo, quiet, sleep, timers, clean and display controls.

## Install / update

Add `https://github.com/bigpaulie/ha-daewoo-electra-ir` in HACS as an **Integration**, install the chosen version and restart Home Assistant. Select the Broadlink remote and temperature sensor in setup. Use the physical remote to establish the intended mode/setpoint and FEELING state before starting sensor reports.

Updates and restarts stop reporting. Check the sensor/appliance and re-arm explicitly. Earlier local-preview users must review learned fallback mappings after updating; existing stored entity selections are retained.
