"""Switching a channel from a MIDI device to an n.b. device without parameters
(user decision 2026-09-11 on suspected defect S4: switching should clear the device parameter
slots; reproduce with an n.b. device first).

README 546: a configured MIDI device's parameters are edited in the norns params menu, and any
value other than Off "will send that MIDI value directly to your MIDI device"; README 526: without
a configuration file the CC Device offers raw CC numbers. README 542: n.b. devices are picked from
the device picker. Channel 1 starts on the CC Device (the device the shared setup picks), whose
first own parameter, CC 1, follows the fourteen visible Mosaic stock parameters in the channel's
params group. Channel 1 is then switched to Jf Kit, an n.b. player that declares no parameters.
After the switch the group must end at the last stock parameter, Quantise Note Mask, and turning
E3 there must send no MIDI. The baseline keeps the CC Device's parameters (CC 1 onwards) in the
group, and a turn of CC 1 still sends CC 1.

The nb-audio profile cannot show this: its only n.b. player, Doubledecker, declares dozens of
parameters, so every slot after the stock parameters is re-hidden on a switch. Jf Kit comes
from the crow-jf profile (nb_jf at its pinned revision).
"""
import base64

STOCK_LAST = 'Quantise Note Mask'
STALE_FIRST = 'CC 1'


def _open_channel_group(c):
    from cases import menu_label
    c.key(1); c.enc(1, 4); c.key(3); menu_label(c, 'LEVELS >')
    roots = c.snapshot()['diagnostics']['parameter_roots']
    position = next(i for i, v in enumerate(roots) if v['id'] == 'midi_device_params_group_channel_1')
    c.enc(2, position); c.key(3); menu_label(c, 'Fixed Note')      # first visible stock parameter


def _selected(c, labels):
    from frame_oracle import selected_line
    c.elapse(.3); state = c.snapshot()
    return [label for label in labels if selected_line(state, label)]


def _controls_after(c, marker):
    return [(m['port'], m['bytes']) for m in c.snapshot()['midi'] if m['index'] > marker and 176 <= m['bytes'][0] <= 191]


def nb_device_switch_slots(c):
    from frame_oracle import render
    assert c.profile in ('crow-jf', 'mixed-outputs'), 'An n.b. player without parameters (Jf Kit) is required'
    c.configure(); c.screen_header('Ch. 1 Device Config')
    # Control: on the CC Device, CC 1 follows the stock parameters and a turn sends CC 1 to
    # channel 1's port (README 526, 546).
    _open_channel_group(c); c.enc(2, 14)
    seen = _selected(c, [STALE_FIRST, STOCK_LAST])
    assert seen == [STALE_FIRST], ('Configured device group', seen)
    marker = c.snapshot()['midi_count']; c.enc(3, 1); c.elapse(.3)
    sent = _controls_after(c, marker)
    assert sent and all(port == 1 and b[0] == 176 and b[1] == 1 for port, b in sent), ('CC 1 before the switch', sent)
    c.results.append(dict(kind='device-param-control', label=STALE_FIRST, sent=sent, passed=True))
    c.key(2); c.key(1); c.screen_header('Ch. 1 Device Config')
    expected = render([(10, 35, 15, 'Jf Kit')])
    indices = [(y*128+x)*4+k for y in range(27, 37) for x in range(10, 62) for k in range(3)]
    for _ in range(40):
        if all(base64.b64decode(c.snapshot()['frame']['pixels_base64'])[i] == expected[i] for i in indices): break
        c.enc(3, 1)
    else: raise AssertionError('Jf Kit not visible in device picker')  # README 542
    c.key(3); c.elapse(1)
    # The norns menu reopens on the params list where it was left, on channel 1's group, now
    # named after the new device.
    from cases import menu_label
    c.key(1); menu_label(c, 'MOSAIC CH 1: JF KIT'); c.key(3); menu_label(c, 'Fixed Note')
    # After the switch the group ends at the last stock parameter (user decision S4: switching
    # clears the slots; README 546 describes these parameters for configured MIDI devices).
    c.enc(2, 14)
    seen = _selected(c, [STALE_FIRST, STOCK_LAST])
    marker = c.snapshot()['midi_count']; c.enc(3, 1); c.elapse(.3)
    sent = _controls_after(c, marker)
    c.results.append(dict(kind='nb-switch-slots', selected=seen, sent=sent))
    assert seen == [STOCK_LAST], ('Group after switching to Jf Kit ends at', seen, 'E3 sent', sent)
    # No MIDI from the Jf Kit channel's params group (user decision S4).
    assert sent == [], ('MIDI sent from the Jf Kit params group', sent)
    c.key(2); c.key(1)
    c.results.append(dict(kind='nb-switch-slots-cleared', passed=True))
