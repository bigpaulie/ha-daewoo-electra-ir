"""Public defaults; installation-specific entities are selected during setup."""

DOMAIN = "daewoo_electra_ir"
DEFAULTS = {
    "name": "Daewoo AC IR",
    "enable_control": False,
    "learned_fallback": False,
    "learned_device": "",
    "off_command": "",
    "cool_low_command": "",
    "cool_medium_command": "",
    "cool_high_command": "",
    "report_interval": 180,
    "sensor_max_age": 1800,
}
PLATFORMS = ["climate"]
