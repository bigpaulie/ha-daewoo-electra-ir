"""Setup validation with HA interface doubles; no installed HA or IR required."""

import importlib
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace

from ha_stub import install, module

install()


class ConfigFlowBase:
    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__()


module(
    "homeassistant.config_entries",
    ConfigEntry=object,
    ConfigFlow=ConfigFlowBase,
    OptionsFlow=object,
)
registry_module = module(
    "homeassistant.helpers.entity_registry", async_get=lambda hass: hass.registry
)
module("homeassistant.helpers.selector")
root = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "config_daewoo",
    root / "custom_components/daewoo_electra_ir/__init__.py",
    submodule_search_locations=[str(root / "custom_components/daewoo_electra_ir")],
)
package = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = package
spec.loader.exec_module(package)
flow = importlib.import_module("config_daewoo.config_flow")


class ConfigValidationTests(unittest.TestCase):
    def setUp(self):
        self.remote = SimpleNamespace(id="test-registry-id", platform="broadlink")
        self.hass = SimpleNamespace(
            registry=SimpleNamespace(async_get=lambda entity: self.remote),
            states=SimpleNamespace(get=lambda entity: SimpleNamespace(state="20")),
        )
        self.data = {
            **flow.DEFAULTS,
            "remote_entity": "remote.test_transmitter",
            "temperature_sensor": "sensor.test_temperature",
        }

    def test_no_installation_entity_defaults(self):
        self.assertNotIn("remote_entity", flow.DEFAULTS)
        self.assertNotIn("temperature_sensor", flow.DEFAULTS)
        self.assertFalse(flow.DEFAULTS["learned_fallback"])
        self.assertEqual(flow.validate(self.hass, self.data), {})

    def test_fallback_requires_group_and_mapping(self):
        self.data["learned_fallback"] = True
        self.assertEqual(flow.validate(self.hass, self.data), {"learned_device": "empty_device"})
        self.data["learned_device"] = "test_group"
        self.assertEqual(flow.validate(self.hass, self.data), {"base": "no_learned_commands"})
        self.data["off_command"] = "test_off"
        self.assertEqual(flow.validate(self.hass, self.data), {})

    def test_missing_or_non_broadlink_remote_is_rejected(self):
        self.remote.platform = "other"
        self.assertEqual(flow.validate(self.hass, self.data), {"remote_entity": "not_broadlink"})
        self.remote = None
        self.assertEqual(flow.validate(self.hass, self.data), {"remote_entity": "not_broadlink"})

    def test_invalid_name_missing_sensor_and_age(self):
        self.data["name"] = " "
        self.assertEqual(flow.validate(self.hass, self.data), {"name": "empty_name"})
        self.data["name"] = "Test AC"
        self.hass.states.get = lambda entity: None
        self.assertEqual(
            flow.validate(self.hass, self.data), {"temperature_sensor": "missing_sensor"}
        )
        self.hass.states.get = lambda entity: SimpleNamespace(state="20")
        self.data["report_interval"] = 600
        self.data["sensor_max_age"] = 300
        self.assertEqual(flow.validate(self.hass, self.data), {"sensor_max_age": "age_too_short"})
