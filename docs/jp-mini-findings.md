# JAMJUM JP-MINI findings

Measured on one JP-MINI (firmware V4, identity "JPMINI" revision 04, KuSuite 5.2) on Windows 11 with Serato DJ Pro 5.0.0.950. Other units or firmware may differ.

## Hardware

- Made by KUWEE Technology (USB manufacturer string). JieLi AC632N chip.
- 16 RGB pads in 3 banks, plus three keys (Play, Stop, Circle) and a bank switch.
- USB MIDI with three cables each way, which Windows shows as `JP-Mini`, `MIDIIN2 (JP-Mini)` and `MIDIIN3 (JP-Mini)`.

## Pads

- Numbered from the bottom-left, rows of four going up. Logical pad 0 is bottom-left, 15 is top-right.
- In this preset bank 1 sends CC 36 to 51 on channel 10 in CC Toggle mode (127 on one press, 0 on the next).
- Factory note mode: Note On channel 10, velocity-sensitive, release sent as Note On velocity 0.

## The double-send problem, and MCP mode

In normal mode **every pad press is sent on two ports**, `JP-Mini` and `MIDIIN2 (JP-Mini)`, about 9 ms apart. Serato listens to both and cannot ignore one, so each press arrived twice. Stems turned off but never came back on, because the second copy undid the first while the stem was fading in.

A single-port bridge through a virtual MIDI port confirmed that was the whole cause. The native fix is **MCP mode**: bit 7 of each pad's first config byte, shown in KuSuite's pad editor as **MCP / MCU** and labelled `MCP-` in the pad list. In MCP mode the pad sends on the third port (`MIDIIN3`) only. CC Toggle values are unchanged. In note mode MCP uses a fixed velocity of 127.

The keys have the same bit. In this preset Circle's short press is in MCP mode, so quantize gets one message per press.

## Keys

| Key | Short press | Long press |
| --- | --- | --- |
| Play | CC 22 | CC 27 |
| Stop | CC 23 | CC 28 |
| Circle | CC 24 | CC 29 |

All are value 127 on channel 1. **No release message is ever sent**, so a key can't be used as a hold or momentary control, and a long press is a separate message rather than a held short press.

## Banks

- Switching banks sends **no MIDI**. The computer can't tell which bank is showing.
- Factory/preset layout: bank 1 CC/notes 36 to 51, bank 2 52 to 67, bank 3 68 to 83.

## Lighting from the computer

- The pads are true RGB, 0 to 127 per channel.
- They don't respond to plain Note/CC feedback. They're lit with a vendor SysEx command (command `0x51`). Serato can send it from a `<sysex>` block.
- Frame: `78 59 CMD LEN(3 bytes, little-endian) PAYLOAD CHECKSUM`, checksum `(~sum(payload)) & 0xFF`, then the whole frame is packed LSB-first into 7-bit bytes between `F0` and `F7`. A command `0x51` message is 73 bytes on the wire.
- Command `0x51` payload (55 bytes): target pad (0 to 15, or `FF` for all), then 16 colour triples in **green, red, blue** order, then 6 auxiliary bytes for the active bank. Only the target pad's triple is applied when a single pad is given.
- **There's no bank field.** The command writes the colours of whichever bank is showing, in RAM. Combined with the silent bank switch, that's why this setup uses bank 1 only: Serato's lights would paint over banks 2 and 3. An attempt to track the bank through a spare Serato setting failed.
- The colours aren't saved to the device. They're gone after a power cycle until Serato sends them again.
- Firmware applies its own logical-to-physical LED order, so send logical pad numbers.

## Practical tips

- Quit Serato before unplugging the JP-MINI. On Windows 11 24H2/25H2 the new MIDI service could hang on disconnect (a known Serato issue at the time).
- After loading a new lighting preset, restart Serato and power-cycle the JP-MINI before judging it.
