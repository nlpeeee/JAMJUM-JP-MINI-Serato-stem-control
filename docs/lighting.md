# Pad lighting in the Serato XML

How [`JP-MIDI-MCP-v3.2.xml`](../config/JP-MIDI-MCP-v3.2.xml) lights the JP-MINI's pads, and how to change colours, brightness or what triggers a light. The helper script [`tools/jpmini_light.py`](../tools/jpmini_light.py) builds the packets for you (Python 3, no extra packages).

## The idea in one paragraph

The JP-MINI doesn't light its pads from ordinary MIDI notes or CCs coming back from Serato. It only takes colour changes through its own SysEx command. Serato can send any fixed SysEx message from a `<sysex>` block when a condition becomes true. So each pad gets **one fixed SysEx packet per state** ("vocals on" = magenta, "vocals off" = dark), and Serato picks which one to send by checking the stem's state.

## Anatomy of one light

```xml
<sysex key="7832453A0300...0313" force_output="true">   <!-- packet: pad 13 magenta -->
    <case>
        <condition>                                        <!-- WHEN deck 1 vocals = on -->
            <codfather_st deck_set="Default" deck_id="0" slot_id="0" cmp_value="on" />
        </condition>
        <userio event="output">                            <!-- WATCH deck 1 vocals for changes -->
            <codfather_st deck_set="Default" deck_id="0" slot_id="0">
                <translation action_on="any">
                    <alias name="on" value="0" />
                    <alias name="off" value="0" />
                </translation>
            </codfather_st>
        </userio>
    </case>
</sysex>
```

- **`key`**: the whole SysEx message as hex, **without** `F0` at the start and `F7` at the end. Serato adds those.
- **`force_output="true"`**: send it every time the watched function changes and the condition matches.
- **`<condition>`**: when to send. `cmp_value` must be the alias **name** (`on` / `off`). Numbers such as `1` / `0` get the whole file rejected.
- **`<userio event="output">`**: which function(s) Serato should watch. When one changes, it re-checks the condition. The alias values inside it aren't used for the light; we copy them as-is from a block that's known to load.
- `deck_id` is 0 for deck 1 and 1 for deck 2. `slot_id` on `codfather_st` is 0 Vocals, 1 Melody, 2 Bass, 3 Drums.

Every stem pad therefore has two `<sysex>` blocks: one with `cmp_value="on"` carrying the colour, and one with `cmp_value="off"` carrying the "off" colour (black, `0 0 0`).

## Combining conditions

- **AND:** put several functions inside one `<condition>`. All must match.
- **OR:** put several `<case>` blocks inside one `<sysex>`. Any one matching sends the packet.

The stem FX pads use both, because Serato rejected lighting them from the FX state itself. Instead they follow the stems each FX mutes:

| FX pad | Bright packet when (AND) | Dim packet when (OR) |
| --- | --- | --- |
| Vocal Echo | vocals off | vocals on |
| Instrumental Echo | melody off AND bass off AND drums off | melody on, OR bass on, OR drums on |
| Instrumental Braker | melody off AND bass off AND drums off | melody on, OR bass on, OR drums on |
| Drums Echo | drums off | drums on |

Example, the dim packet for deck 1 Instrumental Echo (shortened):

```xml
<sysex key="...dim green pad 10..." force_output="true">
    <case><condition><codfather_st deck_set="Default" deck_id="0" slot_id="1" cmp_value="on" /></condition>
          <userio event="output">...watch slots 1, 2, 3...</userio></case>
    <case><condition><codfather_st deck_set="Default" deck_id="0" slot_id="2" cmp_value="on" /></condition>
          <userio event="output">...</userio></case>
    <case><condition><codfather_st deck_set="Default" deck_id="0" slot_id="3" cmp_value="on" /></condition>
          <userio event="output">...</userio></case>
</sysex>
```

Side effect: muting those stems by hand also brightens the FX pad, because the light can't tell the difference.

## Colours and brightness

Each colour channel is **0 to 127** (red, green, blue). There's no separate brightness setting: a dimmer light is just smaller numbers in the same ratio.

| Light | Colour (R G B) |
| --- | --- |
| Vocals on | 100 0 100 (magenta) |
| Melody on | 0 100 100 (cyan) |
| Bass on | 0 0 100 (blue) |
| Drums on | 100 65 0 (amber) |
| Any stem off | 0 0 0 |
| Vocal Echo bright / dim | 127 127 127 / 45 45 45 |
| Instrumental Echo bright / dim | 0 127 0 / 0 45 0 |
| Instrumental Braker bright / dim | 127 0 0 / 45 0 0 |
| Drums Echo bright / dim | 127 83 0 / 45 29 0 |

The FX "dim" level was raised from 20 to 45 because 20 looked dull next to the stems. If you want everything brighter, scale the values towards 127.

## The packet (JP-MINI command 0x51)

You only need this if you want to understand or hand-check a `key`. The script does it for you.

1. **Payload, 55 bytes:**
   - byte 0: target pad, `0`-`15` (pad 1 at the bottom-left = 0, pad 16 at the top-right = 15).
   - bytes 1-48: 16 colour triples, one per pad, in **green, red, blue** order. Only the target pad's triple is applied; the others are filler.
   - bytes 49-54: six auxiliary bytes for the bank (`FF 00 00 41 30 1D` here, copied from the working preset).
2. **Frame:** `78 59 51` + payload length as 3 bytes little-endian (`37 00 00`) + payload + checksum, where checksum = `(~sum(payload)) & 0xFF`.
3. **7-bit packing:** MIDI SysEx data bytes can't have the top bit set, so the 62-byte frame is packed into a continuous stream of 7-bit bytes, least significant bit first (71 bytes). That hex string is the `key`. On the wire Serato adds `F0` and `F7`, making 73 bytes.

## Making your own lights

Print a key for one pad and colour:

```
python tools/jpmini_light.py packet --pad 13 --rgb 100 0 100
```

Print a ready-made on/off pair of `<sysex>` blocks that follow a stem (this one is exactly the deck 1 vocals light in the shipped file):

```
python tools/jpmini_light.py sysex --pad 13 --deck 1 --stem vocals --on 100 0 100
```

Check what an existing key does:

```
python tools/jpmini_light.py decode 7832453A0300...
```

Paste new `<sysex>` blocks just before `</midi>`. To change a colour, replace the `key` of the existing block for that pad and state. Then quit Serato, power-cycle the JP-MINI and load the preset.

Every key in the shipped XML decodes to the same pad, colour and auxiliary bytes as the script's output for that pad and colour.

## Caveats

- **Saving in Serato strips every `<sysex>` block.** Edit lighting by hand, and save any Serato-side mapping changes under a new name.
- **No bank number.** Command 0x51 always paints the bank that's currently showing, and the bank switch sends no MIDI. Serato lights will paint over banks 2 and 3 if you switch to them.
- **Not saved on the device.** The colours live in the controller's RAM. After a power cycle the pads show the KuSuite preset colours until Serato sends a change.
- **Restart before you debug.** After loading a changed lighting file, quit Serato and power-cycle the JP-MINI. A correct file once lit up and then left the pads dead until both were restarted.
- **One block at a time.** Serato only logs "MIDI XML is not valid" with no detail, so add and test lights in small steps.
