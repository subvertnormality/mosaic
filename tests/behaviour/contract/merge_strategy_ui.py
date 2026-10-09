"""One player-visible merge strategy shared by grid and norns.

Initial acceptance is characterized against the pre-alignment README; final
manual citations are added when the shared selector documentation settles.
The exact emitted music/LED expectations remain independent of Lua state.
"""
from contract.merge_extensions import two_patterns, loop_leds, play_loops


def valid_anchor_fixture(c):
    two_patterns(c, (5, 7))
    # Configure the assigned P01 anchor without changing the effective legacy
    # strategy. Rhythm remains reachable from both old OFF and new ALL.
    c.ui.channel_page("merge_shape", channel=1)
    c.ui.turn(2, 1); c.ui.press_key(3)
    c.ui.expect_header("merge_rhythm", channel=1)
    c.ui.turn(3, 1); c.ui.press_key(3)
    c.ui.expect_selected_field("detail", "Anchor", "1")
    # The existing assignment route opens C09; remove/reassign P02 so the
    # original two-pattern musical fixture is restored exactly.
    c.ui.tap_control("channel_editor")
    c.ui.tap_control("pattern_slot", 2)
    c.ui.tap_control("pattern_slot", 2)
    c.ui.expect_header("merge_detail", channel=1)
    c.ui.select_row("trig_mode", 1)
    # C09 applies one direction step per event; send distinct detents.
    for _ in range(5):
        c.ui.turn(3, -1)  # explicitly establish SKIP at the lower bound
    c.ui.turn(3, 1)       # ONLY
    c.ui.turn(3, 1)       # ALL; do not assume configure defaults


def foundation_selection(c):
    valid_anchor_fixture(c)
    # A positive detent beyond legacy ALL reaches Foundation, rather than
    # clamping at ALL. The valid saved anchor must not be silently replaced.
    c.ui.turn(3, 1)
    c.ui.expect_selected_field("detail", "Strategy", "FOUNDATION")
    c.results.append(dict(kind="merge-strategy-foundation-selection",passed=True,
                          characterization="shared five-choice effective selector"))


def witness(c):
    import json,hashlib
    s=c.snapshot();observation=c.observations[-1]
    return dict(observation_index=len(c.observations)-1,frame_sha256=s["frame"]["sha256"],
                grid_sha256=hashlib.sha256(json.dumps(s["grid"],sort_keys=True,separators=(",",":")).encode()).hexdigest(),
                midi_count=s["midi_count"],midi_outstanding=s["midi_capture"]["outstanding"],
                monotonic_ns=observation["monotonic_ns"],logical_ns=s.get("clock",{}).get("logical_ns"),
                recipe_index=len(c.recipe))

def music(c,events,**record):
    start=witness(c);play_loops(c,events,**record);end=witness(c)
    c.results[-1].update(witness=dict(start=start,end=end),midi_start_exclusive=start["midi_count"],midi_end_inclusive=end["midi_count"])

def checkpoint(c,name,**details):
    first=getattr(c,"_merge_checkpoint_result_start",0)
    fields=[dict(layout=r["layout"],label=r["label"],value=r["value"],observation_index=r["observation_index"],frame_sha256=r["frame_sha256"]) for r in c.results[first:] if r.get("kind")=="selected-field" and "observation_index" in r]
    c.results.append(dict(kind="merge-strategy-ui",checkpoint=name,passed=True,
                          characterization="shared effective selector",fields=fields,witness=witness(c),**details))
    c._merge_checkpoint_result_start=len(c.results)

STRATEGIES = ("SKIP", "ONLY", "ALL", "FOUNDATION", "FRAGMENTS")
FOUNDATION_EVENTS = [(1,1,60,127),(2,1,62,117),(3,1,64,107),(4,1,65,97),(5,1,60,70),(7,1,60,70)]
LEGACY_EVENTS = [(1,1,60,127),(2,1,62,117),(3,1,64,107),(4,1,65,97),(5,1,60,100),(7,1,60,100)]
FRAGMENT_EVENTS = [(5,1,60,100),(7,1,60,100)]


def strategy(c, value):
    c.ui.select_row("trig_mode", 1)
    for _ in range(5): c.ui.turn(3, -1)
    for _ in range(STRATEGIES.index(value)): c.ui.turn(3, 1)
    c.ui.expect_selected_field("detail", "Strategy", value)


def actual(c, value):
    c.ui.select_row("active_strategy", 2)
    c.ui.expect_selected_field("detail", "Active", value)


def saved_numeric_modes(c):
    for row,label in [(4,"Note mode inactive"),(5,"Velocity mode inactive"),(6,"Length mode inactive")]:
        c.ui.select_row("saved_mode", row)
        c.ui.expect_selected_field("detail",label,"AVERAGE SAVED")
        c.ui.turn(3,1)
        c.ui.expect_selected_field("detail",label,"AVERAGE SAVED")


