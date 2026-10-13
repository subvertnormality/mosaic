"""Public-input acceptance for remaining manual controls; no production access."""

def song_levels(state, expected):
    """Literal README Song indicators: empty2, populated7, selected/playing15."""
    actual=[state["grid"][slot-1] for slot in range(1,len(expected)+1)]
    assert actual==list(expected), {"actual":actual,"expected":list(expected)}
    return actual

def phrase_prefix(notes):
    expected=[[144,60,127],[144,62,117],[144,64,107],[144,65,97]]
    actual=[event["bytes"] for event in notes[:4]]
    assert actual==expected,{"actual":actual,"expected":expected}
    assert all(event["port"]==1 for event in notes[:4])
    return actual

BLINK_TIMING = dict(blink_period_ns=400000000,grid_flush_period_ns=50000000,
    real_clock_allowance_ns=10000000,min_transition_ns=340000000,max_transition_ns=460000000,
    observation_poll_ns=30000000,window_ns=3330000000,
    source="mosaic.lua blink clock.sleep(0.4); grid_redraw clock.sleep(1/20); existing real musical allowance0.01s")

def queued_blink_waveform(samples,native):
    import hashlib,json
    assert len(samples)>=7
    start,end=samples[0]['monotonic_ns'],samples[-1]['monotonic_ns']
    assert all(s['levels'][0] in (1,7) and s['levels'][1:]==[15,2] for s in samples)
    assert all(0<b['monotonic_ns']-a['monotonic_ns']<BLINK_TIMING['min_transition_ns'] for a,b in zip(samples,samples[1:]))
    # The initial state is censored: it is not the global blink callback's phase.
    rows=[];last=samples[0]['levels'][0]
    for index,event in enumerate(native):
        if event.get('kind')!=2 or not start<event['monotonic_ns']<=end:continue
        levels=event['leds'][:3]
        assert levels[0] in (1,7) and levels[1:]==[15,2]
        if levels[0]!=last:
            rows.append(dict(native_event_index=index,id=event['id'],monotonic_ns=event['monotonic_ns'],
                leds_sha256=hashlib.sha256(json.dumps(event['leds'],sort_keys=True,separators=(',',':')).encode()).hexdigest(),levels=levels))
            last=levels[0]
    assert len(rows)>=7,'Need seven native changes and six complete visual dwell periods'
    assert all(BLINK_TIMING['min_transition_ns']<=b['monotonic_ns']-a['monotonic_ns']<=BLINK_TIMING['max_transition_ns'] for a,b in zip(rows,rows[1:]))
    return rows

def queued_blink_levels(samples, controlled, native=None):
    expected=[1,7,1,7,1,7,1]
    if controlled:
        assert [sample['levels'][0] for sample in samples]==expected
        assert all(sample['levels'][1:]==[15,2] for sample in samples)
        assert all(b['logical_ns']-a['logical_ns']==400000000 for a,b in zip(samples,samples[1:]))
    else:
        assert native is not None,'Real-time blink requires the native visual waveform'
        queued_blink_waveform(samples,native)
    return expected


