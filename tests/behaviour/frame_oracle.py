"""Independent literal Mosaic header oracle, never sampled from app output.

Pinned page.lua places the selected page title at (0,9), 8px norns font,
level 10. ui.lua places 'm' at (120,9). Body controls begin below this band.
Use the shared font/rasterizer as a rendering primitive, not Mosaic draw code.
"""
import base64,ctypes as C
from driver import EMULATOR_ROOT as ROOT
from ui_map import CHANNEL_COUNT, HEADERS, SCREEN, header_text
import json
def read_json(path):return json.loads(path.read_text())

_font_state=None

def render(commands,font_size=8,antialias=2):
    global _font_state
    ft,ca=_font_state[:2] if _font_state else (C.CDLL('libfreetype.so.6'),C.CDLL('libcairo.so.2'))
    def bind(lib,name,args,result=None):
        f=getattr(lib,name);f.argtypes=args;f.restype=result;return f
    ptr=C.c_void_p; integer=C.c_int; double=C.c_double
    # Cairo caches scaled fonts beyond a context's lifetime. Keep their
    # FreeType face/library alive for this oracle process, not just one draw.
    if _font_state is None:
        library=ptr();face=ptr()
        assert bind(ft,'FT_Init_FreeType',[C.POINTER(ptr)],integer)(C.byref(library))==0
        font=read_json(ROOT/'.runtime/current.json')['source']+'/resources/norns.ttf'
        assert bind(ft,'FT_New_Face',[ptr,C.c_char_p,C.c_long,C.POINTER(ptr)],integer)(library,font.encode(),0,C.byref(face))==0
        fontface=bind(ca,'cairo_ft_font_face_create_for_ft_face',[ptr,integer],ptr)(face,0)
        _font_state=(ft,ca,library,face,fontface)
    else:
        ft,ca,library,face,fontface=_font_state
    surface=bind(ca,'cairo_image_surface_create',[integer,integer,integer],ptr)(0,128,64)
    context=bind(ca,'cairo_create',[ptr],ptr)(surface)
    options=bind(ca,'cairo_font_options_create',[],ptr)()
    try:
        bind(ca,'cairo_font_options_set_antialias',[ptr,integer])(options,antialias)
        bind(ca,'cairo_set_font_options',[ptr,ptr])(context,options)
        bind(ca,'cairo_set_font_face',[ptr,ptr])(context,fontface)
        bind(ca,'cairo_set_font_size',[ptr,double])(context,font_size)
        for command in commands:
            x,y,level,label=command[:4]
            # An optional fifth element sets this command's font size.
            size=command[4] if len(command)>4 else font_size
            bind(ca,'cairo_set_font_size',[ptr,double])(context,size)
            if x is None or isinstance(x,tuple):
                extents=(double*6)()
                bind(ca,'cairo_text_extents',[ptr,C.c_char_p,C.POINTER(double)])(context,label.encode(),extents)
                right=127 if x is None else x[1]
                x=right-extents[2]  # Native text_right subtracts ink width.
            bind(ca,'cairo_set_source_rgb',[ptr,double,double,double])(context,level/15,level/15,level/15)
            bind(ca,'cairo_move_to',[ptr,double,double])(context,x,y)
            bind(ca,'cairo_show_text',[ptr,C.c_char_p])(context,label.encode())
        bind(ca,'cairo_surface_flush',[ptr])(surface)
        data=bind(ca,'cairo_image_surface_get_data',[ptr],ptr)(surface)
        return C.string_at(data,128*64*4)
    finally:
        bind(ca,'cairo_destroy',[ptr])(context)
        bind(ca,'cairo_surface_destroy',[ptr])(surface)
        bind(ca,'cairo_font_options_destroy',[ptr])(options)

def header(text,selected=None,tabs=8):
    if selected is None:
        matches_by_key = [data for key,data in HEADERS.items()
                          if "{channel}" in data["template"] and
                          any(header_text(key,channel=channel)==text
                              for channel in range(1,CHANNEL_COUNT+1))]
        if len(matches_by_key)!=1:raise KeyError(text)
        selected=matches_by_key[0]['selected'];tabs=matches_by_key[0]['tabs']
    commands=[((tab-1)*SCREEN['tab_pitch'],SCREEN['tab_baseline'],10 if tab==selected else 1,'_') for tab in range(1,tabs+1)]
    commands += [((*SCREEN['title'],text)),SCREEN['brand']]
    return render(commands)[:128*SCREEN['header_rows'][1]*4]

