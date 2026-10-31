"""UI setup; setup and options never transmit IR."""

from __future__ import annotations

try:
    import probatio as vol  # Home Assistant 2026.10
except ImportError:
    import voluptuous as vol  # Earlier supported Home Assistant releases
from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers import selector

from .const import DEFAULTS, DOMAIN


def schema(values: dict) -> vol.Schema:
    return vol.Schema(
        {
            vol.Required("name", default=values["name"]): str,
            (
                vol.Required("remote_entity", default=values["remote_entity"])
                if values.get("remote_entity")
                else vol.Required("remote_entity")
            ): selector.EntitySelector(
                selector.EntitySelectorConfig(domain="remote", integration="broadlink")
            ),
            (
                vol.Required("temperature_sensor", default=values["temperature_sensor"])
                if values.get("temperature_sensor")
                else vol.Required("temperature_sensor")
            ): selector.EntitySelector(
                selector.EntitySelectorConfig(domain="sensor", device_class="temperature")
            ),
            vol.Required("enable_control", default=values["enable_control"]): bool,
            vol.Required("learned_fallback", default=values["learned_fallback"]): bool,
            vol.Required("learned_device", default=values["learned_device"]): str,
            **{
                vol.Optional(key, default=values[key]): str
                for key in (
                    "off_command",
                    "cool_low_command",
                    "cool_medium_command",
                    "cool_high_command",
                )
            },
            vol.Required("report_interval", default=values["report_interval"]): vol.All(
                vol.Coerce(int), vol.Range(min=60, max=600)
            ),
            vol.Required("sensor_max_age", default=values["sensor_max_age"]): vol.All(
                vol.Coerce(int), vol.Range(min=300, max=86400)
            ),
        }
    )


def validate(hass, data):
    if not data["name"].strip():
        return {"name": "empty_name"}
    registry = er.async_get(hass)
    remote = registry.async_get(data["remote_entity"])
    if remote is None or remote.platform != "broadlink":
        return {"remote_entity": "not_broadlink"}
    if hass.states.get(data["temperature_sensor"]) is None:
        return {"temperature_sensor": "missing_sensor"}
    if data["learned_fallback"] and not data["learned_device"].strip():
        return {"learned_device": "empty_device"}
    if data["learned_fallback"] and not any(
        data.get(key, "").strip()
        for key in ("off_command", "cool_low_command", "cool_medium_command", "cool_high_command")
    ):
        return {"base": "no_learned_commands"}
    if data["sensor_max_age"] < data["report_interval"]:
        return {"sensor_max_age": "age_too_short"}
    return {}


class DaewooConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input=None):
        errors = {}
        if user_input is not None:
            errors = validate(self.hass, user_input)
            if not errors:
                unique = er.async_get(self.hass).async_get(user_input["remote_entity"]).id
                await self.async_set_unique_id(unique)
                self._abort_if_unique_id_configured()
                return self.async_create_entry(title=user_input["name"], data=user_input)
        return self.async_show_form(
            step_id="user", data_schema=schema({**DEFAULTS, **(user_input or {})}), errors=errors
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return DaewooOptionsFlow()


class DaewooOptionsFlow(config_entries.OptionsFlow):
    async def async_step_init(self, user_input=None):
        errors = {}
        if user_input is not None:
            errors = validate(self.hass, user_input)
            remote = er.async_get(self.hass).async_get(user_input["remote_entity"])
            if remote is not None and remote.id != self.config_entry.unique_id:
                errors["remote_entity"] = "remote_fixed"
            if not errors:
                return self.async_create_entry(title="", data=user_input)
        values = {
            **DEFAULTS,
            **self.config_entry.data,
            **self.config_entry.options,
            **(user_input or {}),
        }
        return self.async_show_form(step_id="init", data_schema=schema(values), errors=errors)
