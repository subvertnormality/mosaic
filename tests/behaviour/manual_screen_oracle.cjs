"use strict";
const PIXELS=128*64;
function expandRle(runs,maximum,label){
 if(!Array.isArray(runs))throw Error(label+" must be an RLE list");
 const pixels=[];
 for(const run of runs){
  if(!Array.isArray(run)||run.length!==2)throw Error(label+" run must be [value,count]");
  const [value,count]=run;
  if(!Number.isInteger(value)||value<0||value>maximum)throw Error(label+" value out of range");
  if(!Number.isInteger(count)||count<1||pixels.length+count>PIXELS)throw Error(label+" count out of range");
  for(let i=0;i<count;i++)pixels.push(value);
 }
 if(pixels.length!==PIXELS)throw Error(label+" must decode to exactly 8192 pixels");
 return pixels;
}
function decodeScreenPixels(output){
 if(!output||typeof output!=="object"||Array.isArray(output))throw Error("Missing captured framebuffer");
 const owns=(key)=>Object.prototype.hasOwnProperty.call(output,key);
 const legacy=owns("screen_rle"),gray=owns("screen_gray8_rle"),tagged=owns("screen_format");
 if(legacy&&(gray||tagged))throw Error("Ambiguous captured framebuffer");
 if(gray){
  if(output.screen_format!=="gray8-rle")throw Error("Unsupported captured framebuffer format");
  return expandRle(output.screen_gray8_rle,255,"Gray8 framebuffer");
 }
 if(tagged||!legacy)throw Error("Unsupported captured framebuffer format");
 return expandRle(output.screen_rle,15,"Legacy framebuffer").map(value=>value*17);
}
module.exports={decodeScreenPixels};
