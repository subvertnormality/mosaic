"""Diagnostic-only app wrapper; never publish its altered entrypoint as acceptance."""
import json,sys
from pathlib import Path
import manual_doctor_capture as doctor
original_freeze=doctor.freeze

def diagnostic_freeze(out):
    app=original_freeze(out)
    original=(app/'mosaic.lua').read_text();(app/'production-entry.lua').write_text(original)
    extra="""
local diagnostic_original_init=init
init=function()
  diagnostic_original_init()
  clock.run(function()
    while true do
      clock.sleep(.2)
      local d=trigger_edit_page and trigger_edit_page.get_rhythm_doctor and trigger_edit_page.get_rhythm_doctor()
      if d then
        print('DOCTOR_DIAGNOSTIC state='..tostring(d.runtime.machine.state)..' feedback='..tostring(d.feedback)..' setup='..tostring(d.setup_draft~=nil)..' controller='..tostring(d.runtime.controller~=nil)..' detail='..tostring(d.status_detail))
      end
    end
  end)
end
"""
    (app/'mosaic.lua').write_text(original+extra)
    (out/'diagnostic-only.json').write_text(json.dumps(dict(acceptance=False,reason='Read-only status logging added to the frozen entrypoint, outside unchanged-application acceptance.',production_entry_sha256=doctor.digest(app/'production-entry.lua')),indent=2)+'\n')
    return app

doctor.freeze=diagnostic_freeze
if __name__=='__main__':raise SystemExit(doctor.main())
