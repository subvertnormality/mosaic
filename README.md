# Patterning

Welcome to *Patterning*.

*Patterning* is a grid-first deliberate generative sequencer that enables the quick creation of complex rhythms and tonal progressions. It uses sequencer techniques from the world of modular, Elektron, and monome together to create a powerful and unique sketching and composition workflow. A 128 grid is required.

At a glance, as of v0.1 patterning gives you the following:

- 16 channels that can each output triggers, notes, note length, velocity and CC to a single midi device
- 16 patterns that can be combined and mutated in different permutation to change their properties in very musical ways
- Song mode with 90 sequencer patterns
- A pattern editor that allows quick creation of trigger patterns using a DrumOps port, includes euclidean, tresillo function, drum preset banks, and NE Numeric Repetitor
- 8 assignable trig locks per channel
- Midi device templates including labelled trig destinations
- Per channel tempo and swing
- Per channel pattern length
- Channel muting
- Scales with root note and degree setting
- Trig lockable octave and scale select

## Core concepts

### Pattern

The pattern is a core entity in the world of *patterning*. It represents a sequence of 64 trigs, 64 note values, 64 velocity values, and length data associated to the trigs. Steps that do not have trigs can (and should) have note and velocity data assigned to them. Patterns are always 64 steps long.

Note data in patterning is decoupled from any one particular scale. Each note represents the position in the currently set scale as it's distance from the root. For example, if C major is selected, the root is C, the note one up from the root in the editor would be D, the note one down from the root is B and so on. It's not possible to select a note outside of the scale using the pattern editor (although we'll look at how accidentals are possible later).

### Channel

A channel is another core entity. Through a channel you determine what device is to be played an precisely what is going to be played. You select the channel's midi device, which midi output to use, what midi channel to use, and the trig locks and associated destinations within a channel. You also select which patterns you want to act through a channel. Each channel can have multiple patterns associated to it. Patterns can also be reused across multiple channels. Channels are monophonic, but multiple channels can output to the same midi device.

When two or more patterns are associated to a single channel, what happens when two trigs collide on a single step is determined by the channel's merge mode. There are multiple merge modes, each giving a slightly different behaviour. For this reason, it is desirable to have patterns that collide in interesting ways.

Channels can be clock divided and swung independently. Channels can also be set to length less than 64 steps for polyrhythmic fun.

### Sequencer Pattern

The sequencer pattern is the third core entity of patterning. It represents all channel and pattern data, including all trig locks, scale settings, merge mode settings, octave settings, etc for a 64 step sequence. There are 90 sequencer pattern slots in a *Patterning* scene. These slots can be chained to form a song.

Sequencer patterns can be set to lengths from 1 step to 64 steps. This applies to all channels.

### Scale

There are 16 scale slots per sequencer pattern. Each scale slot has a root note, a scale type (Dorian, Major, etc), and a degree setting. You can set a channel's default scale independently, set scale trig locks per channel, or you can set global scale trig locks that apply to all channels if there is no channel-specific trig lock in action. In this way, you can create complex chord progressions.

### Device

A device represents a midi device in your studio. It is made up of metadata, the most important being midi destinations, device name, CC midi destinations. There are some present device templates and trig lock destinations can be either set manually on norns, or configured via a configuration file.

## Pages

Patterning is made up of 5 pages. Each page has a grid UI and a set of configuration options on the norns device. It is designed to be grid first. You use the norns to set a few basics up such as scales, midi devices and outputs, and then you stick to the grid to create the music.

### Menu

The menu at the bottom of the grid allows you to select the current page using the first five buttons. These are consistent across all pages. There are also page-context sensitive functions to the right.
 
![The menu as shown on the pattern edit page](/designs/Images/menu.png)

From left to right, the buttons select the:

* Channel editor
* Song editor
* Trig editor (selected here)
* Note editor
* Velocity editor

### Trig editor

The trig editor is where you create your trig patterns using _Patterning_'s DrumOp tools. Here you create your patterns and assign length data to each step. The following image shows the trig editor with a complex pattern made up of trigs and length data.

![Trig editor with a complex trig pattern](/designs/Images/trig_editor.png)

Using the top row you select one of 16 patterns. The image shows pattern 2 as being selected.

![Pattern select buttons](/designs/Images/trig_editor_pattern_select.png)

You can tap in individual trig data on the sequencer. The brightly lit steps represent a trig. You can  enter length data by holding a trig and selecting the desired last step of the length. Length data is shown as dimly lit. Patterns are monophonic. The length of a trig will end when it encounters another trig.

![Trig sequencer](/designs/Images/trig_editor_sequencer.png)

Trig patterns can be created using a number of in-built algorithms, selected using the buttons shown here.

![Algorithm select](/designs/Images/trig_editor_algorithms.png)

* Button 1 selects the drum algorithm. This uses preset banks of drum patterns for traditional beats.
* Button 2 selects the tresillo algorithm. This uses a 3/3/2 ratio to create varations on the preset drum banks.
* Button 3 selects euclidian, a powerful mathmatic based rhythm tool.
* Button 4 selects NE Numeric Repitor, another powerful mathmatic based ryhthm tool.

The grid is context aware. Different algorithms have different options associated with them. These controls change the parameters of the different algorithms. You can press on a grid key and usually a tooltip will be shown on the norns screen describing it's function.

The faders to the left select values within the algorithm. If the end buttons of the faders a brightly lit, these select fine-grain values within the fader. The dimly lit buttons select course grain values within the fader.

The fader to the right generally selects banks within the algorithm.

![Algorithm controls](/designs/Images/trig_editor_algorithm_controls.png)

To view the effect of the currently selected algorithm, you must press the prime button. This primes a new pattern ready to paint onto the sequencer. The sequencer shows the new steps as bright blinking lights. Whilst the steps are blinking, they are not painted. If a step is already active, it is shown as dimly blinking. Painting the new pattern will deactive existing, dimly blinking steps. This way your patterns can be built into super complex and unusual sequences that are always rooted in established rythmic theory. 

Whilst the new pattern has not been painted, the prime button will blink. Press it again to apply your changes. Tip: If you press the prime button again without changing the algorithm or algoithm parameters, you can apply the changes again to undo the last paint.

![Prime and print button](/designs/Images/trig_editor_prime_and_print.png)

You can cancel a primed pattern using the cancel button.

![Cancel button](/designs/Images/trig_editor_cancel.png)

Whilst a new pattern is primed, you can move it left or right using the move controls. The first button moves left, the third moves right, and the centre button returns the pattern to it's original position. Don't forget to paint.

![Left, centre, right buttons](/designs/Images/trig_editor_left_right.png)

### Note editor

TODO

### Velocity editor

TODO

### Channel editor

TODO

### Song editor

TODO

# Development

See https://trello.com/b/kMZ4qEhk/patterning for backlog. Please raise bugs and issues in Github.