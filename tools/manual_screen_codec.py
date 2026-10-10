"""Exact screen payload codecs for captured 128x64 native frames."""
PIXELS=8192
RGBA_BYTES=32768
class ScreenEncodingError(ValueError): pass
def rle(values):
 result=[]
 for value in values:
  if result and result[-1][0]==value: result[-1][1]+=1
  else: result.append([value,1])
 return result
def _expand(rows,maximum,label):
 if not isinstance(rows,list): raise ScreenEncodingError(label+" must be an RLE list")
 values=[];previous=None
 for row in rows:
  if not isinstance(row,list) or len(row)!=2: raise ScreenEncodingError(label+" rows must be [value,count]")
  value,count=row
  if type(value)is not int or not 0<=value<=maximum: raise ScreenEncodingError(label+" value is out of range")
  if type(count)is not int or not 1<=count<=PIXELS: raise ScreenEncodingError(label+" count is out of range")
  if len(values)+count>PIXELS: raise ScreenEncodingError(label+" exceeds 128x64")
  values.extend([value]*count);previous=value
 if len(values)!=PIXELS: raise ScreenEncodingError(label+" must decode to exactly 8192 pixels")
 return values
def encode_native_frame(rgba):
 """Encode channel-zero luminance; caller retains and hash-binds all native bytes."""
 try: raw=bytes(rgba)
 except (TypeError,ValueError) as exc: raise ScreenEncodingError("native framebuffer must be bytes") from exc
 if len(raw)!=RGBA_BYTES: raise ScreenEncodingError("native framebuffer must contain 128x64 RGBA8 bytes")
 channel0=list(raw[0::4])
 if all(value%17==0 for value in channel0): return {"screen_rle":rle([value//17 for value in channel0])}
 if any(raw[i]!=raw[i+1] or raw[i]!=raw[i+2] for i in range(0,RGBA_BYTES,4)):
  raise ScreenEncodingError("non-16-level screen must be exact grayscale")
 return {"screen_format":"gray8-rle","screen_gray8_rle":rle(channel0)}
def decode_screen_payload(output):
 if not isinstance(output,dict): raise ScreenEncodingError("screen output must be an object")
 legacy="screen_rle" in output;gray8="screen_gray8_rle" in output;tagged="screen_format" in output
 if legacy and (gray8 or tagged): raise ScreenEncodingError("ambiguous screen encodings")
 if gray8:
  if output.get("screen_format")!="gray8-rle": raise ScreenEncodingError("unknown gray8 screen format")
  return "gray8",_expand(output["screen_gray8_rle"],255,"gray8 RLE")
 if tagged: raise ScreenEncodingError("screen format tag has no payload")
 if not legacy: raise ScreenEncodingError("missing screen payload")
 return "legacy16",_expand(output["screen_rle"],15,"screen RLE")
