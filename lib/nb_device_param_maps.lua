local nb_device_param_maps = {}

local plaits_params = {
  "plaits_model_%d",
  "plaits_harmonics_%d",
  "plaits_timbre_%d",
  "plaits_morph_%d", 
  "plaits_fm_mod_%d",
  "plaits_timb_mod_%d",
  "plaits_morph_mod_%d",
  "plaits_a_%d",
  "plaits_d_%d",
  "plaits_s_%d", 
  "plaits_r_%d",
  "plaits_lpg_color_%d",
  "plaits_amp_%d",
  "plaits_aux_%d",
  "plaits_gain_%d",
  "plaits_pan_%d",
  "plaits_send_a_%d",
  "plaits_send_b_%d"
 }

 local plaits_default_params = {
  "plaits_model_%d",
  "plaits_harmonics_%d",
  "plaits_timbre_%d",
  "plaits_morph_%d", 
  "plaits_fm_mod_%d",
  "plaits_timb_mod_%d",
  "plaits_morph_mod_%d",
  "plaits_aux_%d",
  "plaits_send_a_%d",
  "plaits_send_b_%d"
 }

 local doubledecker_params = {
  "doubledecker_voices",
  "doubledecker_voice_spread",
  "doubledecker_lfo_phase_spread",
  "doubledecker_mix",
  "doubledecker_amp",
  "doubledecker_send_a",
  "doubledecker_send_b",
  "doubledecker_pan",
  "doubledecker_detune",
  "doubledecker_drift",
  "doubledecker_pitch_env",
  "doubledecker_portomento",
  "doubledecker_brilliance",
  "doubledecker_resonance",
  -- Layer specific params (repeated for layers 1 and 2)
  "doubledecker_pitch_ratio_1",
  "doubledecker_pitch_ratio_2",
  "doubledecker_layer_lfo_freq_1",
  "doubledecker_layer_lfo_freq_2",
  "doubledecker_pwm_1",
  "doubledecker_pwm_2",
  "doubledecker_pw_1",
  "doubledecker_pw_2",
  "doubledecker_shape_1",
  "doubledecker_shape_2",
  "doubledecker_noise_1",
  "doubledecker_noise_2",
  "doubledecker_hp_freq_1",
  "doubledecker_hp_freq_2",
  "doubledecker_hp_res_1",
  "doubledecker_hp_res_2",
  "doubledecker_lp_freq_1",
  "doubledecker_lp_freq_2",
  "doubledecker_lp_res_1",
  "doubledecker_lp_res_2",
  "doubledecker_filter_init_1",
  "doubledecker_filter_init_2",
  "doubledecker_filter_attack_level_1",
  "doubledecker_filter_attack_level_2",
  "doubledecker_filter_attack_1",
  "doubledecker_filter_attack_2",
  "doubledecker_filter_decay_1",
  "doubledecker_filter_decay_2",
  "doubledecker_filter_release_1",
  "doubledecker_filter_release_2",
  "doubledecker_filt_1",
  "doubledecker_filt_2",
  "doubledecker_sine_1",
  "doubledecker_sine_2",
  "doubledecker_amp_attack_1",
  "doubledecker_amp_attack_2",
  "doubledecker_amp_decay_1",
  "doubledecker_amp_decay_2",
  "doubledecker_amp_sustain_1",
  "doubledecker_amp_sustain_2",
  "doubledecker_amp_release_1",
  "doubledecker_amp_release_2",
  "doubledecker_velocity_to_filter_1",
  "doubledecker_velocity_to_filter_2",
  "doubledecker_velocity_to_amp_1",
  "doubledecker_velocity_to_amp_2",
  "doubledecker_pressure_to_filter_1",
  "doubledecker_pressure_to_filter_2",
  "doubledecker_pressure_to_amp_1",
  "doubledecker_pressure_to_amp_2",
  "doubledecker_filter_keyfollow_lo_1",
  "doubledecker_filter_keyfollow_lo_2",
  "doubledecker_filter_keyfollow_hi_1",
  "doubledecker_filter_keyfollow_hi_2",
  "doubledecker_amp_keyfollow_lo_1",
  "doubledecker_amp_keyfollow_lo_2",
  "doubledecker_amp_keyfollow_hi_1",
  "doubledecker_amp_keyfollow_hi_2",
  "doubledecker_layer_amp_1",
  "doubledecker_layer_amp_2",
  "doubledecker_invert_hpf_1",
  "doubledecker_invert_hpf_2",
  -- LFO params
  "doubledecker_lfo_shape",
  "doubledecker_lfo_rate",
  "doubledecker_lfo_to_freq",
  "doubledecker_lfo_to_filter",
  "doubledecker_lfo_to_amp",
  "doubledecker_lfo_pres_to_freq",
  "doubledecker_lfo_pres_to_vibrato",
  "doubledecker_lfo_pres_to_filt",
  "doubledecker_lfo_pres_to_amp",
  "doubledecker_lfo_sync",
  "doubledecker_lfo_scope"
}

local doubledecker_default_params = {
  "doubledecker_shape_1",
  "doubledecker_shape_2",
  "doubledecker_pitch_env",
  "doubledecker_portomento",
  "doubledecker_noise_1",
  "doubledecker_resonance",
  "doubledecker_lfo_shape",
  "doubledecker_lfo_rate",
  "doubledecker_lfo_pres_to_vibrato",
  "doubledecker_lfo_to_filter"
}

local rudiments_params = {
  "rudiments_shape_%d",
  "rudiments_freq_%d", 
  "rudiments_decay_%d",
  "rudiments_sweep_%d",
  "rudiments_lfoFreq_%d",
  "rudiments_lfoShape_%d",
  "rudiments_lfoSweep_%d",
  "rudiments_gain_%d"
}

local polyperc_params = {
  "polyperc_decay_%d",
  "polyperc_cutoff_%d",
  "polyperc_tracking_%d",
  "polyperc_pw_%d",
  "polyperc_amp_%d",
  "polyperc_gain_%d",
  "polyperc_pan_%d",
  "polyperc_send_a_%d",
  "polyperc_send_b_%d"
}

function nb_device_param_maps.get_params_for_device(device)

  local instance_params = {}

  if fn.starts_with(device, "emplait") then
    for _, param in ipairs(plaits_params) do
      table.insert(instance_params, string.format(param, fn.get_last_char(device)))
    end
  elseif device == "doubledecker" then
    instance_params = doubledecker_params
  elseif fn.starts_with(device, "rudiments") then
    for _, param in ipairs(rudiments_params) do
      table.insert(instance_params, string.format(param, fn.get_last_char(device)))
    end
  elseif fn.starts_with(device, "polyperc") then
    for _, param in ipairs(polyperc_params) do
      table.insert(instance_params, string.format(param, fn.get_last_char(device)))
    end
  end

  return instance_params
  
end

function nb_device_param_maps.get_default_params_for_device(device)

  local instance_params = {}

  if fn.starts_with(device, "emplait") then
    for _, param in ipairs(plaits_default_params) do
      table.insert(instance_params, string.format(param, fn.get_last_char(device)))
    end
  elseif device == "doubledecker" then
    instance_params = doubledecker_default_params
  elseif fn.starts_with(device, "rudiments") then
    for _, param in ipairs(rudiments_params) do
      table.insert(instance_params, string.format(param, fn.get_last_char(device)))
    end
  elseif fn.starts_with(device, "polyperc") then
    for _, param in ipairs(polyperc_params) do
      table.insert(instance_params, string.format(param, fn.get_last_char(device)))
    end
  end

  return instance_params
  
end


return nb_device_param_maps