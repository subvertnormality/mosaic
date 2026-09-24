"""MIDI keyboard mapping options (MAN-103..106): defaults, white keys, honour switches."""

MAJOR=[0,2,4,5,7,9,11];MINOR=[0,2,3,5,7,8,10]
# README MAN-103: the scale runs up the white keys from C. A black key is not
# a white key; the implementation plays it as the next white key's degree
# (C#->D). That extra behaviour is recorded as characterised, not documented.
KEY_DEGREE=[0,1,1,2,2,3,4,4,5,5,6,6]

def mapped(key,intervals,degree_shift=0,rotation=0,transpose=0):
    """Independent keyboard table: seven scale positions per keyboard octave."""
    position=KEY_DEGREE[key%12]
    # Degree n starts the positions on the scale's n-th note (II: D..C above).
    shifted=position+degree_shift
    pitch=intervals[shifted%7]+12*(shifted//7)
    # Rotation r lowers the last r of the seven positions by an octave.
    if position>=7-rotation:pitch-=12
    return max(0,min(127,60+12*(key//12-5)+pitch+transpose))

def keyboard_options(c):
    ui = c.ui
    ui.configure();velocity=90
    def sweep(label,keys,expected_for):
        marker=c.snapshot()['midi_count'];expected=[]
        for key in keys:
            c.action(type='midi',port=1,bytes=[144,key,velocity]);c.action(type='midi',port=1,bytes=[128,key,0])
            note=expected_for(key);expected+=[(1,[144,note,velocity]),(1,[128,note,0])]
        state=c.wait(lambda s:s['midi_count']-marker>=len(expected),timeout=10)
        actual=[(m['port'],m['bytes']) for m in state['midi'] if m['index']>marker]
        assert actual==expected,dict(stage=label,expected=expected,actual=actual)
        assert not state['midi_capture']['outstanding'],state['midi_capture']['outstanding']
        c.results.append(dict(kind='keyboard-mapping',stage=label,keys=list(keys),notes=[e[1][1] for e in expected[::2]],passed=True))
    octave=list(range(60,73))
    # Fresh defaults: white-key mapping Off plays the raw key, the whole range.
    sweep('default-raw',range(128),lambda k:k)
    ui.set_mosaic_options([('Map scale to white keys',True)])
    sweep('white-major',range(128),lambda k:mapped(k,MAJOR))
    assert [mapped(k,MAJOR) for k in octave]==[60,62,62,64,64,65,67,67,69,69,71,71,72]
    # The scale page selects the scale track, which takes no keyboard notes;
    # return to channel 1 before each sweep.
    ui.scale_editor();ui.set_value(2);ui.press_key(3);ui.tap_control('channel_editor') # Major -> natural minor: mapping follows the scale.
    sweep('white-minor',octave,lambda k:mapped(k,MINOR))
    # Degree II, rotation two and transpose +2 on the scale page and fader.
    ui.scale_editor()
    ui.turn(2,1);ui.set_value(1);ui.press_key(3);ui.turn(2,-1)
    ui.turn(2,3);ui.set_value(2);ui.press_key(3);ui.turn(2,-3)
    ui.tap_control('global_transpose_minimum')
    for _ in range(14):ui.tap_control('global_transpose_increment')
    ui.tap_control('channel_editor')
    # Honour switches still at their defaults (Off): none of the three applies.
    sweep('honour-defaults-off',octave,lambda k:mapped(k,MINOR))
    for label,options,shift,rotation,transpose in [
        ('honour-degree',[('Honour scale degree',True)],1,0,0),
        ('honour-degree-rotation',[('Honour scale rotations',True)],1,2,0),
        ('honour-all',[('Honour scale transpose',True)],1,2,2),
        ('honour-rotation-transpose',[('Honour scale degree',False)],0,2,2),
        ('honour-transpose',[('Honour scale rotations',False)],0,0,2)]:
        ui.set_mosaic_options(options)
        sweep(label,octave,lambda k:mapped(k,MINOR,shift,rotation,transpose))
    ui.set_mosaic_options([('Map scale to white keys',False)])
    sweep('white-off-raw',octave,lambda k:k)
