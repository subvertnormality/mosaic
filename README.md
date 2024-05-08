Welcome to Mosaic, an intuitive XoX-style midi sequencer for Monome Norns and Grid. It melds the powerful features of the Elektron sequencer with innovative generative techniques, all within the Monome ecosystem, allowing you to craft complex rhythms and harmonies with ease. Whether you are sketching or composing, Mosaic provides a unique, deep musical experience.

- [Getting started](#mosaic)
  * [Install](#install)
  * [Set up](#set-up)
    + [Hardware](#hardware)
    + [Device configuration](#device-configuration)
      - [Stock devices](#stock-devices)
      - [Custom devices](#custom-devices)
      - [Mods and software devices](#mods-and-software-devices)
  * [Typical workflow](#typical-workflow)
    + [Basic operation](#getting-around-mosaic)
      - [Grid menu navigation](#grid-menu-navigation)
      - [Norns menu navigation](#norns-menu-navigation)
      - [Sequencer start and stop](#sequencer-start-and-stop)
      - [Midi panic](#midi-panic)
    + [Sound design](#sound-design)
    + [Chord progression design](#harmony-design)
    + [Rhythm section design](#pattern-design)
      - [Adding trigs](#adding-trigs)
      - [Adding notes](#adding-notes)
      - [Adding velocity](#adding-velocity)
    + [Harmony composition](#rhythm-and-harmony-composition)
      - [Adding patterns to channels](#adding-patterns-to-channels)
      - [Using merge modes](#using-merge-modes)
      - [Adding chords](#adding-chords)
    + [Melody composition](#melody-composition)
      - [Adding melodic notes over harmony and drums](#adding-melodic-notes-over-harmony-and-drums)
      - [Midi input](#midi-input)
    + [Modulation, movement and interest](#modulation-movement-and-interest)
    + [Song composition](#song-composition)
    + [Save and load](#save-and-load)
- [Core concepts](#core-concepts)
  * [Pattern](#pattern)
  * [Channel](#channel)
  * [Scale](#scale)
    + [Global scale](#global-scale-editor)
    + [Channel scale](#global-scale-editor)
  * [Device](#device)
    + [Midi sound sources](#midi-sound-sources)
    + [Norns sound sources with n.b.](#norns-sound-sources-with-n-b)
  * [Merge mode](#channel)
  * [Song sequence](#song-sequence)
  * [Trig parameter](#trig-params)
  * [Trig lock](#trig-locks)
    + [Sequencer lock](#trig-locks)
      - [Probability](#probability)
      - [Fixed note](#fixed-note)
      - [Quantised fixed note](#quantised-fixed-note)
      - [Random note](#random-note)
      - [Random twos note](#random-twos-note)
      - [Chord notes](#chord-notes)
      - [Chord strum](#chord-strum)
    + [Midi locks](#trig-locks)
    + [Scale locks](#scale-locks)
    + [Octave locks](#octave-locks)
  * [Options](#options)
    + [Elektron sync](#elektron-sync)
    + [Sinfonion connect](#sinfonion-connect)
- [Development](#development)
- [Device config template](#device-config-template)



# Getting started

## Install

To install, simply run `;install https://github.com/subvertnormality/mosaic` in maiden.

## Setup

### Hardware

_Mosaic_ requires Monome Norns and a 128 Grid as a minimum. You can create simple songs with just these two, but external sound sources are strongly encouraged to get the most out of the sequencing possibilities. You'll need a midi interface to do this. All sound sources with midi input are supported, but those that have stock or manually created config files will work best. Crow, Just Friends and Ansible work out of the box using [n.b.](https://github.com/sixolet/nb/). You can use Norns to generate sounds by installing [n.b.](https://github.com/sixolet/nb/) mods. The list of currently supported mods can be seen in the [Norns sound sources with n.b.](#norns-sound-sources-with-n-b) section.

[Midi input](#midi-input) devices make the experience smoother, but aren't mandetory. A midi keyboard will make melody creation easier, and a midi controller with encoders that support relative bin offsets makes the data input process nicer.

ACL [Sinfonion connect](#sinfonion-connect) is supported via a simple hardware build. This allows you to sync up _Mosaic_'s quantisation with the Sinfonion Eurorack module.

### Midi device configuration

#### Stock devices

TODO 

#### Custom devices

You can customise _Mosaic_ to fit your studio set up precisely using custom device configuration. If your desired device isn't included in the stock config folder, simply create a .json file named after your device, and fill in a [device config template](#device-config-template) following your device's midi spec. 

#### Mods and software devices

It is possible to use internal Norns sound sources and utilise Crow, and use Just Friends and Ansible via i2c, by installing [n.b.](https://github.com/sixolet/nb/) mods. These appear in _Mosaic_'s device list when the mod is installed and enabled in the Norns setting menu. The n.b. mod must be in the allow list before it can be used with _Mosaic_. The follow mods are currently supported:

* [nb_ansible](https://github.com/sixolet/nb_ansible) - Ansible voices.
* [emplaitress](https://github.com/sixolet/emplaitress) - Gives four MI Plaits to use in parallel.
* [nb_jf](https://github.com/sixolet/nb_jf) - Provide access to Just Friends. Has multiple voice modes — individual mono voice (with slew), polysynth, kit, and unison mode.
* [nb_crow](https://github.com/sixolet/nb_crow) - Crow v/8 and envelope.

More to come soon!

## Typical workflow

Were we walk you through _Mosaic_'s functionality and basic operations by describing a typical workflow for creating a song.

### Getting around Mosaic

#### Grid menu navigation

The majority of navigation happens on the grid. The lower left five buttons are the main manu buttons. From left to right, you can navigate to the "[Channels](#channel)", "[Song sequence](#song-sequence) page", "[Pattern](#pattern) editor", "[Notes](#adding-notes) page", and "[Velocity](#adding-velocity) page".

[TODO: image of the grid outlining the navigation button section]

#### Norns menu navigation

Each grid page has a set of pages represented on the Norns screen. The settings in these pages are designed to be set and forget, where possible. The pages can be navigated left and right using the [TODO] knob, and the various settings can be navigated vertically using the [TODO] knob.

[TODO: image of norns device, with knobs highlighted for functionality]

#### Sequencer start and stop

To start the sequencer simply hit the navigation button of the currently selected page - the lit button - in the navigation section.

To stop the sequencer, hold down the currently selected page in the navigation section for a second.

#### Midi panic

In the event you midi output devices get stuck, you can clear all midi-on events by holding down the currently selected page in the navigation section, whilst also pressing a non-selected page in the navigation section. This will send a stop event to all devices, on all channels, for all notes. 


### Sound design

The first step we typically undertake is to create a few basic voices. These initial attempts at sound design are unlikely to remain unchanged until the end of the song creation process, but they will provide a base from which to start sketching out the rhythmic, harmonic, and melodic elements of your composition.

We begin by identifying the device we wish to use for certain elements. This could be an internal Norns player device, or perhaps an external drum machine, or elements of a modular patch. Whichever it may be, you need assign the device to a _Mosaic_ [channel](#channel). See the [device](#device) section for details on how to do this. You will find it helpful to group different instrumentation elements together. For example, we keep drums grouped to channels 1-6, harmonic and textural elements to channels 7-10, Melodic elements to 11-14, and reserve 15 and 16 for modulation channels. Whatever works for your specific song and music style is fine, of course.

Once you have a selection of devices assigned to multiple channels, it's time to move onto the first part of the composition process.


### Rhythm design

Rhythm is composed using the [Pattern](#pattern) editor, accessed by pressing the third button in the main menu button cluster, bottom left of your grid. The pattern is a core concept in Mosaic. Think of it as a sequence of 64 trigs, 64 notes, 64 velocities, and length data for each trig. Each pattern spans 64 steps.

The pattern editor gives you multiple tools to create complex rhythms. It's possible to manually enter trigs XOX style. Alternatively, you can select a pattern from banks of predefined bass, snare, and high hat patterns. If this isn't what you need, you can use eclidian patterns or patterns from noise engineering's Numeric Repetitor. Still not complex enough? You can mix up any of these patterns using a tresillo modifier, which utilises a 3-3-2 repeating pattern to spice up any rhythm. You can mix and match all of these types of rhythms using by selecting and "painting" them onto the grid.

#### Adding trigs

Trigs are added in the pattern editor.

![Trig editor with a complex trig pattern](https://github.com/subvertnormality/mosaic/raw/main/designs/Images/trig_editor.png)

With the top row, pick one of the 16 patterns available. In the image, you can see pattern 2 is selected.

![Pattern select buttons](https://github.com/subvertnormality/mosaic/raw/main/designs/Images/trig_editor_pattern_select.png)

To set your rhythm, simply tap in steps using the sequencer. Bright steps symbolise a trig. To define its length, press and hold a trig, then choose its ending step. Steps with a subtle glow show the length. In a single pattern, one trig’s duration ends upon meeting another.

![Trig sequencer](https://github.com/subvertnormality/mosaic/raw/main/designs/Images/trig_editor_sequencer.png)

Craft unique rhythms using a variety of built-in algorithms.

* button 1: The drum algorithm, drawing from a rich collection of classic drum patterns.
* button 2: The tresillo algorithm, utilising a 3/3/2 ratio for diverse rhythm variations. The tresillo multiplier can be set on the norns screen for more variations.
* button 3: Euclidian, a rhythm tool rooted in mathematical logic.
* button 4: NE Numeric Repetitor, another rhythm tool based on mathematical principles.

![Algorithm select](https://github.com/subvertnormality/mosaic/raw/main/designs/Images/trig_editor_algorithms.png)

The grid is intuitive and adapts to your choices. Each algorithm brings its set of options, and pressing on a grid key typically displays its function on the norns screen.

The left side faders adjust algorithm values. Brightly lit ends refine values, while the dimmer ones adjust them broadly. The rightmost fader typically toggles between different algorithm banks.

![Algorithm controls](https://github.com/subvertnormality/mosaic/raw/main/designs/Images/trig_editor_algorithm_controls.png)

To see your algorithm's impact, hit the prime button. This prepares a new pattern, and new steps are showcased as flashing bright steps on the sequencer. While these steps flash, they aren’t painted yet. Any step that would be painted over an existing active step will blink dimly. By painting the new pattern, you'll deactivate the faintly blinking steps. This approach lets you craft intricate sequences, grounded in rhythmic fundamentals, that don't get too busy. You can modify algorithm parameters whilst the pattern is primed.

If you haven’t painted the new pattern, the prime button continues to blink. Pressing it again paints your edits. Double-pressing the prime button without tweaking the algorithm or its parameters acts as an undo for the last action.

![Prime and print button](https://github.com/subvertnormality/mosaic/raw/main/designs/Images/trig_editor_prime_and_print.png)

Opt out of a prepared pattern by using the cancel button.

![Cancel button](https://github.com/subvertnormality/mosaic/raw/main/designs/Images/trig_editor_cancel.png)

While previewing a new pattern, use the move controls to shift its position. The first button shifts it left, the third to the right, and the centre button resets it. Remember to paint your changes.

![Left, centre, right buttons](https://github.com/subvertnormality/mosaic/raw/main/designs/Images/trig_editor_left_right.png)

On the norns screen, you can see the selected channel's grid state on page 1. This is the merged version of the channel and is a useful context for editing your pattern. Use E2 to select channels.

![Channel grid viewer](https://github.com/subvertnormality/mosaic/raw/main/designs/Images/UI/trig_edit_grid_viewer.png)

On page 2 you can select trig editor options. Currently this allows you to edit the tresillo multiplier in use. Experiment with different values to get wildly different results with the tresillo algorithm.

![Channel grid viewer](https://github.com/subvertnormality/mosaic/raw/main/designs/Images/UI/trig_edit_options.png)

#### Adding notes

In _Mosaic_, notes aren't strictly bound to a single scale. Instead, they are valued by their position within the currently active scale, measured by distance from the root. Take C major for instance: C is your starting point. One step up brings you to D, and one step down lands on B. If you were to change the applied scale to E minor, the root of your pattern would now be E, one step up would output F sharp, one down would be D. 

You'll see in the [Harmony design](#harmony-design) section that it's possible to sequence scale and degree changes, and this affects the notes your patterns will play. When adding notes to patterns, consider that they represent the harmony of your song and map to what traditionally would be called the rhythm section. It is possible to create melodies using patterns, but it is difficult to do so in a deliberate way as your scale progressions will alter the tonality of your pattern. We'll learn about the recommended way to deliberate [melodies](#melody-composition) later. 

Select the note edtior by pressing the fourth key in the main menu button cluster on the grid. 

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

#### Adding velocity

Now let's look at the velocity editor, which functions similarly to the note page. Access it by pressing the fifth button in the main menu cluster.

The velocity editor spans two vertical pages: the first displays velocities from 127 down to 67, while the second displays values between 58 and 0. Adjust these to fine-tune the dynamics of your sequence.

On the norns screen you can see the channel grid visualiser. Use E2 to select the current channel.

### Harmony design

Each project offers 16 scale slots. A single slot has a root note, a scale variation (e.g. Dorian, Major, etc), a degree setting, and a scale rotation.

TODO

This flexibility paves the way for intricate chord progressions and the ability to add variation to patterns.

### Rhythm and harmony composition

TODO

#### Adding patterns to channels

TODO

#### Using merge modes

TODO

### Melody composition

TODO

#### Adding melodic notes over harmony and drums

TODO

#### Adding chords

TODO

#### Midi input

TODO

### Modulation, movement and interest

TODO

#### Sequencer trig locks

TODO

### Song composition

TODO

### Save and load

TODO

## Core concepts

TODO

### Patterns

TODO

### Channels

TODO

### Scales

TODO

#### Global scales

TODO

#### Channel scales

TODO

### Devices

TODO

#### Midi sound sources

TODO

#### Norns sound sources with n.b.

TODO

### Merge modes

TODO

### Song sequence

TODO

### Trig parameters

TODO

### Trig locks

TODO

### Sequencer locks

TODO

#### Probability

TODO

#### Fixed note

TODO

#### Quantised fixed note

TODO

#### Random note

TODO

#### Random twos note

TODO

#### Chord notes

TODO

#### Chord strum

TODO

### Midi locks

TODO

### Scale locks

TODO

### Octave locks

TODO

### Options

TODO

#### Elektron sync

TODO

#### Sinfonion connect

TODO

## Development

TODO

## Device config template

If copying the below code, you must exclude all text appearing after "//"

```javascript
[{
  "params": [
    {
      "cc_msb": 7, // the midi cc number to send the command on.
      "name": "Level", // the name representing this param.
      "cc_max_value": 127, // the maximum value that can be sent over midi.
      "short_descriptor_1": "AMP", // the label that identifies the trigger param in _Mosaic_ at the top of the dial.
      "short_descriptor_2": "LVL", // the label that identifies the trigger param in _Mosaic_ at the bottom of the dial.
      "id": "level", // the unique ID of the param
      "off_value": -1, // the value that determines when the param is off, usually -1
      "cc_min_value": -1 //-- the lower value of the midi param, usually -1
    },
    { // here a specially sequencer param "fixed note" is used to lock the note to a certain midi note value, which is useful for some drum devices in combination with "maps_params_automatically".
      "short_descriptor_2": "NOTE",
      "name": "Fixed Note",
      "cc_max_value": 127,
      "default": 36, // the midi device will only send out the value 36, regardless of note assignment
      "cc_min_value": -1,
      "short_descriptor_1": "FIXD",
      "off_value": -1,
      "id": "fixed_note" -- this identifies the param as a special "fixed note" sequencer trig param
    }
  ],
  "type": "midi", // mandetory: leave as midi for custom devices.
  "unique": true, // mandetory: true if you only allow one instance of this device in use at one time, false allows multiple instances.
  "map_params_automatically": true, // mandetory: when true, the first 10 params are mapped and assigned on the device's channel trig parameters.
  "polyphonic": false, // mandetory: true if more than one note can be played at once on the device.
  "value": 8, // mandetory: arbitrary value, choose any number.
  "default_midi_device": 1, // optional: use this to set a default midi output device. When in use it will no longer be possible to change the output device in _Mosiac_.
  "default_midi_channel": 10, // optional: use this to set a default midi output channel. When in use it will no longer be possible to change the output channel in _Mosaic_.
  "name": "Your device", // mandetory: the name used to identify the device _Mosaic_.
  "id": "a-unique-id" // mandetory: the ID used to identify the device _Mosaic_. Must be unique.

}]
```