def queued_cycle(c):
    """Literal first ALL loop, then Foundation on the next channel cycle."""
    from contract.merge_extensions import _note_ons, _placed, _loop_events
    strategy(c,"ALL")
    start=witness(c);before=start["midi_count"]
    c.ui.play()
    c.wait(lambda s:len(_note_ons(s,before))>=1)
    # The public request and read-only pending rows are observed before the
    # eight-step cycle boundary; no private scheduling state is consulted.
    c.action(type="enc",n=3,delta=2)
    c.ui.turn(2,2)
    c.ui.expect_selected_field("detail","Pending","FOUNDATION")
    c.ui.turn(2,4)
    c.ui.expect_selected_field("detail","Boundary","NEXT CYCLE")
    checkpoint(c,"pending-cycle",active="ALL",pending="FOUNDATION",boundary="NEXT CYCLE")
    wanted=_loop_events(LEGACY_EVENTS,0)+_loop_events(FOUNDATION_EVENTS,1)+_loop_events(FOUNDATION_EVENTS,2)[:1]
    state=c.wait(lambda s:len(_note_ons(s,before))>=len(wanted),timeout=8)
    observed,tolerance=_placed(c,_note_ons(state,before)[:len(wanted)])
    assert observed==wanted,dict(expected=wanted,actual=observed)
    c.ui.stop();c.wait(lambda s:s["midi_capture"]["outstanding"]==[])
    actual(c,"FOUNDATION")
    c.ui.select_row("pending_strategy",3)
    c.ui.expect_selected_field("detail","Pending","NONE")
    end=witness(c)
    c.results.append(dict(kind="merge-strategy-next-cycle",witness=dict(start=start,end=end),midi_start_exclusive=start["midi_count"],midi_end_inclusive=end["midi_count"],expected=[list(e) for e in wanted],actual=[list(e) for e in observed],tolerance_seconds=tolerance,passed=True))


