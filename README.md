# Mosaic

Welcome to *Mosaic*.

*Mosaic* for monome norns is a grid-centric, intentioned generative sequencer. Bridging the world of modular, Elektron, and monome, it weaves intricate rhythms and melodies with finesse. Dive into a profound and singular tapestry of sketching and composition.

At a glance, as of v0.1 _Mosaic_ gives you the following:

- 16 channels that can each output triggers, notes, note length, velocity and CC to a single midi device
- 16 patterns that can be combined and mutated in different permutations to change their properties in very musical ways
- Song mode with 90 sequencer patterns
- Save, load, autosave
- A pattern editor that allows quick creation of trigger patterns using a DrumOps port, includes euclidean, tresillo function, drum preset banks, and NE Numeric Repetitor
- 8 assignable trig locks per channel
- Midi device templates including labelled trig destinations
- Per channel tempo and swing
- Per channel pattern length
- Channel muting
- Scales with root note and degree setting
- Trig lockable octave and scale select

Requirements:

- Norns
- 128 grid
- Midi interface
- Midi instruments

## Core concepts

### Pattern

In _Mosaic_, the 'pattern' is the central pillar. Think of it as a sequence enriched with 64 trigs, 64 notes, 64 velocities, and length data for each trig. Each pattern spans 64 steps.

In the world of _Mosaic_, notes don't strictly adhere to a single scale. Instead, they are valued by their position within the chosen scale, measured by distance from the root. Take C major for instance: C is your starting point. One step up brings you to D, and one step down lands on B. If you were to change the applied scale to E minor, the root of your pattern would now be E, one step up would output F sharp, one down would be D. 

