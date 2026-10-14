#!/usr/bin/env python3
"""Make or decode JP-MINI pad-colour SysEx for Serato <sysex key="..."> blocks.

Examples:
  python jpmini_light.py packet --pad 13 --rgb 100 0 100
  python jpmini_light.py sysex --pad 13 --on 100 0 100 --deck 1 --stem vocals
  python jpmini_light.py decode 7832453A0300...

Pads are numbered 1-16 from the bottom-left, rows of four going up (the same
numbering as the README). Colour values are 0-127 per channel.
"""
import argparse

FILLER = bytes([0x41, 0x30, 0x1D])            # GRB of the other 15 pads (ignored by the device)
AUX = bytes([0xFF, 0x00, 0x00, 0x41, 0x30, 0x1D])  # 6 auxiliary bytes copied from the working preset
STEMS = {'vocals': 0, 'melody': 1, 'bass': 2, 'drums': 3}


def pack7(data):
    acc = bits = 0
    out = bytearray()
    for b in data:
        acc |= b << bits
        bits += 8
        while bits >= 7:
            out.append(acc & 127)
            acc >>= 7
            bits -= 7
    if bits:
        out.append(acc & 127)
    return bytes(out)


def unpack7(data):
    acc = bits = 0
    out = bytearray()
    for b in data:
        acc |= b << bits
        bits += 7
        while bits >= 8:
            out.append(acc & 255)
            acc >>= 8
            bits -= 8
    return bytes(out)


def packet(pad, rgb):
    """Serato key (hex, no F0/F7) that sets one pad (1-16) to rgb (0-127 each)."""
    if not 1 <= pad <= 16:
        raise SystemExit('pad must be 1-16')
    if any(not 0 <= v <= 127 for v in rgb):
        raise SystemExit('colour values must be 0-127')
    logical = pad - 1
    r, g, b = rgb
    triples = bytearray(FILLER * 16)
    triples[3 * logical:3 * logical + 3] = bytes([g, r, b])   # device wants green, red, blue
    payload = bytes([logical]) + bytes(triples) + AUX          # 55 bytes
    raw = b'\x78\x59\x51' + len(payload).to_bytes(3, 'little') + payload
    raw += bytes([(~sum(payload)) & 0xFF])
    return pack7(raw).hex().upper()


def decode(key):
    raw = unpack7(bytes.fromhex(key.replace(' ', '')))
    payload = raw[6:6 + int.from_bytes(raw[3:6], 'little')]
    pad = payload[0]
    g, r, b = payload[1 + 3 * pad:4 + 3 * pad]
    return {'command': hex(raw[2]), 'pad': pad + 1, 'rgb': (r, g, b)}


def watch(deck, slot, indent):
    sp = ' ' * indent
    return (f'{sp}<codfather_st deck_set="Default" deck_id="{deck}" slot_id="{slot}">\n'
            f'{sp}    <translation action_on="any">\n'
            f'{sp}        <alias name="on" value="0" />\n'
            f'{sp}        <alias name="off" value="0" />\n'
            f'{sp}    </translation>\n{sp}</codfather_st>\n')


def sysex_block(key, deck, slot, state):
    return (f'    <sysex key="{key}" force_output="true">\n'
            '        <case>\n            <condition>\n'
            f'                <codfather_st deck_set="Default" deck_id="{deck}" slot_id="{slot}" cmp_value="{state}" />\n'
            '            </condition>\n            <userio event="output">\n'
            + watch(deck, slot, 16) +
            '            </userio>\n        </case>\n    </sysex>\n')


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest='cmd', required=True)
    p = sub.add_parser('packet', help='print the key for one pad and colour')
    p.add_argument('--pad', type=int, required=True)
    p.add_argument('--rgb', type=int, nargs=3, required=True, metavar=('R', 'G', 'B'))
    s = sub.add_parser('sysex', help='print on/off <sysex> blocks that follow a stem')
    s.add_argument('--pad', type=int, required=True)
    s.add_argument('--deck', type=int, choices=[1, 2, 3, 4], required=True)
    s.add_argument('--stem', choices=STEMS, required=True)
    s.add_argument('--on', type=int, nargs=3, required=True, metavar=('R', 'G', 'B'))
    s.add_argument('--off', type=int, nargs=3, default=[0, 0, 0], metavar=('R', 'G', 'B'))
    d = sub.add_parser('decode', help='show which pad and colour a key sets')
    d.add_argument('key')
    a = ap.parse_args()
    if a.cmd == 'packet':
        print(packet(a.pad, a.rgb))
    elif a.cmd == 'sysex':
        deck, slot = a.deck - 1, STEMS[a.stem]
        print(sysex_block(packet(a.pad, a.on), deck, slot, 'on') +
              sysex_block(packet(a.pad, a.off), deck, slot, 'off'), end='')
    else:
        print(decode(a.key))


if __name__ == '__main__':
    main()