def song_controls(c, global_length=32):
    from midi_window import MidiWindow
    ui=c.ui;ui.configure()
    ui.set_mosaic_options([("Song mode",False)])
    ui.song_editor()
    # README Adjusting Song sequence length: a shorter global length keeps the
    # queued-slot hand-over audible in seconds rather than the default 64 steps.
    # The slot must still outlast the 3.33s real blink window (24 steps at 90 BPM).
    from channel_gestures import set_global_pattern_length
    set_global_pattern_length(ui,global_length)
    ui.copy_slot(1,2,control="song_pattern_slot")
    ui.tap_control("song_pattern_slot",2)
    def lights(stage, expected, **extra):
        c.led_values([(slot,1) for slot in range(1,len(expected)+1)],expected)
        observed=song_levels(c.snapshot(),expected)
        c.results.append(dict(kind="manual-song-indicators",stage=stage,levels=observed,
            citation="README.md#button-indicators",
            characterisation="Stopped selected slot is also bright (outside the README playing-only wording).",
            passed=True,**extra))
    lights("copied-selected",[7,15,2])
    ui.open_task("Song","slot_setup")
    ui.expect_selected_field("vertical_list",label="Repeats",value="1")
    for value,delta in [(1,0),(16,15),(2,-14)]:
        if delta:ui.turn(3,delta);ui.press_key(3)
        ui.expect_selected_field("vertical_list",label="Repeats",value=str(value))
        c.results.append(dict(kind="manual-song-slot-setting",field="Repeats",value=value,
            citation="README.md#navigating-the-norns-display",passed=True))
    ui.song_editor()
    marker=c.snapshot()["midi_count"];window=MidiWindow(marker);ui.play()
    state=c.wait(lambda s:window.extend(s) and len(window.note_ons())>=5,timeout=3)
    notes=window.note_ons();phrase=phrase_prefix(notes)
    domain="logical_ns" if c.clock_mode=="controlled-experimental" else "monotonic_ns"
    tolerance=2e-9 if c.clock_mode=="controlled-experimental" else .01
    for index,event in enumerate(notes[:4]):
        assert abs((event[domain]-notes[0][domain])/1e9-index/6)<=tolerance
    lights("playing",[7,15,2],midi_start_index=marker,phrase=phrase,tolerance_seconds=tolerance)
    ui.stop();c.wait(lambda s:not s["midi_capture"]["outstanding"])
    stopped=c.snapshot()["midi_count"];c.elapse(.25)
    assert not [e for e in c.snapshot()["midi"] if e["index"]>stopped and e["bytes"][0]&240==144 and e["bytes"][2]>0]
    # README Song Mode Operations: a manual selection waits for the next
    # sequence boundary. The first phrase above remains unchanged; now make
    # slot1 an independently audible +1-octave destination through grid input.
    ui.song_editor();ui.tap_control("song_pattern_slot",1)
    ui.channel_editor();ui.tap_control("channel_octave",1)
    ui.song_editor();ui.tap_control("song_pattern_slot",2)
    queue_marker=c.snapshot()["midi_count"];queued=MidiWindow(queue_marker);ui.play()
    c.wait(lambda s:queued.extend(s) and len(queued.note_ons())>=1,timeout=2)
    queue_recipe_start=len(c.recipe);queue_ack=ui.control_edge("song_pattern_slot",True,1)
    ui.control_edge("song_pattern_slot",False,1);queue_recipe_end=len(c.recipe)
    c.wait(lambda s:queued.extend(s) and s["grid"][:3]==[1,15,2],timeout=1)
    import hashlib,json
    def sample():
        state=c.snapshot();queued.extend(state)
        observation=c.observations[-1]
        return dict(observation_index=len(c.observations)-1,frame_sha256=state["frame"]["sha256"],
            grid_sha256=hashlib.sha256(json.dumps(state["grid"],sort_keys=True,separators=(",",":")).encode()).hexdigest(),
            grid_revision=observation["grid_revision"],monotonic_ns=observation["monotonic_ns"],logical_ns=state["clock"]["logical_ns"] if c.clock_mode=="controlled-experimental" else None,
            levels=state["grid"][:3])
    blink_samples=[sample()]
    controlled=c.clock_mode=="controlled-experimental"
    if controlled:
        for _ in range(6):c.elapse(.4);blink_samples.append(sample())
        native_grid_transitions=[]
    else:
        from contract.mini_header_animation_ui import native_events
        while blink_samples[-1]['monotonic_ns']-blink_samples[0]['monotonic_ns']<BLINK_TIMING['window_ns']:
            c.elapse(.03);blink_samples.append(sample())
        native_grid_transitions=queued_blink_waveform(blink_samples,native_events(c))
    queued_blink_levels(blink_samples,controlled,None if controlled else native_events(c))
    c.results.append(dict(kind="manual-song-queue-blink",stage="waiting",samples=blink_samples,
        recipe_start_index=queue_recipe_start,recipe_end_index=queue_recipe_end,
        input_sequence=queue_ack["sequence"],native=queue_ack["native"],queued_slot=1,playing_slot=2,
        period_ns=400000000,native_grid_transitions=native_grid_transitions,
        timing_contract=None if controlled else BLINK_TIMING,citation="README.md#song-mode-operations",
        characterisation="Characterisation outside README: populated queued slot alternates exact LED levels1/7 on the source0.4s blink clock; controlled samples are exactly0.4s apart. Real native visual dwell bounds derive from the20Hz grid flush plus the existing10ms clock allowance; fast observations do not assume the global blink phase.",passed=True))
    c.wait(lambda s:queued.extend(s) and len(queued.note_ons())>=global_length+5,timeout=15)
    ui.stop();c.wait(lambda s:queued.extend(s) and not s["midi_capture"]["outstanding"])
    notes=queued.note_ons()
    from cases import assert_durations
    for index,event in enumerate(notes):
        pitch=[60,62,64,65][index%4]+(12 if index>=global_length else 0)
        assert event["port"]==1 and event["bytes"]==[144,pitch,[127,117,107,97][index%4]],(index,event)
        assert abs((event[domain]-notes[0][domain])/1e9-index/6)<=tolerance
    assert_durations(c,notes,[1]*(len(notes)-1))
    c.led_values([(1,1),(2,1),(3,1)],[15,7,2])
    c.results.append(dict(kind="manual-song-queue-transition",midi_start_index=queue_marker,
        from_slot=2,to_slot=1,transition_index=global_length,old_phrase=[60,62,64,65],new_phrase=[72,74,76,77],
        velocities=[127,117,107,97],onsets=len(notes),onset_spacing_seconds=1/6,
        tolerance_seconds=tolerance,levels=[15,7,2],citation="README.md#song-mode-operations",passed=True))
    ui.copy_slot(3,2,control="song_pattern_slot");ui.tap_control("song_pattern_slot",1)
    lights("empty-copy-erases",[15,2,2])

