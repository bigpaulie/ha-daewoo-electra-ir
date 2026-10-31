"""Offline protocol validation against captures and independent known payloads."""

import base64
import importlib.util
import itertools
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "test_protocol_impl", ROOT / "custom_components/daewoo_electra_ir/protocol.py"
)
p = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = p
spec.loader.exec_module(p)
CAPTURES = json.loads((ROOT / "fixtures/captures.json").read_text())


class ProtocolTests(unittest.TestCase):
    def test_real_captures(self):
        expected = {
            "manual_ifeel_on": "c387160ea000285f0020001ed3",
            "manual_ifeel_off": "c387111ba00020000020001e74",
            "sensor_23": "c3871279600088610020001e5c",
            "sensor_25": "c387134f600088630020001e35",
        }
        for name, code in CAPTURES.items():
            self.assertEqual(p.decode(code).hex(), expected[name])
            self.assertEqual(p.ticks_to_packet(p.packet_to_ticks(code)), code)

    def test_tested_21_and_expected_28(self):
        hardware = json.loads((ROOT / "fixtures/hardware_tests.json").read_text())
        self.assertEqual(p.decode(hardware["tested_21"]), p.sensor_frame(21))
        self.assertEqual(p.sensor_frame(21).hex(), "c38712796000885f0020001e5a")
        self.assertEqual(p.sensor_frame(28).hex(), "c3871279600088660020001e61")

    def test_sensor_only_changes_measurement_and_checksum(self):
        wave = p.Waveform.from_capture(CAPTURES["sensor_23"])
        for temp in range(51):
            with self.subTest(temp=temp):
                data = p.sensor_frame(temp)
                self.assertEqual(data[7], temp + 74)
                self.assertEqual(data[:7], p.SENSOR_TEMPLATE[:7])
                self.assertEqual(data[8:12], p.SENSOR_TEMPLATE[8:12])
                self.assertTrue(data[3] & 64)
                self.assertEqual(p.decode(wave.encode(data)), data)

    def test_exhaustive_control_fields(self):
        wave = p.Waveform.from_capture(CAPTURES["manual_ifeel_on"])
        for mode, fan, target, power, ifeel in itertools.product(
            p.MODES, p.FANS, range(16, 33), [False, True], [False, True]
        ):
            data = p.control_frame(
                mode, target, fan, power=power, sensor_temperature=21 if ifeel else None
            )
            self.assertEqual(data[1] >> 3, target - 8)
            self.assertEqual(data[4] >> 5, p.FANS[fan])
            self.assertEqual(data[6] >> 5, p.MODES[mode])
            self.assertEqual(bool(data[9] & 32), power)
            self.assertEqual(bool(data[6] & 8), ifeel and power)
            self.assertFalse(data[3] & 64)
            self.assertEqual(data[12], sum(data[:12]) % 256)
            self.assertEqual(p.decode(wave.encode(data)), data)
            # Preserved unknown fields; no new swing/light/timer features inferred.
            for index in (0, 2, 8, 10, 11):
                self.assertEqual(data[index], p.MANUAL_TEMPLATE[index])

    def test_upstream_real_example(self):
        # IRremoteESP8266 test/ir_Electra_test.cpp RealExampleDecode, issue #527.
        data = bytes.fromhex("c3 87 f6 28 60 00 20 00 00 20 00 05 0d")
        self.assertEqual(p.validate_frame(data), data)
        result = p.describe(data)
        self.assertEqual(result["setpoint_c"], 24)
        self.assertEqual(result["mode_code"], 1)
        self.assertEqual(result["fan_code"], 3)
        self.assertFalse(result["ifeel"])

    def test_broadlink_layout_and_independent_bit_order(self):
        wave = p.Waveform.from_capture(CAPTURES["sensor_23"])
        raw = base64.b64decode(wave.encode(p.sensor_frame(28)))
        self.assertEqual(raw[:2], b"\x26\x00")
        self.assertEqual(int.from_bytes(raw[2:4], "little"), len(raw) - 4)
        ticks = p.packet_to_ticks(base64.b64encode(raw).decode())
        self.assertEqual(ticks[:2], list(wave.ticks[:2]))
        self.assertEqual(ticks[-2:], list(wave.ticks[-2:]))
        # Decode independently, MSB-string groups reversed per byte (LSB on air).
        bitstring = "".join("1" if v > 35 else "0" for v in ticks[3:210:2])
        decoded = bytes(int(bitstring[i : i + 8][::-1], 2) for i in range(0, 104, 8))
        self.assertEqual(decoded.hex(), "c3871279600088660020001e61")

    def test_invalid_inputs(self):
        for value in [float("nan"), float("inf"), -1, 50.01]:
            with self.assertRaises(ValueError):
                p.sensor_frame(value)
        for value in [15.9, 32.1, float("nan")]:
            with self.assertRaises(ValueError):
                p.control_frame("cool", value, "low")
        for code in ["not base64", "JgAAAQ==", base64.b64encode(b"\x26\x00\x01\x00\x00").decode()]:
            with self.assertRaises(ValueError):
                p.decode(code)
        with self.assertRaises(ValueError):
            p.control_frame("unsupported", 24, "auto")
        with self.assertRaises(ValueError):
            p.control_frame("cool", 24, "turbo")
        with self.assertRaises(ValueError):
            p.validate_frame(bytes.fromhex("c3871279600088660020001e60"))

    def test_half_up(self):
        self.assertEqual(p.whole_temperature(20.5, 0, 50), 21)
        self.assertEqual(p.whole_temperature(20.49, 0, 50), 20)
