# Writing Serato DJ Pro MIDI mapping XML by hand

Notes from building [`JP-MIDI-MCP-v3.2.xml`](../config/JP-MIDI-MCP-v3.2.xml) for Serato DJ Pro 5.0.0.950 on Windows. Things marked *(inferred)* weren't proven directly.

## File shape

Serato's own files look like this (note the leading space in `app`):

```xml
<midi app=" 5.0.0.950">
  <control channel="10" event_type="Control Change" data_type="Relative OnOff" control="44">
    <userio event="click">
      <codfather_fx deck_set="Default" deck_id="0" slot_id="0">
        <translation action_on="press" behaviour="toggle"/>
      </codfather_fx>
    </userio>
    <userio event="output">
      <codfather_fx deck_set="Default" deck_id="0" slot_id="0">
        <translation action_on="any">
          <alias name="on" value="127"/>
          <alias name="off" value="0"/>
        </translation>
      </codfather_fx>
    </userio>
  </control>
  <sysex key="HEX" force_output="true">
    <case>
      <condition>
        <codfather_st deck_set="Default" deck_id="0" slot_id="0" cmp_value="on"/>
      </condition>
      <userio event="output">
        <codfather_st deck_set="Default" deck_id="0" slot_id="0">...</codfather_st>
      </userio>
    </case>
  </sysex>
</midi>
```

- `channel` is 1-based (`"10"` = MIDI channel 10). JAMJUM's KuSuite counts from 0, so its "9" is the same channel. Getting this wrong by one gave pads that did nothing.
- `deck_id` is 0-based: 0 = deck 1, 1 = deck 2.
- `click` is input (controller → Serato). `output` is feedback (Serato → controller).

## Stem functions

| Function | What it is | Slots |
| --- | --- | --- |
| `codfather_st` | Stem on/off (mute) | 0 Vocals, 1 Melody, 2 Bass, 3 Drums |
| `codfather_fx` | Stem FX | 0 Vocal Echo, 1 Instrumental Echo, 2 Instrumental **Braker**, 3 Drums Echo |
| `codfather_ac` / `codfather_in` | Acapella / Instrumental | per deck |

"Braker" is Serato's own spelling in its UI. It never appears in the XML; the FX is chosen by `slot_id` only.

Serato's stem FX work by muting stems: Vocal Echo mutes vocals, Instrumental Echo and Instrumental Braker mute melody, bass and drums, and Drums Echo mutes drums. The stem buttons on screen change too.

## Conditions must use alias names

`<sysex>` blocks contain one or more `<case>` elements. Each case has a `<condition>` and an `<userio event="output">` listing the functions to watch. When the condition is true, Serato sends the SysEx in `key`.

- Several functions inside one `<condition>` are ANDed.
- Several `<case>` blocks under one `<sysex>` act as OR (any true case sends it).
- **If the function has named aliases (`on`/`off`), `cmp_value` must be the alias name.** A file with `cmp_value="1"` / `"0"` on `codfather_fx` was rejected outright. Serato's parser looks the value up in the alias map and does not fall back to a number.
- `codfather_st` with `cmp_value="on"` / `"off"` works and is what lights the pads here.
- Lighting pads from the `codfather_fx` state directly never worked for us, so the FX pads here are lit from the `codfather_st` stems that each FX mutes.

## SysEx output

- `key` is the message body as contiguous hex **without** `F0` and `F7`. Serato adds the framing; including it doubles it.
- `force_output="true"` makes Serato send it on every matching change.
- Use one fixed packet per pad per state (for example "vocals on" and "vocals off"), each chosen by its own condition.

## Input data types and behaviours

| Use | `data_type` | translation |
| --- | --- | --- |
| Pad that sends 127/0 alternately (CC Toggle) and should **set** state | none | `action_on="any" behaviour="explicit"` |
| Pad or key that should **flip** state on each press (stem FX, global toggles) | `Relative OnOff` | `action_on="press" behaviour="toggle"` |

Our key (Circle) sends only a press, never a release, so `press` + `toggle` is the only form that makes sense for it.

## Gotchas

- **Saving in Serato strips SysEx.** Any edit and save in Serato's MIDI panel rewrites the file without its `<sysex>` blocks. Save Serato edits under a new name and merge the `<control>` blocks back by hand.
- **Learning a global control per deck.** MIDI-learning quantize (a single global setting) created one toggle per deck, four in total. Four toggles on one press cancel out or race, so it sometimes took two presses. Keep one control block.
- **Stacked mappings.** Loading presets on top of each other left old bindings active. Serato's `AUTO_SAVE.xml` had four or five copies of some pad bindings. Load a preset once, and if things double up, quit Serato and start from a clean mapping.
- **Unhelpful errors.** A rejected file only logs "MIDI XML is not valid", with no line or element. Start from a block Serato wrote itself and add one block at a time.
- **Restart before debugging.** After loading a new lighting preset, quit Serato and power-cycle the controller before judging it. Our first test of a correct file lit once and then the pads went dead until both were restarted.
- **Hidden function names.** Serato stores most mapping function names obfuscated in its executable *(each byte is `ror(b ^ 0x10, index & 7)`)*, so `strings` won't find them. The reliable way to get a name is to MIDI-learn the control once in Serato, save under a new name and copy what it wrote.

## Vocabulary seen in Serato's executable

For reference, from static analysis of Serato DJ Pro 5.0.0.950 *(not all tested)*:

- `data_type`: `Absolute 7`, `Absolute 14`, `Relative Signed Bit`, `Relative Binary Offset`, `Relative 2's Complement`, `Relative 14 2's Complement`, `Relative OnOff`, `Wrapped`, `Absolute 14 Wrapped`, `Absolute 14 Wrapped Little Endian`.
- `action_on`: `press`, `release`, `any`.
- `behaviour`: `explicit`, `toggle`, `static`, `increment`, `decrement`, `increment_wrapped`, `decrement_wrapped`, `toggle_on_down`, `static_on_down` and more.
- Condition `operator`: `equal` (default), `not equal`, `less or equal`, `greater or equal`.
