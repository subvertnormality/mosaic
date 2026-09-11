"""Note Dashboard after a grid channel select (README 679: "On the Norns first page in the
channel mode you can see the last played notes on the currently selected channel").

Selecting a channel on the grid resets the dashboard to "no note played". No note has
velocity -1 or length -1, so the Vel and Len cells must show the same absence marker the
Note cell shows, "X" (the marker itself is characterisation, not manual text). After the
channel plays, the cells show a played note's values again.
"""
import base64

CELLS = (('Note', 0), ('Vel', 25), ('Len', 50))


def dashboard_cells(c, candidates):
    from frame_oracle import render
    pixels = base64.b64decode(c.snapshot()['frame']['pixels_base64'])
    labels = render([(0, 18, 1, 'Note'), (25, 18, 1, 'Vel'), (50, 18, 1, 'Len')])
    label_idx = [(y*128+x)*4+k for y in range(11, 19) for x in range(75) for k in range(3)]
    out = {'labels': all(pixels[i] == labels[i] for i in label_idx)}
    for name, x in CELLS:
        idx = [(y*128+xx)*4+k for y in range(19, 29) for xx in range(x, x+24) for k in range(3)]
        hit = [t for t in candidates[name] if all(pixels[i] == render([(x, 26, 1, t)])[i] for i in idx)]
        out[name] = hit[0] if len(hit) == 1 else ('?' if not hit else '|'.join(hit))
    return out


def dashboard_channel_select(c):
    absent = {'Note': ['X', '-1'], 'Vel': ['X', '-1'], 'Len': ['X', '-1.0', '-1']}
    c.configure(); c.tap(3, 8)
    c.enc(1, -20)
    for _ in range(10):
        if dashboard_cells(c, absent)['labels']: break
        c.enc(1, 1)
    else:
        raise AssertionError('Note Dashboard not found')
    for channel in (2, 1):
        c.tap(channel, 1); c.elapse(.3)
        cells = dashboard_cells(c, absent)
        c.results.append(dict(kind='dashboard-after-channel-select', channel=channel, **cells))
        assert cells == {'labels': True, 'Note': 'X', 'Vel': 'X', 'Len': 'X'}, ('Dashboard after selecting channel %d' % channel, cells)
    c.tap(1, 8); c.elapse(1.4); c.tap(1, 8)
    c.wait(lambda s: not s['midi_capture']['outstanding'])
    played = dashboard_cells(c, {'Note': ['X'], 'Vel': ['X', '-1'], 'Len': ['X', '-1.0', '-1']})
    c.results.append(dict(kind='dashboard-after-play', **played))
    assert played['labels'] and all(played[k] == '?' for k in ('Note', 'Vel', 'Len')), ('Dashboard still shows no note after playing', played)
    c.results.append(dict(kind='dashboard-channel-select-summary', passed=True))
