"""Daewoo full-state climate and explicitly armed silent temperature reporting."""

from __future__ import annotations

import asyncio
import json
import logging
import math
import time
from datetime import timedelta
from importlib.resources import files
from typing import ClassVar

from homeassistant.components.climate import ClimateEntity, ClimateEntityFeature, HVACMode
from homeassistant.const import ATTR_TEMPERATURE, UnitOfTemperature
from homeassistant.core import callback
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError
from homeassistant.helpers import entity_platform
from homeassistant.helpers.event import async_track_state_change_event, async_track_time_interval
from homeassistant.helpers.restore_state import RestoreEntity
from homeassistant.util import dt as dt_util
from homeassistant.util.unit_conversion import TemperatureConverter

from .const import DEFAULTS, DOMAIN
from .protocol import FANS, MODES, Waveform, control_frame, sensor_frame, whole_temperature

_LOGGER = logging.getLogger(__name__)
CAPTURES = json.loads(files(__package__).joinpath("captures.json").read_text())
CONTROL_WAVEFORM = Waveform.from_capture(CAPTURES["manual_ifeel_on"])
SENSOR_WAVEFORM = Waveform.from_capture(CAPTURES["sensor_23"])


async def async_setup_entry(hass, entry, async_add_entities):
    async_add_entities([DaewooClimate(entry)])
    platform = entity_platform.async_get_current_platform()
    platform.async_register_entity_service("start_sensor_updates", {}, "async_start_sensor_updates")
    platform.async_register_entity_service("stop_sensor_updates", {}, "async_stop_sensor_updates")