def selected_line(state,text,x=0,width=70,top=None):
    # Native menu selected rows use baseline30, level15. Ignore the separate
    # right-hand value field, not the text glyphs or background around them.
    row=SCREEN['selected_row'];top=row['top'] if top is None else top
    expected=render([(x,row['baseline'],row['level'],text)])
    actual=base64.b64decode(state['frame']['pixels_base64'])
    return all(actual[(y*128+col)*4+k]==expected[(y*128+col)*4+k]
               for y in range(top,row['bottom']) for col in range(x,x+width) for k in range(3))

def matches(state,expected):
    actual=base64.b64decode(state['frame']['pixels_base64'])[:len(expected)]
    # Cairo's clear surface and hardware framebuffer differ in alpha only.
    return all(actual[i]==expected[i] for i in range(len(expected)) if i%4!=3)

def selected_value(state,text):
    row=SCREEN['selected_row'];value=SCREEN['selected_value']
    expected=render([(None,row['baseline'],row['level'],text)])
    actual=base64.b64decode(state['frame']['pixels_base64'])
    return all(actual[(y*128+x)*4+k]==expected[(y*128+x)*4+k]
               for y in range(row['top'],row['bottom']) for x in range(value['left'],value['right']) for k in range(3))


# Live screen oracle (lib/ui_render.lua). The functions below reproduce the
# renderer's text placement from its layout rules with the shared rasterizer,
# never from Mosaic output: title row, scope, and each layout's full-value
# route for the selected field. Levels and baselines are the renderer's.
_extent_cache={}

def text_width(label,size=8,antialias=None):
    """Native screen.text_extents width (cairo ink width) at a font size.

    `antialias` measures with that cairo font antialias option; hinting makes a
    large size's width depend on it (STEREO at 21: 70 default, 72 unhinted)."""
    key=(label,size,antialias)
    if key not in _extent_cache:
        ft,ca=(C.CDLL('libfreetype.so.6'),C.CDLL('libcairo.so.2')) if _font_state is None else _font_state[:2]
        render([(0,0,0,'')])  # ensure the font face exists
        ft,ca,library,face,fontface=_font_state
        def bind(lib,name,args,result=None):
            f=getattr(lib,name);f.argtypes=args;f.restype=result;return f
        ptr=C.c_void_p;integer=C.c_int;double=C.c_double
        surface=bind(ca,'cairo_image_surface_create',[integer,integer,integer],ptr)(0,1,1)
        context=bind(ca,'cairo_create',[ptr],ptr)(surface)
        options=bind(ca,'cairo_font_options_create',[],ptr)()
        try:
            # Native large (>8) text is drawn and measured unantialiased, whose
            # hinted metrics are wider than the default (13px 'NO VOICING RANGE'
            # measures 130, not 122), so the renderer's size search differs.
            if antialias is None and size>8:
                antialias=1
            if antialias is not None:
                bind(ca,'cairo_font_options_set_antialias',[ptr,integer])(options,antialias)
                bind(ca,'cairo_set_font_options',[ptr,ptr])(context,options)
            bind(ca,'cairo_set_font_face',[ptr,ptr])(context,fontface)
            bind(ca,'cairo_set_font_size',[ptr,double])(context,size)
            extents=(double*6)()
            bind(ca,'cairo_text_extents',[ptr,C.c_char_p,C.POINTER(double)])(context,label.encode(),extents)
            _extent_cache[key]=extents[2]
        finally:
            bind(ca,'cairo_destroy',[ptr])(context)
            bind(ca,'cairo_surface_destroy',[ptr])(surface)
            bind(ca,'cairo_font_options_destroy',[ptr])(options)
    return _extent_cache[key]

def fit(label,width):
    """ui_render fit(): whole text, else trimmed with a trailing ~, else empty."""
    label=str(label)
    if text_width(label)<=width:return label
    if text_width('~')>width:return ''
    while label and text_width(label+'~')>width:label=label[:-1]
    return label+'~'