def essential_clock_rows(state, selected, clock_value="/1"):
    import base64
    from frame_oracle import render,_region_matches,text_width
    actual=base64.b64decode(state["frame"]["pixels_base64"])
    for index,label in enumerate(["Rate","Feel source","Swing type"]):
        baseline=27+index*9;level=15 if index==selected else 7
        commands=[(7,baseline,level,label)]
        if index==selected:commands.append((0,baseline,15,">"))
        if not _region_matches(actual,render(commands),baseline-7,baseline+2,0,8+int(text_width(label))):return False
    for index,value in enumerate([clock_value,"GLOBAL","X"]):
        baseline=27+index*9;level=15 if index==selected else 10
        left=max(7,126-int(text_width(value))-2)
        if not _region_matches(actual,render([((None,126),baseline,level,value)]),baseline-7,baseline+2,left,127):return False
    return True

def mark_pixels(state):
    import base64
    from contract.mini_header_animation_ui import atlas,left_edge
    spec=atlas()['C04'];pixels=base64.b64decode(state['frame']['pixels_base64'])
    return bytes(pixels[(y*128+x)*4+k] for y in range(8) for x in range(left_edge(spec),128) for k in range(3))

def motion_marker_changed(enabled,samples):
    assert len(samples)>=6, "At least six independently recorded native samples required"
    changed=len({sample["mark_sha256"] for sample in samples})>1
    assert changed==enabled,{"enabled":enabled,"decorative_mark_changed":changed}
    return changed

