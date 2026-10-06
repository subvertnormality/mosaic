"""Continuous beginner-course acceptance; public input only.

Authored MIDI expectations are independent of Mosaic state. The driver starts
empty; stages edit one project and never call configure() or inject Lua.
Native execution is gated until all course route contracts are authored.
"""
from collections import Counter

CITATION="README.md#typical-workflow"

def rows(notes,port=1,status=144,length=.5):
    return [dict(port=port,status=status,note=n,velocity=v,step=s,length=length)
            for s,n,v in notes]

FIRST=rows([(0,60,80),(1,60,80),(2,60,80),(3,60,80)])
BAR=rows([(0,60,80),(4,60,80),(8,60,80),(12,60,80)])
ENDING=rows([(0,60,80),(4,60,80),(8,60,80),(12,62,80)])
QUIET=rows([(0,60,80),(4,60,80),(8,60,80),(12,62,50)])
DEFAULT_G=rows([(0,67,80),(4,67,80),(8,67,80),(12,62,50)])
BASS=rows([(0,48,100),(8,55,100)],port=2,status=145,length=1)
D_UPPER=rows([(0,62,80),(4,62,80),(8,62,80),(12,64,50)])
D_BASS=rows([(0,50,100),(8,57,100)],port=2,status=145,length=1)
PICKUP=QUIET+rows([(14,60,35)])
MERGE_SKIP=rows([(4,60,80),(12,62,50)])

def arranged():
    return BASS+[dict(row,step=row['step']+16) for row in PICKUP+BASS]

CONTRACTS={
 'first-sound-hear':(4,FIRST),
 'build-a-phrase-compare':(16,BAR),
 'masks-listen':(16,ENDING),
 'masks-quiet':(16,QUIET),
 'masks-default-g':(16,DEFAULT_G),
 'masks-default-restored':(16,QUIET),
 'masks-clear':(16,BAR),
 'masks-keep':(16,QUIET),
 'sequence-composition-both':(16,QUIET+BASS),
 'sequence-composition-merge-skip':(16,MERGE_SKIP+BASS),
 'sequence-composition-merge-all':(16,QUIET+BASS),
 'sequence-composition-merge-restored':(16,QUIET+BASS),
 'harmony-design-relative':(16,QUIET+BASS),
 'harmony-design-draft':(16,QUIET+BASS),
 'harmony-design-apply-d':(16,D_UPPER+D_BASS),
 'harmony-design-apply-restored':(16,QUIET+BASS),
 'modulation-movement-and-interest-level':(16,PICKUP+BASS),
 'song-composition-transition':(32,arranged()),
 'keep-your-work-perform':(32,arranged()),
}

def musical(c,stage):
    """Two complete cycles, exact notes/velocity/order/timing/gates and no extras."""
    period,expected=CONTRACTS[stage]
    key='logical_ns' if c.clock_mode=='controlled-experimental' else 'monotonic_ns'
    tolerance=2e-9 if c.clock_mode=='controlled-experimental' else .01
    start=c.snapshot()['midi_count'];c.ui.play()
    def ons(state):return [m for m in state['midi'] if m['index']>start and 144<=m['bytes'][0]<=159 and m['bytes'][2]>0]
    state=c.wait(lambda s:len(ons(s))>=len(expected)*2+1,timeout=3+period*2/6)
    sounded=ons(state);boundary=sounded[len(expected)*2]
    end=boundary['index']-1
    packets=[m for m in state['midi'] if start<m['index']<=end and 128<=m['bytes'][0]<=159]
    complete=sounded[:len(expected)*2]
    origin=complete[0][key]
    wanted=[dict(r,step=r['step']+cycle*period) for cycle in range(2) for r in expected]
    for port in (1,2):
        actual=[m for m in complete if m['port']==port]
        literal=sorted([r for r in wanted if r['port']==port],key=lambda r:r['step'])
        assert [(m['bytes'][0],m['bytes'][1],m['bytes'][2]) for m in actual]==[(r['status'],r['note'],r['velocity']) for r in literal],(stage,port,actual,literal)
        for m,r in zip(actual,literal):
            assert abs((m[key]-origin)/1e9-r['step']/6)<=tolerance,(stage,'onset',m,r)
            release=next(p for p in packets if p['index']>m['index'] and p['port']==port and p['bytes']==[r['status']-16,r['note'],r['velocity']])
            assert abs((release[key]-m[key])/1e9-r['length']/6)<=tolerance,(stage,'gate',m,release,r)
    wanted_packets=Counter((r['port'],r['status'],r['note'],r['velocity']) for r in wanted)
    wanted_packets.update((r['port'],r['status']-16,r['note'],r['velocity']) for r in wanted)
    assert Counter((p['port'],*p['bytes']) for p in packets)==wanted_packets,(stage,'unexpected packets',packets)
    c.ui.stop();c.wait(lambda s:not s['midi_capture']['outstanding'])
    c.results.append(dict(kind='manual-course-midi',stage=stage,bpm=90,cycle_steps=period,cycles=2,
        expected=expected,midi_start_index=start,midi_end_index=end,next_cycle_index=boundary['index'],
        timing_tolerance_seconds=tolerance,citation=CITATION,passed=True))

