"""Note Dashboard after a grid channel select (README 679: "On the Norns first page in the
channel mode you can see the last played notes on the currently selected channel").

Selecting a channel on the grid resets the dashboard to "no note played". No note has
velocity -1 or length -1, so the note and its velocity and length must all show the same
absence marker. After the channel plays, they show a played note's values again.

C06 OUTPUT (the live Note Dashboard) is a dashboard: the old Note cell is its Note row (the
note, then the chord voices that play) and the old Vel and Len cells are its Vel / Len row
("<vel> / <len>"); each row is read exactly, whole. With nothing played both read NO EVENT
(the owner's absence marker since 25 September 2026, characterisation; it was X). A grid
channel select returns the live screen to the remembered Channel family, so OUTPUT is
reopened through Channel Tasks (navigation only) before it is read.
"""

ABSENT = {'note': 'NO EVENT', 'vel_len': 'NO EVENT'}


def dashboard_rows(c):
    """The Note and Vel / Len rows: NO EVENT (nothing played) when shown, else '?'."""
    return {field: c.ui.output_field_value(field, [value]) for field, value in ABSENT.items()}


def dashboard_channel_select(c):
    c.configure(); c.tap(3, 8)
    c.ui.channel_page('note_dashboard', confirm=False); c.ui.expect_header('note_dashboard', channel=1)
    for channel in (2, 1):
        c.tap(channel, 1); c.elapse(.3)
        c.ui.channel_page('note_dashboard', channel=channel, confirm=False)
        c.ui.expect_header('note_dashboard', channel=channel)
        for field, value in ABSENT.items():
            c.ui.expect_output_field(field, value)
        c.results.append(dict(kind='dashboard-after-channel-select', channel=channel, **ABSENT))
    c.tap(1, 8); c.elapse(1.4); c.tap(1, 8)
    c.wait(lambda s: not s['midi_capture']['outstanding'])
    played = dashboard_rows(c)
    c.results.append(dict(kind='dashboard-after-play', **played))
    assert all(played[k] == '?' for k in ABSENT), ('Dashboard still shows no note after playing', played)
    c.results.append(dict(kind='dashboard-channel-select-summary', passed=True))