def motion_controls(c):
    import hashlib,json
    from frame_oracle import vertical_selected_field_matches
    from cases import assert_durations
    ui=c.ui;ui.configure()
    for enabled in [False,True]:
        ui.set_mosaic_options([("UI motion",enabled)])
        ui.channel_page("clock_mods",channel=1);ui.select_row("rate",0)
        c.wait(lambda s:essential_clock_rows(s,0),timeout=.25)
        # Back-to-back public E3 and K3 edges; decorative animation cannot
        # postpone their effect. This bound is captured UI responsiveness,
        # not hardware scheduling equivalence.
        c.snapshot();edit_before=len(c.observations)-1;edit_recipe_index=len(c.recipe)
        edit_ack=ui.encoder_event(3,-2);ui.key_edge(3,True);ui.key_edge(3,False);edit_recipe_end=len(c.recipe)
        c.wait(lambda s:vertical_selected_field_matches(s,"Rate","/1.5"),timeout=.25)
        response_receipts=[dict(stage="edit",before_observation_index=edit_before,response_observation_index=len(c.observations)-1,recipe_start_index=edit_recipe_index,recipe_end_index=edit_recipe_end,input_sequence=edit_ack["sequence"],native=edit_ack["native"])]
        from contract.mini_header_animation_ui import sample as mini_sample
        # Literal full Clock motif and independently checked native beat phase;
        # the old corner tile region is constant in every accepted Clock pose.
        mini_sample(c,'C04',enabled,3.0 if enabled else .75,require_all=enabled,tempo=90)
        mini_assertion=c.results[-1];samples=[]
        for item in mini_assertion['samples']:
            state=c.observations[item['observation_index']]['state']
            assert essential_clock_rows(state,0,'/1.5'), 'Essential Clock labels/value changed during decoration'
            samples.append(dict(item,grid_sha256=hashlib.sha256(json.dumps(state['grid'],sort_keys=True,separators=(',',':')).encode()).hexdigest(),
                logical_ns=state['clock']['logical_ns'] if c.clock_mode=='controlled-experimental' else None,
                mark_sha256=hashlib.sha256(mark_pixels(state)).hexdigest()))
        changed=motion_marker_changed(enabled,samples)
        # Teaching frames: README UI Motion says the mark animates only when UI motion
        # is On. Capture the rest pose and a moved pose so the contrast is visible.
        def mark_now():return hashlib.sha256(mark_pixels(c.snapshot())).hexdigest()
        def pose_row(phase,mark):
            c.results.append(dict(kind="manual-motion-pose",enabled=enabled,phase=phase,mark_sha256=mark,
                rest_mark_sha256=rest_mark,at_rest=mark==rest_mark,clock_value="/1.5",citation="README.md#ui-motion",passed=True))
        if not enabled:
            rest_mark=samples[0]["mark_sha256"]
            pose_row("rest",mark_now());c.elapse(.5)
            moved=mark_now();assert moved==rest_mark,"Mark moved with UI motion Off"
            pose_row("moved",moved)
        else:
            waited=0.0
            while mark_now()!=rest_mark:
                c.elapse(.125);waited+=.125;assert waited<=4.0,"Mark never returned to its rest pose"
            pose_row("rest",rest_mark);waited=0.0
            while mark_now()==rest_mark:
                c.elapse(.125);waited+=.125;assert waited<=4.0,"Mark never left its rest pose"
            moved=mark_now();assert moved!=rest_mark
            pose_row("moved",moved)
        c.snapshot();restore_before=len(c.observations)-1;restore_recipe_index=len(c.recipe)
        restore_ack=ui.encoder_event(3,2);ui.key_edge(3,True);ui.key_edge(3,False);restore_recipe_end=len(c.recipe)
        c.wait(lambda s:vertical_selected_field_matches(s,"Rate","/1") and essential_clock_rows(s,0),timeout=.25)
        response_receipts.append(dict(stage="restore",before_observation_index=restore_before,response_observation_index=len(c.observations)-1,recipe_start_index=restore_recipe_index,recipe_end_index=restore_recipe_end,input_sequence=restore_ack["sequence"],native=restore_ack["native"]))
        for receipt in response_receipts:
            before=c.observations[receipt["before_observation_index"]];after=c.observations[receipt["response_observation_index"]]
            start=before["state"]["clock"]["logical_ns"] if c.clock_mode=="controlled-experimental" else before["monotonic_ns"]
            end=after["state"]["clock"]["logical_ns"] if c.clock_mode=="controlled-experimental" else after["monotonic_ns"]
            assert 0<=end-start<=250000000,receipt
        c.results.append(dict(kind="manual-motion-stable-rows",enabled=enabled,
            rows=["Rate","Feel source","Swing type"],clock_value="/1",
            sample_selected_row=0,sample_clock_value="/1.5",samples=samples,public_mini_header_assertion=mini_assertion,response_receipts=response_receipts,decorative_mark_changed=changed,
            public_feedback_bound_seconds=.25,characterisation="Characterisation outside README: visible feedback bound on admitted emulator runtime, no hardware scheduling equivalence",citation="README.md#ui-motion",passed=True))
        marker=c.snapshot()["midi_count"]
        notes=c.playback([(1,[144,p,v]) for p,v in [(60,127),(62,117),(64,107),(65,97)]],cycles=2,timeout=4)
        assert_durations(c,notes,[1]*8)
        domain="logical_ns" if c.clock_mode=="controlled-experimental" else "monotonic_ns"
        allowed=2e-9 if c.clock_mode=="controlled-experimental" else .01
        for index,event in enumerate(notes):
            assert abs((event[domain]-notes[0][domain])/1e9-index/6)<=allowed
        ui.expect_leds({("play_stop",None):"off"})
        c.results.append(dict(kind="manual-motion-music",enabled=enabled,
            midi_start_index=marker,pitches=[60,62,64,65],velocities=[127,117,107,97],
            onset_spacing_seconds=1/6,tolerance_seconds=allowed,stopped=True,
            citation="README.md#ui-motion",passed=True))


