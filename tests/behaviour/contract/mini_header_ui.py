"""Literal mini-header acceptance, independent of Mosaic drawing code.

Atlas is an authored external design contract frozen before implementation,
not a sampled application framebuffer. Public recipes identify their pages.
"""
import base64,json,hashlib
from pathlib import Path
ATLAS_SHA256="ed4d8972b1012b7570d402b6ba997c6c78c6c0926e577f974e03758782ed3c54"

def atlas():
    p=Path(__file__).with_name("mini_header_atlas.json")
    raw=p.read_bytes()
    assert hashlib.sha256(raw).hexdigest()==ATLAS_SHA256,"Literal mini-header design contract changed"
    a=json.loads(raw)
    assert a["palette"]=={".":0,"a":7,"b":11,"c":15}
    return {x["id"]:x for x in a["screens"]}

def literal_pixels(spec,rows):
    assert len(rows)==8 and spec["height"]==8
    width=spec["width"];x,y=spec["origin"]
    assert 1<=width<=32 and (x,y)==(128-width,0)
    assert all(len(row)==width and set(row)<=set(".abc") for row in rows)
    data=bytearray(128*64*4);level={".":0,"a":7,"b":11,"c":15}
    for yy,row in enumerate(rows):
        for xx,char in enumerate(row):
            z=17*level[char];i=((y+yy)*128+x+xx)*4
            data[i:i+3]=bytes((z,z,z))
    return bytes(data)

def band(data,left,right=128,top=0,bottom=8):
    return bytes(data[(y*128+x)*4+k] for y in range(top,bottom) for x in range(left,right) for k in range(3))

def matching_poses(state,page):
    spec=atlas()[page];data=base64.b64decode(state["frame"]["pixels_base64"])
    left=121 if spec["layout"] in ("overview_masks","overview_params","dashboard") else 96
    assert spec["origin"][0]>=left
    observed=band(data,left)
    return [i for i,rows in enumerate(spec["frames"]) if observed==band(literal_pixels(spec,rows),left)]

def require_icon(state,page,enabled):
    matches=matching_poses(state,page)
    assert matches and (enabled or 0 in matches),dict(page=page,enabled=enabled,expected="literal authored mini-header frame" if enabled else "literal resting mini-header pose0",actual_matching_poses=matches)
    return matches

def set_motion(c,enabled):
    """Public Mosaic option input; Screen separator owns row22, glyphs start23."""
    from frame_oracle import selected_line
    from ui_map import NATIVE_MENU
    c.ui.press_key(1);c.ui.turn(1,4);c.ui.press_key(3)
    c.ui.expect_menu_label(NATIVE_MENU["levels_root"])
    position=next(i for i,v in enumerate(c.snapshot()["diagnostics"]["parameter_roots"]) if v["id"]=="mosaic")
    c.ui.turn(2,position);c.ui.press_key(3);c.ui.turn(2,-60)
    for _ in range(40):
        if selected_line(c.snapshot(),"UI motion",top=23):break
        c.ui.turn(2,1)
    else:raise AssertionError("Exact public UI motion label not reached")
    c.ui.turn(3,3 if enabled else -3)
    c.ui.expect_menu_option_row("UI motion","On" if enabled else "Off",top=23)
    c.results.append(dict(kind="mosaic-option-input",label="UI motion",enabled=enabled))
    c.ui.press_key(2);c.ui.turn(2,-60);c.ui.expect_menu_label(NATIVE_MENU["levels_root"])
    c.ui.press_key(2);c.ui.press_key(1)

def missing_icon_regression(c):
    """Smallest positive contract: reachable Clock resting icon replaces mark."""
    c.configure()
    set_motion(c,False)
    c.ui.channel_page("clock_mods",channel=1);c.ui.select_row("rate",0)
    c.ui.expect_selected_field("vertical_list","Rate","/1")
    s=c.snapshot();matches=require_icon(s,"C04",False)
    c.results.append(dict(kind="public-mini-header",page="C04",enabled=False,passed=True,matching_poses=matches,atlas_sha256=ATLAS_SHA256,observation_index=len(c.observations)-1,citation="README.md#ui-motion",characterization="literal external mini-header design acceptance"))
