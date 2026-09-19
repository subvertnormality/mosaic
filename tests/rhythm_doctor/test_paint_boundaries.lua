-- Characterisation outside README: PLAN.md painting policy and pinned-preview contract.
package.path="./lib/?.lua;"..package.path
local Paint=require("rhythm_doctor.paint")
local n=0
local function ok(v,m) n=n+1;if not v then error(m,2) end end
local function preview(policy,shift,cells)
 return {project_id="p",generation=1,analysis_revision=2,lane="BD",window_start=0,window_revision=3,target={project_id="p",song_slot=1,pattern_id=1,revision=4},policy=policy,shift=shift,cells=cells}
end
local function source()
 local s={revision=4,trigs={},velocities={},lengths={},notes={"keep"}}
 for i=1,64 do s.trigs[i],s.velocities[i],s.lengths[i]=false,i,i%4 end
 return s
end
do
 local c={[1]={velocity=70},[64]={velocity=99}}; local s=source(); local a=assert(Paint.apply(s,assert(Paint.preview(preview("add",64,c)))))
 ok(a.trigs[1] and a.trigs[64] and a.velocities[64]==99 and a.notes[1]=="keep","add/shift64 preserves paired fields")
 local empty=assert(Paint.apply(s,assert(Paint.preview(preview("toggle",-64,{})))));ok(not empty.trigs[1] and empty.velocities[1]==s.velocities[1],"empty toggle no-op")
 local r=assert(Paint.apply(s,assert(Paint.preview(preview("replace",0,{[1]={velocity=88}})))))
 ok(r.trigs[1] and not r.trigs[2] and r.velocities[2]==s.velocities[2] and r.notes[1]=="keep","replace keeps absent velocity and unrelated notes")
end
-- Literal oracle: each policy's effects are stated here, not derived from Paint.
do
 local shifts={-65,-64,-1,0,63,64,65}
 for _,policy in ipairs({"toggle","add","replace"}) do for _,shift in ipairs(shifts) do for _,numeric in ipairs({false,true}) do
  local s=source(); if numeric then s.trig_values={};for i=1,64 do s.trig_values[i]=i%2 end end
  for i=1,64 do if not numeric then s.trigs[i]=i%2==1 end end
  local cells={[1]={velocity=41},[64]={velocity=99}}; local p=assert(Paint.preview(preview(policy,shift,cells)))
  local adapter=numeric and {trig_field="trig_values",velocity_field="velocities",length_field="lengths",on=1,off=0} or nil
  local a=assert(Paint.apply(s,p,adapter)); local pos1=((0+shift)%64)+1;local pos64=((63+shift)%64)+1
  for step=1,64 do
   local hit=step==pos1 or step==pos64; local before=numeric and s.trig_values[step]==1 or s.trigs[step]
   local expected=before
   if policy=="replace" then expected=hit elseif hit and policy=="add" then expected=true elseif hit then expected=not before end
   local actual=numeric and a.trig_values[step]==1 or a.trigs[step]
   ok(actual==expected,"literal policy cell "..policy.."/"..shift.."/"..step)
   local expected_velocity=s.velocities[step]; local expected_length=s.lengths[step]
   if policy=="replace" then if hit then expected_velocity=(step==pos1 and 41 or 99);expected_length=1 else expected_length=0 end
   elseif hit and (policy=="add" or not before) then expected_velocity=(step==pos1 and 41 or 99);if not before then expected_length=1 end
   elseif hit then expected_length=0 end
   ok(a.velocities[step]==expected_velocity and a.lengths[step]==expected_length,"literal velocity/length "..policy.."/"..shift.."/"..step)
  end
  ok(a.notes[1]=="keep" and s.notes[1]=="keep","notes/source preserved")
 end end end
end
do
 local closed=preview("add",0,{}); closed.lane="CHH"; ok(Paint.preview(closed),"closed hat lane accepted")
 local open=preview("add",0,{}); open.lane="OHH"; ok(Paint.preview(open),"open hat lane accepted")
 local legacy=preview("add",0,{}); legacy.lane="HH"; ok(not Paint.preview(legacy),"combined legacy hat lane rejected")
 local tom=preview("add",0,{}); tom.lane="TOM"; ok(not Paint.preview(tom),"removed tom lane rejected")
 local bad=preview("add",0/0,{}); ok(not Paint.preview(bad),"nan shift rejected")
 bad=preview("add",.5,{}); ok(not Paint.preview(bad),"fractional shift rejected")
 bad=preview("add",0,{[65]={velocity=1}}); ok(not Paint.preview(bad),"out-of-window cell rejected")
 bad=preview("add",0,{[1]={velocity=1.5}}); ok(not Paint.preview(bad),"fractional velocity rejected")
 bad=preview("add",0,{[1]={velocity=128}}); ok(not Paint.preview(bad),"velocity128 rejected")
 bad=preview("add",0,{}); bad.window_start=-1; ok(not Paint.preview(bad),"negative window rejected")
 bad=preview("add",0,{}); bad.window_start=0/0; ok(not Paint.preview(bad),"nan window rejected")
 bad=preview("add",0,{}); bad.window_start=math.huge; ok(not Paint.preview(bad),"infinite window rejected")
 bad=preview("add",0,{}); bad.lane="NOPE"; ok(not Paint.preview(bad),"unknown lane rejected")
 bad=preview("add",0,{}); bad.target=nil; ok(not Paint.preview(bad),"target pins required")
 bad=preview("add",0,{}); bad.target.project_id="other"; ok(not Paint.preview(bad),"target project pin required")
 bad=preview("add",0,{}); bad.generation=1.5; ok(not Paint.preview(bad),"fractional generation rejected")
end
print("paint boundaries: "..n.." assertions passed")
