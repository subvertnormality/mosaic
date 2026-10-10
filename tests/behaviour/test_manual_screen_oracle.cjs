"use strict";
const assert=require("node:assert/strict");
const {decodeScreenPixels}=require("./manual_screen_oracle.cjs");
let passed=0;
function check(fn){fn();passed++;}
check(()=>assert.deepEqual(decodeScreenPixels({screen_rle:[[15,8192]]}),Array(8192).fill(255)));
check(()=>assert.deepEqual(decodeScreenPixels({screen_format:"gray8-rle",screen_gray8_rle:[[0,1],[34,1],[68,1],[128,1],[255,8188]]}),[0,34,68,128,...Array(8188).fill(255)]));
check(()=>assert.deepEqual(decodeScreenPixels({screen_format:"gray8-rle",screen_gray8_rle:[[128,4096],[128,4096]]}),Array(8192).fill(128)));
for(const payload of [
 {screen_rle:[[16,8192]]},
 {screen_rle:[[8,0]]},
 {screen_rle:[[8,8191]]},
 {screen_rle:[[8,8193]]},
 {screen_format:"gray8-rle",screen_gray8_rle:[[256,8192]]},
 {screen_format:"gray8-rle",screen_gray8_rle:[[128,8191]]},
 {screen_format:"gray8-rle",screen_gray8_rle:[[128,4096],[128,4097]]},
 {screen_format:"rgba8",screen_gray8_rle:[[128,8192]]},
 {screen_format:"gray8-rle",screen_gray8_rle:[[128,8192]],screen_rle:[[8,8192]]},
 {screen_format:"gray8-rle",screen_rle:[[8,8192]]},
 {screen_gray8_rle:[[128,8192]]},
 {screen_rle:[[8,8192],[8,1]]}
])check(()=>assert.throws(()=>decodeScreenPixels(payload)));
console.log(JSON.stringify({passed:true,checks:passed,pixels:8192,legacy:"0..15 scaled exactly by 17",gray8:"0..255 exact bytes"}));
