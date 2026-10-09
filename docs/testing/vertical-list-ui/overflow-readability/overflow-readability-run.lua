local root='/home/andy/mosaic-manual-1.4.0/'
function include(path)return dofile(root..path:gsub('^mosaic/','')..'.lua')end
luaunit=dofile('/tmp/mosaic-vertical-lua-1t31i1nb/mosaic/lib/tests/test_artefacts/norns_test_artefact/lua/lib/test/luaunit.lua')
include('mosaic/lib/tests/lib/ui_vertical_list_tests')
os.exit(luaunit.LuaUnit.run())
