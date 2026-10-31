"""Pure ELECTRA_AC / Broadlink encoder using this Daewoo's captured templates.

Protocol field definitions cross-checked with IRremoteESP8266 ir_Electra.h/.cpp.
No network access, Home Assistant imports, or third-party dependencies.
"""

from __future__ import annotations

import base64
import binascii
import math
from dataclasses import dataclass
from statistics import median

TICK_US = 32.84
MODES = {"heat_cool": 0, "cool": 1, "dry": 2, "heat": 4, "fan_only": 6}
FANS = {"auto": 5, "low": 3, "medium": 2, "high": 1}
MANUAL_TEMPLATE = bytes.fromhex("c3 87 16 0e a0 00 28 5f 00 20 00 1e d3")
SENSOR_TEMPLATE = bytes.fromhex("c3 87 12 79 60 00 88 61 00 20 00 1e 5c")


def validate_frame(frame: bytes) -> bytes:
    if len(frame) != 13 or frame[0] != 0xC3:
        raise ValueError("Expected a 13-byte ELECTRA_AC frame starting with C3")
    if sum(frame[:12]) & 0xFF != frame[12]:
        raise ValueError("Invalid ELECTRA_AC checksum")
    return frame


def checksum(frame: bytearray) -> bytes:
    frame[12] = sum(frame[:12]) & 0xFF
    return validate_frame(bytes(frame))


def whole_temperature(value: float, minimum: int, maximum: int) -> int:
    """Round half up, rejecting out-of-range inputs rather than inventing readings."""
    if not math.isfinite(value) or not minimum <= value <= maximum:
        raise ValueError(f"Temperature must be finite and in {minimum}..{maximum} C")
    return math.floor(value + 0.5)


def control_frame(
    mode: str,
    temperature: float,
    fan: str,
    *,
    power: bool = True,
    sensor_temperature: float | None = None,
) -> bytes:
    """Build an absolute state. Leave undocumented fields as captured."""
    if mode not in MODES or fan not in FANS:
        raise ValueError("Unsupported HVAC mode or fan speed")
    target = whole_temperature(temperature, 16, 32)
    data = bytearray(MANUAL_TEMPLATE)
    data[1] = (data[1] & 0x07) | ((target - 8) << 3)
    data[3] &= ~0x40  # Full state, never a sensor-only update.
    data[4] = (data[4] & 0x1F) | (FANS[fan] << 5)
    data[5] &= ~0xC0  # Turbo and quiet are not exposed.
    data[6] = (data[6] & 0x17) | (MODES[mode] << 5)
    data[6] &= ~0x08
    data[7] = 0
    if sensor_temperature is not None and power:
        data[6] |= 0x08
        data[7] = whole_temperature(sensor_temperature, 0, 50) + 0x4A
    data[9] = (data[9] & ~0x20) | (0x20 if power else 0)
    return checksum(data)


def sensor_frame(temperature: float) -> bytes:
    """Change ONLY sensor temperature and checksum in the captured silent frame."""
    data = bytearray(SENSOR_TEMPLATE)
    data[7] = whole_temperature(temperature, 0, 50) + 0x4A
    return checksum(data)


def packet_to_ticks(code: str) -> list[int]:
    code = code.strip().removeprefix("b64:")
    try:
        raw = base64.b64decode(code, validate=True)
    except (binascii.Error, ValueError) as err:
        raise ValueError("Invalid Base64") from err
    if len(raw) < 4 or raw[0] != 0x26 or raw[1] != 0:
        raise ValueError("Expected an IR packet with no packet-level repeats")
    length = int.from_bytes(raw[2:4], "little")
    if length == 0 or len(raw) < 4 + length:
        raise ValueError("Truncated Broadlink payload")
    if any(raw[4 + length :]):
        raise ValueError("Unexpected nonzero Broadlink padding")
    payload = raw[4 : 4 + length]
    pulses, offset = [], 0
    while offset < length:
        ticks = payload[offset]
        offset += 1
        if ticks == 0:
            if offset + 2 > length:
                raise ValueError("Truncated extended pulse")
            ticks = int.from_bytes(payload[offset : offset + 2], "big")
            offset += 2
        if ticks == 0:
            raise ValueError("Zero-length pulse")
        pulses.append(ticks)
    return pulses


def ticks_to_packet(ticks: list[int]) -> str:
    payload = bytearray()
    for tick in ticks:
        if not 1 <= tick <= 65535:
            raise ValueError("Pulse outside Broadlink range")
        if tick < 256:
            payload.append(tick)
        else:
            payload.extend(b"\x00" + tick.to_bytes(2, "big"))
    return base64.b64encode(b"\x26\x00" + len(payload).to_bytes(2, "little") + payload).decode()


def decode(code: str) -> bytes:
    """Strictly decode one captured 104-bit frame, including footer and checksum."""
    pulses = packet_to_ticks(code)
    if len(pulses) != 212:
        raise ValueError("Expected one ELECTRA_AC frame (212 durations)")
    for actual, expected in [(pulses[0], 9166), (pulses[1], 4470)]:
        if abs(actual * TICK_US - expected) > expected * 0.35:
            raise ValueError("Invalid ELECTRA_AC header")
    data = bytearray(13)
    for bit in range(104):
        mark, space = (p * TICK_US for p in pulses[2 + bit * 2 : 4 + bit * 2])
        if not 300 <= mark <= 950:
            raise ValueError("Invalid bit mark")
        if 250 <= space <= 950:
            value = 0
        elif 1200 <= space <= 2200:
            value = 1
        else:
            raise ValueError("Invalid bit space")
        data[bit // 8] |= value << (bit % 8)
    if not 350 <= pulses[-2] * TICK_US <= 950 or pulses[-1] * TICK_US < 15000:
        raise ValueError("Invalid ELECTRA_AC footer")
    return validate_frame(bytes(data))


@dataclass(frozen=True)
class Waveform:
    """Preserve captured marks, header, footer; replace data spaces only."""

    ticks: tuple[int, ...]
    zero: int
    one: int

    @classmethod
    def from_capture(cls, code: str) -> Waveform:
        decode(code)
        pulses = packet_to_ticks(code)
        spaces = pulses[3:210:2]
        return cls(
            tuple(pulses),
            int(median(p for p in spaces if p * TICK_US < 1100)),
            int(median(p for p in spaces if p * TICK_US > 1100)),
        )

    def encode(self, frame: bytes) -> str:
        validate_frame(frame)
        pulses = list(self.ticks)
        for bit in range(104):
            pulses[3 + bit * 2] = self.one if frame[bit // 8] & (1 << (bit % 8)) else self.zero
        return ticks_to_packet(pulses)


def describe(frame: bytes) -> dict:
    validate_frame(frame)
    return {
        "hex": frame.hex(" "),
        "checksum_valid": True,
        "power": bool(frame[9] & 0x20),
        "setpoint_c": (frame[1] >> 3) + 8,
        "mode_code": frame[6] >> 5,
        "fan_code": frame[4] >> 5,
        "ifeel": bool(frame[6] & 8),
        "sensor_update": bool(frame[3] & 0x40),
        "sensor_c": frame[7] - 0x4A if frame[7] >= 0x4A else None,
    }
