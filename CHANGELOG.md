
# 0.5.3

* Performance and bug fixes

# 0.5.2

* Fixing some minor issues with chord masks

# 0.5.1

* Fixing issue where certain files would not initialise properly on fresh install
* Fixing issue when assigning midi devices when no midi output devices are configured in Norns

# 0.5.0 - Beta

_Breaking update. Please backup and remove your .pset and .ptn data files from previous versions._

* More bug fixes
* New improved manual
* Scale and quantiser have been streamlined, global scale UI simplified
* Note Masks: It's now possible to add and remove trigs to a channel directly from the channel page, overwriting pattern values
* Note Masks: It's possible to set notes, velocities, and lengths, directly from the channel page, overwriting pattern values
* Note Masks: Chords are now editable directly in the channel editor
* Note Masks: Create note mask locks by using a midi keyboard
* It's now possible to sync elektron devices with Mosaic's song mode. Patterns will be selected based on the currently selected Mosaic song pattern
* UI elements no long wrap when selecting horizontally
* Param on/off options are now in a sensible order
* Digitakt 2 config file added
* N.B. note players must now be allow-listed before being loaded to prevent crashes
* Added option to lock all notes to pentatonic versions of each scale
* Added option to lock merged notes to pentatonic versions of each scale - on by default
* Added option to lock random notes to pentatonic versions of each scale - on by default

# 0.4.4

* Reworked the device configuration process to be simpler and less error prone. Custom devices are now respresented by `.json` files and will appear in mosaic when included in `dust/data/mosaic/config`. See `dust/code/mosaic/lib/config` for example configuration files.

# 0.4.3

* Added trig scale masks in the channel editor
* More bug fixes

# 0.4.2

* It's now possible to select a manual chord degree rotation on the scale page
* More bug fixes

# 0.4.1

* Chord rotations now ascend by default rather than wrapping unpredictably
* Bug and performance fixes
* Global scale mode no longer glitches when rapid channel step scale triggers are used
* Midi keyboards now pass through on selected channel
* Added windows unit test runner
* Pattern merge modes now merges values from channels even if they aren't activated

# 0.4.0

* Sinfonion sync is no longer experimental and doesn't require modifications to norns
* NB now doesn't crash the script if there are no mods installed

# 0.3.7

* Added chord velocity modifier trig param
* Added chord strum pattern trig param

# 0.3.7

* Stability fixes
* Fixing a regression which was making note length resolution inconsistent with tracks using swing

# 0.3.6

* Sinfonion sync is no longer as resource intensive
* Fixed regression with trig lock values not displaying properly when the sequencer is playing

# 0.3.5

* Removing a mod no longer causes problems with the channel that had the mod applied via a device
* Devices can now be set to polyphonic and non-polyphonic. Non-polyphonic devices stop all notes before playing the next note. This is good for devices that utilises gates. Polyphonic devices allow the device to deal with overlapping notes.
* Introduced chord strum trig param.

# 0.3.4

* Fixed bug that led to trig lengths not correctly following the channel's current clock division or swing

# 0.3.3

* Fixed regression that stopped trig locks from displaying in the UI

# 0.3.2

* Chord notes trig params added. These can be used to append an additional note to trigs on a single channel, thereby forming a chord. Chords follow scales and locks.

# 0.3.1

_Breaking update. Please backup and remove your .pset and .ptn data files from previous versions._

* It's now possible to set a clock division or multiplication for global scale, enabling slower or faster scale progressions and progressions that apply using sequences of less than 64 steps.
* Midi clock sync logic has been improved
* Clock logic has been entirely rewritten and is much more stable
* Various clock and sequencer bug fixes


# 0.3

_Breaking update. Please backup and remove your .pset and .ptn data files from previous versions._

* Destructive device changes now require confirmation before they are applied
* Channel devices are now persistent across all song sequences
* Custom device config files are now stored in data and are not overwritten on script update
* Midi device init patches can now be configured and stored as norns params
* Midi device trig params sync up with their respective norn param values
* Scale slots can now be saved across all song sequences by holding K2 when selecting
* Sinfonion sync now corrects for the "feature" in the Sinfonion where the minor scale's fifth degree has a flattened note 
* EX Multi Sample and Matrix Mixer device templates added
* Param lock clearing and management has been improved
* Various bug fixes

# 0.2.5

* Added random velocity trig lock
* Dual and long press logic has been improved, making the UX more reliable
* Global transposition added to global scale page

# 0.2.4

* To stop the sequencer you now hold down the currently active page's LED in the menu. This prevents accidental stops whilst navigating pages.
* NB devices now send proper velocities
* Added quantised fixed note trig lock
* Added bipolar random note trig lock
* Added twos random note trig lock