_Mosaic_ ensures you remain within your selected scale (though there are ways to flirt with notes outside of it, which we'll delve into later). You'll find several methods to adjust scales seamlessly as you go, which we'll cover  shortly.

### Channel

The 'channel' is the second crucial component in _Mosaic_. Through a channel, you decide the musical device to play and the specifics of its sound. You select the channel's MIDI device, pick the MIDI output, choose the MIDI channel, the scale, and set up trig locks and their related destinations. Additionally, you can assign various patterns to one channel. Remember, a single pattern can be linked to multiple channels, and while each channel is monophonic, several can send signals to the same MIDI device.

When two patterns overlap in one channel and their trigs coincide, the outcome depends on the channel's 'merge mode'. There are several merge modes, each with its own characteristic. This feature encourages designing patterns that, when they overlap, produce intriguing results.

You can adjust the rhythm for each channel individually, allowing for different clock divisions and swings. Plus, if you're looking to mix up the rhythm, channels can be set to fewer than the standard 64 steps, opening the door to polyrhythmic experiments.

### Sequencer Pattern

The sequencer pattern stands as the last of the three foundational elements in _Mosaic_. This entity encompasses all details from channels and patterns, ranging from trig locks and scale preferences to merge modes and octave choices for a 64-step sequence. Within a scene, you're provided with 90 sequencer pattern slots, which can be seamlessly linked to craft a song. All sequencer patterns can have their global length adjusted anywhere between 1 to 64 steps, which will apply to all channels.

### Scale

Each sequencer pattern offers 16 scale slots. A single slot can house a root note, a scale variation (eg Dorian or Major), and a degree setting. Scales can be selected in various ways: setting a default scale for a channel, designating scale trig locks for specific channels activated on certain steps, or setting global scale trig locks influencing all channels unless a particular channel-specific trig lock takes precedence. This flexibility paves the way for intricate chord progressions.

### Device

Think of a device as a representation of a MIDI device in your workspace. It's primarily defined by attributes like MIDI destinations, device name, and CC MIDI destinations. While there are some ready-made device templates to get you started, trig lock destinations can be customized either directly on the norns or through a configuration file.

## Pages

At its heart, _Mosaic_ comprises five distinct pages. Every page presents a grid interface complemented by a set of configurable options on the norns device. The design prioritizes the grid, urging users to initiate some basics via the norns—like scales and MIDI setups—and then dive deep into the grid for music creation.

### Menu

The grid's lower menu facilitates page selection using bottom-left five buttons, a feature maintained consistently across all pages. On the right, there are functions sensitive to the current page context.
 
![The menu as shown on the pattern edit page](/designs/Images/menu.png)

From the left moving rightward, the buttons activate:

* Channel editor
* Song editor
* Trig editor (highlighted in this instance)
* Note editor
* Velocity editor

To start or halt the sequencer, simply press the active page in the menu. If the sequencer is in motion, the active page button will give off a gentle blink.

### Trig editor

Dig into rhythmic design with the trig editor in _Mosaic_. Using DrumOps tools, originally seen in the Teletype ecosystem but now available here, you can craft intricate patterns and define the duration of each step.

![Trig editor with a complex trig pattern](/designs/Images/trig_editor.png)

With the top row, pick one of the 16 patterns available. In the image, you can see pattern 2 being selected.

![Pattern select buttons](/designs/Images/trig_editor_pattern_select.png)

To set your rhythm, simply tap in steps using the sequencer. Bright steps symbolize a trig. To define its length, press and hold a trig, then choose its ending step. Steps with a subtle glow show the length. Since patterns are monophonic, one trig’s duration ends upon meeting another.

![Trig sequencer](/designs/Images/trig_editor_sequencer.png)

Craft unique rhythms using a variety of built-in algorithms.

* Button 1: The drum algorithm, drawing from a rich collection of classic drum patterns.
* Button 2: The tresillo algorithm, utilizing a 3/3/2 ratio for diverse rhythm variations. The tresillo multiplier can be set on the norns screen for more varations.
* Button 3: Euclidian, a rhythm tool rooted in mathematical logic.
* Button 4: NE Numeric Repetitor, another rhythm tool based on mathematical principles.

![Algorithm select](/designs/Images/trig_editor_algorithms.png)

The grid is intuitive and adapts to your choices. Each algorithm brings its set of options, and pressing on a grid key typically displays its function on the norns screen.

The left side faders adjust algorithm values. Brightly lit ends refine values, while the dimmer ones adjust them broadly. The rightmost fader typically toggles between different algorithm banks.

![Algorithm controls](/designs/Images/trig_editor_algorithm_controls.png)

To see your algorithm's impact, hit the prime button. This prepares a new pattern, and new steps are showcased as flashing bright steps on the sequencer. While these steps flash, they aren’t painted yet. Any step that would be painted over an existing active step will blink dimly. By painting the new pattern, you'll deactivate the faintly blinking steps. This approach lets you craft intricate sequences, grounded in rhythmic fundamentals, that don't get too busy. You can modify algorithm parameters whilst the pattern is primed.

If you haven’t painted the new pattern, the prime button continues to blink. Pressing it again paints your edits. Here’s a tip: Double-pressing the prime button without tweaking the algorithm or its parameters acts as an undo for the last action.

![Prime and print button](/designs/Images/trig_editor_prime_and_print.png)

Opt out of a prepared pattern by using the cancel button.

![Cancel button](/designs/Images/trig_editor_cancel.png)

While previewing a new pattern, use the move controls to shift its position. The first button shifts it left, the third to the right, and the center button resets it. Remember to paint your changes.

![Left, centre, right buttons](/designs/Images/trig_editor_left_right.png)

On the norns screen, you can see the selected channel's grid state on page 1. This is the merged version of the channel and is useful context for editing your pattern. Use E2 to select channels.

![Channel grid viewer](/designs/Images/UI/trig_edit_grid_viewer.png)

On page 2 you can select trig editor options. Currently this allows you to edit the tresillo multiplier in use. Experiment with different values to get wildly different results with the tresillo algorithm.

![Channel grid viewer](/designs/Images/UI/trig_edit_options.png)


### Note editor

Set the harmony and melody of your rhythmic creations with the note editor.

This space displays 16 steps at a glance. Active trigs appear as soft-glowing vertical bars while the  root note lies in a subtle horizontal line. The notes you've actively chosen glow brightly. To pick a note for any of the 16 steps, just press. The gentle flicker on the top row indicates the currently chosen pattern. If you wish to explore a different pattern, press and hold on this top row.

Remember, each note you select links back to the root of the scale you're working within. The scale is applied to the channel, not the pattern. You must start to think about your patterns as being disconnected from each channel. This is why we say _Mosaic_ is an intentioned generative sequencer. Expect happy accidents. The channel grid viewer on the norns screen can help you here.

![Note select](/designs/Images/note_editor_note_selector.png)

Switch between the four sets of 16 steps using the dedicated buttons.

![16 step selector](/designs/Images/note_editor_16_selector.png)

Aim for higher pitches or dive deeper with the octave select buttons, expanding your melodic range.

![melodic range selector](/designs/Images/note_editor_octave_selector.png)

Hint: Even if a step lacks a trig, don't hesitate to assign a note. This data might come in handy with different merge modes in play.

You can use the four by four button to toggle a mode that lets you more quickly enter repeating notes across the four note grid pages. In four by four mode, any entered note is automatically duplicated across all 4 screens.

![Four by four](/designs/Images/note_editor_four_by_four.png)

On the norns screen you can see the channel grid visualiser. Use E2 to select the current channel.

### Velocity editor

Now let's look at the velocity editor, a close kin of the note editor. It spans two vertical pages: the initial displays velocities from 127 down to 67, while the latter showcases values between 58 and 0. Adjust these to fine-tune the dynamics of your sequence.

On the norns screen you can see the channel grid visualiser. Use E2 to select the current channel.

### Channel editor

Time to create the heart of your masterpiece with the channel editor. Here, individual patterns find harmony, merging into cohesive sounds.

Begin by selecting from the 16 available channels:

![Channel selector](/designs/Images/channel_edit_channel_select.png)

Next, lend your channel its voice by assigning one or more patterns:

![Pattern selector](/designs/Images/channel_edit_pattern_select.png)

Each channel can have a default scale. Or, apply a specific scale to certain steps using trig locks. Scales will persist until the next scale lock or the end of the pattern (you can turn this behaviour off in the params). To select a scale for your channel, simply press on the scale fader. To remove a scale and return to chromatic, simply press the currently lit scale.

Want to harmonize the scale across all channels? Here's how with the global scale editor:

To accessing the editor, press and hold any scale select button. You'll be presented with a streamlined grid offering a few clear options. On this page, you can define a global scale by pressing on the scale fader or global scale trigs using the trig lock technique. These will be consistent across all channels. This is great for crafting harmonized chord sequences. Again, to deactive the global scale, simply press the currently selected scale. 

Scales apply in the following priority order:

* Channel Scale Trig Locks: These have the highest priority. No matter your other settings, these are always honored.
* Global Scale Trig Locks: These come next in line.
* Default Channel Scale: If no scale locks are set, the sequencer uses the channel default.
* Global Default Scale: If there are no scale locks and your channel doesn't have a default scale set, the sequencer uses the global scale.
* If none of the above are set, your sequence will play chromatically.

Tip: When a trig or a global default scale is active, its corresponding scale button will glow with a soft light.

The global scale runs against the master clock. This makes any channels that are running with fewer than 64 steps extra fun when combined with global scales and global scale trigs!

![Scale selector](/designs/Images/channel_edit_scale_select.png)

The sequencer visualizes the music: a tapestry of selected patterns, tailored by the chosen merge mode. To set a channel's length, press and hold the first and last step simultaneously. Active steps light up, guiding your symphony.

Want a step to hold a unique sound or scale? Press and keep it down while selecting the desired parameter, scale, or octave. Clearing these trig locks is a breeze:

* For scale: Press and hold the step until it fades.
* For parameters: Press and hold the step, then tap the K3 button.
* For octave: Reset the trig lock to 0 on the octave selector.

![Channel sequencer](/designs/Images/channel_edit_sequencer.png)

Adjust a channel's octave range with:

![Octave selector](/designs/Images/channel_edit_octave_selector.png)

And how do your patterns meld? Define this with the merge mode selector:

![Merge mode selector](/designs/Images/channel_edit_merge_mode.png)

Let's get into into the merge modes:

* Pattern Merge: A harmonious blend, this mode combines trigs from all patterns, yet only takes note and velocity from the chosen pattern. To toggle through patterns, press repeatedly. For a quick switch, press and hold your desired pattern key, then tap the pattern merge mode key.
* Skip Merge: A gracious dancer, this mode elegantly sidesteps any clashing trigs.
* Average Merge: A maestro in its own right, this mode fuses clashing note values, offering fresh melodies from familiar notes.
* Add & Subtract Merge: A duet of creativity, these modes play with note values, resulting in a myriad of melodies. Tap repeatedly to switch between the two modes.

You can view detailed configurations of your selected channel on the Norns screen. Each page offers intuitive and interactive tools to sculpt your sonic experience.

On page 1 you're greeted with an array of parameters. Navigate pages with E1. Rotate E2 to highlight a parameter, and E3 to refine its value. Want a different parameter active in the selected parameter slot? Tap K2. As you change the value, the system automatically locks in your changes. As metioned above, these can be trig locked on each step by holding the step and rotating E3.

![Trig lock page](/designs/Images/UI/channel_edit_param_select.png)

You can define your channel's rhythmic character on page 2. Use E2 to navigate and E3 to finesse values. The channel grid keys let you specify which channel to adjust.

![Channel clocks and swing page](/designs/Images/UI/channel_edit_clocks.png)

On page 3 choose from the 16 quantizers. The layout is straightforward: the left indicates the root note, center introduces the scale type, and the right selects the scale's degree. Change between options with E2 and fine-tune with E3. The change the scale, use the scale grid keys.

![Channel quantiser config](/designs/Images/UI/channel_edit_quantiser.png)

On page 4 you can change how your channel interacts externally. To the left, find the MIDI output device. The center highlights the CC value for this channel. The final section lets you select the device preset which determines the params available in the parameter selector.

![Channel device config](/designs/Images/UI/channel_edit_device_config.png)

### Song editor

The song editor is a grid of 90 slots, each one representing the potential of combining your patterns in unique ways. These sequencer patterns embody patterns, channels, rhythms, scales, and all other compoenents of your rhythms, the heartbeat of your creation.

* Dim buttons: Think of these as blank canvases, waiting for your touch.
* Mid-glow buttons: These slots are already filled with your rhythms and patterns.
* Brightly lit button: this is the sequencer pattern in play right now.

Want to choose a pattern? A simple press will do. Looking to replicate one slot to another? Press and hold the source, then the desired destination. Warning: this action replaces the content of the target slot. To erase a slot, simply copy an empty one over it. There is no undo. Be careful.

Now, if the "song mode" setting is toggled on, after a pattern finishes playing it's set number of times, the sequencer gracefully changes to the next slot. Should it find the next slot empty, it circles back to the first filled slot in that group. This lets you craft distinctive pattern clusters to shift between. And if you get an urge to switch up slots while the sequencer plays? No worries, it queues your request, waiting for the current sequence to finish.

![Song sequencer pattern selector](/designs/Images/song_mode_sequencer_pattern_selector.png)


Adjust the global sequencer pattern length with the fader located at the song editor page's lower end. For precise adjustments, use the end cap buttons. If you prefer broader changes, the central fader buttons have you covered. You have a spectrum from 1-64 to explore.

![Pattern length selector](/designs/Images/song_mode_sequencer.png)

On the norns display, you're the conductor of your song's flow. On page 1 you can dictate how many times a chosen sequencer pattern plays before gracefully transitioning to the next slot when song mode is turned on. When song mode is off, take control and manually activate slots for your song to progress.

![Song progression page](/designs/Images/UI/song_progression.png)

On page 2, whether you desire a serene lullaby or a frantic mess, you can set the tempo to your liking.


## Save and load

You can save and load your creation in the param menu. On save, you will be prompted for a name. 

When the sequencer is not playing, it will autosave with the name "autosave" after 60 seconds. When autosaving, your norns will briefly display the _Mosaic_ logo and your grid will flash. When you launch _Mosaic_ the autosave will be automatically be loaded. Be careful to save into a named slot if you want to keep your creation forever!

## Custom device maps

You can define every device in your studio using the `custom_midi_device_map.lua` file in `Mosaic/lib/user_config/`. Copy the template and add your device's cc and midi information. *Always include new entries at the end of the file* to ensure backwards compatability.

You can hide the factory devices from the device list. To do this, add an entry to your `custom_midi_device_map.lua` file as so:

```  
{
  ["id"] = "op-1",
  ["hide"] = true
},
```

Including this entry will hide the OP-1 device from your list.

You can also override options. For example, if you want your EX Braids algorithm to always be set to midi channel 16, you would include the following in your `custom_midi_device_map.lua` file:

```  
  {
    ["id"] = "ex-braids",
    ["hide"] = false,
    ["default_midi_channel"] = 16
  },
```  

If you'd like, you define devices that have default paramaters defined. These parameters can also have a midi channel that differs from the device's default. The following device has two param knobs automatically assigned on the device param page. The knobs control cc 13 and 14 respectively, on midi channel 13, even though the midi trig and note information is being sent to midi channel 14.

```
{ 
    ["type"] = "midi",
    ["name"] = "Euro 4",
    ["id"] = "euro-4",
    ["fixed_note"] = nil, 
    ["map_params_automatically"] = true, -- if true, params will be mapped to channel param knobs automatically, from 1-8, otherwise user selects
    ["params"] = { -- up to 8 params 
      {
        ["id"] = "flame_13",
        ["name"] = "Flame 13",
        ["channel"] = 15,
        ["cc_msb"] = 13, -- midi cc value
        ["cc_lsb"] = nil, -- not currently used but could be in the future
        ["cc_min_value"] = 0, -- bottom range of values
        ["cc_max_value"] = 127, -- top range of values
        ["nrpn_msb"] = 1, -- not currently used but could be in the future
        ["nrpn_lsb"] = 102, -- not currently used but could be in the future
        ["nrpn_min_value"] = 0, -- not currently used but could be in the future
        ["nrpn_max_value"] = 127, -- not currently used but could be in the future
        ["short_descriptor_1"] = "U16M", -- 4 caps letters 
        ["short_descriptor_2"] = "13", -- 4 caps letters
      },
      {
        ["id"] = "flame_14",
        ["name"] = "Flame 14",
        ["channel"] = 15,
        ["cc_msb"] = 14, -- midi cc value
        ["cc_lsb"] = nil, -- not currently used but could be in the future
        ["cc_min_value"] = 0, -- bottom range of values
        ["cc_max_value"] = 127, -- top range of values
        ["nrpn_msb"] = 1, -- not currently used but could be in the future
        ["nrpn_lsb"] = 102, -- not currently used but could be in the future
        ["nrpn_min_value"] = 0, -- not currently used but could be in the future
        ["nrpn_max_value"] = 127, -- not currently used but could be in the future
        ["short_descriptor_1"] = "U16M", -- 4 caps letters 
        ["short_descriptor_2"] = "14", -- 4 caps letters
      },
    },
    ["default_midi_channel"] = 14
  },
```


Some devices respond to trigs on specific note numbers. Without locking a channel to the relevant note numbers, things can get strange very quickly in the world of _Mosaic_ as merging patterns often alters the note numbers on clashing steps (by design). This is obviously not desirable for devices that require a specific midi note for a specific drum sound, for example. You can lock a device's note number using the "Fixed Note" param on the trig lock page. You can also set this in your `custom_midi_device_map.lua` file:

```
  { 
    ["type"] = "midi", -- leave this as is
    ["name"] = "DRM BD",
    ["id"] = "drm-bd",
    ["fixed_note"] = 0, -- fixed midi note number that channel will always output
    ["map_params_automatically"] = false, -- if true, params will be mapped to channel param knobs automatically, from 1-8, otherwise user selects
    ["params"] = { -- up to 8 params 
    },
    ["default_midi_channel"] = 15
  },
```

# Sinfonion connect

_Experimental_

You will need to mod your norns to do this. I only recommend this on a norns shield. This mod is _at your own risk_.

The sinfonion expects an inverted serial signal for it's sync function. This means you'll need to wire up a simple NOT gate. Don't worry - it's not as scary as it sounds. I did this with some strip board. 

- First, connect your norns Raspberry PI's UART0 TX (pin 8, there's a convenient TX pad on the norns shield PCB) first to a 1K Resister and then on to the middle pin on a 2N3904 transistor. 
- Now connect the top pin of your 2N3904 to a 3K resistor then on to power (pin 2) on your PI.
- Next also connect the top pin on your 2N3904 to the tip connector on a TS jack. 
- The sleeve connector of your TS jack connects to ground (there's a convenient ground pad on the norn's shield's PCB). 
- Now also connect the bottom pin of your 2N3904 to ground

![Inverter circuit digagram](/designs/Images/Sinfonion/inverter.png)

That's the hardware bit done. You now need to configure your norns.

SSH into your norns.

- `ssh we@norns`
- PW: `sleep`

Enter the raspi-config tool:

`sudo raspi-config`

Scroll down to `Interface Options`, then to `Serial Port`.

- Select `No` when it asks you `Would you like a login shell to be accessible over serial?`. 
- Select `Yes` when it asks `Would you like the serial port hardware to be enabled`

Click `Finish`. 

Reboot your norns.

Next: TBC

# Development

See https://trello.com/b/kMZ4qEhk/Mosaic for backlog. Please raise bugs and issues in Github.