def song_repeats_advance(c):
    """README Song Mode Operations: with Song mode On a slot plays its Repeats, then the song moves on."""
    from midi_window import MidiWindow
    from channel_gestures import set_global_pattern_length
    ui=c.ui;ui.configure()
    ui.song_editor();set_global_pattern_length(ui,8)
    ui.copy_slot(1,2,control="song_pattern_slot");ui.tap_control("song_pattern_slot",2)
    ui.channel_editor();ui.tap_control("channel_octave",1)
    ui.song_editor()
    ui.open_task("Song","slot_setup")
    ui.expect_selected_field("vertical_list",label="Repeats",value="1")
    ui.turn(3,1);ui.press_key(3)
    ui.expect_selected_field("vertical_list",label="Repeats",value="2")
    ui.song_editor();ui.tap_control("song_pattern_slot",1);ui.song_editor()
    c.led_values([(slot,1) for slot in (1,2,3)],[15,7,2])
    domain="logical_ns" if c.clock_mode=="controlled-experimental" else "monotonic_ns"
    tolerance=2e-9 if c.clock_mode=="controlled-experimental" else .01
    marker=c.snapshot()["midi_count"];window=MidiWindow(marker);ui.play()
    low=[60,62,64,65];high=[72,74,76,77];velocity=[127,117,107,97]
    expected=[(low[i%4]) for i in range(8)]+[high[i%4] for i in range(16)]+[low[i%4] for i in range(4)]
    def stage(name,count,levels,pass_text,expected_notes,**extra):
        state=c.wait(lambda s:window.extend(s) and len(window.note_ons())>=count,timeout=12)
        c.led_values([(slot,1) for slot in (1,2,3)],levels)
        if pass_text:ui.expect_dashboard_row("Pass",pass_text)
        notes=window.note_ons()
        assert [e["bytes"][1] for e in notes[count-4:count]]==expected_notes,(name,[e["bytes"] for e in notes])
        c.results.append(dict(kind="manual-song-repeat-advance",stage=name,levels=levels,pass_text=pass_text,
            latest_pitches=expected_notes,onsets_so_far=len(notes),citation="README.md#song-mode-operations",passed=True,**extra))
    stage("slot-1",4,[15,7,2],"1 / 1",low)
    stage("slot-2-pass-1",12,[7,15,2],"1 / 2",high)
    stage("slot-2-pass-2",20,[7,15,2],"2 / 2",high)
    stage("wrapped",28,[15,7,2],"1 / 1",low)
    ui.stop();c.wait(lambda s:window.extend(s) and not s["midi_capture"]["outstanding"])
    notes=window.note_ons()[:28]
    assert [e["bytes"][1] for e in notes]==expected,[e["bytes"] for e in notes]
    assert [e["bytes"][2] for e in notes]==[velocity[i%4] for i in range(28)]
    assert all(e["port"]==1 for e in notes)
    for index,event in enumerate(notes):
        assert abs((event[domain]-notes[0][domain])/1e9-index/6)<=tolerance,(index,event)
    c.results.append(dict(kind="manual-song-repeat-sequence",pitches=[e["bytes"][1] for e in notes],
        slot_passes=[1,2,1],onset_spacing_seconds=1/6,tolerance_seconds=tolerance,
        citation="README.md#song-mode-operations",passed=True))


