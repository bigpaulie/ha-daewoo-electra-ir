# Protocol and fixtures

This implementation uses an ELECTRA_AC-compatible 104-bit / 13-byte frame with least-significant-bit-first encoding within each byte. It is scoped to the contributed profile, not all Daewoo products.

| Anonymized fixture | Decoded payload | ELECTRA interpretation |
|---|---|---|
| manual_ifeel_on | `C3 87 16 0E A0 00 28 5F 00 20 00 1E D3` | Full state: COOL 24°C, auto fan, IFeel on, sensor 21°C |
| manual_ifeel_off | `C3 87 11 1B A0 00 20 00 00 20 00 1E 74` | Full state: COOL 24°C, auto fan, IFeel off |
| sensor_23 | `C3 87 12 79 60 00 88 61 00 20 00 1E 5C` | Silent measured-temperature update, 23°C |
| sensor_25 | `C3 87 13 4F 60 00 88 63 00 20 00 1E 35` | Silent measured-temperature update, 25°C |

Fixture labels describe the decoded frames. They are not measurements independently taken by this package.

Sensor byte 7 is Celsius + `0x4A`. Byte 12 is the sum of bytes 0–11 modulo 256. Silent reports change only bytes 7 and 12 in the `sensor_23` template. Full-state controls modify the documented fields while preserving unknown fields. In a sensor-only frame, mode/power bits are retained from the capture and are not intended as control instructions.

The 21°C regression payload is `C3 87 12 79 60 00 88 5F 00 20 00 1E 5A`. Its contributed waveform matches the generated payload. The calculated 28°C payload is `C3 87 12 79 60 00 88 66 00 20 00 1E 61`; no original 28°C waveform is available for a direct comparison.

Broadlink IR packets start with `26 00`, followed by a little-endian payload length. Short durations use one count byte; long durations use `00` plus a big-endian 16-bit count. Conversion uses a 32.84µs tick. The encoder preserves captured header/marks/footer and uses median captured zero/one spaces. Normalized output need not be Base64-identical to a captured signal even when payload bytes match.

The manual IFeel-off fixture contains two noisy approximately 328µs marks. It is accepted only with valid length, header, spaces, footer and checksum, and is not used as a transmit template.

Generate or inspect offline; these tools never transmit:

```sh
python3 tools/ir_tool.py validate
python3 tools/ir_tool.py sensor 20.6
python3 tools/ir_tool.py control heat 24 low --sensor 21
```

References:

- [IRremoteESP8266 Electra fields](https://github.com/crankyoldgit/IRremoteESP8266/blob/master/src/ir_Electra.h)
- [Electra encoding and sensor-update semantics](https://github.com/crankyoldgit/IRremoteESP8266/blob/master/src/ir_Electra.cpp)
- [Independent upstream recorded test frame](https://github.com/crankyoldgit/IRremoteESP8266/blob/master/test/ir_Electra_test.cpp)
- [Broadlink pulse representation](https://github.com/mjg59/python-broadlink/blob/master/broadlink/remote.py)
- [Home Assistant Broadlink service](https://www.home-assistant.io/integrations/broadlink/)
