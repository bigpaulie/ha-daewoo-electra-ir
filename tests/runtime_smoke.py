"""Real Home Assistant runtime smoke tests with a fake remote service.

Run separately from the offline doubles, using a supported HA Python environment.
These tests do not load an entire HA installation or communicate with hardware.
"""

import importlib
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from homeassistant.config_entries import ConfigEntries
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er

from custom_components.daewoo_electra_ir import climate, config_flow
from custom_components.daewoo_electra_ir.const import DEFAULTS
from custom_components.daewoo_electra_ir.protocol import decode, sensor_frame


class RuntimeSmokeTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.directory = TemporaryDirectory()
        self.hass = HomeAssistant(self.directory.name)
        self.hass.config_entries = ConfigEntries(self.hass, {})
        await self.hass.config_entries.async_initialize()
        dr.async_setup(self.hass)
        await dr.async_load(self.hass, load_empty=True)
        registry = er.async_get(self.hass)
        await registry.async_load(load_empty=True)
        remote = registry.async_get_or_create(
            "remote", "broadlink", "synthetic-remote", suggested_object_id="runtime_remote"
        )
        self.data = {
            **DEFAULTS,
            "remote_entity": remote.entity_id,
            "temperature_sensor": "sensor.runtime_temperature",
        }
        self.hass.states.async_set(remote.entity_id, "on")
        self.hass.states.async_set(
            "sensor.runtime_temperature",
            "20.6",
            {"unit_of_measurement": "°C", "device_class": "temperature"},
        )
        self.hass.states.async_set("climate.existing_unit", "heat")
        self.calls = []

        async def capture(call):
            self.calls.append(dict(call.data))

        self.hass.services.async_register("remote", "send_command", capture)
        self.entity = climate.DaewooClimate(
            SimpleNamespace(entry_id="runtime-synthetic-entry", data=self.data, options={})
        )
        self.entity.hass = self.hass
        self.entity.entity_id = "climate.runtime_ac"
        self.entity.async_write_ha_state = lambda: None
        self.entity._active = True

    async def asyncTearDown(self):
        self.entity._active = False
        await self.hass.async_block_till_done()
        await self.hass.async_stop()
        self.directory.cleanup()

    async def test_actual_schema_required_entities_and_validation(self):
        schema = config_flow.schema(DEFAULTS)
        with self.assertRaises(config_flow.vol.Invalid):
            schema(DEFAULTS)
        selected = schema(self.data)
        self.assertEqual(config_flow.validate(self.hass, selected), {})
        self.assertNotIn("remote_entity", DEFAULTS)
        self.assertNotIn("temperature_sensor", DEFAULTS)

    async def test_sensor_only_with_real_state_and_service_objects(self):
        self.assertEqual(self.calls, [])
        await self.entity.async_start_sensor_updates()
        self.assertEqual(len(self.calls), 1)
        self.assertEqual(decode(self.calls[0]["command"][0]), sensor_frame(21))
        self.assertEqual(self.calls[0]["entity_id"], self.data["remote_entity"])
        self.assertEqual(self.hass.states.get("climate.existing_unit").state, "heat")
        self.assertIsNone(self.entity.hvac_mode)
        await self.entity.async_stop_sensor_updates()
        self.assertFalse(self.entity._reporting)
        self.assertEqual(len(self.calls), 1)

    async def test_full_state_real_climate_properties(self):
        self.entity._config["enable_control"] = True
        await self.entity.async_set_temperature(temperature=25, hvac_mode="heat")
        self.assertEqual(self.entity.hvac_mode.value, "heat")
        self.assertEqual(self.entity.native_target_temperature, 25)
        self.assertEqual(self.entity.fan_mode, "auto")
        await self.entity.async_set_preset_mode("ifeel")
        self.assertTrue(self.entity._reporting)
        await self.entity.async_set_preset_mode("none")
        self.assertFalse(decode(self.calls[-1]["command"][0])[6] & 8)

    async def test_lifecycle_hooks_without_automatic_transmission(self):
        self.entity._active = False
        with patch.object(self.entity, "async_get_last_state", new=AsyncMock(return_value=None)):
            await self.entity.async_added_to_hass()
        self.assertEqual(self.calls, [])
        self.assertTrue(self.entity._active)
        await self.entity.async_will_remove_from_hass()
        self.assertFalse(self.entity._active)


if __name__ == "__main__":
    print("Runtime:", importlib.import_module("homeassistant.const").__version__)
    unittest.main(verbosity=2)
