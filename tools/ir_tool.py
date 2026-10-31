"""Offline inspection / generation; never transmits IR."""

import argparse
import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
path = ROOT / "custom_components/daewoo_electra_ir/protocol.py"
spec = importlib.util.spec_from_file_location("daewoo_protocol", path)
protocol = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = protocol
spec.loader.exec_module(protocol)

parser = argparse.ArgumentParser(description=__doc__)
sub = parser.add_subparsers(dest="operation", required=True)
sub.add_parser("validate")
p = sub.add_parser("decode")
p.add_argument("base64")
p = sub.add_parser("sensor")
p.add_argument("temperature", type=float)
p = sub.add_parser("control")
p.add_argument("mode", choices=protocol.MODES)
p.add_argument("temperature", type=float)
p.add_argument("fan", choices=protocol.FANS)
p.add_argument("--off", action="store_true")
p.add_argument("--sensor", type=float)
args = parser.parse_args()
captures = json.loads((ROOT / "fixtures/captures.json").read_text())
try:
    if args.operation == "validate":
        result = {name: protocol.describe(protocol.decode(code)) for name, code in captures.items()}
        hardware = json.loads((ROOT / "fixtures/hardware_tests.json").read_text())
        result["tested_21"] = protocol.describe(protocol.decode(hardware["tested_21"]))
        assert protocol.decode(hardware["tested_21"]) == protocol.sensor_frame(21)
        for temp in range(51):
            frame = protocol.sensor_frame(temp)
            wave = protocol.Waveform.from_capture(captures["sensor_23"])
            assert protocol.decode(wave.encode(frame)) == frame
    elif args.operation == "decode":
        result = protocol.describe(protocol.decode(args.base64))
    else:
        sensor = args.operation == "sensor"
        frame = (
            protocol.sensor_frame(args.temperature)
            if sensor
            else protocol.control_frame(
                args.mode,
                args.temperature,
                args.fan,
                power=not args.off,
                sensor_temperature=args.sensor,
            )
        )
        wave = protocol.Waveform.from_capture(
            captures["sensor_23" if sensor else "manual_ifeel_on"]
        )
        result = {**protocol.describe(frame), "command": "b64:" + wave.encode(frame)}
    print(json.dumps(result, indent=2))
except (ValueError, AssertionError) as err:
    parser.exit(1, f"Validation failed: {err}\n")