def panic_releases_sounding_note(c):
    """README MIDI Panic: holding another page button sends Note Off everywhere, sounding notes included."""
    ui=c.ui;ui.configure()
    long_steps=24  # one trig lasts to the end of its range: 24 steps = 4s at 90 BPM
    ui.set_range(1,long_steps);ui.pattern_editor()
    for step in (2,3,4):ui.tap_step(step)
    # README Typical Workflow: hold a trig, then choose its ending step to give it a long length.
    with ui.hold_step(1):ui.tap_step(long_steps)
    ui.song_editor()
    domain="logical_ns" if c.clock_mode=="controlled-experimental" else "monotonic_ns"
    marker=c.snapshot()["midi_count"]
    def onsets(state,after):
        return [e for e in state["midi"] if e["index"]>after and e["port"]==1 and e["bytes"]==[144,60,127]]
    ui.play()
    state=c.wait(lambda s:len(onsets(s,marker))>=1,timeout=3)
    onset=onsets(state,marker)[0]
    c.results.append(dict(kind="panic-note-sounding",port=1,note=60,velocity=127,
        natural_length_steps=long_steps,natural_end_seconds=long_steps/6,
        citation="README.md#midi-panic",passed=True))
    before=c.snapshot()["midi_count"];start=len(c.observations)
    press=ui.control_edge("channel_editor",True)
    seen={}
    def watch(snapshot):
        # The snapshot keeps only recent MIDI; polling every 0.1s sees every event of the 0.4s sweep.
        for e in snapshot["midi"]:
            if e["index"]>before:seen[e["index"]]=e
        return snapshot
    c.elapse(.9);watch(c.snapshot())
    for _ in range(10):
        c.elapse(.1);watch(c.snapshot())
        if len(c.observations)>start+2:del c.observations[start+1:-1]
    ui.control_edge("channel_editor",False);c.elapse(.06)
    state=watch(c.snapshot());cursor=state["midi_count"]
    # Panic Note Offs carry velocity 0; the note's own scheduled release would carry its velocity 127.
    sweep=sorted((e for e in seen.values() if e["bytes"][0]&240==128),key=lambda e:e["index"])
    expected=[[128+channel,note,0] for note in range(128) for channel in range(16)]
    assert len(sweep)==6144,len(sweep)
    for port in (1,2,3):assert [e["bytes"] for e in sweep if e["port"]==port]==expected,port
    released=[e for e in sweep if e["port"]==1 and e["bytes"]==[128,60,0]][0]
    release_seconds=(released[domain]-onset[domain])/1e9
    assert release_seconds<long_steps/6-0.5,release_seconds
    assert not [e for e in seen.values() if e["port"]==1 and e["bytes"]==[128,60,127]],"Natural release arrived before the panic"
    c.led_values([(x,8) for x in (3,4,5,6)],[2,2,2,15])
    state=c.wait(lambda s:len(onsets(s,cursor))>=1,timeout=6)
    again=onsets(state,cursor)[0]
    assert abs((again[domain]-onset[domain])/1e9-long_steps/6)<=(2e-9 if domain=="logical_ns" else .01)
    c.results.append(dict(kind="panic-releases-sounding-note",port=1,note=60,
        release_seconds_after_note_on=release_seconds,natural_end_seconds=long_steps/6,released_early=True,
        sweep_messages=len(sweep),ports=3,playback_continued=True,
        next_note_on_seconds=(again[domain]-onset[domain])/1e9,
        citation="README.md#midi-panic",passed=True))
    ui.stop();c.wait(lambda s:not s["midi_capture"]["outstanding"])