OVERVIEWS={'overview_masks','overview_params'}
# Layouts whose scope shares the title row, right-aligned at x118 level 9.
TITLE_ROW_SCOPE=OVERVIEWS|{'dashboard'}

def _title_row_scope_width(title,layout):
    """Overviews fit the scope to 45 px; a dashboard gives it the room its
    title leaves, at least 45 px (lib/ui_render.lua)."""
    if layout=='dashboard':return max(45,112-text_width(fit(title,78)))
    return 45

def live_header(title,scope,layout):
    """Expected title row (and scope line) for a live screen, rows 0..18."""
    if layout in TITLE_ROW_SCOPE:
        commands=[(1,7,15,fit(title,78)),((None,118),7,9,fit(scope,_title_row_scope_width(title,layout)))]
        rows=8  # row 8 carries an overview's selected cell outline
    else:
        commands=[(1,7,15,fit(title,126)),(1,17,7,fit(scope,126))]
        rows=19
    return render(commands),rows

def _region_matches(actual,expected,top,bottom,left=0,right=128):
    for y in range(top,bottom):
        for x in range(left,right):
            i=(y*128+x)*4
            if actual[i]!=expected[i] or actual[i+1]!=expected[i+1] or actual[i+2]!=expected[i+2]:
                return False
    return True

def live_header_matches(state,title,scope,layout):
    expected,rows=live_header(title,scope,layout)
    actual=base64.b64decode(state['frame']['pixels_base64'])
    # The top-right tile is a transient motion accent; the text must be exact.
    return _region_matches(actual,expected,0,rows,0,118)

DETAIL_ROWS=(27,36,45,54)

def _detail_row(label,value,y):
    value=str(value)
    commands=[(0,y,15,'>')]
    room=min(72,119-text_width(value)-4)
    if room>0:commands.append((7,y,15,fit(label,room)))
    if value!='':commands.append(((None,126),y,15,value))
    return render(commands)

def _focused_size(value,width):
    # ui_render full_value(): the largest size <= 23 whose native width fits.
    # Large values are drawn unhinted (render(..., antialias=1)), and the native
    # measurement agrees with that, not with the default-option width.
    size=23
    while size>8 and text_width(value,size,1)>width:size-=1
    return size if text_width(value,size,1)<=width else None

def selected_field_matches(state,layout,label=None,value=None,art=False):
    """True when the selected field shows `label` and/or `value` on its layout's full-value route."""
    actual=base64.b64decode(state['frame']['pixels_base64'])
    value=None if value is None else str(value)
    if layout=='detail':
        for y in DETAIL_ROWS:
            if label is not None and value is not None:
                expected=_detail_row(label,value,y)
                if _region_matches(actual,expected,y-7,y+2,0,127):return True
            elif label is not None:
                expected=render([(0,y,15,'>'),(7,y,15,label)])
                if _region_matches(actual,expected,y-7,y+2,0,7+int(text_width(label))+1):return True
            else:
                expected=render([((None,126),y,15,value),(0,y,15,'>')])
                w=int(text_width(value))+2
                if _region_matches(actual,expected,y-7,y+2,126-w,127) and _region_matches(actual,expected,y-7,y+2,0,6):return True
        return False
    if layout in OVERVIEWS:
        commands=[]
        if value is not None:commands.append(((None,127),53,15,value))
        if label is not None:
            room=126-(text_width(value) if value is not None else 0)-4
            commands.append((1,53,10,fit(label,room)))
        expected=render(commands)
        return _region_matches(actual,expected,46,55,0,128)
    # focused
    ok=True
    if label is not None:
        ok=_region_matches(actual,render([(1,28,10,fit(label,126))]),21,30,0,128)
    if ok and value is not None:
        width=70 if art else 126
        size=_focused_size(value,width)
        if size is None and art:size=_focused_size(value,126)
        if size is None:return False
        right=int(text_width(value,size,1))+2
        ok=_region_matches(actual,render([(1,48,15,value,size)],antialias=1),30,50,0,min(128,1+right))
    return ok

