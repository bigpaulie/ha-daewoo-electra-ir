"""Behavioral tests with HA interface doubles, no real device access."""

import importlib.util
import sys
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock

from ha_stub import HomeAssistantError, ServiceValidationError, install

install()
ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "behavior_daewoo",
    ROOT / "custom_components/daewoo_electra_ir/__init__.py",
    submodule_search_locations=[str(ROOT / "custom_components/daewoo_electra_ir")],
)
package = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = package
spec.loader.exec_module(package)
import importlib

m = importlib.import_module("behavior_daewoo.climate")


def state(value, unit="°C", age=0):
    return SimpleNamespace(
        state=str(value),
        attributes={"unit_of_measurement": unit},
        last_reported=datetime.now(timezone.utc) - timedelta(seconds=age),
    )


class BehaviorTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        entry = SimpleNamespace(
            entry_id="separate-entry",
            data={
                "remote_entity": "remote.test_transmitter",
                "temperature_sensor": "sensor.test_temperature",
                "learned_fallback": True,
                "learned_device": "test_ac",
                "off_command": "test_off",
                "cool_low_command": "test_cool_low",
                "cool_medium_command": "test_cool_medium",
                "cool_high_command": "test_cool_high",
            },
            options={},
        )
        self.entity = m.DaewooClimate(entry)
        self.states = {
            "remote.test_transmitter": state("on"),
            "sensor.test_temperature": state(20.6),
            "climate.existing_ac": state("heat"),
        }
        self.original = self.states["climate.existing_ac"]
        self.entity.hass = SimpleNamespace(
            states=SimpleNamespace(get=self.states.get),
            services=SimpleNamespace(async_call=AsyncMock()),
        )
        await self.entity.async_added_to_hass()
        self.calls = self.entity.hass.services.async_call

    async def test_no_startup_transmit_or_restored_power(self):
        self.calls.assert_not_called()
        self.assertIsNone(self.entity._attr_hvac_mode)
        self.assertFalse(self.entity._reporting)
        await self.entity._tick(None)
        self.calls.assert_not_called()

    async def test_control_disabled_but_sensor_only_available(self):
        with self.assertRaises(ServiceValidationError):
            await self.entity.async_turn_on()
        self.calls.assert_not_called()
        await self.entity.async_start_sensor_updates()
        self.assertIsNone(self.entity._attr_hvac_mode)
        self.assertTrue(self.entity._reporting)
        code = self.calls.call_args.args[2]["command"][0]
        from behavior_daewoo.protocol import decode

        self.assertEqual(decode(code), m.sensor_frame(21))
        self.assertIs(self.states["climate.existing_ac"], self.original)
        for call in self.calls.call_args_list:
            self.assertEqual(call.args[:2], ("remote", "send_command"))
            self.assertEqual(call.args[2]["entity_id"], "remote.test_transmitter")

    async def test_throttle_change_refresh_and_stop(self):
        await self.entity.async_start_sensor_updates()
        self.states["sensor.test_temperature"] = state(22)
        await self.entity._async_report()
        self.assertEqual(self.calls.call_count, 1)
        self.entity._last_attempt_mono -= 61
        await self.entity._async_report()
        self.assertEqual(self.calls.call_count, 2)
        self.entity._last_attempt_mono -= 61
        await self.entity._async_report()
        self.assertEqual(self.calls.call_count, 2)
        self.entity._last_report_mono -= 181
        await self.entity._async_report()
        self.assertEqual(self.calls.call_count, 3)
        await self.entity.async_stop_sensor_updates()
        self.entity._last_attempt_mono -= 61
        await self.entity._async_report()
        self.assertEqual(self.calls.call_count, 3)

    async def test_invalid_stale_unknown_unit_no_fabricated_reading(self):
        await self.entity.async_start_sensor_updates()
        for value, unit, age in [
            ("unavailable", "°C", 0),
            ("unknown", "°C", 0),
            ("NaN", "°C", 0),
            ("inf", "°C", 0),
            (51, "°C", 0),
            (20.6, "°C", 1801),
            (20.6, "bad", 0),
        ]:
            self.states["sensor.test_temperature"] = state(value, unit, age)
            self.entity._last_attempt_mono -= 61
            await self.entity._async_report()
            self.assertIsNone(self.entity.current_temperature)
        self.assertEqual(self.calls.call_count, 1)
        self.states["sensor.test_temperature"] = state(23)
        await self.entity._async_report()
        self.assertEqual(self.calls.call_count, 2)

    async def test_fahrenheit_conversion(self):
        self.states["sensor.test_temperature"] = state(68, "°F")
        self.assertAlmostEqual(self.entity.current_temperature, 20)
        await self.entity.async_start_sensor_updates()
        self.assertEqual(self.entity._last_report, 20)

    async def test_offline_and_failures_not_committed_or_flooded(self):
        self.entity._config["enable_control"] = True
        self.states["remote.test_transmitter"] = state("off")
        with self.assertRaises(HomeAssistantError):
            await self.entity.async_turn_on()
        self.calls.assert_not_called()
        self.states["remote.test_transmitter"] = state("on")
        self.calls.side_effect = RuntimeError("network")
        with self.assertRaises(HomeAssistantError):
            await self.entity.async_turn_on()
        self.assertIsNone(self.entity._attr_hvac_mode)
        self.calls.side_effect = None
        await self.entity.async_start_sensor_updates()
        self.calls.side_effect = RuntimeError("network")
        self.entity._last_attempt_mono -= 61
        self.entity._last_report_mono -= 181
        await self.entity._async_report()
        count = self.calls.call_count
        await self.entity._async_report()
        self.assertEqual(self.calls.call_count, count)
        self.assertEqual(self.entity._status, "transport_error")

    async def test_setpoint_fan_off_cache_and_combined_on(self):
        self.entity._config["enable_control"] = True
        await self.entity.async_set_temperature(temperature=23)
        await self.entity.async_set_fan_mode("low")
        self.calls.assert_not_called()
        await self.entity.async_set_temperature(temperature=25, hvac_mode="heat")
        self.assertEqual(self.calls.call_count, 1)
        self.assertEqual(self.entity._attr_hvac_mode, "heat")
        self.assertEqual(self.entity._last_transport, "generated")
        await self.entity.async_turn_off()
        self.assertEqual(self.calls.call_args.args[2]["command"], ["test_off"])
        self.assertEqual(self.calls.call_args.args[2]["device"], "test_ac")
        self.assertFalse(self.entity._reporting)

    async def test_learned_cooling_fallback_and_ifeel_clear(self):
        self.entity._config["enable_control"] = True
        await self.entity.async_set_fan_mode("medium")
        await self.entity.async_set_hvac_mode("cool")
        self.assertEqual(self.calls.call_args.args[2]["command"], ["test_cool_medium"])
        await self.entity.async_set_preset_mode("ifeel")
        self.assertEqual(self.entity._last_transport, "generated")
        self.assertTrue(self.entity._reporting)
        await self.entity.async_set_preset_mode("none")
        self.assertEqual(self.entity._last_transport, "generated")
        from behavior_daewoo.protocol import decode

        data = decode(self.calls.call_args.args[2]["command"][0])
        self.assertFalse(data[6] & 8)
        self.assertFalse(self.entity._reporting)

    async def test_unload_prevents_queued_reports(self):
        await self.entity.async_start_sensor_updates()
        await self.entity.async_will_remove_from_hass()
        self.entity._last_attempt_mono -= 181
        await self.entity._async_report()
        self.assertEqual(self.calls.call_count, 1)
        with self.assertRaises(HomeAssistantError):
            await self.entity.async_start_sensor_updates()

    async def test_remote_outage_disarms_until_explicit_restart(self):
        await self.entity.async_start_sensor_updates()
        self.states["remote.test_transmitter"] = state("unavailable")
        self.entity._state_changed(None)
        self.assertFalse(self.entity._reporting)
        self.assertFalse(self.entity.available)
        self.states["remote.test_transmitter"] = state("on")
        await self.entity._tick(None)
        self.assertEqual(self.calls.call_count, 1)
        await self.entity.async_start_sensor_updates()
        self.assertEqual(self.calls.call_count, 2)
