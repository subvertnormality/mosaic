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
      - [Adding velocity](#adding-notes)
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
  * [Patterns](#pattern)
  * [Channels](#channel)
  * [Scales](#scale)
    + [Global scales](#global-scale-editor)
    + [Channel scales](#global-scale-editor)
  * [Devices](#device)
    + [Midi sound sources](#midi-sound-sources)
    + [Norns sound sources with n.b.](#norns-sound-sources-with-n-b)
  * [Merge modes](#channel)
  * [Song sequence](#song-sequence)
  * [Trig parameters](#trig-params)
  * [Trig locks](#trig-locks)
    + [Sequencer locks](#trig-locks)
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

ALM [Sinfonion connect](#sinfonion-connect) is supported via a simple hardware build. This allows you to sync up _Mosaic_'s quantisation with the Sinfonion Eurorack module.

### Midi device configuration

#### Stock devices

TODO 

#### Custom devices

TODO

#### Mods and software devices

TODO

## Typical workflow

### Getting around Mosaic

TODO

#### Grid menu navigation

TODO

#### Norns menu navigation

TODO

#### Sequencer start and stop

TODO

#### Midi panic

TODO


### Sound design

TODO

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