def pocket_ghost_trigs(c):
    """README Channel Length / Adding Trigs: a 64-step channel shows every bar on the trig rows
    at once (steps 1-16 on row 4 down to 49-64 on row 7); the ghost-note trigs sit on step 12 of
    bars 3 and 4, steps 44 and 60, one step before the accents on 45 and 61."""
    ui=c.ui;ui.configure()
    ui.tap_control("channel_editor");ui.set_range(1,64)
    ui.pattern_editor()
    # The default phrase already trigs steps 1-4; the pocket groove keeps only step 1 of them.
    for step in (2,3,4):ui.tap_step(step)
    hits=[1]+list(range(5,65,4))
    for step in hits[1:]:ui.tap_step(step)
    ui.tap_control("channel_editor")
    ui.expect_steps({step:"selected" for step in hits})
    c.results.append(dict(kind="ghost-main-hits",steps=hits,rows=[4,5,6,7],citation="README.md#channel-length",passed=True))
    for bar,step in ((3,44),(4,60)):
        ui.pattern_editor();ui.tap_step(step);ui.tap_control("channel_editor")
        ui.expect_steps({step:"selected"})
        cell=[(step-1)%16+1,(step-1)//16+4]
        c.results.append(dict(kind="ghost-trig-grid",bar=bar,step=step,local_cell=cell,
            neighbour_accent=step+1,citation="README.md#channel-length",passed=True))
    ui.expect_steps({step:"selected" for step in hits+[44,60]})
    c.results.append(dict(kind="ghost-bar-complete",hits=len(hits),ghosts=[44,60],
        citation="README.md#channel-length",passed=True))


def polymeter_song_reset(c):
    """README Song editor: Reset on song seq change restarts every channel's loop at a slot change
    (On, the default); Off lets the loops run on. Four-against-three, ten-step slots, so slot two
    starts at step 11: restarted loops give 60 and 79; free-running loops give 64 (4 loop, 10 mod 4 = 2)
    and 81 (3 loop, 10 mod 3 = 1)."""
    from channel_gestures import set_global_pattern_length
    from range_rejection import four_against_three_setup
    ui=c.ui
    four_against_three_setup(c)
    ui.song_editor()
    set_global_pattern_length(ui,10)
    ui.copy_slot(1,2,control="song_pattern_slot")
    ui.tap_control("song_pattern_slot",1)
    field="logical_ns" if c.clock_mode=="controlled-experimental" else "monotonic_ns"
    tolerance=2e-9 if c.clock_mode=="controlled-experimental" else .01
    phrases={1:[[144,60,127],[144,62,117],[144,64,107],[144,65,97]],2:[[145,79,40],[145,81,60],[145,79,40]]}
    for reset in (True,False):
        ui.set_mosaic_options([("Reset on song seq change",reset)])
        ui.song_editor();ui.tap_control("song_pattern_slot",1)
        marker=c.snapshot()["midi_count"]
        def emitted(state):return [m for m in state["midi"] if m["index"]>marker and 144<=m["bytes"][0]<=159 and m["bytes"][2]>0]
        ui.play()
        state=c.wait(lambda s:all(sum(m["port"]==port for m in emitted(s))>=14 for port in (1,2)),timeout=6)
        ui.stop();c.wait(lambda s:not s["midi_capture"]["outstanding"])
        ports={port:[m for m in emitted(state) if m["port"]==port][:14] for port in (1,2)}
        first_slot_two=[]
        for port in (1,2):
            notes=ports[port];phrase=phrases[port]
            for index,note in enumerate(notes):
                wanted=phrase[(index-10 if reset and index>=10 else index)%len(phrase)]
                assert note["bytes"]==wanted,(reset,port,index,note["bytes"],wanted)
                assert abs((note[field]-notes[0][field])/1e9-index/6)<=tolerance,(reset,port,index)
            first_slot_two.append(notes[10]["bytes"])
        c.results.append(dict(kind="song-boundary-reset-polymeter",reset_on_song_change=reset,
            slot_steps=10,slot2_first_onsets=first_slot_two,citation="README.md#song-editor",passed=True))

CASES={"M-MANUAL-CLOSURE-GHOST-001":dict(run=pocket_ghost_trigs,requirements=["CH-RANGE"],description="64-step channel: sixteen main hits on beats 1-4 of four bars, then ghost trigs on steps 44 and 60 (step 12 of bars 3 and 4), read from the channel trig rows"),
"M-MANUAL-CLOSURE-RESET-001":dict(run=polymeter_song_reset,requirements=["SONG-SLOTS","SONG-SETTINGS"],description="Four-against-three polymeter across ten-step song slots: Reset on song seq change On restarts both loops at slot two (60 and 79), Off lets them run on (64 and 81), exact MIDI phase"),
"M-MANUAL-CLOSURE-MOTION-001":dict(run=motion_controls,requirements=["CH-TEMPO"],description="Public native UI motion Off/On, continuously literal editor labels and rate, immediate input feedback, decorative marker and unchanged exact MIDI"),
"M-MANUAL-CLOSURE-PANIC-001":dict(run=panic_releases_sounding_note,requirements=["PANIC-GESTURE"],description="Panic held from Song while a long note sounds: its Note Off arrives early inside the 6,144-message sweep and playback continues"),
"M-MANUAL-CLOSURE-SONG-002":dict(run=song_repeats_advance,requirements=["SONG-SLOTS","SONG-SETTINGS"],
    description="Song mode On: slot 1 once, slot 2 for Repeats 2, then back to slot 1, with exact MIDI, slot lights and Pass readout"),
"M-MANUAL-CLOSURE-SONG-001":dict(run=song_controls,
    requirements=["SONG-SLOTS","SONG-SETTINGS"],
    description="Public Song copy/play/erase LEDs2/7/15, Slot Setup repeats1/16/2, exact four-note MIDI phase and stopped quiescence")}
