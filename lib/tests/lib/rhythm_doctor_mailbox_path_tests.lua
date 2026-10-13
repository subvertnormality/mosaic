-- README.md "Rhythm Doctor": local capture analysis uses the stock worker.
-- Characterisation outside manual: file IPC accepts owned native-session paths
-- within Linux PATH_MAX, including each complete temporary message filename.
local Mailbox = include("mosaic/lib/rhythm_doctor/file_mailbox")
local function root_of_length(length)
  local parts, remaining = {}, length-1
  while remaining>64 do parts[#parts+1]=string.rep("a",64);remaining=remaining-65 end
  parts[#parts+1]=string.rep("a",remaining)
  return "/"..table.concat(parts,"/")
end
local function open(root,outbound)
  return Mailbox.open(root,outbound or "c2w","w2c",{limit=64,claim=false})
end
function test_rhythm_doctor_mailbox_path_accepts_public_native_session_root()
  local root="/tmp/norns_emu_"..string.rep("a",32).."/dust/data/mosaic/rhythm-doctor-analysis-runtime/ipc"
  luaunit.assert_equals(#root,99)
  luaunit.assert_not_nil(open(root),"Public native worker root must connect")
end
function test_rhythm_doctor_mailbox_path_accounts_for_complete_message_suffix()
  local suffix="/c2w/000000001.msg.part"
  local root=root_of_length(4095-#suffix)
  luaunit.assert_not_nil(open(root),"Full temporary filename at PATH_MAX-1 must fit")
  local mailbox,problem=open(root.."a")
  luaunit.assert_nil(mailbox)
  luaunit.assert_equals(problem,"INVALID_MAILBOX_ROOT")
end
function test_rhythm_doctor_mailbox_path_accounts_for_direction_component()
  local direction=string.rep("a",200)
  local suffix="/"..direction.."/000000001.msg.part"
  local root=root_of_length(4095-#suffix)
  luaunit.assert_not_nil(open(root,direction))
  luaunit.assert_nil(open(root.."a",direction))
end
function test_rhythm_doctor_mailbox_path_preserves_invalid_root_and_layout_refusals()
  for _,root in ipairs({"relative","/tmp/rd/","/tmp/rd\n","/tmp/rd\t","/tmp/rd\0"})do
    luaunit.assert_nil(open(root))
  end
  for _,direction in ipairs({"../c2w","c2w/sub","c2w-1","C2W"})do
    luaunit.assert_nil(open("/tmp/rd",direction))
  end
end