def checkpoint(c,stage,page,params=None,mask_fields=(),selected=None,leds=()):
    params=params or {}
    from ui_map import header_parts
    from frame_oracle import live_header_matches
    if page in ('song_setup','song_global_settings'):
        title='SLOT SETUP' if page=='song_setup' else 'GLOBAL FEEL'
        header=dict(title=title,scope='SONG %02d'%params.get('song_slot',1),layout='vertical_list')
        c.wait(lambda state:live_header_matches(state,**header))
    else:
        c.ui.expect_header(page,**params)
        title,scope,layout=header_parts(page,**params);header=dict(title=title,scope=scope,layout=layout)
    for name,value in mask_fields:c.ui.expect_field_value(name,str(value))
    if selected:c.ui.expect_selected_field(**selected)
    if leds:c.led_values([(x,y) for x,y,v in leds],[v for x,y,v in leds])
    c.results.append(dict(kind='manual-course-ui',stage=stage,page=page,params=params,header=header,
        mask_fields=[dict(field=n,value=str(v),layout='overview_masks') for n,v in mask_fields],
        selected_field=selected,leds=[dict(x=x,y=y,level=v) for x,y,v in leds],citation=CITATION,passed=True))

def mask(c,field,delta,step=None):
    index={'trig':0,'note':1,'velocity':2,'length':3}[field]
    c.enc(2,-12)
    if index:c.enc(2,index)
    if step is None:c.enc(3,delta)
    else:
        with c.ui.hold_step(step):c.enc(3,delta)

def project_files(c,name):
    from driver import digest
    paths=[c.data_directory/(name+suffix) for suffix in ('.ptn','.pset')]
    return {p.name:digest(p) for p in paths} if all(p.is_file() for p in paths) else None

def persistence(c,stage,name,expected):
    from pathlib import Path
    from driver import digest
    dest=c.out/'course-project-evidence';dest.mkdir(exist_ok=True)
    for filename,sha in expected.items():
        original=c.data_directory/filename;copy=dest/(stage+'-'+filename)
        copy.write_bytes(original.read_bytes());assert digest(copy)==sha
    c.results.append(dict(kind='manual-course-persistence',stage=stage,name=name,files=expected,
        evidence_directory=str(dest),citation='README.md#save-and-load',passed=True))

def save_project(c,name):
    ui=c.ui;ui.select_project_action('save')
    ui.turn(2,-1)
    for _ in range(3):ui.press_key(3)  # Native default name new, DEL selected.
    ui.turn(3,-1);position=28
    for character in name:
        target=(ord(character)-37)%95;delta=(target-position)%95
        if delta>47:delta-=95
        if delta:ui.turn(2,delta)
        ui.press_key(3);position=target
    ui.turn(3,1);ui.turn(2,1);ui.press_key(3);ui.press_key(1)

