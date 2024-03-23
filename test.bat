@echo off

REM Change directory to the directory containing the Lua script
cd ".\tests\"

REM Run the Lua script with a parameter
lua .\run_tests_windows.lua -p test_%1