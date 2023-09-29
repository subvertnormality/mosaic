# 0.3

_Breaking update. Please backup and remove your .pset and .ptn data files from previous versions._

* Destructive device changes now require confirmation before they are applied
* Channel devices are now persistent across all sequencer patterns
* Custom device config files are now stored in data and are not overwritten on script update
* Midi device init patches can now be configured and stored in the params menu
* Midi device trig params sync up with their respective norn param values
* Scale slots can now be saved across all sequencer patterns by holding K2 when selecting
* Sinfonion sync now corrects for the "feature" in the Sinfonion where the minor scale's firth degree has a flattened note 
* EX Multi Sample and Matrix Mixer device templates added

# 0.2.5

* Added random velocity trig lock
* Dual and long press logic has been improved, making the UX more reliable
* Global transposition added to global scale page

# 0.2.4

* To stop the sequencer you now need to hold down the currently active page's LED in the menu. This prevents accidental stops whilst navigating pages.
* NB devices now send proper velocities
* Added quantised fixed note trig lock
* Added bipolar random note trig lock
* Added twos random note trig lock