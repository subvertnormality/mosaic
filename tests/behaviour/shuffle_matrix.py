"""Native shuffle controls with rational musical timelines, never output goldens."""
from fractions import Fraction as F

# Eight outgoing interval weights, starting at the first played step. These are
# the shipped musical feel definitions (README Swing/Shuffle; Cyrene attribution
# in lib/clock/m_lattice.lua), expressed separately from scheduler arithmetic.
# A bar has 384 pulses; at /1 each eight-interval phrase totals 192 pulses.
FEELS = {
 'Drunk': [(9,[3,2,2,2,3,2,2,2]),(7,[2,2,1,2,2,2,1,2]),(5,[2,1,1,1,2,1,1,1]),(6,[3,1,1,1,3,1,1,1]),(8,[4,2,1,1,4,2,1,1]),(9,[5,2,1,1,5,2,1,1])],
 'Smooth': [(18,[5,4,4,5,5,4,4,5]),(14,[4,3,3,4,4,3,3,4]),(10,[3,2,2,3,3,2,2,3]),(6,[2,1,1,2,2,1,1,2]),(16,[5,3,3,5,5,3,3,5]),(18,[7,3,2,6,7,3,2,6])],
 'Heavy': [(9,[2,2,1,4,2,2,1,4]),(7,[1,2,1,3,1,2,1,3]),(5,[1,1,1,2,1,1,1,2]),(6,[1,1,1,3,1,1,1,3]),(8,[1,2,1,4,1,2,1,4]),(9,[1,2,1,5,1,2,1,5])],
 'Clave': [(9,[3,2,2,3,2,2,2,2]),(7,[2,1,2,2,1,2,2,2]),(5,[2,1,1,2,1,1,1,1]),(12,[4,2,3,4,2,3,3,3]),(16,[6,3,4,5,3,4,4,3]),(18,[7,3,4,7,2,5,4,4])],
}
BASIS = ('9','7','5','6','8??','9??')


def pulse_plan(feel,basis,amount,count):
    denominator,weights=FEELS[feel][basis-1]
    intervals=[24+F(amount,100)*(F(96*w,denominator)-24) for w in weights]
    assert sum(intervals)==192 and min(intervals)>0
    # Independently specified constructor preview and cumulative nearest-pulse
    # contract; use rational sums, not the production per-cycle carry loop.
    initial=intervals[0]+F(49,100)
    total=initial;origin=initial.__floor__();pulses=[]
    for i in range(count):
        pulses.append(total.__floor__()-origin)
        total+=intervals[i%8]
    return pulses


def shuffle_matrix(c,feel):
    from note_accounting import note_pairs
    ui = c.ui
    ui.configure()
    ui.channel_page('clock_mods', 'midi_config', channel=1, confirm=False)
    ui.wait_for_header('clock_mods', channel=1)
    ui.select_field('shuffle', offset=1)
    ui.set_value(2)
    ui.press_key(3)                                               # X -> local Shuffle.
    ui.select_field('shuffle_feel', offset=1)
    ui.set_value(list(FEELS).index(feel)+1)
    ui.press_key(3)
    current_basis=0;current_amount=0
    # All bases at full amount, then a fractional basis at amount boundaries
    # and midpoint, followed by restoration. Amount0 must be straight timing.
    stages=[(basis,100) for basis in range(1,7)]+[(1,a) for a in (1,50,99,0,100)]
    for basis,amount in stages:
        ui.select_field('shuffle_basis', offset=1)
        ui.set_value(basis-current_basis)
        ui.press_key(3)
        ui.select_field('shuffle_amount', offset=1)
        # Establish lower bound before authoring a value; also proves clamping.
        ui.set_value(-101)
        ui.press_key(3)
        if amount:
            ui.set_value(amount)
            ui.press_key(3)
        ui.select_field('shuffle_amount', offset=-2)
        ui.wait_for_header('clock_mods', channel=1)
        before=c.snapshot()['midi_count']
        notes=c.playback([(1,[144,n,v]) for n,v in ((60,127),(62,117),(64,107),(65,97))],cycles=4,timeout=8)
        state=c.snapshot();events=[e for e in state['midi'] if e['index']>before]
        pairs=note_pairs(events)
        assert len(pairs)==len([e for e in events if e['bytes'][0]==144 and e['bytes'][2]>0]),'Missing/duplicate releases'
        field='logical_ns' if c.clock_mode=='controlled-experimental' else 'monotonic_ns'
        expected=pulse_plan(feel,basis,amount,len(notes));origin=notes[0][field]
        tolerance=2e-9 if c.clock_mode=='controlled-experimental' else .01
        errors=[(n[field]-origin)/1e9-p/144 for n,p in zip(notes,expected)]
        assert max(map(abs,errors))<=tolerance,dict(feel=feel,basis=BASIS[basis-1],amount=amount,expected_pulses=expected,errors=errors)
        # Every complete one-step gate ends at the following shuffled onset.
        for note,nxt in zip(notes,notes[1:]):
            off=[e for e in events if e['index']>note['index'] and e['bytes']==[128,note['bytes'][1],note['bytes'][2]]][0]
            assert abs(off[field]-nxt[field])/1e9<=tolerance,dict(feel=feel,basis=basis,amount=amount,note=note,off=off,next=nxt)
        c.results.append(dict(kind='shuffle-feel-basis-amount',feel=feel,basis=BASIS[basis-1],amount=amount,onsets=len(notes),expected_pulses=expected,max_phase_error_seconds=max(map(abs,errors)),complete_gates=len(notes)-1,release_pairs=len(pairs),passed=True))
        current_basis=basis;current_amount=amount
