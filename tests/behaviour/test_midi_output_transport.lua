-- Actual Mosaic adapter with controlled native scheduler/output boundaries.
local function setup()
  local callbacks,threads,events={}, {}, {}
  local next_id=0
  clock={midi={}}
  function clock.midi.subscribe_output(c)callbacks[1]=c;return 1 end
  function clock.midi.cancel_output(id)callbacks[id]=nil end
  function clock.run(f)
    next_id=next_id+1;local id=next_id;threads[id]=coroutine.create(f)
    assert(coroutine.resume(threads[id]));return id
  end
  function clock.sync()return coroutine.yield()end
  function clock.cancel(id)threads[id]=nil end
  local lattice={ppqn=96,auto=true,enabled=false,count=0}
  function lattice:start()assert(not self.auto);self.enabled=true end
  function lattice:pulse()assert(self.enabled);events[#events+1]='P'..self.count;self.count=self.count+1 end
  local owner=assert(loadfile('lib/clock/midi_output_transport.lua'))()
  local stop=owner.start(lattice,function()events[#events+1]='FA'end)
  local function boundary(deadline,epoch)
    if callbacks[1] then callbacks[1].before(deadline,epoch,{1},deadline) end
    events[#events+1]='F8'
    if callbacks[1] then callbacks[1].after(deadline,epoch,{1},deadline) end
  end
  local function resume(deadline,epoch,id)
    local co=threads[id or next_id]
    if co then local ok,err=coroutine.resume(co,deadline,deadline,epoch);assert(ok,err) end
  end
  return {events=events,boundary=boundary,resume=resume,stop=stop,lattice=lattice,threads=threads}
end
local function expect(t,s)assert(table.concat(t.events,',')==s,table.concat(t.events,','))end
do
  local t=setup();t.stop();t.boundary(1,0);expect(t,'F8')
end
do
  local t=setup();t.boundary(1,0)
  t.resume(1+1/96,0);t.resume(1+2/96,0);t.resume(1+3/96,0)
  t.resume(1+4/96,0);expect(t,'FA,F8,P0,P1,P2,P3')
  t.boundary(1+4/96,0);expect(t,'FA,F8,P0,P1,P2,P3,F8,P4');t.stop()
end
do
  local t=setup();t.boundary(1,0)
  -- A late intermediate callback cannot emit the next boundary pulse early.
  t.resume(1+12/96,0);expect(t,'FA,F8,P0,P1,P2,P3')
  t.boundary(1+4/96,0);t.boundary(1+8/96,0)
  expect(t,'FA,F8,P0,P1,P2,P3,F8,P4,F8,P5,P6,P7,P8');t.stop()
end
do
  local t=setup();t.boundary(1,0);t.stop();t.resume(10,0);t.boundary(10,0)
  expect(t,'FA,F8,P0,F8');assert(next(t.threads)==nil)
end
do
  local t=setup();t.boundary(1,0);t.resume(1+1/96,0)
  t.boundary(0,1);assert(t.lattice.count==5,'Epoch reset replayed historical pulses')
  t.resume(100,0);assert(t.lattice.count==5,'Stale epoch emitted pulses')
  t.resume(1/96,1);assert(t.lattice.count==6)
  t.boundary(4/96,1);assert(t.lattice.count==9);t.stop()
end
do
  local t=setup();t.boundary(1,0);t.resume(1+3/96,0);t.resume(1+3/96,0)
  expect(t,'FA,F8,P0,P1,P2,P3');t.stop();t.stop()
end
print('PASS:6 adapter scenarios; pending cancellation, pulse ownership, delayed delivery, active cancellation, epoch change, duplicate wakeups')
