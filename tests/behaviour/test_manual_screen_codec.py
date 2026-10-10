import base64, hashlib, json, sys, unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/"tools"))
from manual_screen_codec import encode_native_frame,decode_screen_payload,ScreenEncodingError
import manual_verify

def raw_frame(values,alpha=None,rgb_equal=True):
 pixels=bytearray()
 for i,value in enumerate(values):
  pixels.extend((value,value if rgb_equal else (value+1)%256,value,255 if alpha is None else alpha[i]))
 return bytes(pixels)

def bound_output(payload,raw,case="M-MATRIX-001"):
 grid=[0]*128
 binding=dict(sha256=hashlib.sha256(raw).hexdigest(),grid_sha256=hashlib.sha256(bytes(grid)).hexdigest(),
              passed=True,semantic_assertions=1,name="manual/"+case+"/frame")
 output=dict(payload,grid=grid,binding=binding);binding["kind"]="documentation-frame";results=[binding]
 observations=[dict(state=dict(frame=dict(sha256=binding["sha256"],pixels_base64=base64.b64encode(raw).decode()),grid=grid))]
 return output,case,results,observations

class ScreenCodec(unittest.TestCase):
 def test_legacy_encoding_stays_exact_and_alpha_agnostic(self):
  values=[(i%16)*17 for i in range(8192)]
  raw=raw_frame(values,[i%256 for i in range(8192)],False);payload=encode_native_frame(raw);expected=[]
  for value in values:
   level=value//17
   if expected and expected[-1][0]==level:expected[-1][1]+=1
   else:expected.append([level,1])
  self.assertTrue(payload=={"screen_rle":expected})
  self.assertTrue(decode_screen_payload(payload)==("legacy16",[v//17 for v in values]))

 def test_gray8_preserves_exact_levels_and_verifies_hash_including_alpha(self):
  values=[0,34,68,128,255]*(8192//5)+[0,34]
  alphas=[0,128,255,0,128]*(8192//5)+[255,0]
  raw=raw_frame(values,alphas);payload=encode_native_frame(raw)
  self.assertTrue(payload["screen_format"]=="gray8-rle" and "screen_rle" not in payload)
  self.assertTrue(decode_screen_payload(payload)==("gray8",values))
  manual_verify.check_frame(*bound_output(payload,raw))

 def test_native_alpha_tamper_fails_even_when_display_luminance_is_identical(self):
  raw=raw_frame([34]*8192,[0]*8192);args=list(bound_output(encode_native_frame(raw),raw))
  observations=args[3];changed=bytearray(raw);changed[3]=1
  observations[0]["state"]["frame"]["pixels_base64"]=base64.b64encode(changed).decode()
  with self.assertRaisesRegex(ValueError,"Framebuffer brightness/hash"):manual_verify.check_frame(*args)

 def test_non_gray_native_rgb_is_rejected_from_gray8_branch(self):
  with self.assertRaisesRegex(ScreenEncodingError,"exact grayscale"):
   encode_native_frame(raw_frame([128]*8192,[255]*8192,False))

 def test_malformed_or_ambiguous_gray8_payload_is_rejected(self):
  for payload in ({"screen_format":"gray8-rle","screen_gray8_rle":[[128,8191]]},
                  {"screen_format":"gray8-rle","screen_gray8_rle":[[256,8192]]},
                  {"screen_format":"gray8-rle","screen_gray8_rle":[[128,4096],[128,4097]]},
                  {"screen_format":"gray8-rle","screen_gray8_rle":[[128,8192]],"screen_rle":[[8,8192]]},
                  {"screen_format":"other","screen_gray8_rle":[[128,8192]]}):
   with self.subTest(payload=payload),self.assertRaises(ScreenEncodingError):decode_screen_payload(payload)

 def test_gray8_accepts_semantically_equivalent_split_runs(self):
  self.assertTrue(decode_screen_payload({"screen_format":"gray8-rle","screen_gray8_rle":[[128,4096],[128,4096]]})==("gray8",[128]*8192))

 def test_schema_declares_exclusive_legacy_and_gray8_payloads(self):
  import jsonschema
  schema=json.loads((ROOT/"manual/screen-output.schema.json").read_text())
  jsonschema.Draft7Validator(schema).validate({"screen_rle":[[8,8192]]})
  jsonschema.Draft7Validator(schema).validate({"screen_format":"gray8-rle","screen_gray8_rle":[[128,8192]]})
  with self.assertRaises(jsonschema.ValidationError):
   jsonschema.Draft7Validator(schema).validate({"screen_format":"gray8-rle","screen_gray8_rle":[[128,8192]],"screen_rle":[[8,8192]]})

 def test_plan_schema_declares_only_the_explicit_gray8_opt_in(self):
  import jsonschema
  schema=json.loads((ROOT/"manual/case-scenes.schema.json").read_text())
  instance={"schema_version":1,"scenes":[{"id":"matrix-depth","feature_id":"matrix","title":"Depth","behaviour_case":"M-MATRIX-001","citation":"manual:masks","screen_format":"gray8-rle","steps":[{"id":"frame","title":"Frame","caption":"Frame","assertion":{"kind":"screen"}}]}]}
  jsonschema.Draft7Validator(schema).validate(instance)
  instance["scenes"][0]["screen_format"]="rgba8"
  with self.assertRaises(jsonschema.ValidationError):jsonschema.Draft7Validator(schema).validate(instance)


 def test_legacy_payload_cannot_round_native_gray8_pixels(self):
  raw=raw_frame([128]*8192)
  with self.assertRaisesRegex(ValueError,"Framebuffer brightness/hash"):
   manual_verify.check_frame(*bound_output({"screen_rle":[[7,8192]]},raw))

if __name__=="__main__":unittest.main()
