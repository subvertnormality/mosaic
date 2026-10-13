package.path='/tmp/mosaic-manual-lua-hs91kkii/mosaic/lib/tests/test_artefacts/norns_test_artefact/lua/lib/?.lua;'..package.path
luaunit=require('test.luaunit')
function include(file)return dofile('/home/andy/mosaic-manual-1.4.0/'..file:gsub('^mosaic/','')..'.lua')end
include('mosaic/lib/tests/lib/ui_vertical_list_tests')
os.exit(luaunit.LuaUnit.run())
