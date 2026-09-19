"""Shift press to stop (MAN README 1062-1066): only a long press or shift (K1) stops."""

PHRASE={60:127,62:117,64:107,65:97}
LONG_PRESS_SECONDS=1 # m_grid.long_press sleeps one second before the long action

def shift_press_to_stop(c):
    from cases import set_mosaic_options
    c.configure()
    def onsets(state,marker):
        return [m for m in state['midi'] if m['index']>marker and m['bytes'][0]&240==144 and m['bytes'][2]>0]
    def check_phrase(notes):
        # Only the configured phrase: a gesture must not alter the music it guards.
        assert all(m['port']==1 and m['bytes'][0]==144 and PHRASE.get(m['bytes'][1])==m['bytes'][2] for m in notes),[m['bytes'] for m in notes]
    def start():
        marker=c.snapshot()['midi_count'];c.tap(1,8)
        c.wait(lambda s:len(onsets(s,marker))>=1,timeout=3)
    def still_playing(label):
        marker=c.snapshot()['midi_count'];c.elapse(.7) # four steps at 1/6 s
        state=c.wait(lambda s:len(onsets(s,marker))>=3,timeout=3)
        check_phrase(onsets(state,marker))
        c.results.append(dict(kind='stop-safety',stage=label,transport='playing',onsets_after_gesture=len(onsets(state,marker)),passed=True))
    def stopped(label):
        state=c.wait(lambda s:not s['midi_capture']['outstanding'],timeout=3)
        marker=state['midi_count'];c.elapse(.7)
        state=c.snapshot()
        assert not onsets(state,marker),dict(stage=label,late=[m['bytes'] for m in onsets(state,marker)])
        c.results.append(dict(kind='stop-safety',stage=label,transport='stopped',passed=True))
    def hold_play(seconds):
        c.action(type='grid',x=1,y=8,state=1)
        try:c.elapse(seconds)
        finally:c.action(type='grid',x=1,y=8,state=0)
        c.elapse(.06)
    def with_key(n,gesture):
        # norns delivers K1 to the script only after its 0.25 s menu threshold.
        c.action(type='key',n=n,state=1)
        try:c.elapse(.4 if n==1 else .1);gesture()
        finally:c.action(type='key',n=n,state=0)
        c.elapse(.06)
    # Default Off: an ordinary tap stops.
    start();still_playing('default-started');c.tap(1,8);stopped('default-tap')
    set_mosaic_options(c,[('Shift press to stop',True)])
    start();still_playing('on-tap-starts')
    c.tap(1,8);still_playing('on-short-tap-ignored')
    hold_play(LONG_PRESS_SECONDS-.1);still_playing('on-hold-below-threshold-ignored')
    with_key(1,lambda:c.tap(1,8));stopped('on-shift-K1-tap-stops')
    start();with_key(3,lambda:c.tap(1,8));still_playing('on-K3-tap-ignored')
    hold_play(LONG_PRESS_SECONDS+.1);stopped('on-long-press-stops')
    set_mosaic_options(c,[('Shift press to stop',False)])
    start();c.tap(1,8);stopped('off-again-tap-stops')
