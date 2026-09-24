"""Note Dashboard after a grid channel select (README 679: "On the Norns first page in the
channel mode you can see the last played notes on the currently selected channel").

Selecting a channel on the grid resets the dashboard to "no note played". No note has
velocity -1 or length -1, so the Vel and Len cells must show the same absence marker the
Note cell shows, "X" (the marker itself is characterisation, not manual text). After the
channel plays, the cells show a played note's values again.

C06 OUTPUT (the live Note Dashboard) shows only its selected field, so each old cell is read
as its field (Root, Velocity, Length) after E2 selects it, exact label and value. A grid channel
select returns the live screen to the remembered Channel family, so OUTPUT is reopened through
Channel Tasks (navigation only) before it is read.
"""

FIELDS = (('Note', 'root'), ('Vel', 'velocity'), ('Len', 'length'))


def dashboard_cells(c, candidates):
    out = {}
    for name, field in FIELDS:
        out[name] = c.ui.output_field_value(field, candidates[name])
    return out


def dashboard_channel_select(c):
    absent = {'Note': ['X', '-1'], 'Vel': ['X', '-1'], 'Len': ['X', '-1.0', '-1']}
    c.configure(); c.tap(3, 8)
    c.ui.channel_page('note_dashboard')
    for channel in (2, 1):
        c.tap(channel, 1); c.elapse(.3)
        c.ui.channel_page('note_dashboard', channel=channel)
        cells = dashboard_cells(c, absent)
        c.results.append(dict(kind='dashboard-after-channel-select', channel=channel, **cells))
        assert cells == {'Note': 'X', 'Vel': 'X', 'Len': 'X'}, ('Dashboard after selecting channel %d' % channel, cells)
    c.tap(1, 8); c.elapse(1.4); c.tap(1, 8)
    c.wait(lambda s: not s['midi_capture']['outstanding'])
    played = dashboard_cells(c, {'Note': ['X'], 'Vel': ['X', '-1'], 'Len': ['X', '-1.0', '-1']})
    c.results.append(dict(kind='dashboard-after-play', **played))
    assert all(played[k] == '?' for k in ('Note', 'Vel', 'Len')), ('Dashboard still shows no note after playing', played)
    c.results.append(dict(kind='dashboard-channel-select-summary', passed=True))