def course(c):
    ui=c.ui
    # No configure: default empty project, no assignment, Record disarmed.
    ui.channel_editor();checkpoint(c,'getting-started-objects','masks',{'channel':1})
    ui.pattern_editor();checkpoint(c,'getting-started-notation','trigger_editor',{'pattern':1})
    ui.channel_editor();ui.channel_page('midi_config',channel=1)
    checkpoint(c,'setup-route','midi_config',{'channel':1})
    c.enc(3,1);ui.press_key(3)
    checkpoint(c,'setup-apply','midi_config',{'channel':1})
    # Public Song Tempo & feel sets a visible exact musical clock.
    ui.song_editor();ui.open_task('Song','tempo_feel');ui.select_row('tempo',0)
    c.enc(3,-300);c.enc(3,60);ui.press_key(3)
    checkpoint(c,'setup-tempo','song_global_settings',selected=dict(layout='vertical_list',label='Tempo',value='90'))
    ui.channel_editor();ui.pattern_editor();ui.tap_control('pattern_select',1)
    for step in (1,2,3,4):ui.tap_step(step)
    checkpoint(c,'first-sound-attacks','trigger_editor',{'pattern':1},leds=[(x,4,15) for x in range(1,5)])
    ui.channel_editor();ui.tap_control('pattern_slot',1);ui.set_range(1,4)
    checkpoint(c,'first-sound-assign','merge_detail',{'channel':1})
    ui.channel_page('masks',channel=1);mask(c,'note',61);mask(c,'velocity',81);mask(c,'length',8)
    checkpoint(c,'first-sound-defaults','masks',{'channel':1},[('note','C3'),('velocity','80'),('length','1/2')])
    musical(c,'first-sound-hear')
    ui.set_range(1,16);ui.channel_page('clock_mods',channel=1);ui.select_row('rate',0)
    c.enc(3,-64);c.enc(3,17);ui.press_key(3)
    checkpoint(c,'build-a-phrase-range','clock_mods',{'channel':1},selected=dict(layout='vertical_list',label='Rate',value='/4'))
    ui.pattern_editor()
    for step in (2,3,4,5,9,13):ui.tap_step(step)
    checkpoint(c,'build-a-phrase-rhythm','trigger_editor',{'pattern':1},leds=[(x,4,15 if x in (1,5,9,13) else 2) for x in range(1,17)])
    ui.channel_editor();ui.channel_page('masks',channel=1);musical(c,'build-a-phrase-compare')
    mask(c,'note',0);checkpoint(c,'masks-open','masks',{'channel':1},[('note','C3')])
    c.action(type='grid',x=13,y=4,state=1);c.elapse(.1)
    checkpoint(c,'masks-hold','masks',{'channel':1,'held':[13]},[('note','C3')])
    c.enc(3,2);checkpoint(c,'masks-edit','masks',{'channel':1,'held':[13]},[('note','D3')])
    c.action(type='grid',x=13,y=4,state=0);c.elapse(.1)
    checkpoint(c,'masks-release','masks',{'channel':1},[('note','C3')]);musical(c,'masks-listen')
    mask(c,'velocity',-30,13);musical(c,'masks-quiet')
    mask(c,'note',7);musical(c,'masks-default-g');mask(c,'note',-7);musical(c,'masks-default-restored')
    with ui.hold_step(13):ui.press_key(2)
    musical(c,'masks-clear')
    mask(c,'note',2,13);mask(c,'velocity',-30,13);musical(c,'masks-keep')
    ui.pattern_editor();ui.tap_control('pattern_select',2)
    for step in (1,9):ui.tap_step(step)
    ui.pattern_editor(view='note',from_view='trigger')
    ui.tap_control('pattern_note_degree',(1,0));ui.tap_control('pattern_note_degree',(9,4))
    checkpoint(c,'sequence-composition-bass-pattern','note_editor',{'pattern':2})
    ui.channel_editor();ui.select_channel(2);ui.channel_page('midi_config',channel=2)
    c.enc(3,1);c.enc(2,1);c.enc(3,1);c.enc(2,1);c.enc(3,1);ui.press_key(3)
    ui.tap_control('pattern_slot',2);ui.set_range(1,16);ui.tap_control('channel_octave',-1)
    checkpoint(c,'sequence-composition-bass-route','merge_detail',{'channel':2,'octave':-1})
    musical(c,'sequence-composition-both')
    ui.select_channel(1);ui.tap_control('pattern_slot',2)
    musical(c,'sequence-composition-merge-skip')
    ui.tap_control('trig_merge_mode')
    ui.expect_selected_field('detail','Strategy','ONLY');c.led_values([(14,8)],[5])
    ui.tap_control('trig_merge_mode')
    ui.expect_selected_field('detail','Strategy','ALL');c.led_values([(14,8)],[8])
    musical(c,'sequence-composition-merge-all')
    ui.tap_control('pattern_slot',2)
    musical(c,'sequence-composition-merge-restored')
    ui.channel_page('masks',channel=1);mask(c,'note',-128)
    with ui.hold_step(13):ui.press_key(2)
    mask(c,'velocity',-30,13)
    checkpoint(c,'harmony-design-inherit','masks',{'channel':1},[('note','X'),('velocity','80')])
    # Entering Pattern from another context always opens Trig.
    ui.pattern_editor()
    ui.tap_control('pattern_select',1);ui.pattern_editor(view='note',from_view='trigger')
    for step,degree in ((1,0),(5,0),(9,0),(13,1)):ui.tap_control('pattern_note_degree',(step,degree))
    ui.channel_editor();musical(c,'harmony-design-relative')
    ui.scale_editor();ui.tap_control('scale_slot',2)
    c.enc(2,-12);c.enc(3,2)
    checkpoint(c,'harmony-design-draft-scale','scale',{'slot':2},selected=dict(layout='vertical_list',label='Root',value='D'))
    ui.select_row('scale',1);ui.expect_selected_field('vertical_list','Scale','Major')
    musical(c,'harmony-design-draft')
    ui.press_key(3);musical(c,'harmony-design-apply-d')
    ui.tap_control('scale_slot',1);ui.press_key(3);musical(c,'harmony-design-apply-restored')
    ui.pattern_editor()
    ui.tap_control('pattern_select',1);ui.tap_step(15)
    ui.pattern_editor(view='note',from_view='trigger');ui.tap_control('pattern_note_degree',(15,0))
    checkpoint(c,'modulation-movement-and-interest-pickup','note_editor',{'pattern':1})
    ui.channel_editor();ui.channel_page('masks',channel=1);mask(c,'velocity',-45,15)
    musical(c,'modulation-movement-and-interest-level')
    ui.song_editor();ui.copy_slot(1,2,control='song_pattern_slot');ui.tap_control('song_pattern_slot',2)
    checkpoint(c,'song-composition-copy','song',{'song_slot':2})
    ui.tap_control('song_pattern_slot',1);ui.channel_editor()
    c.action(type='key',n=1,state=1);c.elapse(.35);ui.tap_control('channel',1);c.action(type='key',n=1,state=0);c.elapse(.1)
    checkpoint(c,'song-composition-sparse-muted','masks',{'channel':1,'mute':True})
    ui.song_editor();ui.tap_control('song_pattern_slot',2);ui.channel_editor()
    checkpoint(c,'song-composition-sparse-copy','masks',{'channel':1,'song_slot':2})
    ui.song_editor()
    for slot in (1,2):
        ui.tap_control('song_pattern_slot',slot);ui.tap_control('global_pattern_length',2)
        ui.open_task('Song','slot_setup');ui.select_row('repeats',0)
        c.enc(3,-64);ui.press_key(3)
        checkpoint(c,'song-composition-length-slot%d'%slot,'song_setup',{'song_slot':slot},selected=dict(layout='vertical_list',label='Repeats',value='1'))
        if slot==2:
            ui.select_row('song_mode',1);c.enc(3,1);ui.press_key(3)
            checkpoint(c,'song-composition-length-mode','song_setup',{'song_slot':2},selected=dict(layout='vertical_list',label='Song mode',value='On'))
        ui.song_editor()
    ui.tap_control('song_pattern_slot',1)
    musical(c,'song-composition-transition')
    save_project(c,'Four notes');saved=project_files(c,'Four notes')
    assert saved,'Named course files absent'
    persistence(c,'keep-your-work-save','Four notes',saved)
    ui.channel_editor()
    c.action(type='key',n=1,state=1);c.elapse(.35);ui.tap_control('channel',1);c.action(type='key',n=1,state=0);c.elapse(.1)
    checkpoint(c,'keep-your-work-temporary-edit','masks',{'channel':1})
    ui.select_project_file('Four notes.ptn',returning=True);ui.press_key(3);ui.press_key(1)
    assert project_files(c,'Four notes')==saved,'Loading altered named project'
    ui.channel_editor();checkpoint(c,'keep-your-work-reload','masks',{'channel':1,'mute':True})
    persistence(c,'keep-your-work-loaded-files','Four notes',saved)
    ui.song_editor();ui.tap_control('song_pattern_slot',1);musical(c,'keep-your-work-perform')

CASES={'M-MANUAL-COURSE-001':dict(run=course,
 requirements=['MANUAL-CONTINUING-COURSE','CH-PATTERN-ASSIGN','MASK-PRECEDENCE','SONG-COMPOSITION','SAVE-NAMED'],
 description='One empty-start project through equal notes, bar rhythm, Masks, bass, reversible merge, harmony, pickup, two sections and named Save/Load')}
