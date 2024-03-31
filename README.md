*Mosaic* for monome norns is a grid-centric, intentioned generative sequencer. Bridging the world of modular, Elektron, and monome, it weaves intricate rhythms and melodies with finesse. Jump into a profound and singular tapestry of sketching and composition.

- [Mosaic](#mosaic)
  * [At a glance](#at-a-glance)
  * [Install](#install)
  * [Core concepts](#core-concepts)
    + [Pattern](#pattern)
    + [Channel](#channel)
    + [Sequencer Pattern](#sequencer-pattern)
    + [Scale](#scale)
    + [Device](#device)
    + [Params](#params)
    + [Trig Locks](#trig-locks)
  * [Pages](#pages)
    + [Menu](#menu)
      - [Sequencer start and stop](#sequencer-start-and-stop)
      - [Midi Panic](#midi-panic)
    + [Trig editor](#trig-editor)
    + [Note editor](#note-editor)
    + [Velocity editor](#velocity-editor)
    + [Channel editor](#channel-editor)
      - [Merge modes](#merge-modes)
      - [Global scale editor](#global-scale-editor)
      - [Stock trig locks](#stock-trig-locks)
        - [Probability](#probability)
        - [Fixed note](#fixed-note)
        - [Quantised fixed note](#quantised-fixed-note)
        - [Random note](#random-note)
        - [Random twos note](#random-twos-note)
        - [Chord notes](#chord-notes)
        - [Chord strum](#chord-strum)
    + [Song editor](#song-editor)
  * [Save and load](#save-and-load)
  * [Custom device maps](#custom-device-maps)
- [Sinfonion connect](#sinfonion-connect)
- [Development](#development)




## At a glance

As of v0.4 _Mosaic_ gives you the following:

- 16 channels that can each output triggers, notes, note length, velocity and CC to a midi or an n.b. voice
- 16 patterns that can be combined and merged in different permutations to change their properties in very musical ways
- Song mode with 90 sequencer patterns
- Save, load, autosave
- Pattern editor enabling quick creation of trigger patterns using DrumOps, includes euclidean, tresillo function, drum preset banks, and NE Numeric Repetitor
- 10 assignable trig locks per channel
- Midi device templates including labelled trig destinations
- Native [n.b.](https://github.com/sixolet/nb/) support
- Per channel tempo, swing, and pattern length
- Channel muting
- Scales with setable root note, degree and transpotion
- Trig lockable octave, scales, chords, transpose, step probability, random note modifiers, random velocity modifiers, and more
- Ability to sync to the Sinfonion eurorack quantiser for even more possibilities

Requirements:

- Norns
- 128 grid
- At minimum, one of the encouraged sound sources

Encouraged:

- Midi interface
- Midi instruments
- Crow, Just Friends, Ansible
- [n.b.](https://github.com/sixolet/nb/)
- Disting EX
- Elektron Digitone, Syntakt, Digitakt
- Sinfonion
- Midi controller with encoders that sends relative bin offsets (for example, intech grid en32)

## Install

To install, simply run `;install https://github.com/subvertnormality/mosaic` in maiden. See the [device configuration section for setting up mosaic's config files](#Device-configuration)

## Core concepts

### Pattern

In _Mosaic_, the 'pattern' is the central pillar. Think of it as a sequence enriched with 64 trigs, 64 notes, 64 velocities, and length data for each trig. Each pattern spans 64 steps.

In _Mosaic_, notes aren't strictly bound to a single scale. Instead, they are valued by their position within the chosen scale, measured by distance from the root. Take C major for instance: C is your starting point. One step up brings you to D, and one step down lands on B. If you were to change the applied scale to E minor, the root of your pattern would now be E, one step up would output F sharp, one down would be D. 

_Mosaic_ ensures you remain within your selected scale although there are ways to experiment with notes outside of it too. You'll find several methods to adjust scales as you go, which we'll cover shortly.

### Channel

The 'channel' represents another pivotal component in _Mosaic_. Through a channel, you decide the musical device to play and the specifics of its sound. You select the channel's internal sound device, MIDI device, pick MIDI outputs, choose MIDI channels, the scale, and set up param trig locks and their related destinations. Additionally, you can assign various patterns to one channel. A single pattern can be linked to multiple channels.

When two patterns overlap in one channel and their trigs coincide, the outcome depends on the channel's 'merge mode'. There are several merge modes, each with its own characteristic. This feature encourages designing patterns that, when they overlap, produce intriguing results.

You can adjust the rhythm for each channel individually, allowing for different clock divisions and swings. Plus, if you're looking to mix up the rhythm, channels can be set to fewer than the standard 64 steps, opening the door to polyrhythmic experiments.

### Sequencer Pattern

The sequencer pattern rounds out the trio of foundational elements in _Mosaic_. This entity encompasses all details from channels and patterns. This includes aspects from trig locks and scale preferences to merge modes and octave choices for a 64-step sequence. Within a scene, you're provided with 90 sequencer pattern slots, which can be linked to create a full song in the song mode page. All sequencer patterns can have their global length adjusted anywhere between 1 to 64 steps, which will apply to all channels.

### Scale

Each sequencer pattern offers 16 scale slots. A single slot has a root note, a scale variation (eg Dorian, Major, etc), and a degree setting. Scales can be selected in various ways: setting a default scale for a channel, designating scale trig locks for specific channels activated on certain steps, or setting global scale trig locks influencing all channels unless a particular channel-specific trig lock takes precedence. This flexibility paves the way for intricate chord progressions and the ability to add variation to patterns.

### Device

Think of a device as a either an internal norns sound engine powered by [n.b.](https://github.com/sixolet/nb/tree/main), or a representation of a MIDI device in your workspace. Devices are applied per scene and are consistent across all sequencer patterns.

n.b. devices are picked up automatically. Simply install the desired mod, and pick from the device picker menu. Be careful not to overwhelm your norns by adding too many internal sound engines to channels.

Midi devices is primarily defined by attributes like MIDI destinations, device name, and CC MIDI destinations. While there are some ready-made device templates to get you started, param trig lock destinations can be customised. See the [device configuration section for setting up mosaic's config files](#Device-configuration) for information

Midi devices can be set to load a stored patch using the params menu. For stock midi devices, all cc parameters are available to edit. A value of -1 against a midi parameter means the function is off. Changing the value will send the midi value to your midi device. When you load a mosiac script, the stored midi param values will be sent to your midi device, effectively loading a patch. It's possible in this way to stored all your sound's patch data with your mosaic patch. This is particularly practical for devices with less midi parameters or where the device's interface is not particularly intuitive.

### Trig Params

Most devices in _Mosaic_ feature a set of trig params that alters either the quality of the sound or the trig in some way. These params can be trig locked. Trig locking is a powerful sequencer device seen on Elektron synthesizers. Each step can be assigned a unique param value, allowing for endless sound variations. See the channel page section for details on how to assign and use params.

### Trig Locks

Param values and many grid functions can be locked to steps on the channel and global scale pages. A locked value is then applied for the duration of the step. Trig params, scales, and octave settings can be locked to a step on the channel page. Global scale and transpose settings can be locked to a step using the global scale page. 

To set a trig lock, hold down the desired step on the sequencer and modify the value to be locked. 

To clear a param trig lock, select the param on the norns screen, hold the step, then press K3. To clear a grid trig lock, hold the desired step and press the currently locked value. To clear all trig locks from a step, hold the step and press K2.

## Pages

At its heart, _Mosaic_ comprises five distinct pages. Every page presents a grid interface complemented by a set of configurable options on the norns device. The grid is the primary interface, with norns offering one-time configuration options. This allows you to set up your scene's configuration once and then use the grid from then on to compose.

### Menu

The grid's lower menu facilitates page selection using bottom-left five buttons, a feature maintained consistently across all pages. On the right, there are functions sensitive to the current page context.
 
![The menu as shown on the pattern edit page](https://raw.githubusercontent.com/subvertnormality/mosaic/main/designs/Images/menu.png)

From the left moving rightward, the buttons activate:

* Channel editor
* Song editor
* Trig editor (highlighted in this instance)
* Note editor
* Velocity editor

#### Sequencer start and stop

To start the sequencer, simply press the active page in the menu. If the sequencer is in motion, the active page button will give off a gentle blink. To stop the sequencer, _hold_ the currently active and gently blinking page in the menu for two seconds.

#### Midi Panic

If you get stuck notes, hold any of the inactive page buttons in the menu. This will perform a midi panic. The system might slow for a short period whilst this is processing.

### Trig editor

The rhythm designer in _Mosaic_ is named the trig editor. Using DrumOps tools, originally seen in the Teletype ecosystem but now available here, you can craft intricate patterns. You can also set the duration of each step.

![Trig editor with a complex trig pattern](https://github.com/subvertnormality/mosaic/raw/main/designs/Images/trig_editor.png)

With the top row, pick one of the 16 patterns available. In the image, you can see pattern 2 is selected.

![Pattern select buttons](https://github.com/subvertnormality/mosaic/raw/main/designs/Images/trig_editor_pattern_select.png)

To set your rhythm, simply tap in steps using the sequencer. Bright steps symbolize a trig. To define its length, press and hold a trig, then choose its ending step. Steps with a subtle glow show the length. In a single pattern, one trig’s duration ends upon meeting another.

![Trig sequencer](https://github.com/subvertnormality/mosaic/raw/main/designs/Images/trig_editor_sequencer.png)

Craft unique rhythms using a variety of built-in algorithms.

* Button 1: The drum algorithm, drawing from a rich collection of classic drum patterns.
* Button 2: The tresillo algorithm, utilizing a 3/3/2 ratio for diverse rhythm variations. The tresillo multiplier can be set on the norns screen for more varations.
* Button 3: Euclidian, a rhythm tool rooted in mathematical logic.
* Button 4: NE Numeric Repetitor, another rhythm tool based on mathematical principles.

![Algorithm select](https://github.com/subvertnormality/mosaic/raw/main/designs/Images/trig_editor_algorithms.png)

The grid is intuitive and adapts to your choices. Each algorithm brings its set of options, and pressing on a grid key typically displays its function on the norns screen.

The left side faders adjust algorithm values. Brightly lit ends refine values, while the dimmer ones adjust them broadly. The rightmost fader typically toggles between different algorithm banks.

![Algorithm controls](https://github.com/subvertnormality/mosaic/raw/main/designs/Images/trig_editor_algorithm_controls.png)

To see your algorithm's impact, hit the prime button. This prepares a new pattern, and new steps are showcased as flashing bright steps on the sequencer. While these steps flash, they aren’t painted yet. Any step that would be painted over an existing active step will blink dimly. By painting the new pattern, you'll deactivate the faintly blinking steps. This approach lets you craft intricate sequences, grounded in rhythmic fundamentals, that don't get too busy. You can modify algorithm parameters whilst the pattern is primed.

If you haven’t painted the new pattern, the prime button continues to blink. Pressing it again paints your edits. Double-pressing the prime button without tweaking the algorithm or its parameters acts as an undo for the last action.

![Prime and print button](https://github.com/subvertnormality/mosaic/raw/main/designs/Images/trig_editor_prime_and_print.png)

Opt out of a prepared pattern by using the cancel button.

![Cancel button](https://github.com/subvertnormality/mosaic/raw/main/designs/Images/trig_editor_cancel.png)

While previewing a new pattern, use the move controls to shift its position. The first button shifts it left, the third to the right, and the center button resets it. Remember to paint your changes.

![Left, centre, right buttons](https://github.com/subvertnormality/mosaic/raw/main/designs/Images/trig_editor_left_right.png)

On the norns screen, you can see the selected channel's grid state on page 1. This is the merged version of the channel and is useful context for editing your pattern. Use E2 to select channels.

![Channel grid viewer](https://github.com/subvertnormality/mosaic/raw/main/designs/Images/UI/trig_edit_grid_viewer.png)

On page 2 you can select trig editor options. Currently this allows you to edit the tresillo multiplier in use. Experiment with different values to get wildly different results with the tresillo algorithm.

![Channel grid viewer](https://github.com/subvertnormality/mosaic/raw/main/designs/Images/UI/trig_edit_options.png)


### Note editor

Set the harmony and melody of your rhythmic creations with the note editor.

This space displays 16 steps at a glance. Active trigs appear as soft-glowing vertical bars while the root note lies in a subtle horizontal line. The notes you've actively chosen glow brightly. To pick a note for any of the 16 steps, just press. The gentle flicker on the top row indicates the currently chosen pattern. If you wish to explore a different pattern, press and hold on this top row.

Remember, each note you select links back to the root of the scale you're working within. The scale is applied to the channel, not the pattern. You must start to think about your patterns as being disconnected from each channel. This is why we say _Mosaic_ is an intentioned generative sequencer. Expect happy accidents. The channel grid viewer on the norns screen can help you here.

![Note select](https://github.com/subvertnormality/mosaic/raw/main/designs/Images/note_editor_note_selector.png)

Switch between the four sets of 16 steps using the dedicated buttons.

![16 step selector](https://github.com/subvertnormality/mosaic/raw/main/designs/Images/note_editor_16_selector.png)

Aim for higher pitches or dive deeper with the octave select buttons, expanding your melodic range.

![melodic range selector](https://github.com/subvertnormality/mosaic/raw/main/designs/Images/note_editor_octave_selector.png)

Hint: Even if a step lacks a trig, don't hesitate to assign a note. This data might come in handy with different merge modes in play.

You can use the four by four button to toggle a mode that lets you more quickly enter repeating notes across the four note grid pages. In four by four mode, any entered note is automatically duplicated across all 4 screens.

![Four by four](https://github.com/subvertnormality/mosaic/raw/main/designs/Images/note_editor_four_by_four.png)

On the norns screen, you'll find the channel grid visualiser. Use E2 to select the current channel.

### Velocity editor

Now let's look at the velocity editor, which functions similarly to the note page. It spans two vertical pages: the first displays velocities from 127 down to 67, while the second displays values between 58 and 0. Adjust these to fine-tune the dynamics of your sequence.

On the norns screen you can see the channel grid visualiser. Use E2 to select the current channel.

### Channel editor

Here's where it all comes together: the channel editor. This is where patterns find harmony, merging into cohesive sounds.

Start by selecting one of the 16 available channels:

![Channel selector](https://github.com/subvertnormality/mosaic/raw/main/designs/Images/channel_edit_channel_select.png)

Next, lend your channel its voice by assigning one or more patterns:

![Pattern selector](https://github.com/subvertnormality/mosaic/raw/main/designs/Images/channel_edit_pattern_select.png)

Each channel can have a default scale. Or, apply a specific scale to certain steps on a channel using trig locks. Scales will persist until the next scale lock or the end of the pattern (you can turn this behaviour off in the params). To select a scale for your channel, simply press on the scale fader. To remove a scale and return to chromatic, simply press the currently lit scale. Use the third page on your norns to dial in a specific scale or chord to each scale slot. 

Each scale slot corresponds specifically to the current sequencer pattern. To change a scale for the selected scale slot across all sequencer patterns, hold K2 and confirm with K3. This saves you from having to manually edit a scale on every sequencer pattern in your song when you want to change the chord progression across all sections.

![Scale selector](https://github.com/subvertnormality/mosaic/raw/main/designs/Images/channel_edit_scale_select.png)

The sequencer visualizes the music: a tapestry of selected patterns, tailored by the chosen merge mode. To set the length of a channel, simultaneously press and hold the first and last steps. Active steps illuminate, guiding the composition of your symphony. 

To explicitly turn a step off. It will blink slightly to show the step is currently deactivated. Press again to turn the step back on.

Want a step to hold a unique sound or scale? Press and keep it down while selecting the desired parameter, scale, or octave. Clearing these trig locks is a breeze:

* For scale: Hold the step and press the currently locked scale.
* For parameters: Select the relevant parameter, press and hold the step, then tap the K3 button.
* For octave: Hold the step and press the currently locked octave.

You can clear all locks for a step by holding the step and tapping the K2 button.

![Channel sequencer](https://github.com/subvertnormality/mosaic/raw/main/designs/Images/channel_edit_sequencer.png)

Adjust a channel's octave range with:

![Octave selector](https://github.com/subvertnormality/mosaic/raw/main/designs/Images/channel_edit_octave_selector.png)


#### Merge modes

And how do your patterns meld? Define this with the merge mode selector:

![Merge mode selector](https://github.com/subvertnormality/mosaic/raw/main/designs/Images/channel_edit_merge_mode.png)

* Trig merge modes: These modes determine how steps trig when there are shared steps across selected patterns.
  * All: steps that are active in any selected pattern will trig
  * Skip: steps that appear in just one selected pattern will trig, those that appear in more than one selected pattern won't.
  * Only: steps that appear in more than one selected pattern will trig, whereas those that only appear in one selected pattern won't.
* Note merge modes: These modes determine how shared step note values are calculated
  * Average: the note value of clashing steps will be calculated by averaging the note values of each selected pattern's step. The note value is then quantised.
  * Higher: the note value of clashing steps will be calculated by taking the average of each step note values, minusing the lowest note value, and adding the highest note value. The note value is then quantised.
  * Lower: the note value of clashing steps will be calculated by minusing the lowest note value in the set from the average of each step note values minus the lowest note value. The note value is then quantised.
  * Pattern: to override note values with a specific pattern's values, hold the note merge button and press the pattern's select button.
* Velocity merge modes: These modes determine how shared step velocity values are calculated
  * Average: the velocity value of clashing steps will be calculated by averaging the velocity of each selected pattern's step.
  * Higher: the velocity of clashing steps will be calculated by taking the average of each step velocity, minusing the lowest velocity, and adding the highest velocity.
  * Lower: the velocity of clashing steps will be calculated by minusing the lowest velocity in the set from the average of each step velocity minus the lowest velocity.
  * Pattern: to override velocity values with a specific pattern's values, hold the velocity merge button and press the pattern's select button.
* Length merge modes: These modes determine how shared length is calculated
  * Average: the length of clashing steps will be calculated by averaging the length of each selected pattern's step.
  * Longer: the length of clashing steps will be calculated by taking the average of each step length, minusing the smallest length, and adding the largest length.
  * Shorter: the length of clashing steps will be calculated by minusing the smallest length in the set from the average of each step length minus the smallest length.
  * Pattern: to override length values with a specific pattern's values, hold the length merge button and press the pattern's select button.


You can view detailed configurations of your selected channel on the Norns screen. Each page offers intuitive and interactive tools to sculpt your sonic experience.

On the first page you're greeted with an array of parameters. Navigate pages with E1. Rotate E2 to highlight a parameter, and E3 to refine its value. Want a different parameter active in the selected parameter slot? Tap K2. As you change the value, the system automatically locks in your changes. As mentioned above, these can be trig locked on each step by holding the step and rotating E3. The default trig param value will be sent to your chosen device destination on steps where there isn't a trig lock. When a trig param is set to "off", _mosaic_ will not send a value to your chosen device destination. When a trig lock is set to "off" on a step, it will not send the default trig param value, and will instead keep sending the value of the last trig lock.

![Param trig lock page](https://github.com/subvertnormality/mosaic/raw/main/designs/Images/UI/channel_edit_param_select.png)

You can define your channel's rhythmic character on the second page. Use E2 to navigate and E3 to set values. The channel grid keys let you specify which channel to adjust.

![Channel clocks and swing page](https://github.com/subvertnormality/mosaic/raw/main/designs/Images/UI/channel_edit_clocks.png)

On the third page, you can assign a chord or scale to one of the 16 scale slots that are selectable on the grid. The layout on the norns screen is straightforward: the left indicates the root note, the center left is the scale type, the center right selects the scale's degree, and the left sets the chord's rotation. The rotation moves the highest note in the scale down an octave successively. A value of 1 will shift the last note in the scale down an octave, a value of 2 will shift the last two notes down an octave, and so on all the way up to 6 which wills shift all but the root note down an octave. This setting can be useful to create chord inversions, of sorts. Change between options with E2 and fine-tune with E3. To change the selected scale slot, use the scale grid keys. 

![Channel quantiser config](https://github.com/subvertnormality/mosaic/raw/main/designs/Images/UI/channel_edit_quantiser.png)

On the fourth page, you can modify how your channel interacts with external devices. To the left, find the MIDI output device. The center highlights the CC value for this channel. The final section lets you select the device preset which determines the params available in the parameter selector. Different devices will have different options depending on your configuration files. Changing a device can be destructive. Scene device configurations, such as params, can be lost when switching devices. You must therefore press K3 to apply any selected device changes. Simply navigate away from the device config page without pressing K3 to cancel unsaved changes.

![Channel device config](https://github.com/subvertnormality/mosaic/raw/main/designs/Images/UI/channel_edit_device_config.png)

#### Global scale editor

Want to harmonize the scale across all channels? Here's how with the global scale editor:

To accessing the global scale editor, press and hold any scale select button. You'll be presented with a streamlined grid offering a few clear options. 

![Global quantiser](https://github.com/subvertnormality/mosaic/raw/main/designs/Images/channel_edit_global_scale.png)

On this page, you can define a global scale by pressing on the scale fader or global scale trigs using the trig lock technique. These will be consistent across all channels. This is great for crafting harmonized chord sequences.

![Global quantiser](https://github.com/subvertnormality/mosaic/raw/main/designs/Images/channel_edit_global_scale_scale_selector.png)

To trig lock, simply hold a step on the sequencer and press your desired scale or transposition. Steps with existing trig locks will blink gently.

![Global quantiser sequencer](https://github.com/subvertnormality/mosaic/raw/main/designs/Images/channel_edit_global_scale_sequencer.png)

Scales apply in the following priority order:

* Channel Scale Trig Locks: These have the highest priority. No matter your other settings, these are always honored.
* Global Scale Trig Locks: These come next in line.
* Default Channel Scale: If no scale locks are set, the sequencer uses the channel default.
* Global Default Scale: If there are no scale locks and your channel doesn't have a default scale set, the sequencer uses the global scale.
* If none of the above are set, your sequence will play chromatically.

Tip: When a trig or a global default scale is active, its corresponding scale button will glow with a soft light.

The global scale runs against the master clock. This makes any channels that are running with fewer than 64 steps extra fun when combined with global scales and global scale trigs!

You can transpose your entire sequencer pattern using the global quantiser transposition fader, either globaly or by step using trig locks. Transposition applies on top of the currently selected scale. 

![Global quantiser transposition fader](https://github.com/subvertnormality/mosaic/raw/main/designs/Images/channel_edit_global_scale_transposition.png)

To return to the channel pages, select a channel using the channel select buttons.

![Global quantiser channel selector](https://github.com/subvertnormality/mosaic/raw/main/designs/Images/channel_edit_global_scale_channel_select.png)

#### Stock trig params

All device types have a set of standard trig params that affect the sequencer rather than the quality of the sound. 

##### Fixed note

Use this trig param to fix your channel to any midi note. The value represents a midi note number. The note is _not_ quantised. This is useful if you have a drum pattern and you don't want note data to affect the drum sound you're playing on a drum machine. This will override any quantised fixed note values or random note values.

##### Quantised fixed note

You can use this trig param to manually select a note in the currently selected scale at any step. The value represents note number, where 0 is the root and higher numbers represent notes in the quantised scale. This overrides the note data coming in from the patterns. This will override random note values.

##### Random note

This trig param introduces an element of random to your selected notes. A value of 0 will leave the note unchanged. A value of 1 will randomly give your existing note or the note one higher in the scale. A value of 2 will randomly give your existing note, the note one higher in your selected scale, or the note one lower. A value of 3 will randomly select notes -1, 0, 1 or 2. A value of 4 will randomly select notes -2, -1, 0, 1 or 2. And so on. Use trig locks to really spice things up. These can be combined with random two's note trig param.

##### Random two's note

Similar to random note, this trig param introduces an element of random to your selected notes. The difference here is that two's note restricts values to those divisible by two. A value of 0 will leave the note unchanged. A value of 1 will randomly give your existing note or the note two higher in the scale. A value of 2 will randomly give your existing note, the note two higher in your selected scale, or the note two lower. A value of 3 will randomly select notes -2, 0, 2 or 4. A value of 4 will randomly select notes -4, -2, 0, 2 or 4. And so on. Use trig locks to really spice things up. These can be combined with random note trig params.

##### Random velocity

Add spice to the velocity of your trigs with this param. Similar to random note, a value of 1 will randomly give your current trig's velocity or a velocity one higher than that value. A value of 2 will give the current velocity, one lower, or one higher. And so on. This can be super useful when applied to all trigs on a channel to humanise your dynamics. Or use it on a step trig lock to add random variation to the dynamics of a single hit.

##### Trig Probability

This trig param can be used to ensure trigs play only with a certain probability. When set to 100, the trig will always play. When set to 0, the trig will never play. At 50, the trig will play half the time. You can set this globally and per step.

##### Chord Notes

Using Chord Notes trig params, you can enhance your music by adding up to four notes to a single trig, creating rich chords with up to five sounds. These added notes, quantized to the selected scale, respect scale locks and derive from the original trig note, post any note modifiers. They inherit the original trig’s length and velocity, ensuring consistent sound dynamics. Note that polyphonic devices are required to avoid unexpected results.

##### Chord Strum

The Chord Strum feature dynamically spaces chord notes using the selected clock division, ensuring they align rhythmically with the channel's settings. Notes are quantized to the current scale, adjusting in real-time if the scale changes mid-strum, guaranteeing each note stays harmonious and in tune, regardless of strum duration.

##### Chord Velocity Modifier

The Chord Velocity Modifier incrementally adjusts the velocity of successive notes in a chord, starting from the chord's root note. This adjustment can either increase or decrease the velocity, thereby creating a "swell" effect for rising intensity or a "fade" effect for a diminishing feel.

### Song editor

The song editor comprises a grid of 90 slots, with each slot representing the potential to combine your patterns in distinctive ways. These sequencer patterns embody patterns, channels, rhythms, scales, and all other compoenents of your rhythms.

* Dim buttons: Think of these as blank canvases, waiting for your touch.
* Mid-glow buttons: These slots are already filled with your rhythms and patterns.
* Brightly lit button: This indicates the sequencer pattern currently in play.

Want to choose a pattern? A simple press will do. Looking to replicate one slot to another? Press and hold the source, then the desired destination. Warning: this action replaces the content of the target slot. To erase a slot, simply copy an empty one over it. There is no undo. Be careful.

Now, if the "song mode" setting is toggled on, after a pattern finishes playing its set number of times, the sequencer gracefully advances to the next slot. Should it find the next slot empty, it circles back to the first filled slot in that group. This lets you craft distinctive pattern clusters to shift between. And if you get an urge to switch up slots while the sequencer plays? No worries, it queues your request, waiting for the current sequence to finish.

![Song sequencer pattern selector](https://github.com/subvertnormality/mosaic/raw/main/designs/Images/song_mode_sequencer_pattern_selector.png)

Adjust the global sequencer pattern length with the fader located at the song editor page's lower end. For precise adjustments, use the end cap buttons. If you prefer broader changes, the central fader buttons have you covered. You have a spectrum from 1-64 to explore.

![Pattern length selector](https://github.com/subvertnormality/mosaic/raw/main/designs/Images/song_mode_sequencer.png)

On the norns display, you can establish your song's flow. On page 1 you can dictate how many times a chosen sequencer pattern plays before gracefully transitioning to the next slot when song mode is turned on. When song mode is off, take control and manually activate slots for your song to progress.

![Song progression page](https://github.com/subvertnormality/mosaic/raw/main/designs/Images/UI/song_progression.png)

On page 2, whether you desire a serene lullaby or a frantic mess, you can set the tempo to your liking.


## Save and load

You can save and load your creation in the param menu. On save, you will be prompted for a name. 

When the sequencer is not playing, it will autosave with the name "autosave" after 60 seconds. When autosaving, your norns will briefly display the _Mosaic_ logo and your grid will flash. When you launch _Mosaic_ the autosave will be automatically be loaded. Be careful to save into a named slot if you want to keep your creation forever!

## Device configuration

By default, you'll only see a "CC Device" in Mosaic's device configuration menu in the channel page. This device can be used to control any midi device of course, but you won't benefit from parameter labels. To get the benefit of more midi devices, you can add config files to `dust/data/mosaic/config` tailored to the specifics of your studio. There are a set of premade configuration files in `dust/code/mosaic/lib/config`. Simply copy the ones that are relevant to your studio over to `dust/data/mosaic/config`. You can edit the configuration files manualy to suit your midi device's configuration, for example, to specify a custom midi channel. Create your own `.json` configuration by following the format of the stock config files. Please also consider adding any you make to the mosaic repository for others to use! 

You can also install devices such as the execellent [emplaitress](https://github.com/sixolet/emplaitress) using [n.b.](https://github.com/sixolet/nb/tree/main). These will appear automatically when a mod is installed and active.

# Midi control

You can connect a midi keyboard to norns to play the device on the currently selected channel. The midi keyboard follows the selected scale at the currently playing step. You can configure whether the midi keyboard honours the degree and note wrapping options of the scale in the Norn's parameters page.

Control all 10 of the trig parameters on the currently selected page independently by using a midi controller such as intech's en64 by sending a relative bin offset midi CC message to cc 15 - 24 respectively.

# Sinfonion connect

You can sync up your eurorack Sinfonion module to mosaic using a DIY device called norns2sinfonion.

See https://github.com/subvertnormality/norns2sinfonion for more information.

# Development

See https://trello.com/b/kMZ4qEhk/Mosaic for backlog. Please raise bugs and issues in Github.

Make sure that the tests are passing before you open a PR. 

```
./test.sh
```

Do not run this on your norns device as you'll end up pulling in the norns repository onto your device, and it'll cause a conflict. If you do this by accident, simply delete `tests/test_artefacts` to get your norns back up and running.
