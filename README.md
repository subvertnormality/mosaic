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

You can customise _Mosaic_ to fit your studio set up precisely using custom device configuration. If your desired device isn't included in the stock config folder, simply create a .json file named after your device, and fill in the template using your device's midi spec. If copying the below code, you must exclude all text appearing after "//"

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

#### Mods and software devices

It is possible to use internal Norns sound sources, utilise Crow and it's i2c related ecosystem such as Just Friends and Ansible by installing [n.b.](https://github.com/sixolet/nb/) mods. These appear in _Mosaic_'s device list when the mod is installed and enabled in the Norns setting menu. The n.b. mod must be in the allow list before it can be used with _Mosaic_. The follow mods are currently supported:

* [nb_ansible](https://github.com/sixolet/nb_ansible) - Ansible voices.
* [emplaitress](https://github.com/sixolet/emplaitress) - Gives four MI Plaits to use in parallel.
* [nb_jf](https://github.com/sixolet/nb_jf) - Provide access to Just Friends. Has multiple voice modes — individual mono voice (with slew), polysynth, kit, and unison mode.
* [nb_crow](https://github.com/sixolet/nb_crow) - Crow v/8 and envelope.

More to come soon!

## Typical workflow

Were we walk you through _Mosaic_'s functionality and basic operations by describing a typical workflow for creating a song.

### Getting around Mosaic

#### Grid menu navigation

The majority of navigation happens on the grid. The lower left five buttons at the main manu buttons. From left to right, you can navigate to the "[Channels](#channel)", "[Song sequence](#song-sequence) page", "[Pattern](#pattern) editor", "[Notes](#adding-notes) page", and "[Velocity](#adding-velocity) page".

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

The first step we typically undertake when creating a song is to create the fundamental elements of the song from a sound design basis. These initial attempts at sound design are unlikely to remain unchanged until the end of the song creation process, but they will provide a base from which to start sketching out the rhythmic, harmonic, and melodic elements of your composition.

We begin by identifying the device we wish to use for certain elements. This could be an internal Norns player device, or perhaps an external drum machine, or elements of a modular patch. Whichever it may be, you need assign the device to a _Mosaic_ [channel](#channel). See the [device](#device) section for details on how to do this. You will find it helpful to group different instrumentation elements together. For example, we keep drums grouped to channels 1-6, harmonic and textural elements to channels 7-10, Melodic elements to 11-14, and reserve 15 and 16 for modulation channels. Whatever works for your specific song and music style is fine, of course.

Once you have a selection of devices assigned to multiple channels, it's time to move onto the first part of the composition process.



### Harmony design

TODO

### Rhythm design

TODO

#### Adding trigs

TODO

#### Adding notes

TODO

#### Adding velocity

TODO

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
