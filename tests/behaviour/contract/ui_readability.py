"""Public readability characterizations; no native vertical-overflow claim.

C07's existing long assignment label is genuinely reachable. Converted Clock
and Scale fields fit their full-width selected regions and remain still.
Dormant parameter-detail routes do not establish native vertical overflow.
"""
import base64
from frame_oracle import render,fit,variants,_region_matches,live_header_matches,text_width
from contract.live_ui_sweep import footer_render,hints
from contract.mini_header_animation_ui import require_icon,sample,ATLAS_SHA256,atlas,native_events,wait_normal_footer
from contract.merge_strategy_ui import witness

LABEL="Quantised Fixed Note"


def pixels(s):return base64.b64decode(s["frame"]["pixels_base64"])


def stable_band(data,excluded=(),icon_left=120):
    return bytes(data[(y*128+x)*4+k] for y in range(64) for x in range(128) for k in range(3)
                 if y not in excluded and not (y<8 and x>=icon_left))


def assignment_marquee(c,enabled):
    c.ui.channel_page("trig_locks",channel=1);c.ui.press_key(2)
    c.ui.expect_selected_field("detail",LABEL,"CURRENT")
    expected=variants(lambda:render([(0,36,15,">"),(7,36,15,fit(LABEL,72)),((None,126),36,15,"CURRENT")]))
    assert text_width(LABEL)>72 and len(expected)>1
    footer=footer_render(hints("C07"))
    c.wait(lambda s:_region_matches(pixels(s),footer,57,64),timeout=5)
    samples=[];fixed=None;grid=None;count=None;phases=set()
    neighbors=render([(7,27,6,"Fixed Note"),(7,45,6,"Random Note")])
    for _ in range(32):
        c.elapse(.08);s=c.snapshot();actual=pixels(s)
        assert live_header_matches(s,"ASSIGN PARAM","CH01","detail")
        assert _region_matches(actual,neighbors,20,29) and _region_matches(actual,neighbors,38,47), "Fitting neighbors moved"
        assert _region_matches(actual,footer,57,64), "Action footer moved"
        matches=[i for i,f in enumerate(expected) if _region_matches(actual,f,29,38)]
        assert len(matches)==1,"Native selected label/value is not an exact authored marquee phase"
        phase=matches[0];phases.add(phase);mini=require_icon(s,"C07",enabled);unchanging=stable_band(actual,range(29,38),icon_left=96)
        if fixed is None:fixed=unchanging;grid=s["grid"];count=s["midi_count"]
        assert unchanging==fixed,"Title, scope or fitting neighbor text changed"
        assert s["grid"]==grid and s["midi_count"]==count,"Marquee changed grid or emitted MIDI"
        samples.append(dict(observation_index=len(c.observations)-1,frame_sha256=s["frame"]["sha256"],expected_phase=phase,mini_matching_poses=mini))
    if enabled:
        assert 0 in phases and len(expected)-1 in phases,"Both complete start and complete suffix phases must be readable"
    else:assert phases=={0},"Motion Off must retain the existing static label trimming"
    c.results.append(dict(kind="public-assignment-marquee",mini_page="C07",atlas_sha256=ATLAS_SHA256,enabled=enabled,label=LABEL,value="CURRENT",samples=samples,expected_phases=len(expected),observed_phases=sorted(phases),passed=True,citation="README.md#trig-parameters",characterization="C07 detail marquee, not native vertical overflow"))
    c.ui.press_key(2)
    c.ui.expect_selected_field("overview_params",LABEL,"X")


def fitting_vertical(c,page,label,value,title,scope,enabled):
    if page=="scale":c.ui.scale_editor();c.ui.select_row("scale",1)
    else:c.ui.channel_page("clock_mods",channel=1);c.ui.select_row("rate",0)
    c.ui.expect_selected_field("vertical_list",label,value)
    wait_normal_footer(c,"S01" if page=="scale" else "C04")
    before=None;samples=[]
    for _ in range(6):
        c.elapse(.08);s=c.snapshot();actual=pixels(s)
        assert live_header_matches(s,title,scope,"vertical_list")
        from frame_oracle import vertical_selected_field_matches
        assert vertical_selected_field_matches(s,label,value)
        require_icon(s,"C04" if page=="clock" else "S01",enabled)
        stable=stable_band(actual,icon_left=96)
        if before is None:before=stable
        assert stable==before,"Fitting vertical text changed during decorative motion"
        samples.append(dict(observation_index=len(c.observations)-1,frame_sha256=s["frame"]["sha256"]))
    c.results.append(dict(kind="public-fitting-vertical-text",page=page,enabled=enabled,label=label,value=value,samples=samples,passed=True,citation="README.md#ui-motion"))


def leave_clock_menu(c):
    """Restore the native LEVELS cursor, as existing Mosaic option setters do."""
    c.ui.press_key(2);c.ui.turn(2,-60)
    c.ui.expect_native_menu_label("levels_root")
    c.ui.press_key(2);c.ui.press_key(1)


def internal_tempo(c,target):
    """Explicit public clock input, with only legal bounded encoder events."""
    c.ui.enter_native_levels_menu();c.ui.select_native_parameter_group("clock")
    c.ui.turn(3,-4);c.ui.expect_native_menu_value("clock_source","internal")
    c.ui.turn(2,1);c.ui.expect_native_menu_label("clock_tempo")
    for _ in range(4):c.action(type="enc",n=3,delta=-126);c.elapse(.05)
    c.ui.expect_menu_value("1")
    remaining=target-1
    while remaining:
        steps=min(63,remaining);c.action(type="enc",n=3,delta=2*steps);c.elapse(.05);remaining-=steps
    c.ui.expect_menu_value(str(target));leave_clock_menu(c)