def selector_workflow(c):
    """Characterization pending updated README merge-strategy citations."""
    foundation_selection(c)
    actual(c,"FOUNDATION")
    checkpoint(c,"foundation-active",strategy="FOUNDATION",active="FOUNDATION")
    loop_leds(c,{1,2,3,4,5,7})
    music(c,FOUNDATION_EVENTS,kind="effective-foundation-musical-result")
    # Foundation owns only trigs; ordinary numeric merge controls still edit.
    for row,label in [(4,"Note mode"),(5,"Velocity mode"),(6,"Length mode")]:
        c.ui.select_row("foundation_numeric",row)
        c.ui.expect_selected_field("detail",label,"AVERAGE")
        c.ui.turn(3,1);c.ui.expect_selected_field("detail",label,"UP")
        c.ui.turn(3,-1);c.ui.expect_selected_field("detail",label,"AVERAGE")
    # The same physical grid key continues from the norns selector.
    c.ui.tap_control("trig_merge_mode")
    c.ui.expect_selected_field("detail","Strategy","FRAGMENTS")
    actual(c,"FRAGMENTS")
    c.led_values([(14,8)],[15])
    saved_numeric_modes(c)
    checkpoint(c,"fragments-inactive",strategy="FRAGMENTS",active="FRAGMENTS",saved_modes=["AVERAGE"]*3)
    loop_leds(c,{5,7})
    music(c,FRAGMENT_EVENTS,kind="effective-fragments-musical-result",size=8,seed=0)
    c.ui.tap_control("trig_merge_mode")
    c.ui.expect_selected_field("detail","Strategy","SKIP")
    actual(c,"SKIP");c.led_values([(14,8)],[2])
    # Saved ordinary merge choices reappear unchanged when Shape is disabled.
    for row,label in [(4,"Note mode"),(5,"Velocity mode"),(6,"Length mode")]:
        c.ui.select_row("restored_mode",row)
        c.ui.expect_selected_field("detail",label,"AVERAGE")
    strategy(c,"SKIP");c.ui.turn(3,-1)
    c.ui.expect_selected_field("detail","Strategy","SKIP")
    checkpoint(c,"legacy-restored",strategy="SKIP",saved_modes=["AVERAGE"]*3)
    c.ui.tap_control("trig_merge_mode")
    c.ui.expect_selected_field("detail","Strategy","ONLY");c.led_values([(14,8)],[5])
    # The two source patterns have no shared trig, so Only must be silent.
    from contract.merge_extensions import _note_ons, LOOP, STEP_SECONDS
    loop_leds(c,set())
    only_start=witness(c);only_before=only_start["midi_count"]
    c.ui.play();c.elapse(2*LOOP*STEP_SECONDS)
    only_state=c.snapshot()
    assert _note_ons(only_state,only_before)==[], "Only sounded non-overlapping source trigs"
    c.ui.stop();c.wait(lambda value:value["midi_capture"]["outstanding"]==[])
    only_end=witness(c)
    c.results.append(dict(kind="effective-only-silence",loops=2,loop_steps=LOOP,elapsed_required_seconds=2*LOOP*STEP_SECONDS,witness=dict(start=only_start,end=only_end),midi_start_exclusive=only_start["midi_count"],midi_end_inclusive=only_end["midi_count"],expected=[],actual=[],passed=True))
    c.ui.tap_control("trig_merge_mode")
    c.ui.expect_selected_field("detail","Strategy","ALL");c.led_values([(14,8)],[8])
    loop_leds(c,{1,2,3,4,5,7})
    music(c,LEGACY_EVENTS,kind="restored-legacy-musical-result")
    # A completely unset anchor refuses Foundation without trapping the
    # five-choice cursor. Configuring the anchor is an explicit user action.
    # Anchor choices cycle only assigned patterns; there is no public NONE
    # choice after an anchor is saved. Use the untouched second channel's
    # genuinely unset anchor, and restore its empty assignment afterwards.
    c.ui.tap_control("channel_editor");c.ui.select_channel(2)
    c.ui.channel_page("merge_shape",channel=2)
    c.ui.select_row("rhythm",1);c.ui.press_key(3)
    c.ui.expect_selected_field("detail","Anchor","NONE")
    c.ui.tap_control("channel_editor")
    c.ui.tap_control("pattern_slot",1);c.ui.tap_control("pattern_slot",2)
    c.ui.expect_header("merge_detail",channel=2)
    strategy(c,"ALL")
    c.ui.turn(3,1)
    c.ui.expect_selected_field("detail","Strategy","FOUNDATION")
    actual(c,"ALL")
    c.ui.select_row("pending_strategy",3);c.ui.expect_selected_field("detail","Pending","NONE")
    c.ui.select_row("strategy_status",8);c.ui.expect_selected_field("detail","Request","NEEDS ANCHOR")
    c.ui.select_row("trig_mode",1);c.ui.expect_selected_field("detail","Strategy","FOUNDATION")
    checkpoint(c,"unset-anchor-refusal",selected="FOUNDATION",active="ALL",pending="NONE",request="NEEDS ANCHOR")
    c.ui.tap_control("trig_merge_mode")
    c.ui.expect_selected_field("detail","Strategy","FRAGMENTS")
    actual(c,"FRAGMENTS")
    strategy(c,"ALL")
    c.ui.tap_control("pattern_slot",1);c.ui.tap_control("pattern_slot",2)
    c.ui.tap_control("channel_editor");c.ui.select_channel(1)
    c.ui.channel_page("merge_shape",channel=1)
    c.ui.select_row("rhythm",1);c.ui.press_key(3)
    c.ui.expect_selected_field("detail","Anchor","1")
    c.ui.tap_control("channel_editor")
    c.ui.tap_control("pattern_slot",2);c.ui.tap_control("pattern_slot",2)
    # An assigned anchor becomes invalid if that pattern is removed. No
    # fallback anchor may silently take over the visible Foundation request.
    c.ui.tap_control("pattern_slot",1)
    c.ui.select_row("trig_mode",1);c.ui.turn(3,1)
    c.ui.expect_selected_field("detail","Strategy","FOUNDATION")
    actual(c,"ALL")
    c.ui.select_row("pending_strategy",3);c.ui.expect_selected_field("detail","Pending","NONE")
    c.ui.select_row("strategy_status",8);c.ui.expect_selected_field("detail","Request","NEEDS ANCHOR")
    c.ui.select_row("trig_mode",1);c.ui.expect_selected_field("detail","Strategy","FOUNDATION")
    checkpoint(c,"unassigned-anchor-refusal",selected="FOUNDATION",active="ALL",pending="NONE",request="NEEDS ANCHOR")
    c.ui.tap_control("trig_merge_mode")
    c.ui.expect_selected_field("detail","Strategy","FRAGMENTS")
    actual(c,"FRAGMENTS")
    c.ui.tap_control("pattern_slot",1)
    strategy(c,"ALL")
    queued_cycle(c)
    # The former independent Mode editor is now a read-only effective strategy.
    c.ui.channel_page("merge_shape",channel=1)
    c.ui.select_row("mode",0)
    c.ui.expect_selected_field("detail","Strategy","FOUNDATION")
    c.ui.turn(3,1)
    c.ui.expect_selected_field("detail","Strategy","FOUNDATION")
    checkpoint(c,"m02-readonly",strategy="FOUNDATION")
    # Dirty Rhythm settings must not survive opening the one selector.
    c.ui.turn(2,1);c.ui.press_key(3)
    c.ui.select_row("add_amount",1);c.ui.turn(3,-1)
    c.ui.expect_selected_field("detail","Add amount","99")
    c.ui.press_key(2)
    c.ui.select_row("strategy_selector",5);c.ui.press_key(3)
    c.ui.expect_header("merge_detail",channel=1)
    c.ui.press_key(2)
    c.ui.select_row("rhythm",1);c.ui.press_key(3)
    c.ui.select_row("add_amount",1)
    c.ui.expect_selected_field("detail","Add amount","100")
    checkpoint(c,"draft-discarded",label="Add amount",value="100")
    c.results.append(dict(kind="effective-merge-selector-summary",passed=True,characterization="shared selector, refusal, read-only saved modes, draft discard and cycle handoff"))
