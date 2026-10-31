# Failure behavior and recovery

The integration reports actual room temperature and leaves thermostat regulation to the AC. It does not synthesize a separate on/off thermostat or command the compressor directly.

## What happens when something fails

| Condition | Integration behavior | What to do |
|---|---|---|
| Sensor missing, unavailable, nonnumeric, nonfinite, out of 0–50°C, stale or unknown unit | Suspend temperature reports; do not invent or reuse a reading | Restore the sensor or stop reporting and use the physical remote |
| Sensor returns with a valid fresh reading | Resume an armed session when rate limits permit | Stop the session explicitly if automatic recovery is unwanted |
| Broadlink remote off/missing/unavailable | Reject sends; mark climate unavailable; disarm on a state event or within 30 seconds | Restore the remote and explicitly re-arm |
| Send raises an error while the remote still appears available | Keep appliance state assumed; automatic report attempts remain rate-limited | Check logs, network and line of sight |
| Restart, reload or removal | Stop reporting; never automatically restore power/mode/arming | Re-establish the intended AC state and re-arm explicitly |
| Stop-reporting action | Stop local reports without sending IR | Clear/re-establish FEELING using the physical remote as appropriate |
| Power-off action fails | Reporting is disarmed first; physical AC state remains unknown | Use a known working off control or the physical remote |

The AC's FEELING timeout and internal-sensor fallback are **unverified**. It may retain the last measurement. Suspending reports does not guarantee internal-sensor regulation. No generated full-state fallback or power-off command is sent automatically on sensor loss. Do not rely on this preview for unattended frost/overheat protection.

The standard Home Assistant entity-action dispatcher does not target unavailable entities. Reporting is therefore disarmed when a remote outage is observed. If a stop action cannot target the unavailable entity, disable/reload this integration to stop it locally, then restore normal physical control. An already in-flight service call can finish before stop/unload returns.

With full controls disabled, a dispatched `climate.turn_off` disarms reporting and rejects the power command. It does not guarantee the appliance is off. Use an existing working off control or the physical remote.

## What “assumed” means

There is no IR receiver or appliance telemetry. A physical-remote command or another integration can invalidate the displayed requested state. Compressor operation is never inferred from target versus room temperature. HVAC action is not reported.

The supported Broadlink service path accepts `b64:` commands, but the checked Home Assistant implementation can log some network errors without raising them. `last_report_at` records a completed service call, not proof that IR was emitted or accepted. Confirm response at the appliance.

## Initial hardware verification

Start with sensor-only reporting while the physical remote sets a known mode and target. Do not report simulated temperatures in routine use. When testing full controls, test one ordinary mode, target or fan change at a time and observe the appliance. Test IFeel enable and disable independently. Keep the physical remote available.

Allow the AC's own compressor protection delay. There are no independent compressor minimum-run/off timers in this integration; avoid rapid power or mode changes. Prevent competing FEELING reports and automations from sending conflicting state commands.

## Troubleshooting

- **Integration absent after copying:** confirm the folder path, restart Home Assistant and refresh the browser. Review setup errors in Settings → System → Logs.
- **Sensor reports suspended:** inspect `source_status`; verify unit, range and age. Set the age limit to exceed the sensor's legitimate reporting interval rather than disabling freshness checks.
- **Climate unavailable:** confirm the selected Broadlink remote is on/available. After recovery, explicitly re-arm reports.
- **Learned command missing:** verify the exact Broadlink device group and command name. A blank mapping means generated control, not a learned fallback.
- **Climate mode unknown:** expected after restart or sensor-only handover. Select a mode explicitly only after enabling full controls, or continue using the physical remote for controls.
- **Stop does not clear FEELING:** expected; the stop action sends no IR. Use the physical remote.
- **Unexpected appliance behavior:** stop reports, restore control with the physical remote, and collect sanitized protocol details before changing the encoder.

Full-state messages preserve unexplained captured fields. Their effects are not fully characterized across models. Sensor-only messages modify only temperature and checksum. Neither fact guarantees universal compatibility.
