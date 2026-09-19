"""Sinfonion software MIDI on the Norns2sinfonion port (README "Sinfonion Connect").

Independent contract (norns2sinfonion README): a program change on channel 1
sets the root, 2 the degree, 3 the mode and 4 the transposition; the program
value is the setting. Mode numbers, the transposition offset and the
init-only commands 5-10 are Mosaic's own and are asserted as characterised.
"""
SINF_PORT=3
INIT=[[192,0],[193,0],[194,0],[195,64],[196,0],[197,0],[198,0],[199,0],[200,64],[201,11]]

def sinf(state,marker):
    return [m['bytes'] for m in state['midi'] if m['index']>marker and m['port']==SINF_PORT]

def settings(messages):
    """Group the per-step channel 1..4 program changes into (root,degree,mode,transposition)."""
    assert all(b[0]&240==192 and 192<=b[0]<=195 for b in messages),('Only channels 1-4 after init',messages)
    assert len(messages)%4==0 and all([b[0] for b in messages[i:i+4]]==[192,193,194,195] for i in range(0,len(messages),4)),messages
    return [tuple(b[1] for b in messages[i:i+4]) for i in range(0,len(messages),4)]

def sinfonion_software(c):
    first=c.snapshot()
    startup=[m['bytes'] for m in first['midi'] if m['port']==SINF_PORT]
    assert startup[:10]==INIT,('Init sequence',startup)
    c.results.append(dict(kind='sinfonion',stage='init',messages=startup[:10],passed=True))
    c.configure()
    def play(stage,seconds=1.2):
        marker=c.snapshot()['midi_count'];c.tap(1,8);c.elapse(seconds);c.tap(1,8)
        state=c.wait(lambda s:not s['midi_capture']['outstanding'])
        messages=sinf(state,marker)
        # Transport is also sent on this port (characterised): Start first, Stop last.
        assert messages and messages[0]==[250] and messages[-1]==[252],('Transport framing',messages[:2],messages[-2:])
        rows=settings(messages[1:-1])
        assert rows,('No Sinfonion updates while playing',stage)
        c.results.append(dict(kind='sinfonion',stage=stage,settings=sorted(set(rows)),updates=len(rows),passed=True))
        return rows
    def edit_root(semitones):c.enc(2,-1);c.enc(3,semitones);c.key(3);c.enc(2,1)
    # Stopped editing sends nothing to the Sinfonion.
    marker=c.snapshot()['midi_count'];c.tap(4,8);c.tap(2,3);edit_root(2);c.tap(3,8)
    assert sinf(c.snapshot(),marker)==[],'Sinfonion traffic while stopped'
    rows=play('applied-D-major')
    assert {r[0] for r in rows}=={2},('Root follows the applied scale',rows)   # contract: D = 2
    assert set(rows)=={(2,0,3,64)},rows                                         # characterised degree/mode/transposition
    # Global transpose +2 changes only the transposition setting.
    c.tap(4,8);c.tap(9,8)
    for _ in range(14):c.tap(16,8)
    c.tap(3,8)
    rows=play('transpose-plus-2');assert set(rows)=={(2,0,3,66)},rows
    # A scale-track lock on global step 2 to slot 3 (E natural minor) reaches the Sinfonion.
    c.tap(4,8);c.tap(3,3);edit_root(4);c.enc(3,2);c.key(3);c.tap(2,3)
    c.action(type='grid',x=2,y=4,state=1)
    try:c.tap(3,3)
    finally:c.action(type='grid',x=2,y=4,state=0)
    c.tap(3,8)
    rows=play('scale-track-lock-E-minor')
    # Step 1 keeps the applied D major; from locked step 2 the global lock holds
    # until the scale track wraps (README MAN scale-lock lifetime).
    assert rows[0]==(2,0,3,66) and rows[1:] and set(rows[1:])=={(4,0,4,66)},('Scale-track lock must reach the Sinfonion',rows)
