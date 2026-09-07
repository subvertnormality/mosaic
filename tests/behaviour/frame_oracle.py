"""Independent literal Mosaic header oracle, never sampled from app output.

Pinned page.lua places the selected page title at (0,9), 8px norns font,
level 10. ui.lua places 'm' at (120,9). Body controls begin below this band.
Use the shared font/rasterizer as a rendering primitive, not Mosaic draw code.
"""
import base64,ctypes as C
from driver import EMULATOR_ROOT as ROOT
import json
def read_json(path):return json.loads(path.read_text())

_font_state=None

def render(commands):
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
        bind(ca,'cairo_font_options_set_antialias',[ptr,integer])(options,2)
        bind(ca,'cairo_set_font_options',[ptr,ptr])(context,options)
        bind(ca,'cairo_set_font_face',[ptr,ptr])(context,fontface)
        bind(ca,'cairo_set_font_size',[ptr,double])(context,8)
        for x,y,level,label in commands:
            if x is None:
                extents=(double*6)()
                bind(ca,'cairo_text_extents',[ptr,C.c_char_p,C.POINTER(double)])(context,label.encode(),extents)
                x=127-extents[2]  # Native text_right subtracts ink width.
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

def header(text,selected=None,tabs=6):
    if selected is None:selected={'Ch. 1 Note Masks':1,'Ch. 1 Memory':3,'Ch. 1 Device Config':5}[text]
    commands=[((tab-1)*10,1,10 if tab==selected else 1,'_') for tab in range(1,tabs+1)]
    commands += [(0,9,10,text),(120,9,10,'m')]
    return render(commands)[:128*10*4]

def selected_line(state,text,x=0,width=70):
    # Native menu selected rows use baseline30, level15. Ignore the separate
    # right-hand value field, not the text glyphs or background around them.
    expected=render([(x,30,15,text)])
    actual=base64.b64decode(state['frame']['pixels_base64'])
    return all(actual[(y*128+col)*4+k]==expected[(y*128+col)*4+k]
               for y in range(22,32) for col in range(x,x+width) for k in range(3))

def matches(state,expected):
    actual=base64.b64decode(state['frame']['pixels_base64'])[:len(expected)]
    # Cairo's clear surface and hardware framebuffer differ in alpha only.
    return all(actual[i]==expected[i] for i in range(len(expected)) if i%4!=3)

def selected_value(state,text):
    expected=render([(None,30,15,text)])
    actual=base64.b64decode(state['frame']['pixels_base64'])
    return all(actual[(y*128+x)*4+k]==expected[(y*128+x)*4+k]
               for y in range(22,32) for x in range(108,128) for k in range(3))