def overview_cell_matches(state,layout,index,short_label,value):
    """An overview cell shows its short label (selected or not) and compact value."""
    columns,width=(4,32) if layout=='overview_masks' else (5,25)
    x=((index-1)%columns)*width;y=9+((index-1)//columns)*18
    value=str(value)
    shown=value if ('~' not in value and text_width(value)<=width-5) else '...'
    actual=base64.b64decode(state['frame']['pixels_base64'])
    for level in (15,9):
        expected=render([(x+2,y+7,level,fit(short_label,width-5)),(x+2,y+15,13,shown)])
        if _region_matches(actual,expected,y+1,y+16,x+1,x+width-3):return True
    return False

def overview_cell_marker(state,layout,index):
    """The one-letter state marker in an overview cell's top-right corner:
    'S' (a slide), 'L' (a lock on a held step) or None. The renderer clears a
    4x7 box at (x+w-6, y+1) and draws the letter at (x+w-6, y+7), level 15."""
    columns,width=(4,32) if layout=='overview_masks' else (5,25)
    x=((index-1)%columns)*width;y=9+((index-1)//columns)*18
    actual=base64.b64decode(state['frame']['pixels_base64'])
    for letter in ('S','L'):
        if _region_matches(actual,render([(x+width-6,y+7,15,letter)]),y+1,y+8,x+width-6,x+width-2):return letter
    return None

# ---- Dashboard layout (lib/ui_render.lua L=='dashboard') ----
# Information-only screens list every field at once with no cursor: title at
# (1,7) level 15, scope right-aligned at x118 level 9 on the title row, then up
# to six rows at baselines 16..56: the label at x1 level 7, fitted to
# 126-width(value)-4, and the whole value right-aligned at x127 level 15.
DASHBOARD_ROWS=(16,24,32,40,48,56)

def _dashboard_row_commands(label,value,y):
    value=str(value)
    commands=[]
    room=126-text_width(value)-4
    if room>0:commands.append((1,y,7,fit(label,room)))
    if value!='':commands.append(((None,127),y,15,value))
    return commands

def dashboard_row_matches(state,index,label,value):
    """Dashboard row `index` (1-based) shows exactly `label` and `value`.

    The 8 px font draws from baseline-5 to baseline+1; the row's band
    baseline-6..baseline+1 holds nothing else (rows are 8 px apart)."""
    y=DASHBOARD_ROWS[index-1]
    actual=base64.b64decode(state['frame']['pixels_base64'])
    return _region_matches(actual,render(_dashboard_row_commands(label,value,y)),y-6,y+2,0,128)

def dashboard_matches(state,title,scope,rows):
    """The whole dashboard: title row, then exactly `rows` ((label, value) in
    order) and nothing else above the footer (no cursor, no other row). The
    title row's top-right mark tiles (x118..) are motion accents."""
    commands=[(1,7,15,fit(title,78)),((None,118),7,9,fit(scope,_title_row_scope_width(title,'dashboard')))]
    for index,(label,value) in enumerate(rows,start=1):
        commands+=_dashboard_row_commands(label,value,DASHBOARD_ROWS[index-1])
    expected=render(commands)
    actual=base64.b64decode(state['frame']['pixels_base64'])
    return _region_matches(actual,expected,0,8,0,118) and _region_matches(actual,expected,8,58,0,128)

# ---- Live footer (group C: ranges, saves, song, tooltips) ----
# lib/ui_render.lua draws the footer line at (1,63): the current tooltip at
# level 9 while it lasts, else the screen's control hints (level 9) or, on
# focused screens without hints, its neighbour fields ('< prev' left at
# level 7, 'next >' right-aligned at x127 level 10).
FOOTER_ROWS=(56,64)

def footer(text):
    """Expected frame for footer `text` (a tooltip/hint string, or a
    (left, right) neighbour pair)."""
    if isinstance(text,tuple):
        commands=[]
        if text[0]:commands.append((1,63,7,text[0]))
        if text[1]:commands.append(((None,127),63,10,text[1]))
        return render(commands)
    return render([(1,63,9,fit(text,126))])

def footer_matches(state,text):
    """The whole footer line shows exactly `text` and nothing else."""
    actual=base64.b64decode(state['frame']['pixels_base64'])
    return _region_matches(actual,footer(text),*FOOTER_ROWS)
