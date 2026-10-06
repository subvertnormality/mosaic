"""Additional manual acceptance fixtures through public grid/key/encoder input.

README Result and Reason, Interlock, and Clocks, Swing and Shuffle.
Expected rows are authored from the literal fixture and display contracts;
no Mosaic state is read. Suppressed Role EMPTY / Velocity NONE is explicitly
characterised outside README's broad role description.
"""
from merge_extension_acceptance import (interlock_pair, Capture, stop_and_drain,
    loop_leds, field, tolerance, interlock_swing_invariance_workflow)
from frame_oracle import dashboard_row_matches

REASON_CITATION = "README.md#result-and-reason"

def reason(c, step, decision, role, velocity, name):
    c.ui.channel_page("merge_shape", channel=1)
    c.ui.select_row("result", 4); c.ui.press_key(3)
    c.ui.expect_header("merge_result", channel=1)
    c.ui.select_row("step", 0); c.ui.turn(3, -64); c.ui.turn(3, step - 1)
    c.ui.expect_selected_field("detail", "Step", str(step))
    c.ui.select_row("decision", 2)
    c.ui.expect_selected_field("detail", "Decision", decision)
    c.ui.select_row("reason", 3); c.ui.press_key(3)
    c.ui.expect_header("merge_reason", channel=1)
    rows = [("Step", str(step)), ("Role", role), ("Decision", decision),
            ("Interlock", "ON"), ("Velocity", velocity), ("Pitch target", "LEGACY")]
    c.wait(lambda state: all(dashboard_row_matches(state, i, label, value)
                            for i, (label, value) in enumerate(rows, 1)))
    c.results.append(dict(kind="manual-reason-dashboard", checkpoint=name,
                          rows=[list(row) for row in rows], citation=REASON_CITATION,
                          characterisation="characterisation outside legacy README: suppressed Role is EMPTY P2 and Velocity is NONE",
                          passed=True))

def reason_workflow(c):
    interlock_pair(c, leader_step=5)
    reason(c, 7, "OK", "ADDITION P2", "70", "admitted-addition")
    reason(c, 5, "INTERLOCK CH02", "EMPTY P2", "NONE", "interlock-rejection")
    # README Rhythm: Anchor gap 1 removes additions adjacent to anchors.
    # Step5 borders anchor4; Interlock also rejects the leader's step5.
    c.ui.channel_page("merge_shape", channel=1); c.ui.select_row("rhythm", 1); c.ui.press_key(3)
    c.ui.expect_header("merge_rhythm", channel=1)
    c.ui.select_row("anchor_gap", 4); c.ui.turn(3, 1); c.ui.press_key(3)
    c.ui.expect_selected_field("detail", "Anchor gap", "1")
    loop_leds(c, {1, 2, 3, 4, 7})
    reason(c, 5, "GAP, INTERLOCK", "EMPTY P2", "NONE", "ordered-gap-interlock")
    capture = Capture(c); midi_start_index=capture.window.after; c.ui.play()
    capture.until(lambda k: len(k.note_ons(1)) >= 6, timeout=5)
    ons=capture.note_ons(1)[:6]; key=field(c); origin=ons[0][key]
    expected=[(0,60,127),(24,62,117),(48,64,107),(72,65,97),
              (144,60,70),(192,60,127)]
    allowed=tolerance(c)
    for event,(pulse,pitch,velocity) in zip(ons,expected):
        assert event['data']==[pitch,velocity], (event,pitch,velocity)
        assert abs((event[key]-origin)/1e9-pulse/144)<=allowed, (event,pulse,allowed)
    stop_and_drain(c,capture)
    c.results.append(dict(kind="manual-reason-midi", expected=[list(v) for v in expected],
                          absent_pulse=96, channel=1, midi_start_index=midi_start_index, tolerance_seconds=allowed,
                          citation="README.md#interlock", passed=True))
    loop_leds(c, {1,2,3,4,7})

def swing_workflow(c):
    # Add a visible setting checkpoint to the unchanged legacy timing case.
    select=c.ui.select_field; press=c.ui.press_key; selected=[None]
    def tracked_select(name, *args, **kwargs):
        selected[0]=name
        return select(name,*args,**kwargs)
    def checked_press(n, *args, **kwargs):
        result=press(n,*args,**kwargs)
        if n==3 and selected[0]=="swing_x":
            c.ui.expect_header("clock_mods", channel=1)
            c.ui.expect_selected_field("vertical_list", "Swing", "25")
            selected[0]=None
        return result
    c.ui.select_field=tracked_select; c.ui.press_key=checked_press
    try: interlock_swing_invariance_workflow(c)
    finally: c.ui.select_field=select; c.ui.press_key=press

CASES={
 "M-MANUAL-REASON-001":dict(run=reason_workflow, requirements=["MERGE-INTERLOCK"],
   description="Six literal Reason rows, ordered independent filters and emitted suppression"),
 "M-MANUAL-SWING-001":dict(run=swing_workflow,
   requirements=["MERGE-INTERLOCK","CH-TEMPO"],
   description="README Swing25 exact pulse times with nominal Interlock suppression")}
