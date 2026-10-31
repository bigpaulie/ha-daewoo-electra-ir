"""Small HA interface doubles. These tests do NOT certify HA runtime compatibility."""

import sys
from datetime import datetime, timezone
from enum import Enum, IntFlag
from types import ModuleType, SimpleNamespace


def module(name, **attrs):
    obj = ModuleType(name)
    obj.__dict__.update(attrs)
    sys.modules[name] = obj
    return obj


class HVACMode(str, Enum):
    OFF = "off"
    HEAT = "heat"
    COOL = "cool"
    HEAT_COOL = "heat_cool"
    DRY = "dry"
    FAN_ONLY = "fan_only"

    def __str__(self):
        return self.value


class Features(IntFlag):
    TARGET_TEMPERATURE = 1
    FAN_MODE = 2
    PRESET_MODE = 4
    TURN_ON = 8
    TURN_OFF = 16


class ClimateEntity:
    async def async_added_to_hass(self):
        pass

    async def async_will_remove_from_hass(self):
        pass

    def async_write_ha_state(self):
        pass

    def async_on_remove(self, unsub):
        pass


class RestoreEntity:
    async def async_get_last_state(self):
        return None


class HomeAssistantError(Exception):
    pass


class ServiceValidationError(HomeAssistantError):
    pass


def install():
    module("probatio", Schema=lambda value: value)
    module("homeassistant")
    module("homeassistant.config_entries", ConfigEntry=object)
    module("homeassistant.components")
    module(
        "homeassistant.components.climate",
        ClimateEntity=ClimateEntity,
        ClimateEntityFeature=Features,
        HVACMode=HVACMode,
    )
    module(
        "homeassistant.const",
        ATTR_TEMPERATURE="temperature",
        UnitOfTemperature=SimpleNamespace(CELSIUS="°C"),
    )
    module("homeassistant.core", callback=lambda f: f, HomeAssistant=object)
    module(
        "homeassistant.exceptions",
        HomeAssistantError=HomeAssistantError,
        ServiceValidationError=ServiceValidationError,
    )
    module("homeassistant.helpers")
    module("homeassistant.helpers.entity_platform", async_get_current_platform=lambda: None)
    module(
        "homeassistant.helpers.event",
        async_track_state_change_event=lambda *args: lambda: None,
        async_track_time_interval=lambda *args: lambda: None,
    )
    module("homeassistant.helpers.restore_state", RestoreEntity=RestoreEntity)
    module("homeassistant.util")
    module("homeassistant.util.dt", utcnow=lambda: datetime.now(timezone.utc))

    def convert(value, from_unit, to_unit):
        if from_unit == "°F":
            return (value - 32) * 5 / 9
        if from_unit == "K":
            return value - 273.15
        if from_unit == "°C":
            return value
        raise ValueError("Unsupported unit")

    module(
        "homeassistant.util.unit_conversion", TemperatureConverter=SimpleNamespace(convert=convert)
    )