class DaewooClimate(ClimateEntity, RestoreEntity):
    _attr_should_poll = False
    _attr_has_entity_name = True
    _attr_name = None
    _attr_assumed_state = True
    if hasattr(ClimateEntity, "native_temperature_unit"):
        _attr_native_temperature_unit = UnitOfTemperature.CELSIUS
    else:
        _attr_temperature_unit = UnitOfTemperature.CELSIUS
    _attr_target_temperature_step = 1
    _attr_min_temp = 16
    _attr_max_temp = 32
    _attr_hvac_modes: ClassVar[list[HVACMode]] = [
        HVACMode.OFF,
        HVACMode.HEAT,
        HVACMode.COOL,
        HVACMode.HEAT_COOL,
        HVACMode.DRY,
        HVACMode.FAN_ONLY,
    ]
    _attr_fan_modes: ClassVar[list[str]] = list(FANS)
    _attr_preset_modes: ClassVar[list[str]] = ["none", "ifeel"]
    _attr_supported_features = (
        ClimateEntityFeature.TARGET_TEMPERATURE
        | ClimateEntityFeature.FAN_MODE
        | ClimateEntityFeature.PRESET_MODE
        | ClimateEntityFeature.TURN_ON
        | ClimateEntityFeature.TURN_OFF
    )

    def __init__(self, entry):
        self._entry = entry
        self._config = {**DEFAULTS, **entry.data, **entry.options}
        self._attr_unique_id = f"{entry.entry_id}_climate"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry.entry_id)},
            "name": self._config["name"],
            "manufacturer": "Daewoo",
            "model": "ELECTRA_AC via Broadlink (IR, assumed state)",
        }
        # This default never claims the unit is physically off.
        self._attr_hvac_mode = None
        self._target = 24
        self._attr_fan_mode = "auto"
        self._attr_preset_mode = "none"
        self._last_mode = "heat"
        self._lock = asyncio.Lock()
        self._reporting = False
        self._external_session = False
        self._last_report = None
        self._last_report_at = None
        self._last_attempt_mono = float("-inf")
        self._last_report_mono = float("-inf")
        self._status = "stopped"
        self._last_transport = None
        self._active = False

    async def async_added_to_hass(self):
        await super().async_added_to_hass()
        old = await self.async_get_last_state()
        if old:
            try:
                # State attributes are converted to HA's display unit before saving.
                unit = old.attributes.get("temperature_unit", "°C")
                target = TemperatureConverter.convert(
                    float(old.attributes["temperature"]), unit, "°C"
                )
                self._target = whole_temperature(target, 16, 32)
            except (KeyError, TypeError, ValueError):
                pass
            if old.attributes.get("fan_mode") in FANS:
                self._attr_fan_mode = old.attributes["fan_mode"]
            if old.state in MODES:
                self._last_mode = old.state
        # Do not restore mode, IFeel, arming, or emit IR on startup/reload.
        self._active = True
        self.async_on_remove(
            async_track_state_change_event(
                self.hass,
                [self._config["remote_entity"], self._config["temperature_sensor"]],
                self._state_changed,
            )
        )
        self.async_on_remove(
            async_track_time_interval(self.hass, self._tick, timedelta(seconds=30))
        )

    async def async_will_remove_from_hass(self):
        self._active = False
        self._reporting = False
        # Wait for an in-flight service call before unloading this entity.
        async with self._lock:
            pass
        await super().async_will_remove_from_hass()

    @property
    def available(self):
        remote = self.hass.states.get(self._config["remote_entity"])
        return remote is not None and remote.state == "on"

    def _source(self):
        state = self.hass.states.get(self._config["temperature_sensor"])
        if state is None:
            return None, "missing_sensor"
        try:
            value = float(state.state)
            if not math.isfinite(value):
                return None, "invalid_sensor"
            unit = state.attributes.get("unit_of_measurement")
            if unit not in ("°C", "°F", "K"):
                return None, "unknown_sensor_unit"
            value = TemperatureConverter.convert(value, unit, "°C")
            if not 0 <= value <= 50:
                return None, "sensor_out_of_range"
            # last_reported advances even when the physical reading is unchanged.
            age = (dt_util.utcnow() - state.last_reported).total_seconds()
            if age > self._config["sensor_max_age"] or age < -60:
                return None, "stale_sensor"
            return value, "valid"
        except (TypeError, ValueError):
            return None, "invalid_sensor"

    @property
    def native_target_temperature(self):
        return self._target

    if not hasattr(ClimateEntity, "native_target_temperature"):

        @property
        def target_temperature(self):
            return self._target

    @property
    def native_current_temperature(self):
        return self._source()[0]

    if not hasattr(ClimateEntity, "native_current_temperature"):

        @property
        def current_temperature(self):
            return self.native_current_temperature

    @property
    def extra_state_attributes(self):
        value, source_status = self._source()
        return {
            "remote_entity": self._config["remote_entity"],
            "temperature_sensor": self._config["temperature_sensor"],
            "control_enabled": self._config["enable_control"],
            "sensor_updates_armed": self._reporting,
            "sensor_only_session": self._external_session,
            "report_status": self._status,
            "source_status": source_status,
            "last_reported_temperature_c": self._last_report,
            "last_report_at": self._last_report_at,
            "last_transport": self._last_transport,
            "state_feedback": "none; all commands are assumed",
            "full_control_hardware_validation": "pending",
            "sensor_temperature_c": value,
        }

    @callback
    def _state_changed(self, event):
        if not self.available:
            self._disarm_for_remote_loss()
        self.async_write_ha_state()
        if self._active and self._reporting:
            self.hass.async_create_task(self._async_report())

    def _disarm_for_remote_loss(self):
        if self._reporting:
            self._reporting = False
            self._external_session = False
            self._attr_preset_mode = "none"
            self._status = "disarmed_remote_unavailable"

    async def _tick(self, now):
        if not self._active:
            return
        if not self.available:
            self._disarm_for_remote_loss()
        self.async_write_ha_state()  # Also refresh the displayed stale-sensor status.
        if self._reporting:
            await self._async_report()

    async def _send(self, command, *, learned=False):
        if not self._active:
            raise HomeAssistantError("Integration is unloading")
        if not self.available:
            raise HomeAssistantError("Broadlink remote is missing, off, or unavailable")
        data = {
            "entity_id": self._config["remote_entity"],
            "command": [command if learned else f"b64:{command}"],
            "num_repeats": 1,
        }
        if learned:
            data["device"] = self._config["learned_device"]
        try:
            await self.hass.services.async_call("remote", "send_command", data, blocking=True)
        except Exception as err:
            self._status = "transport_error"
            self.async_write_ha_state()
            raise HomeAssistantError(f"Broadlink command failed: {err}") from err
        self._last_transport = "learned" if learned else "generated"
        # Broadlink's service can swallow network errors; service completion is not
        # proof of transmission or appliance reception. Always keep assumed_state.

    def _require_control(self):
        if not self._config["enable_control"]:
            raise ServiceValidationError(
                "Enable full controls in integration options after reading the hardware-validation limits"
            )

    async def _apply(self, *, mode=None, target=None, fan=None, preset=None):
        self._require_control()
        async with self._lock:
            new_mode = (
                str(mode)
                if mode is not None
                else (str(self._attr_hvac_mode) if self._attr_hvac_mode else None)
            )
            new_target = target if target is not None else self._target
            new_fan = fan if fan is not None else self._attr_fan_mode
            new_preset = preset if preset is not None else self._attr_preset_mode
            if new_fan not in FANS or new_preset not in self._attr_preset_modes:
                raise ServiceValidationError("Unsupported fan or preset")
            if new_mode is not None and new_mode != "off" and new_mode not in MODES:
                raise ServiceValidationError("Unsupported HVAC mode")
            if new_mode in (None, "off") and mode is None:
                if preset == "ifeel":
                    raise ServiceValidationError(
                        "Select an active HVAC mode, or use start_sensor_updates with the physical remote"
                    )
                # Setpoint/fan changes while off/unknown are cached, never turn on.
                self._target = new_target
                self._attr_fan_mode = new_fan
                if preset == "none":
                    self._reporting = False
                    self._external_session = False
                    self._attr_preset_mode = "none"
                    self._status = "stopped_local_unit_may_remain_ifeel"
                self.async_write_ha_state()
                return
            power = new_mode != "off"
            source = None
            if power and new_preset == "ifeel":
                source, reason = self._source()
                if source is None:
                    raise ServiceValidationError(f"Cannot enable IFeel: {reason}")
            native_mode = new_mode if power else self._last_mode
            learned = None
            if self._config["learned_fallback"]:
                if not power:
                    learned = self._config["off_command"].strip() or None
                elif (
                    native_mode == "cool"
                    and new_target == 24
                    and new_fan in ("low", "medium", "high")
                    and new_preset == "none"
                    and self._attr_preset_mode == "none"
                ):
                    learned = self._config[f"cool_{new_fan}_command"].strip() or None
            if learned:
                await self._send(learned, learned=True)
            else:
                code = CONTROL_WAVEFORM.encode(
                    control_frame(
                        native_mode, new_target, new_fan, power=power, sensor_temperature=source
                    )
                )
                await self._send(code)
            self._attr_hvac_mode = HVACMode(new_mode)
            self._target = new_target
            self._attr_fan_mode = new_fan
            self._attr_preset_mode = new_preset if power else "none"
            self._reporting = power and new_preset == "ifeel"
            self._external_session = False
            if power:
                self._last_mode = native_mode
            self._status = "armed" if self._reporting else "stopped"
            if self._reporting:
                self._last_report = whole_temperature(source, 0, 50)
                self._last_report_at = dt_util.utcnow().isoformat()
                self._last_attempt_mono = self._last_report_mono = time.monotonic()
            self.async_write_ha_state()

    async def async_set_hvac_mode(self, hvac_mode):
        await self._apply(mode=hvac_mode)

    async def async_set_temperature(self, **kwargs):
        if ATTR_TEMPERATURE not in kwargs:
            raise ServiceValidationError("A target temperature is required")
        try:
            target = whole_temperature(float(kwargs[ATTR_TEMPERATURE]), 16, 32)
        except (TypeError, ValueError) as err:
            raise ServiceValidationError(str(err)) from err
        await self._apply(mode=kwargs.get("hvac_mode"), target=target)

    async def async_set_fan_mode(self, fan_mode):
        await self._apply(fan=fan_mode)

    async def async_set_preset_mode(self, preset_mode):
        await self._apply(preset=preset_mode)

    async def async_turn_on(self):
        await self._apply(mode=self._last_mode)

    async def async_turn_off(self):
        # Disarm before attempting off; even a failed off must stop sensor traffic.
        self._reporting = False
        self._external_session = False
        self._status = "stopped"
        self.async_write_ha_state()
        await self._apply(mode=HVACMode.OFF, preset="none")

    async def async_start_sensor_updates(self):
        """Explicit sensor-only handover: no power, mode, or setpoint command."""
        async with self._lock:
            source, reason = self._source()
            if source is None:
                raise ServiceValidationError(f"Cannot start sensor updates: {reason}")
            code = SENSOR_WAVEFORM.encode(sensor_frame(source))
            await self._send(code)
            self._reporting = True
            self._external_session = True
            self._attr_hvac_mode = None  # Physical-remote handover invalidates the old assumption.
            self._attr_preset_mode = "ifeel"
            self._record_report(source)
            self.async_write_ha_state()

    async def async_stop_sensor_updates(self):
        """Stop locally without issuing an unverified full control frame."""
        async with self._lock:
            self._reporting = False
            self._external_session = False
            self._attr_preset_mode = "none"
            self._status = "stopped_local_unit_may_remain_ifeel"
            self.async_write_ha_state()

    def _record_report(self, source):
        self._last_report = whole_temperature(source, 0, 50)
        self._last_report_at = dt_util.utcnow().isoformat()
        self._last_report_mono = self._last_attempt_mono = time.monotonic()
        self._status = "service_completed_unconfirmed"

    async def _async_report(self):
        async with self._lock:
            if not self._active or not self._reporting:
                return
            if not self.available:
                self._disarm_for_remote_loss()
                self.async_write_ha_state()
                return
            source, reason = self._source()
            if source is None:
                if self._status != reason:
                    _LOGGER.warning(
                        "Daewoo temperature reports suspended: %s; use the physical remote if needed. Appliance fallback is unverified",
                        reason,
                    )
                self._status = reason
                self.async_write_ha_state()
                return
            now = time.monotonic()
            rounded = whole_temperature(source, 0, 50)
            if now - self._last_attempt_mono < 60:
                return
            if (
                rounded == self._last_report
                and now - self._last_report_mono < self._config["report_interval"]
            ):
                return
            self._last_attempt_mono = now  # Rate-limit failures as well as success.
            try:
                await self._send(SENSOR_WAVEFORM.encode(sensor_frame(source)))
            except HomeAssistantError as err:
                self._status = "transport_error"
                _LOGGER.warning("Daewoo temperature report failed: %s", err)
            else:
                self._record_report(source)
            self.async_write_ha_state()
