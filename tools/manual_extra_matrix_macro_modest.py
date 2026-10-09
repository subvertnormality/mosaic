"""Modest Matrix Macro 1 teaching case; exact native MIDI oracle."""
import math
CASE_ID="M-MANUAL-MODULATION-001"
CITATION="manual:lfos-and-modulation"
BASE_CC,DEPTH,MACRO_VALUE,EXPECTED_CC=32,.10,.50,38
PHRASE=((60,127),(62,117),(64,107),(65,97))
def expected_cc(base,depth,source): return math.floor(base+128*depth*source+.5)
def assert_phase(events,notes,value,clock_mode):
    ons=[e for e in events if e["port"]==1 and e["bytes"][0]==144 and e["bytes"][2]>0]
    ccs=[e for e in events if e["bytes"] and e["bytes"][0]&240==176]
    want_notes=[(1,[144,*PHRASE[i%4]]) for i in range(len(notes))]
    assert [(e["port"],e["bytes"]) for e in ons]==want_notes, (want_notes,[(e["port"],e["bytes"]) for e in ons])
    # Control 1 is a device parameter here, not a trig-lock slot: Mosaic sends its
    # current (modulated) value once as playback starts, never per onset.
    # Contrast M-MOD-004, where Control 1 is also a lock slot and every step sends.
    assert [(e["port"],e["bytes"]) for e in ccs]==[(1,[176,1,value])], ([(1,[176,1,value])],[(e["port"],e["bytes"]) for e in ccs])
    starts=[e for e in events if e["bytes"]==[250]]
    assert starts and ccs[0]["index"]<starts[0]["index"]<ons[0]["index"]
    field="logical_ns" if clock_mode=="controlled-experimental" else "monotonic_ns"
    tolerance=2e-9 if clock_mode=="controlled-experimental" else .01
    for i,note in enumerate(ons):
        assert abs((note[field]-ons[0][field])/1e9-i/6)<=tolerance
def run(c):
    from cases import assert_durations
    from note_accounting import continuation_onsets, window_onsets
    def label(k): c.ui.expect_native_menu_label(k)
    def depth(k): c.ui.expect_native_menu_value("modulation_control_1",k)
    assert c.profile=="midi-modulation"
    c.ui.open_patch_control(configured=True); label("patch_control_configured")
    depth("off"); c.ui.turn_patch_control(33); depth("base_32"); c.ui.press_key(1)
    # Public Matrix route: configured CC Control 1 <- Macro 1, depth +0.10.
    c.ui.press_key(1); c.ui.turn(1,-4); c.ui.turn(2,1); c.ui.press_key(3)
    label("mod_devices_root"); c.ui.turn(2,2); label("mod_mods_root")
    c.ui.press_key(3); label("mod_matrix_root"); c.ui.press_key(3); label("levels_root")
    c.ui.seek_native_parameter_root("channel_1_device_parameters")
    c.ui.press_key(3); c.ui.expect_trig_parameter("fixed_note")
    c.ui.seek_native_menu_parameter("configured_control_1",attempts=180)
    label("patch_control_configured"); c.ui.press_key(3); label("mod_rhythm_1")
    c.ui.turn(2,12); label("mod_macro_1"); c.ui.turn(3,10)
    c.ui.expect_menu_value("0.10")
    c.results.append(dict(kind="manual-modulation-cc-phase",phase="route-depth",depth=DEPTH,source=0,cc=32,citation=CITATION,passed=True))
    phrase=[(1,[144,n,v]) for n,v in PHRASE]
    def phase(name,source,depth_value,cc_value):
        before=c.snapshot()["midi_count"]; played=c.playback(phrase,cycles=2)
        events=[e for e in c.snapshot()["midi"] if e["index"]>before]
        notes=window_onsets(events)
        late=continuation_onsets(c,played,notes,phrase,lambda i:i/6,name)
        assert_phase(events,notes,cc_value,c.clock_mode)
        assert_durations(c,notes,[1]*(len(notes)-1),events=events)
        c.results.append(dict(kind="manual-modulation-cc-phase",phase=name,depth=depth_value,source=source,cc=cc_value,notes=len(notes),late_window_onsets=len(late),citation=CITATION,passed=True))
    phase("zero-source",0,DEPTH,32)
    # Toolkit Macro 1 has a linear 0..1 control; 50 detents set 0.50 (readout 0.5).
    c.ui.turn(1,4); c.ui.press_key(2); c.ui.encoder_event(2,-126); c.elapse(.15)
    label("levels_root"); c.ui.seek_native_parameter_root("macro_1")
    c.ui.press_key(3); label("mod_active"); c.ui.turn(2,1); label("mod_value")
    c.ui.encoder_event(3,100); c.elapse(.15); c.ui.expect_menu_value("0.5")
    phase("halfway",MACRO_VALUE,DEPTH,EXPECTED_CC)
    assert EXPECTED_CC==expected_cc(BASE_CC,DEPTH,MACRO_VALUE)
    # Matrix formula plus M-MOD-004's 128-interval sweep predicts CC 38; remain strict.
    # The norns menu stays open on the PARAMS page through playback. As in M-MOD-004,
    # E1 returns to the Mods page, whose Matrix screen is remembered on Macro 1; no K1,
    # which would close the menu and send E1 to Mosaic.
    c.ui.turn(1,-4); c.ui.press_key(3); c.ui.press_key(3); c.ui.press_key(3)
    label("mod_macro_1"); c.ui.press_key(3); depth("clear_depth")
    c.results.append(dict(kind="manual-modulation-cc-phase",phase="cleared-depth",depth=None,source=MACRO_VALUE,cc=32,citation=CITATION,passed=True))
    phase("clear-baseline",MACRO_VALUE,None,32)
    # Leave route clear and source at its initial value.
    # Same Matrix-to-levels exit as before the halfway phase; the menu is still open.
    c.ui.turn(1,4); c.ui.press_key(2); c.ui.encoder_event(2,-126); c.elapse(.15)
    label("levels_root"); c.ui.seek_native_parameter_root("macro_1"); c.ui.press_key(3)
    label("mod_active"); c.ui.turn(2,1); label("mod_value")
    c.ui.encoder_event(3,-100); c.elapse(.15); c.ui.expect_menu_value("0.0")
    c.results.append(dict(kind="manual-modulation-cc-phase",phase="returned-to-source-baseline",depth=None,source=0,cc=32,citation=CITATION,passed=True))
CASES={CASE_ID:{"run":run,"requirements":["MOD-ROUTING","MOD-ROUTE-001"],"description":"At +0.10 depth, Macro 1 at 0.50 moves configured CC 1 from 32 to 38; clearing the route restores 32 while the four-note phrase, timing and gates stay the same.","case_id":CASE_ID,"citation":CITATION}}
