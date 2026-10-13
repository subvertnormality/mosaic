"""Measure hold delivery bounds at the public norns-input boundary."""


def hold_sample_durations(clock_mode):
    """Use exact threshold edges in controlled time and safe host margins in real time."""
    if clock_mode == 'controlled-experimental':
        return .999999999, 1.000000001
    return .90, 1.05


def hold_input_bounds_sample(c, control, seconds, expected_long, interrupt=False):
    import time
    logical_start=c.logical_ns;t0=time.monotonic_ns()
    c.ui.control_edge(control,True);t1=time.monotonic_ns()
    if interrupt:
        c.elapse(.5);c.ui.tap_control('pattern_note_degree',(4,4));c.elapse(.6)
    else:c.elapse(seconds)
    t2=time.monotonic_ns();logical_end=c.logical_ns
    c.ui.control_edge(control,False);t3=time.monotonic_ns()
    lower=(t2-t1)/1e9;upper=(t3-t0)/1e9
    x=c.ui.control_cell(control)[0]
    sample=dict(kind='hold-input-bounds',x=x,interrupted=interrupt,
        expected_long=expected_long,logical_seconds=(logical_end-logical_start)/1e9,
        wall_lower_seconds=lower,wall_upper_seconds=upper)
    return sample


def assert_hold_input_boundary(clock_mode, sample):
    """Validate a sample after its failure evidence has been recorded."""
    if clock_mode=='real-time' and not sample['interrupted']:
        lower=sample['wall_lower_seconds'];upper=sample['wall_upper_seconds']
        assert lower>1 if sample['expected_long'] else upper<1, 'Host input delivery crossed the intended one-second hold boundary'
