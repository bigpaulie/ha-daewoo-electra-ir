# Daewoo ELECTRA IR

[![Validation](https://github.com/bigpaulie/ha-daewoo-electra-ir/actions/workflows/checks.yml/badge.svg)](https://github.com/bigpaulie/ha-daewoo-electra-ir/actions/workflows/checks.yml)

A local Home Assistant custom integration for a **Daewoo AC with an ELECTRA_AC-compatible remote**, using an existing Broadlink IR transmitter and a room temperature sensor.

**Preview release.** Silent FEELING temperature reports have contributor-reported hardware evidence on one unit. Generated power, mode, temperature, fan and IFeel enable/disable commands are implemented and protocol-tested, but still need appliance verification. Full controls are disabled by default. Compatibility is not claimed for every Daewoo model.

This integration creates a separate climate entity and does not change existing climate integrations, automations or learned codes. All appliance states are assumed: there is no AC state feedback.

## Requirements

- Home Assistant **2026.10 or newer**; the minimum version is not a guarantee of compatibility with every future release.
- HACS for repository installation, or file access for manual installation.
- A configured Broadlink integration with a working IR-capable `remote` entity.
- A temperature sensor with a temperature device class, reporting °C, °F or K.
- The physical AC remote for initial setup and recovery.

Setup, saving options, restart and reload send no IR. Reporting must be explicitly started.

## Install

### HACS

Source repository: [bigpaulie/ha-daewoo-electra-ir](https://github.com/bigpaulie/ha-daewoo-electra-ir). On first publication, wait for the repository validation checks to pass before installing. Release and deployment checks are tracked in [publication status](PUBLICATION.md).

1. Back up Home Assistant.
2. In **HACS → ⋮ → Custom repositories**, add `https://github.com/bigpaulie/ha-daewoo-electra-ir` with type **Integration**.
3. Open **Daewoo ELECTRA IR** and download the desired release. Before the first GitHub Release exists, HACS may offer the default branch; prefer a tagged release for reproducible updates.
4. Restart Home Assistant.
5. Go to **Settings → Devices & services → Add integration → Daewoo ELECTRA IR**.
6. Select the Broadlink remote and room sensor. Keep **Full controls** and **Learned fallback** disabled initially.
7. Confirm the new entity ID. Examples use `climate.daewoo_ac_ir`; use the actual ID if it differs.

[Open this repository in HACS](https://my.home-assistant.io/redirect/hacs_repository/?owner=bigpaulie&repository=ha-daewoo-electra-ir&category=integration).

HACS installs files; adding the integration creates its device and entity. HACS currently supports public GitHub repositories. Do not install a second copy manually while HACS manages the same integration folder.

### Manual ZIP

Extract the release ZIP and copy only `custom_components/daewoo_electra_ir` into the Home Assistant configuration directory. The result must include `/config/custom_components/daewoo_electra_ir/manifest.json`. Merge existing folders rather than replacing `custom_components`. Restart, then follow steps 5–7 above. No YAML configuration or extra Python installation is required inside Home Assistant.

## Start with sensor-only reporting

1. With the physical remote, turn the AC on, select the intended mode and target, and enable FEELING.
2. Prevent that remote from sending competing temperature reports; keep it available for recovery.
3. Verify that the selected room sensor is fresh and plausible. Stop any other automation that sends FEELING reports.
4. Run this in **Developer Tools → Actions**:

```yaml
action: daewoo_electra_ir.start_sensor_updates
target:
  entity_id: climate.daewoo_ac_ir
```

This immediately reports the measured temperature and arms periodic reporting. It does not power the AC, enable FEELING, or change its mode or setpoint. The HVAC mode becomes unknown because external control cannot be observed.

To stop:

```yaml
action: daewoo_electra_ir.stop_sensor_updates
target:
  entity_id: climate.daewoo_ac_ir
```

Stopping sends no IR and does not clear FEELING on the AC. Use the physical remote to restore normal control. Sensor reports also stop on integration restart/reload, and disarm when a remote outage is observed. Re-arm explicitly after recovery.

**Lost reports do not guarantee fallback to the AC's internal sensor.** The appliance may retain its last reported temperature. See [failure behavior and recovery](docs/SAFETY.md) before unattended use.

## Enable climate controls

In this integration's **Configure** options, enable **Full controls** only when ready to test the appliance response. Saving reloads the entry and stops reporting.

| Feature | Behavior / limitation |
|---|---|
| Off / on | Absolute power command; on uses the last requested active mode, initially HEAT at 24°C |
| Mode | Heat, cool, dry, fan-only and heat/cool; heat/cool is the protocol's automatic changeover mode |
| Target | 16–32°C in whole-degree steps; the appliance may support a narrower range |
| Fan | Auto, low, medium, high; appliance restrictions still apply |
| Preset `ifeel` | Generated full-state enable with the current sensor reading, then silent reports; requires a known active mode |
| Preset `none` | Generated full-state IFeel disable when a known mode is active; hardware behavior needs verification |

Setting temperature/fan while mode is off or unknown caches preferences without turning the AC on. Selecting a mode sends the full state. For example:

```yaml
action: climate.set_temperature
target:
  entity_id: climate.daewoo_ac_ir
data:
  hvac_mode: heat
  temperature: 24
```

Selecting preset `ifeel` requires a valid sensor. For a physical-remote handover use the sensor-only start action instead. To hand control back without sending a full-state command, use the stop action and physical remote.

**Unsupported:** swing/vane positioning, turbo, quiet fan, sleep, eco, timers, clock, clean, display/light toggles, humidity control, AC state reception, and arbitrary protocol learning. A silent sensor update is not a quiet-fan feature.

### Optional learned fallback

Learned fallback is disabled by default and contains no installation-specific command names. To enable it, enter the exact Broadlink learned-code **device group** and any existing power-off / COOL-at-24°C low-, medium-, or high-fan command names. Configure only commands whose physical effect is already known.

Only an exact configured match uses a learned command. Blank command fields use the generator. Cooling fallbacks apply only when IFeel is not active or requested. An IFeel-disable command uses the generator. If a configured learned send fails, the integration does not silently try a generated alternative. The device group is a Broadlink storage label, not an entity target.

## Options and diagnostics

| Option | Default | Notes |
|---|---|---|
| Remote / temperature sensor | User selection required | No personal entity names are shipped |
| Full controls / learned fallback | Disabled | Explicit opt-in |
| Learned group / commands | Blank | Required only when a fallback is enabled/configured |
| Report interval | 180 seconds | Allowed 60–600; checked every 30 seconds |
| Maximum sensor age | 1800 seconds | Allowed 300–86400; at least the report interval |

Sensor readings are converted to Celsius and rounded half up. Changed whole-degree readings are reported no faster than once per minute; unchanged readings are refreshed at the report interval, with up to 30 seconds scheduling delay. Freshness uses the sensor's last report time, including unchanged reports.

Useful entity attributes: `source_status`, `report_status`, `sensor_updates_armed`, `sensor_only_session`, `last_transport`, `last_reported_temperature_c`, and `last_report_at`. A completed service call is not confirmed appliance reception. Check Home Assistant logs for Broadlink errors.

## Update, rollback or remove

- **Update:** stop reporting, install the selected release through HACS, restart Home Assistant, check the sensor, and re-arm explicitly.
- **Rollback:** use HACS **Redownload** and select a compatible previous published release, then restart. Read migration notes first.
- **Remove:** stop reporting, restore normal control with the physical remote, remove this integration under Devices & services, then remove its files through HACS or delete only its own folder and restart. Do not delete other integrations or Broadlink's learned-code files.

No source update, restart, rollback or removal can confirm or reset the physical AC's state.

## Development and verification

- [Validation results and remaining limits](VALIDATION.md)
- [Safety, failure behavior and troubleshooting](docs/SAFETY.md)
- [Protocol and regression fixtures](docs/PROTOCOL.md)
- [Maintaining and releasing](MAINTAINING.md)
- [Changelog](CHANGELOG.md)
- [Privacy policy](PRIVACY.md)
- [Publication readiness](PUBLICATION.md)
- [Security reporting](SECURITY.md)
- [First publication and release steps](docs/RELEASING.md)

For bugs, use [GitHub Issues](https://github.com/bigpaulie/ha-daewoo-electra-ir/issues) with sanitized details.

Offline checks use Python's standard library:

```sh
python3 -m unittest discover -s tests -v
python3 tools/ir_tool.py validate
python3 tools/check_publication.py
```

The tests do not transmit IR. Behavioral doubles do not certify Home Assistant runtime compatibility. Official validators and release metadata are tracked separately in the validation record. This project is independent of Daewoo, Broadlink, Home Assistant and IRremoteESP8266.
