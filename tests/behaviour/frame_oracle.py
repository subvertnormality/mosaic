"""Independent literal Mosaic header oracle, never sampled from app output.

Pinned page.lua places the selected page title at (0,9), 8px norns font,
level 10. ui.lua places 'm' at (120,9). Body controls begin below this band.
Use the shared font/rasterizer as a rendering primitive, not Mosaic draw code.
"""
import base64,ctypes as C
from driver import EMULATOR_ROOT as ROOT
import json
def read_json(path):return json.loads(path.read_text())

def header(text,selected=None,tabs=6):
    ft=C.CDLL('libfreetype.so.6'); ca=C.CDLL('libcairo.so.2')
    def bind(lib,name,args,result=None):
        f=getattr(lib,name);f.argtypes=args;f.restype=result;return f
    ptr=C.c_void_p; integer=C.c_int; double=C.c_double
    library=ptr();face=ptr()
    assert bind(ft,'FT_Init_FreeType',[C.POINTER(ptr)],integer)(C.byref(library))==0
    font=read_json(ROOT/'.runtime/current.json')['source']+'/resources/norns.ttf'
    assert bind(ft,'FT_New_Face',[ptr,C.c_char_p,C.c_long,C.POINTER(ptr)],integer)(library,font.encode(),0,C.byref(face))==0
    surface=bind(ca,'cairo_image_surface_create',[integer,integer,integer],ptr)(0,128,64)
    context=bind(ca,'cairo_create',[ptr],ptr)(surface)
    fontface=bind(ca,'cairo_ft_font_face_create_for_ft_face',[ptr,integer],ptr)(face,0)
    options=bind(ca,'cairo_font_options_create',[],ptr)()
    try:
        bind(ca,'cairo_font_options_set_antialias',[ptr,integer])(options,2)
        bind(ca,'cairo_set_font_options',[ptr,ptr])(context,options)
        bind(ca,'cairo_set_font_face',[ptr,ptr])(context,fontface)
        bind(ca,'cairo_set_font_size',[ptr,double])(context,8)
        # Six channel tabs (pages.lua); Masks is tab 1, Device Config tab 5.
        if selected is None:selected={'Ch. 1 Note Masks':1,'Ch. 1 Memory':3,'Ch. 1 Device Config':5}[text]
        for tab in range(1,tabs+1):
            level=(10 if tab==selected else 1)/15
            bind(ca,'cairo_set_source_rgb',[ptr,double,double,double])(context,level,level,level)
            bind(ca,'cairo_move_to',[ptr,double,double])(context,(tab-1)*10,1)
            bind(ca,'cairo_show_text',[ptr,C.c_char_p])(context,b'_')
        bind(ca,'cairo_set_source_rgb',[ptr,double,double,double])(context,10/15,10/15,10/15)
        for x,label in ((0,text),(120,'m')):
            bind(ca,'cairo_move_to',[ptr,double,double])(context,x,9)
            bind(ca,'cairo_show_text',[ptr,C.c_char_p])(context,label.encode())
        bind(ca,'cairo_surface_flush',[ptr])(surface)
        data=bind(ca,'cairo_image_surface_get_data',[ptr],ptr)(surface)
        return C.string_at(data,128*10*4)
    finally:
        bind(ca,'cairo_destroy',[ptr])(context)
        bind(ca,'cairo_surface_destroy',[ptr])(surface)
        bind(ca,'cairo_font_face_destroy',[ptr])(fontface)
        bind(ca,'cairo_font_options_destroy',[ptr])(options)
        bind(ft,'FT_Done_Face',[ptr],integer)(face)
        bind(ft,'FT_Done_FreeType',[ptr],integer)(library)

def matches(state,expected):
    actual=base64.b64decode(state['frame']['pixels_base64'])[:len(expected)]
    # Cairo's clear surface and hardware framebuffer differ in alpha only.
    return all(actual[i]==expected[i] for i in range(len(expected)) if i%4!=3)
