local env_mod = include("mosaic/lib/tests/helpers/ui_live_env")
function test_ui_live_boot_smoke()
  env_mod.isolated(function(env)
    print("screen", ui_live.state().screen, ui_live.state().context, env_mod.channel_page())
  end)
end
