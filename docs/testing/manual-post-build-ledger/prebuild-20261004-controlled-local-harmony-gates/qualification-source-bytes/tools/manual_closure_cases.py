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


def song_controls(c):
    from midi_window import MidiWindow
    ui=c.ui;ui.configure()
    ui.set_mosaic_options([("Song mode",False)])
    ui.song_editor();ui.copy_slot(1,2,control="song_pattern_slot")
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
    c.wait(lambda s:queued.extend(s) and len(queued.note_ons())>=69,timeout=15)
    ui.stop();c.wait(lambda s:queued.extend(s) and not s["midi_capture"]["outstanding"])
    notes=queued.note_ons()
    from cases import assert_durations
    for index,event in enumerate(notes):
        pitch=[60,62,64,65][index%4]+(12 if index>=64 else 0)
        assert event["port"]==1 and event["bytes"]==[144,pitch,[127,117,107,97][index%4]],(index,event)
        assert abs((event[domain]-notes[0][domain])/1e9-index/6)<=tolerance
    assert_durations(c,notes,[1]*(len(notes)-1))
    c.led_values([(1,1),(2,1),(3,1)],[15,7,2])
    c.results.append(dict(kind="manual-song-queue-transition",midi_start_index=queue_marker,
        from_slot=2,to_slot=1,transition_index=64,old_phrase=[60,62,64,65],new_phrase=[72,74,76,77],
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


CASES={"M-MANUAL-CLOSURE-MOTION-001":dict(run=motion_controls,requirements=["CH-TEMPO"],description="Public native UI motion Off/On, continuously literal editor labels and rate, immediate input feedback, decorative marker and unchanged exact MIDI"),
"M-MANUAL-CLOSURE-SONG-001":dict(run=song_controls,
    requirements=["SONG-SLOTS","SONG-SETTINGS"],
    description="Public Song copy/play/erase LEDs2/7/15, Slot Setup repeats1/16/2, exact four-note MIDI phase and stopped quiescence")}
