"""Public-input acceptance for vertical editors; README Norns Menu Navigation.
New vertical layout is characterisation pending the companion README update.
Literal row labels and raster positions never come from app output.
"""
import base64
from frame_oracle import render, _region_matches, text_width

def label_row(state, label, y, selected=False):
    commands=[(7,y,15 if selected else 7,label)]
    if selected: commands.append((0,y,15,">"))
    return _region_matches(base64.b64decode(state["frame"]["pixels_base64"]),
        render(commands), y-7,y+2,0,8+int(text_width(label)))

def clock_list(c):
    c.ui.channel_page("clock_mods", channel=1)
    c.ui.select_row("rate",0)
    try:
        c.wait(lambda state: label_row(state,"Rate",27,True) and
               label_row(state,"Feel source",36) and label_row(state,"Swing type",45),timeout=2)
    except AssertionError as error:
        raise AssertionError("vertical-list acceptance: Clock must simultaneously show selected Rate, Feel source and Swing type in stable rows") from error
    c.ui.expect_selected_field("vertical_list","Rate","/1")
    c.results.append(dict(kind="vertical-list-ui",checkpoint="clock-neighbors",passed=True,
        rows=["Rate","Feel source","Swing type"],citation="README.md#norns-menu-navigation"))

    # Same live scope and selection survive native PARAMS entry/return.
    c.ui.press_key(1); c.ui.press_key(1)
    c.ui.expect_selected_field("vertical_list","Rate","/1")
    c.ui.select_row("swing_type",1)
    # README.md#clocks-swing-and-shuffle: Swing type starts at X (follow the global feel).
    c.ui.expect_selected_field("vertical_list","Swing type","X")
    c.ui.turn(3,-3); c.ui.press_key(3)
    c.ui.expect_selected_field("vertical_list","Swing type","X")
    c.results.append(dict(kind="vertical-list-ui",checkpoint="inherit-sentinel",passed=True,
        label="Swing type",value="X",citation="README.md#clocks-swing-and-shuffle"))
    c.ui.turn(3,2); c.ui.press_key(3)
    c.ui.expect_selected_field("vertical_list","Swing type","Shuffle")
    # Large physical delta clamps at the last row, never wraps.
    c.ui.encoder_event(2,126); c.elapse(.2)
    c.ui.expect_selected_field("vertical_list","Shuffle amount","0")
    c.results.append(dict(kind="vertical-list-ui",checkpoint="scroll-end",passed=True,
        label="Shuffle amount",value="0",citation="README.md#norns-menu-navigation"))
    c.ui.encoder_event(2,-126); c.elapse(.2)
    c.ui.expect_selected_field("vertical_list","Rate","/1")
    c.ui.channel_page("masks",channel=1)
    c.ui.select_row("note",1); c.ui.expect_selected_mask("note","X")
    c.ui.expect_field_value("velocity","X")
    c.ui.expect_field_value("length","X")
    c.results.append(dict(kind="vertical-list-ui",checkpoint="masks-unchanged",passed=True,
        layout="overview_masks",citation="README.md#norns-menu-navigation"))
    c.ui.pattern_editor()
    c.ui.trig_options()
    c.ui.encoder_event(3,-126); c.elapse(.2)
    c.ui.expect_selected_field("vertical_list","Tresillo amount","x8")
    c.results.append(dict(kind="vertical-list-ui",checkpoint="single-field",passed=True,
        label="Tresillo amount",value="x8",citation="README.md#adding-trigs"))

CASES={"M-UI-VERTICAL-001":dict(run=clock_list,requirements=["CH-TEMPO"],
 description="Visible vertical Clock neighbors through public norns inputs")}
