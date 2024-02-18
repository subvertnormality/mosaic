-- Function to check if the norns directory exists with extracted files
function directory_and_files_exist(path, sample_file_name)
  local check_command = string.format('find "%s" -type f -name "%s"', path, sample_file_name)
  local handle = io.popen(check_command)
  local result = handle:read("*a")
  handle:close()
  return result ~= ""
end

local expected_file_name = "norns.lua" 

if directory_and_files_exist("./test_artefacts/norns/lua/core", expected_file_name) then
  print("The './test_artefacts/norns/lua/core/norns.lua' file already exists. Skipping download.")
else
  print("Fetching latest release of norns...")

  -- Ensure the test_artefacts directory exists
  os.execute("mkdir -p ./test_artefacts")

  -- Fetch the latest release data from GitHub and save it to a file within test_artefacts
  os.execute("curl -s https://api.github.com/repos/monome/norns/releases/latest > ./test_artefacts/latest_release.json")

  -- Read the file and extract the download URL
  local file = io.open("./test_artefacts/latest_release.json", "r")
  local content = file:read("*all")
  file:close()

  -- Attempt to extract the zipball download URL using Lua pattern matching
  local download_url = content:match('"zipball_url":%s*"([^"]+)"')

  if download_url then
      -- Download the latest release zip file into test_artefacts
      os.execute(string.format("curl -L '%s' -o ./test_artefacts/norns_latest.zip", download_url))

      -- Extract the zip file into a temporary directory within test_artefacts
      os.execute("unzip ./test_artefacts/norns_latest.zip -d ./test_artefacts/temp_norns")

      -- Determine the name of the top-level directory
      local top_level_dir_command = "ls ./test_artefacts/temp_norns | head -n 1"
      local handle = io.popen(top_level_dir_command)
      local top_level_dir = handle:read("*a"):gsub("\n", "")
      handle:close()

      -- Move the contents from the top-level directory to the desired location and clean up
      if top_level_dir ~= "" then
          os.execute(string.format("mv ./test_artefacts/temp_norns/%s/* ./test_artefacts/norns", top_level_dir))
          os.execute("rm -rf ./test_artefacts/temp_norns")
          print("norns has been successfully downloaded and extracted to './test_artefacts/norns'.")
      else
          print("Failed to identify the top-level directory within the zip archive.")
      end
  else
      print("Failed to extract the download URL from the JSON response.")
  end
end

local my_path = "./test_artefacts/norns/lua/lib/?.lua;" 
package.path = my_path .. package.path

util = require('util')
luaunit = require('test.luaunit')

-- global include function
function include(file)
  local dirs = {'../../../', './test_artefacts/norns/lua/extn/'}
  for _, dir in ipairs(dirs) do
    local p = dir..file..'.lua'
    if util.file_exists(p) then
      print("including "..p)
      return dofile(p)
    end
  end

  -- didn't find anything
  print("### MISSING INCLUDE: "..file)
  error("MISSING INCLUDE: "..file,2)
end

function require_all_files_in_folder(folder)
  local command = string.format('ls %s/*.lua', folder)
  local handle = io.popen(command)
  local result = handle:read("*a")
  handle:close()

  -- Iterate through each line in the result
  for filename in string.gmatch(result, '[^\r\n]+') do
      -- Remove the directory path and extension from the filename to get the module name
      local module = filename:match("^.+/(.+).lua$")
      if module then
          local module_path = folder .. '.' .. module
          require(module_path:gsub('/', '.'))
      end
  end
end

require_all_files_in_folder('./lib')

os.exit( luaunit.LuaUnit.run() )