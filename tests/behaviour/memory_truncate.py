"""Memory K1+K3 / K1+K2: jump, then forget the history (README Memory section)."""

def memory_truncate(c):
    ui = c.ui
    c.configure()
    ui.channel_page("memory", "midi_config", confirm=False)
    ui.expect_header("memory", channel=1)
    baseline=[(60,127),(62,117),(64,107),(65,97)]
    first=[(72,90),*baseline[1:]]
    both=[(72,90),(76,80),*baseline[2:]]
    third=[(72,90),(76,80),(79,70),(65,97)]
    def counter(current,total):
        ui.expect_memory_position(current,total)
    def phrase(label,values):
        c.playback([(1,[144,n,v]) for n,v in values],cycles=2)
        c.results.append(dict(kind='memory-truncate-phrase',stage=label,notes=values,passed=True))
    def record(step,note,velocity):
        ui.channel_page("masks", "memory", confirm=False)
        ui.expect_header("masks", channel=1)
        ui.record_key(step, note, velocity, hold_seconds=.05)
        c.elapse(.1)
        ui.channel_page("memory", "masks", confirm=False)
        ui.expect_header("memory", channel=1)
    def shift(n):
        # norns passes K1 to the script only after its 0.25 s menu threshold.
        with ui.hold_keys(1):
            c.elapse(.4)
            ui.press_key(n)
        c.elapse(.1)
    counter(0,0);phrase('baseline',baseline)
    record(1,72,90);record(2,76,80);counter(2,2);phrase('two-edits',both)
    ui.turn(3,-1);counter(1,2);phrase('undone-to-first',first)
    # K1+K3 from the middle: apply the latest action, then forget all history.
    shift(3);counter(0,0);phrase('shift-K3-applied',both)
    ui.turn(3,-1);counter(0,0);phrase('forgotten-E3-inert',both)
    ui.press_key(2);counter(0,0);phrase('forgotten-K2-inert',both)
    # A new action starts a fresh history whose beginning is the applied state.
    record(3,79,70);counter(1,1);phrase('fresh-history',third)
    # K1+K2: return to the beginning of this history, then forget it.
    shift(2);counter(0,0);phrase('shift-K2-undone',both)
    ui.press_key(3);counter(0,0);phrase('forgotten-K3-inert',both)
    ui.turn(3,1);counter(0,0);phrase('forgotten-E3-forward-inert',both)
    # K1+K2 from the middle of a two-action history also returns to its start.
    record(3,79,70);record(4,84,60);counter(2,2)
    ui.turn(3,-1);counter(1,2);phrase('second-history-middle',third)
    shift(2);counter(0,0);phrase('shift-K2-from-middle',both)