def enable_master_clock_output(c):
    """Existing public CLOCK output, without resetting the four-note fixture."""
    from frame_oracle import selected_line
    c.ui.enter_native_levels_menu();c.ui.select_native_parameter_group("clock")
    c.ui.turn(2,-32);c.ui.expect_native_menu_label("clock_source")
    c.ui.expect_native_menu_value("clock_source","internal")
    c.ui.turn(2,7)
    c.wait(lambda state:selected_line(state,"1. Emulator MIDI",top=24))
    def enabled(state):
        data=pixels(state)
        return all(data[(y*128+x)*4+k]==255 for y in range(26,29) for x in range(124,127) for k in range(3))
    assert not enabled(c.snapshot()),"Fresh native MIDI clock output must start disabled"
    c.ui.turn(3,1);c.wait(enabled);receipt=witness(c)
    leave_clock_menu(c)
    return receipt


def readability_workflow(c):
    c.configure();internal_tempo(c,90);c.ui.channel_page("trig_locks",channel=1);c.ui.press_key(2)
    c.ui.turn(3,1);c.ui.turn(3,1);c.ui.press_key(3)
    c.ui.expect_selected_field("detail",LABEL,"CURRENT")
    c.ui.press_key(2)
    masks=[];params=[];overview_receipts=[]
    for enabled in (False,True):
        c.ui.set_mosaic_options([("UI motion",enabled)])
        assignment_marquee(c,enabled)
        params.append(stable_band(pixels(c.snapshot()),range(8)))
        overview_receipts.append(dict(page="C02",enabled=enabled,**witness(c)))
        sample(c,"C02",enabled,3,require_all=enabled,tempo=90)
        fitting_vertical(c,"clock","Rate","/1","CLOCK","CH01",enabled)
        sample(c,"C04",enabled,3,require_all=enabled,tempo=90)
        fitting_vertical(c,"scale","Scale","Major","SCALE","SLOT 01",enabled)
        sample(c,"S01",enabled,4,require_all=enabled,tempo=90)
        c.ui.tap_control("channel_editor")
        c.ui.channel_page("masks",channel=1);c.ui.select_row("note",1)
        c.ui.expect_selected_mask("note","X")
        c.ui.expect_field_value("velocity","X");c.ui.expect_field_value("length","X")
        masks.append(stable_band(pixels(c.snapshot()),range(8)))
        overview_receipts.append(dict(page="C01",enabled=enabled,**witness(c)))
        sample(c,"C01",enabled,3,require_all=enabled,tempo=90)
    assert masks[0]==masks[1],"Motion setting changed the actual Masks overview"
    assert params[0]==params[1],"Motion setting changed the actual Trig Params overview"
    for tempo in (40,240):
        internal_tempo(c,tempo);c.ui.channel_page("clock_mods",channel=1);c.ui.select_row("rate",0)
        c.ui.expect_selected_field("vertical_list","Rate","/1")
        sample(c,"C04",True,5,require_all=(tempo==40),tempo=tempo)
    internal_tempo(c,90)
    clock_output_setup=enable_master_clock_output(c)
    c.ui.channel_page("masks",channel=1);c.ui.select_row("note",1)
    start=witness(c)
    # Preserve actual intermediate native specimens for the independent F8
    # phase audit; playback's exact musical and Stop assertions are unchanged.
    previous_limit=getattr(c,"wait_observation_limit",None)
    c.wait_observation_limit=2048
    try:
        c.playback([(1,[144,n,v]) for n,v in [(60,127),(62,117),(64,107),(65,97)]],cycles=2)
    finally:c.wait_observation_limit=previous_limit
    end=witness(c)
    # Playback retains the unchanged exact original phrase. Each visible
    # transport frame must also contain an exact authored Masks motif.
    play_frames=[]
    for i in range(start["observation_index"],end["observation_index"]+1):
        state=c.observations[i]["state"];found=require_icon(state,"C01",True)
        envelope=c.observations[i]
        play_frames.append(dict(observation_index=i,frame_sha256=state["frame"]["sha256"],frame_revision=envelope["frame_revision"],monotonic_ns=envelope["monotonic_ns"],matching_poses=found))
    from mini_phase_oracle import check_playing_phases
    phase_check=check_playing_phases(play_frames,c.observations,native_events(c),atlas()["C01"],start["midi_count"],end["midi_count"],c.clock_mode,tempo=90)
    c.results.append(dict(kind="public-readability-summary",clock_source="public-midi-clock-output",transport="playing",clock_output_setup=clock_output_setup,phase_check=phase_check,overviews=overview_receipts,witness=dict(start=start,end=end),midi_start_exclusive=start["midi_count"],midi_end_inclusive=end["midi_count"],playing_mini_frames=play_frames,atlas_sha256=ATLAS_SHA256,passed=True,citation="README.md#norns-menu-navigation",citations=["README.md#ui-motion","README.md#trig-parameters","README.md#norns-menu-navigation"],characterization="C07 overflow positive; converted fitting text and overviews stable; vertical overflow positive is component-only because no reachable converted field exceeds119px"))
