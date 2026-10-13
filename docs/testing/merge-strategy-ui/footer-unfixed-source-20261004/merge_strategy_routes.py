"""Public navigation to the shared five-choice Strategy selector.

Musical expectations remain in each caller. No private configuration is read
or edited here; each target is reached through C09's clamped E3 events.
"""
CHOICES=('SKIP','ONLY','ALL','FOUNDATION','FRAGMENTS')

def select_strategy(c,value,channel=1):
    c.ui.open_channel_task('merge')
    c.ui.expect_header('merge_detail',channel=channel)
    c.ui.select_row('trig_mode',1)
    for _ in range(5):c.ui.turn(3,-1)
    for _ in range(CHOICES.index(value)):c.ui.turn(3,1)
    c.ui.expect_selected_field('detail','Strategy',value)
    c.ui.select_row('active_strategy',2)
    c.ui.expect_selected_field('detail','Active',value)
    c.ui.select_row('trig_mode',1)


def foundation_rhythm(c,channel=1):
    # Save the explicitly assigned anchor before requesting Foundation.
    c.ui.channel_page('merge_shape',channel=channel)
    c.ui.expect_header('merge_shape',channel=channel)
    c.ui.select_row('rhythm',1);c.ui.press_key(3)
    c.ui.expect_header('merge_rhythm',channel=channel)
    c.ui.select_row('anchor',0);c.ui.turn(3,1);c.ui.press_key(3)
    select_strategy(c,'FOUNDATION',channel)
    c.ui.channel_page('merge_shape',channel=channel)
    c.ui.expect_header('merge_shape',channel=channel)
    c.ui.select_row('rhythm',1);c.ui.press_key(3)
    c.ui.expect_header('merge_rhythm',channel=channel)
    c.ui.select_row('anchor',0);c.ui.press_key(3)
