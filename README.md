Welcome to Mosaic, an intuitive XoX-style MIDI sequencer for Monome Norns and Grid. It melds the powerful features of the Elektron sequencer with innovative generative techniques, all within the Monome ecosystem, and allows you to craft complex rhythms and harmonies with ease. Whether you are sketching or composing, Mosaic provides a unique, deep musical experience. 

- [Getting Started](#getting-started)
  * [Install](#install)
  * [Setup](#setup)
    + [Hardware](#hardware)
    + [MIDI Device Configuration](#midi-device-configuration)
      - [Stock Devices](#stock-devices)
      - [Custom Devices](#custom-devices)
      - [Mods and Software Devices](#mods-and-software-devices)
  * [Typical Workflow](#typical-workflow)
    + [Getting Around Mosaic](#getting-around-mosaic)
      - [Grid Menu Navigation](#grid-menu-navigation)
      - [Norns Menu Navigation](#norns-menu-navigation)
      - [Tooltips](#tooltips)
      - [Sequencer Start and Stop](#sequencer-start-and-stop)
      - [Long Press Shortcut](#long-press-shortct)
      - [MIDI Panic](#midi-panic)
    + [Sound Design](#sound-design)
    + [Rhythm Section Design](#rhythm-section-design)
    + [Harmony Design](#harmony-design)
    + [Sequence Composition](#sequence-composition)
      - [Using Merge Modes](#using-merge-modes)
      - [Melody Composition](#melody-composition)
    + [Modulation, Movement, and Interest](#modulation-movement-and-interest)
    + [Song Composition](#song-composition)
- [Dig Deeper](#dig-deeper)
  * [Pattern Editor](#pattern-editor)
      - [Adding Trigs](#adding-trigs)
      - [Adding Notes](#adding-notes)
      - [Adding Velocity](#adding-velocity)
  * [Channel Editor](#channel-editor)
    + [Adding Patterns to Channels](#adding-patterns-to-channels)
    + [Masks](#masks)
      - [Adding Melodic Notes over Harmony and Drums](#adding-melodic-notes-over-harmony-and-drums)
      - [Adding Chords](#adding-chords)
      - [MIDI Input](#midi-input)
    + [Merge Modes](#merge-modes)
      - [Trig Merge Modes](#trig-merge-modes)
      - [Note Merge Modes](#note-merge-modes)
      - [Velocity Merge Modes](#velocity-merge-modes)
      - [Length Merge Modes](#length-merge-modes)
    + [Scale Editor](#scale-editor)
      - [Transposition](#transposition)
    + [Note Dashboard](#note-dashboard)
    + [Clocks, Swing and Shuffle](#clocks-swing-and-shuffle)
    + [Channel Length](#channel-length)
    + [Muting Channels](#muting-channels)
    + [Devices](#devices)
      - [MIDI Sound Sources](#midi-sound-sources)
      - [Norns Sound Sources with n.b.](#norns-sound-sources-with-nb)
      - [Device Parameters](#device-parameters)
    + [Trig Parameters](#trig-parameters)
      - [Sequencer Params](#sequencer-params)
        + [Trig Probability](#trig-probability)
        + [Fixed Note](#fixed-note)
        + [Quantized Fixed Note](#quantized-fixed-note)
        + [Random Note](#random-note)
        + [Random Twos Note](#random-twos-note)
        + [Chord Strum](#chord-strum)
        + [Chord Arpeggio](#chord-arpeggio)
        + [Chord Acceleration](#chord-acceleration)
        + [Chord Spread](#chord-spread)
        + [Chord Velocity Modifier](#chord-velocity-modifier)
        + [Chord Shape Modifier](#chord-shape-modifier)
      - [Locks](#locks)
        + [Trig Param Locks](#trig-param-locks)
        + [Scale Locks](#scale-locks)
        + [Transposition Locks](#transposition-locks)
        + [Octave Locks](#octave-locks)
  * [Song Sequencer](#song-sequencer)
    + [Button Indicators](#button-indicators)
    + [Interacting with Slots](#interacting-with-slots)
    + [Song Mode Operations](#song-mode-operations)
    + [Adjusting Song Sequence Length](#adjusting-song-sequence-length)
    + [Navigating the Norns Display](#navigating-the-norns-display)
  * [Save and Load](#save-and-load)
  * [Options](#options)
    + [Sequencer Options](#sequencer-options)
      - [Song Mode](#song-mode)
      - [Reset at Sequence End](#reset-at-sequence-end)
      - [Reset at Seq Pattern End](#reset-at-seq-pattern-end)
      - [Elektron Program Changes](#elektron-program-changes)
      - [Elektron Program Change Channel](#elektron-program-change-channel)
    + [Parameter Lock Options](#parameter-lock-options)
      - [Trigless Locks](#trigless-locks)
    + [Quantizer Options](#quantizer-options)
      - [Quantize Note Masks](#quantize-note-masks)
      - [Scales Lock Until Ptn End](#scales-lock-until-ptn-end)
      - [Lock All to Pentatonic](#lock-all-to-pentatonic)
      - [Lock Random to Pentatonic](#lock-random-to-pentatonic)
      - [Lock Merged to Pentatonic](#lock-merged-to-pentatonic)
    + [MIDI Controller Options](#midi-controller-options)
      - [Map Scale to White Keys](#map-scale-to-white-keys)
      - [Honor Scale Rotations](#honor-scale-rotations)
      - [Honor Scale Degree](#honor-scale-degree)
  * [Sinfonion Connect](#sinfonion-connect)
- [Development](#development)
- [Device Config Template](#device-config-template)

## Getting Started

### Install

To install, simply run `;install https://github.com/subvertnormality/mosaic` in maiden.

### Setup

#### Hardware

_Mosaic_ operates with the Monome Norns and a 128 Grid at a minimum. These two components alone will allow you to create simple songs, but incorporating external sound sources via a MIDI interface will vastly expand your sequencing capabilities. Devices with MIDI in are all supported, although those set up in _Mosaic_ using pre-existing or manually created configuration files are optimal. Crow, Just Friends, and Ansible are natively supported using [n.b.](https://github.com/sixolet/nb/).

Using [MIDI input](#midi-input) devices, while not essential, enhances the user experience. A MIDI keyboard simplifies melody creation, and a MIDI controller with encoders supporting relative bin offsets can improve the data input process.

For those using an ACL Sinfonion, support is available through a straightforward [hardware build](#sinfonion-connect). This setup allows synchronization between Mosaic's quantization and the Sinfonion Eurorack module.

#### MIDI Device Configuration

##### Stock Devices

Mosaic includes a range of stock devices that you can integrate into your setup, but first, they need to be configured to appear in the device selector. Here’s how to set this up using [maiden](https://monome.org/docs/norns/maiden/):

1. **Access Configuration Files**: Open Maiden and navigate to the directory path `code > mosaic > lib > config`. Here, you will find the stock device configuration files.
2. **Create a New Configuration Folder**: Next, go to the directory `data > mosaic`. In this location, create a new folder named `config`.
3. **Copy Configuration Files**: Copy the device configuration files that you wish to use from `code > mosaic > lib > config` into the `data > mosaic > config` folder you just created.
4. Once these steps are completed, Mosaic will automatically load the device configurations you've selected, and they will be available in the device picker on the channel page.

This setup ensures that you can easily access and use your preferred stock devices within Mosaic.

##### Custom Devices

Once you've copied the stock device configuration files into the `data > mosaic > config` folder, you can also personalize these configurations to better suit your setup. This is particularly useful for setting common defaults like the MIDI output device.

You can customize Mosaic to perfectly align with your studio setup by configuring it to work seamlessly with your specific devices. If your device is not included in the standard configuration, create a .json file named after your device in the `dust > mosaic > config` folder. Populate this file using a [device config template](#device-config-template) that matches your device’s MIDI specifications.

##### Mods and Software Devices

Mosaic can also use internal Norns sound sources and manage devices like Crow, Just Friends, and Ansible via i2c by installing [n.b.](https://github.com/sixolet/nb/) mods. These mods will appear in Mosaic's device list once installed and activated in the Norns settings menu. Ensure the n.b. mod is on the allow list to use with Mosaic. See [Norns sound sources with n.b.](#norns-sound-sources-with-nb) for more information.

## Typical Workflow

This section provides an overview of Mosaic's functionality and basic operations, outlining a typical workflow for song creation. Here, we present a broad perspective without going into the operational specifics. For more detailed information on navigating through the user interface, understanding precise functionalities, exploring options, and more, please refer to the [Dig Deeper](#dig-deeper) section. This should allow you to grasp the essential processes first, setting a solid foundation for more advanced exploration later.

### Getting Around Mosaic

#### Grid Menu Navigation

Navigation within Mosaic primarily occurs via the Grid. The lower left five buttons serve as the global menu buttons. From left to right, these buttons allow access to the "[Channel](#channel-editor) page", "[Song Sequencer](#song-sequencer) page", "[Pattern](#pattern-editor) editor", "[Notes](#adding-notes) page", and "[Velocity](#adding-velocity) page".

![The menu as shown on the pattern edit page](https://raw.githubusercontent.com/subvertnormality/mosaic/main/designs/Images/menu.png)

#### Norns Menu Navigation

Further configuration happens on Norns. Each grid page corresponds to several grouped pages on the screen. Settings in these pages are typically set once and require minimal adjustments. Navigation through these pages is accomplished by moving left and right with the E1 encoder, the selected setting can be chosen using the E2 encoder, and the value of the settings can be adjusted by moving up and down with the E3 encoder. Some settings require a confirmation before they are set. Press the K3 button to apply any selected changes. If you navigate away from the page without applying, the change will be cancelled.

For a detailed reference on the layout of your Norns device, consult the official [Norns documentation](https://monome.org/docs/norns/).

#### Tooltips

Most _Mosaic_ functions are described by tooltips that appear at the bottom of the Norns screen when activated. If you're not sure what a button does, try pressing it and watching out for the tooltip.

#### Sequencer Start and Stop

To start the sequencer, press the global menu button of the currently selected page — the illuminated button — in the navigation section.

To stop the sequencer, hold down the global menu button of the currently selected page for around a second.

#### Long Press Shortcut

Hold K2 whilst performing grid functions to turn long press functions into a single press. For example, you can stop the sequencer immediately by holding K2 and pressing the navigation button of the currently selected page. You can mute an unmute tracks straight away by holding K2 and pressing a channel button.

#### MIDI Panic

Should your MIDI output devices become unresponsive, you can clear all MIDI-on events by holding down the navigation button of the currently selected page while pressing a non-selected navigation button. This action will send a stop signal to all devices, on all channels, for all notes.

### Sound Design

The initial stage of song creation with _Mosaic_ involves setting up a few basic voices. These preliminary sound designs may evolve, but it's useful to have a basic foundation for developing the rhythmic, harmonic, and melodic aspects of your track.

Start by selecting the device for each element of your composition, whether it be an internal Norns player, an external drum machine or synthesizer, or components of a modular patch. To do this, assign each device to a Mosaic [channel](#channel-editor) as detailed in the [device](#devices) section. Organizing different instruments can be helpful; for instance, group drums on channels 1-6, harmonic and textural elements on channels 7-10, melodic elements on channels 11-14, and reserve channels 15 and 16 for modulation. Adapt these assignments to suit your specific musical style and needs.

With your devices assigned, you're ready to begin the rhythm and harmony design process.

### Rhythm Section Design

The rhythm of your track is crafted using the [pattern editor](#pattern-editor), accessible by pressing the third button in the global menu cluster located at the bottom left of your grid. A pattern in Mosaic is defined as a sequence composed of 64 steps with trigs, notes, velocities, and duration data. Patterns are the building blocks of your rhythm section.

The pattern editor provides multiple tools to create these building blocks. You can input trigs manually in an XOX style, or choose from predefined banks featuring bass, snare, and hi-hat patterns. For more complex needs, explore using Euclidean patterns or patterns from Noise Engineering's Numeric Repetitor. To add unique rhythmic variations, apply a tresillo modifier, which introduces a 3-3-2 repeating pattern. These rhythm types can be blended by selecting and "painting" them onto the grid. It's possible to paint more than one pattern at a time, and then edit further to taste XOX style. To learn more about this process, refer to the [Adding Trigs](#adding-trigs) section.

After establishing a pattern of trigs, assign relative [notes](#adding-notes) and [velocity](#adding-velocity) data. These patterns will later be merged and remixed to form your rhythm and harmony sections.

### Harmony Design

_Mosaic_'s harmony tools enable you to compose your song's chordal progressions. These progressions can dynamically modulate your patterns, allowing for the creation of complex harmonic sequences with minimal music theory knowledge.

Harmonic progressions can be applied globally — modulating all notes across all channels to the same key, degree, and scale rotation — or on a per-channel basis, affecting only the notes within that channel. This decoupling of patterns and notes from the active scale enables dynamic and experimental tonal modulations. For example, setting your global scale to change in a polyrhythmic pattern relative to your channel's note data can create captivating musical textures.

Each project supports 16 scale slots. Each slot includes a root note, a scale type (e.g., Dorian, Major), a degree, and a scale rotation. The [Scale Editor](#scale-editor) is where you craft the scales that will form your chord progressions, and you can sequence these using [Scale Locks](#scale-locks) either globally from the scale editor, or per channel using the channel editor.

### Sequence Composition

At this point you will have a set of sound sources attached to a number of channels, a set of patterns with relative notes, trigs, velocities, and lengths, and a set of scales that work well together - possibly assigned as either a global scale or a set of trig locks on the global scale editor. Now it's time to compose your first sequence. The pattern tools offer the ability to craft intricate rhythmic and harmonic sections. However, the true heart of Mosaic is the [Channel Editor](##channel-editor). The channel editor is used to lay out your harmonic and rhythm sections by [adding patterns to channels](#adding-patterns-to-channels).

#### Using Merge Modes

When assigning multiple patterns to a single channel, you might notice that overlapping steps in different patterns deactivate. This occurs because the default "skip" merge mode is active. [Merge Modes](#merge-mode) control the behavior of these overlaps, allowing patterns to be combined in different combinations across multiple channels whilst interacting in harmonically meaningful ways. Experiment with different merge modes to explore various musical interactions.

#### Melody Composition

The [Channel Editor](##channel-editor) doesn't merely allow you to add, merge, and apply scales to patterns; it enables you to enhance them with melodies and other elements to further enrich your music. In fact, you could compose entire songs using just the channel editor if you wanted to, thanks to [Masks](#masks). Masks provide a direct method to input triggers, notes, velocities, and chords right into the channel editor grid, giving you precise control over your musical creations. You can overwrite pattern values or create entirely new steps.

### Modulation, Movement, and Interest

Even a song crafted with compelling chord progressions, engaging rhythms, and striking melodies can sometimes sound flat when produced on electronic devices. The secret to invigorating such tracks lies in the addition of dynamics, movement, and interest, which is often achieved through thoughtful and abundant modulation. _Mosaic_ provides robust tools for modulation, including [Trig Parameters](#trig-parameters) and [Trig Locks](#trig-locks). "Trig lock" is a term borrowed from Elektron, referring to the ability to fix a parameter to a specific value at a certain step in the sequence. This feature allows you to control any MIDI device parameter, modulation parameter, the octave of a note, and even the scale to which the note is quantized, at each step, offering precise manipulation over the quality and dynamics of your music.

### Song Composition

At this point, your sequence is likely "full to the brim," containing all the elements of your song in its most complex form. For those familiar with Elektron devices, this stage can feel like a precarious juncture, where it's tempting to fall into a cycle of making minor adjustments to the same pattern repeatedly. _Mosaic_ offers a solution with its [Song Sequencer](#song-sequencer), designed to help you break free from this procrastination loop.

To access the song editor, press the second key in the global menu's Grid button cluster. You'll be greeted by a grid where the first button is dimly lit, indicating the sequence you are currently working on. The song editor allows you to take this sequence and creatively manipulate it: you can mute channels, modify scale locks, alter pattern combinations and merge modes, adjust masks, and more. This flexibility enables you to develop your composition from the base sequence upwards. As you become accustomed to this workflow, you'll find that you can construct an entire song from a single sequence, streamlining your creative process.

## Dig Deeper

Now that you have a grasp of the basic workflow, we'll dig into the more advanced functionalities of _Mosaic_. This section will explore the deeper capabilities and features that allow for sophisticated manipulation and fine-tuning of your music, enabling you to fully harness the potential of this powerful sequencer.

### Pattern Editor

Patterns serve as the foundational elements of your harmony and rhythm sections. You start by creating a set of patterns using the pattern editor tools. Once established, these patterns can be merged and remixed within the channel editor to construct and enhance your song. This approach allows you to experiment with different combinations and sequences, giving you the flexibility to refine and evolve your musical ideas into a cohesive composition.

Access the pattern editor by pressing the third key in the global menu cluster on your Grid.

#### Adding Trigs

Trigs are added in the pattern editor.

![Trig editor with a complex trig pattern](https://github.com/subvertnormality/mosaic/raw/main/designs/Images/trig_editor.png)

Using the top row, pick one of the 16 patterns available. In the image, you can see pattern 2 is selected.

![Pattern select buttons](https://github.com/subvertnormality/mosaic/raw/main/designs/Images/trig_editor_pattern_select.png)

To set your rhythm, simply tap in steps using the sequencer. Bright steps symbolize a trig. To define its length, press and hold a trig, then choose its ending step. Steps with a subtle glow show the length. In a single pattern, one trig’s duration ends upon meeting another.

![Trig sequencer](https://github.com/subvertnormality/mosaic/raw/main/designs/Images/trig_editor_sequencer.png)

Craft unique rhythms using a variety of built-in algorithms. The algorithm is selected using the four algorithm select buttons. From left to right:

* Button 1: The drum algorithm, drawing from a rich collection of classic drum patterns.
* Button 2: The tresillo algorithm, utilizing a 3/3/2 ratio for diverse rhythm variations. The tresillo multiplier can be set on the Norns screen for more variations.
* Button 3: Euclidean, a rhythm tool rooted in mathematical logic.
* Button 4: NE Numeric Repetitor, another rhythm tool based on mathematical principles.

![Algorithm select](https://github.com/subvertnormality/mosaic/raw/main/designs/Images/trig_editor_algorithms.png)

The grid is intuitive and adapts to your choices. Each algorithm brings its set of options, and pressing on a grid key typically displays its function on the Norns screen.

The left side faders adjust algorithm values. Brightly lit end buttons refine values, with the furthest left-hand button incrementing downwards and the furthest right-hand button incrementing upwards. The dimmer ones in the middle of the faders adjust values broadly. The rightmost fader typically toggles between different banks in the selected algorithm.

![Algorithm controls](https://github.com/subvertnormality/mosaic/raw/main/designs/Images/trig_editor_algorithm_controls.png)

To see your algorithm's impact, hit the prime button. This primes the currently selected algorithm's pattern. Potential new steps are shown as flashing bright steps on the sequencer. While these steps flash, they aren’t painted yet. Any step that would be painted over an existing active step will blink dimly. By painting the new pattern, you'll deactivate the faintly blinking steps. This approach lets you craft intricate sequences, grounded in rhythmic fundamentals, that don't get too busy. You can modify algorithm parameters while the pattern is primed.

If you haven’t painted the new pattern, the prime button continues to blink. Pressing it again paints your edits. Pressing the prime button again without tweaking the algorithm or its parameters effectively acts as an undo for the last action.

![Prime and print button](https://github.com/subvertnormality/mosaic/raw/main/designs/Images/trig_editor_prime_and_print.png)

Opt out of a prepared pattern by using the cancel button.

![Cancel button](https://github.com/subvertnormality/mosaic/raw/main/designs/Images/trig_editor_cancel.png)

While previewing a new pattern, use the move controls to shift its position. The first button shifts it left, the third to the right, and the center button resets it. Remember to paint your changes.

![Left, center, right buttons](https://github.com/subvertnormality/mosaic/raw/main/designs/Images/trig_editor_left_right.png)

On the Norns screen, you can see the selected channel's grid state on page 1. This is the merged version of the channel and is a useful context for editing your pattern. Use E2 to select channels.

![Channel grid viewer](https://github.com/subvertnormality/mosaic/raw/main/designs/Images/UI/trig_edit_grid_viewer.png)

On page 2 you can select trig editor options. Currently, this allows you to edit the tresillo multiplier in use. Experiment with different values to get wildly different results with the tresillo algorithm.

![Channel grid viewer](https://github.com/subvertnormality/mosaic/raw/main/designs/Images/UI/trig_edit_options.png)

#### Adding Notes

In _Mosaic_, pattern notes aren't strictly bound to a single scale. Instead, they are valued by their position within the currently active scale, measured by distance from the root. Take C major for instance: C is your starting point. One step up brings you to D, and one step down lands on B. If you were to change the applied scale to E minor, the root of your pattern would now be E, one step up would output F sharp, one down would be D.

You've seen in the [Harmony Design](#harmony-design) section that it's possible to sequence scale and degree changes, and this affects the notes your patterns will play. When adding notes to patterns, consider that they represent the harmony of your song and map to what traditionally would be called the rhythm section. It is possible to create melodies using patterns, but it is difficult to do so in a deliberate way as your scale progressions will alter the tonality of your pattern. We'll learn about the recommended way to deliberate [Melodies](#masks) later.

Select the note editor by pressing the fourth key in the global menu button cluster on the grid.

This space displays 16 steps at a glance. Active trigs appear as soft-glowing vertical bars while the root note lies in a subtle horizontal line. The notes you've actively chosen glow brightly. To pick a note for any of the 16 steps, just press. The gentle flicker on the top row indicates the currently chosen pattern. If you wish to explore a different pattern, press and hold on this top row.

Remember, each note you select links back to the root of the scale you're working within. The scale is applied to the channel, not the pattern. You must start to think about your patterns as being disconnected from each channel. This is why we say _Mosaic_ is an intentioned generative sequencer. Expect happy accidents. The channel grid viewer on the Norns screen can help you here.

![Note select](https://github.com/subvertnormality/mosaic/raw/main/designs/Images/note_editor_note_selector.png)

Switch between the four sets of 16 steps using the dedicated buttons.

![16 step selector](https://github.com/subvertnormality/mosaic/raw/main/designs/Images/note_editor_16_selector.png)

Aim for higher pitches or dive deeper with the octave select buttons, expanding your melodic range.

![Melodic range selector](https://github.com/subvertnormality/mosaic/raw/main/designs/Images/note_editor_octave_selector.png)

Hint: Even if a step lacks a trig, don't hesitate to assign a note. This data might come in handy with different merge modes in play.

You can use the four by four button to toggle a mode that lets you more quickly enter repeating notes across the four note grid pages. In four by four mode, any entered note is automatically duplicated across all 4 screens.

![Four by four](https://github.com/subvertnormality/mosaic/raw/main/designs/Images/note_editor_four_by_four.png)

On the Norns screen, you'll find the channel grid visualizer. Use E2 to select the current channel.

#### Adding Velocity

Now let's look at the velocity editor, which functions similarly to the note page. Access it by pressing the fifth button in the global menu cluster.

The velocity editor spans two vertical pages: the first displays velocities from 127 down to 67, while the second displays values between 58 and 0. Adjust these to fine-tune the dynamics of your sequence.

On the Norns screen, you can see the channel grid visualizer. Use E2 to select the current channel.

### Channel Editor

Select the channel editor page by pressing the far left global menu button, and select one of the 16 available channels using the channel select row at the top of _Mosaic_'s Grid UI.

![Channel selector](https://github.com/subvertnormality/mosaic/raw/main/designs/Images/channel_edit_channel_select.png)

#### Adding Patterns to Channels

The core of your rhythm and harmony sections are formed by adding patterns to channels. To do this, first select a channel using the channel buttons. A single channel can accommodate multiple patterns, and likewise, a single pattern can be assigned to multiple channels. To assign patterns, use the pattern select row, located second from the top on Mosaic’s Grid UI.

![Pattern selector](https://github.com/subvertnormality/mosaic/raw/main/designs/Images/channel_edit_pattern_select.png)

#### Masks

Masks in _Mosaic_ allow you to precisely control trig values, notes, velocities, lengths, and chords for specific steps within the channel page's sequencer. Ideal for crafting intentional melodies, masks can superimpose these elements onto your existing harmonic and rhythmic foundation. You can apply masks to override pattern values either individually or all at once—a process aptly named "masking."

With masking, you have the flexibility to modify individual attributes of a pattern. For instance, you could increase the velocity of a note without changing other settings, add additional chord tones, or completely silence a note. Masks also enable you to assign values to steps that are currently void of any pattern influence. By default, notes added this way will align with the selected musical scale. However, they will not conform to specific scale degrees or rotations. If you wish to incorporate accidentals or embrace a more dissonant sound, this default behavior can be disabled in the _Mosaic_ settings.

##### Adding Melodic Notes over Harmony and Drums

To add a mask to your sequence, start by accessing the mask page on your Norns device. Once there, press and hold the step you wish to modify, then input the desired value as a trig lock. Alternatively, you can hold the step while pressing a corresponding key on your MIDI keyboard to set the value. This method allows you to easily and intuitively assign specific musical attributes to any step in your sequence.

You can apply masks to all steps in a channel by setting the mask value without holding down a step. It's possible, for example, to add a chord note to every trigger, or set a fixed velocity for every trigger, or even turn on or off every trigger. The default mask value will apply to all steps that don't have a specific mask lock set.

##### Adding Chords

Chords can be seamlessly integrated into your sequence using masks. You can add up to four additional voices to the root note, provided that your selected device supports polyphony. To do this, make sure you are on the masks page of your Norns. Then, hold the desired step and select each note you want to include in the chord.

Additionally, take advantage of the chord trig params to enhance your musical expression. Experiment with the "[chord strum](#chord-strum)" and "[chord velocity modifier](#chord-velocity-modifier)" trig parameters to vary the playback dynamics and timing of each chord component. These tools allow you to create more nuanced and dynamic chord progressions, adding depth to your compositions.

##### MIDI Input

You can input notes, velocity, and chords using a MIDI keyboard. However, setting the length of these inputs requires manual selection. To do this, ensure you have your desired channel selected on _Mosaic_. Then, while holding the desired step, press the corresponding key on your keyboard. If you are on the mask page of your Norns, the values you input will display as trig locks.

To preview notes before committing them to your sequence, simply press the keys on your keyboard without holding down a step. This method ensures that changes are only made when you explicitly hold down a step, preventing accidental inputs.

By default, the keyboard maps the steps to the currently selected scale on the white keys, with the root note of your selected scale starting from C. You can adjust this mapping in the settings of Mosaic to better suit your musical preferences or project requirements.

You are also able to control all 10 of the trig parameters on the currently selected page independently using a MIDI controller such as Intech's en64 by sending a relative bin offset MIDI CC message to cc 15 - 24 respectively.

#### Merge Modes

To determine how your patterns interact and meld within the composition, you'll need to use the merge mode selector. This feature enables nuanced control over how overlapping patterns in the same channel behave, impacting trigs, notes, velocity, and length.

![Merge mode selector](https://github.com/subvertnormality/mosaic/raw/main/designs/Images/channel_edit_merge_mode.png)

##### Trig Merge Modes

These modes define how trigs are activated when there are overlapping steps across selected patterns:

* **All**: Trigs will activate if they appear in any selected pattern.
* **Skip**: Trigs will activate only if they appear in exactly one selected pattern. If a trig appears in multiple patterns, it won't activate.
* **Only**: Trigs will activate only if they appear in more than one selected pattern, ignoring those that appear in just one.

##### Note Merge Modes

These modes determine how note values are handled when steps overlap:

* **Average**: The note value for overlapping steps is the average of those steps' values in each pattern, subsequently quantized.
* **Higher**: The highest note value from overlapping steps is used after calculating the average and adjusting by subtracting the lowest and adding the highest note value, followed by quantization.
* **Lower**: The lowest note value is used after calculating the average and subtracting the lowest note value from the average, followed by quantization.
* **Pattern**: To prioritize a specific pattern's note values during conflicts, hold the note merge button and select the desired pattern.

By default, notes will snap to the pentatonic version of the currently active scale to assist with avoiding unpleasant harmonic interactions. This can be disabled in _Mosaic_'s settings.

##### Velocity Merge Modes

These settings affect how velocity values are calculated for overlapping steps:

* **Average**: The velocity is the average of the velocities from overlapping steps in each pattern.
* **Higher**: The velocity is calculated by taking the average of each step's velocity, subtracting the lowest velocity, and adding the highest velocity.
* **Lower**: The velocity is calculated by taking the average of each step's velocity, subtracting the lowest velocity, and not adding the highest value back.
* **Pattern**: To use a specific pattern’s velocity values, hold the velocity merge button and press the pattern's select button.

##### Length Merge Modes

These modes dictate how the duration of notes is calculated for overlapping steps:

* **Average**: The length is the average of the lengths from overlapping steps in each pattern.
* **Longer**: The length is determined by taking the average length, subtracting the shortest length, and adding the longest length.
* **Shorter**: The length is calculated by subtracting the shortest length from the average of each step's length minus the shortest length.
* **Pattern**: To apply a specific pattern’s length values, hold the length merge button and press the pattern's select button.

#### Scale Editor

Access the scale editor by selecting the channel page using the far left global menu button, then pressing any of the scale buttons.

![Scale selector](https://github.com/subvertnormality/mosaic/raw/main/designs/Images/channel_edit_scale_select.png)

When in the scale editor, a short press of the scale buttons selects one of the 16 scales; the currently selected scale is dimly lit on the grid. Use the Norns interface to adjust the root, scale, degree, and rotation for the selected scale.

A long press on a scale button selects it as the global scale, indicated by a brightly lit scale button. All patterns now default to this scale unless overridden by a global scale trig lock or channel scale trig lock.

Scale locks can be set to apply a scale globally or to a single channel, activating at a designated step and persisting until the end of the pattern. To set a scale lock, hold a step and press the desired scale slot button. On the scale page, this applies globally to all channels without an active channel scale trig lock; on a channel's page, it applies as a channel scale trig lock, affecting only that channel. Channel-specific scale locks override global scales and locks.

You can also adjust the rate of the global scale track and set its length independently of other channels, enabling chord progressions that extend beyond a single pattern. This feature offers substantial flexibility for crafting intricate chord progressions and varying patterns.

To return to the channel edit page, press any of the channel buttons at the top of the grid.

#### Scale Editor

On the Norns first page in the channel mode you can see the last played notes on the currently selected channel.

#### Clocks, Swing and Shuffle

You can easily adjust the tempo of your entire composition directly from the song sequencer page on your Norns screen. Each sequence can have its own tempo, allowing for varied pacing throughout your composition. Furthermore, you can manage clock division and multiplication for individual channels via the channel editor page in the Norns menu. This feature enables each channel to operate on independent timings, which is perfect for creating complex polyrhythms and other intricate rhythmic patterns.

Additionally, adding swing to each channel allows you to shift notes off the grid, giving your music a more human, less mechanically precise feel. This can be particularly effective in genres like jazz or funk, where a looser, more organic rhythm is often desirable. There are two modes to choose from: swing, which moves notes closer or further apart depending on the value which ranges from -50 to 50. Shuffle uses more complex patterns and can be set to a "feel" and a "basis". Each channel can have an independent setting, giving endless possibilities. If a channel's swing/shuffle settings are not set, they will take the global setting which can be set on the song sequencer page global settings page.

Clock, swing and shuffle settings apply when the sequencer resets if the sequencer is currently playing.

Note: Shuffle only works if the global pattern length is set to a multiple of 8, otherwise the sequencer will fall back to swing.

#### Channel Length

Channels in your sequencer can be customized to range from 1 to 64 steps in length, and each channel can be adjusted independently, including the global scale pattern. This feature allows for intricate layering and timing variations within your compositions.

To adjust the length of a channel, you need to specify the start and end points. Hold down the button corresponding to the start step in the channel editor. While holding it, press the button for the desired end step. The active range of the channel will be indicated by buttons that appear slightly brighter than the others.

The behavior of the sequencer when handling patterns of different lengths can also be tailored to your needs. Navigate to the Norns param pages where you can find various [options](#options) that determine how the sequencer manages channels with differing lengths.

##### Transposition

You can transpose your entire Song Sequence using the global quantizer transposition fader, either globally or by step using trig locks. Transposition applies on top of the currently selected scale.

![Global quantizer transposition fader](https://github.com/subvertnormality/mosaic/raw/main/designs/Images/channel_edit_global_scale_transposition.png)

#### Muting Channels

To mute a channel on your sequencer, press and hold the select button for the desired channel for one second. The button will dim to indicate that the channel has been muted. This function allows for muting on a per-sequence basis, enabling you to selectively silence different channels at various stages of your composition. This feature is particularly useful for creating dynamic shifts and variations in your overall song structure.

#### Devices

For _Mosaic_ to do anything, you must have a device assigned to a channel. Devices represent a hardware device in your studio, perhaps a software device on your computer, or a software device in Norns itself.

##### MIDI Sound Sources

In Mosaic, a device can be either an internal Norns sound engine powered by [n.b.](https://github.com/sixolet/nb/tree/main), or a representation of a MIDI device within your workspace. Devices are assigned per scene and maintain their settings consistently across all song sequences. To utilise MIDI sound sources, you must have a MIDI output device configured in Norns.

If your device has an associated configuration file, such as those available for Elektron -takt devices, the device's name will be displayed, allowing you to select parameters directly without needing to know the MIDI CC numbers. If no such configuration exists, you can still use the CC device, but you will need to manually look up and input CC numbers.

##### Norns Sound Sources with n.b.

[n.b.](https://github.com/sixolet/nb/tree/main) mods give _Mosaic_ the ability to sequence internal sound sources and device connected via Crow. Supported mods include:

* [nb_ansible](https://github.com/sixolet/nb_ansible) for Ansible voices.
* [emplaitress](https://github.com/subvertnormality/emplaitress/) offers four MI Plaits voices in parallel. Note this fork allows Emplatress's params to be locked in _Mosaic_.
* [nb_jf](https://github.com/sixolet/nb_jf) accesses multiple voice modes from Just Friends, including individual mono voice (with slew), polysynth, kit, and unison modes.
* [nb_crow](https://github.com/sixolet/nb_crow) for Crow v/8 and envelope functions.

n.b. devices are picked up automatically. Simply install the desired mod, and pick from the device picker menu. Be careful not to overwhelm your norns by adding too many internal sound engines to channels.

More mods are expected to be supported soon.

#### Device Parameters

MIDI devices can be configured to load a stored patch through the Norns' params menu. For devices that are configured, all CC parameters are accessible for editing. Setting a MIDI parameter to a value of -1 ensures that the current setting on the device remains unchanged. Any other value entered will send that MIDI value directly to your MIDI device. When you load a Mosaic script or press play, these stored MIDI param values are transmitted to your MIDI device, effectively loading a patch. These settings will remain consistent across different song patterns, allowing you to preserve all your sound's patch data within your Mosaic patch. This feature is especially useful for devices that have limited MIDI parameters or interfaces that are less user-friendly.

### Trig Parameters

Most devices in _Mosaic_ feature a set of trig params that alters either the quality of the sound or the trig in some way. Trig params are unique to a song pattern, allowing drastic transitions when moving from one section to another. Each channel can have up to 10 trig params assigned, and each trig param can be [trig locked](#locks) independently. Trig locking is a powerful sequencer device seen on Elektron synthesizers. Each step can be assigned a unique param value, allowing for endless sound variations. 

In the second user interface page of the channel editor on the Norns screen, you will encounter a variety of parameters. Here's how to navigate and manipulate these settings:

* **Page Navigation**: Use E1 to switch between pages.
* **Selecting Parameters**: To select a parameter, turn E2. Once highlighted, adjust the parameter's value by rotating E3.
* **Activating Parameters**: To activate a different parameter within the same slot, press K2.
* **Locking Changes**: As you adjust values, the system automatically saves your changes. You can also create "trig locks" on specific steps by holding down the step and turning E3. This allows you to set values that will override the default parameter for that step.
* **Default Parameter Values**: By default, a pre-set parameter value is transmitted to your selected device on steps without a trig lock. If a parameter's trig lock is set to "off," the mosaic will not send any value to your device for that parameter.
* **Handling Off Settings**: If you set a trig lock to "off" on a step, the system will continue to send the last trig locked value instead of reverting to the default parameter value.

![Param trig lock page](https://github.com/subvertnormality/mosaic/raw/main/designs/Images/UI/channel_edit_param_select.png)

These controls offer flexibility and precision in shaping the behavior of each sequence, ensuring that your musical creativity can be fully realized through the Norns system.

#### Sequencer Params

All device types have a set of standard trig params that affect the sequencer rather than the quality of the sound.

##### Trig Probability

This trig lock can be used to ensure trigs play only with a certain probability. When set to 100, the trig will always play. When set to 0, the trig will never play. At 50, the trig will play half the time. You can set this globally and per step.

##### Fixed Note

Use this trig param to fix your channel to any MIDI note. The value represents a MIDI note number. The note is _not_ quantized. This is useful if you have a drum pattern and you don't want note data to affect the drum sound you're playing on a drum machine. This will override any quantized fixed note values or random note values.

##### Quantized Fixed Note

You can use this trig param to manually select a note in the currently selected scale at any step. The value represents note number, where 0 is the root and higher numbers represent notes in the quantized scale. This overrides the note data coming in from the patterns. This will override random note values.

##### Random Note

This trig param introduces an element of random to your selected notes. A value of 0 will leave the note unchanged. A value of 1 will randomly give your existing note or the note one higher in the scale. A value of 2 will randomly give your existing note, the note one higher in your selected scale, or the note one lower. A value of 3 will randomly select notes -1, 0, 1 or 2. A value of 4 will randomly select notes -2, -1, 0, 1 or 2. And so on. Use trig locks to really spice things up. These can be combined with random twos note trig param. By default, random notes are quantized to the pentatonic version of the currently selected scale to reduce the chance of dissonant harmonic interactions. This can be disabled in _Mosaic_'s param settings.

##### Random Twos Note

Similar to random note, this trig param introduces an element of random to your selected notes. The difference here is that twos note restricts values to those divisible by two. A value of 0 will leave the note unchanged. A value of 1 will randomly give your existing note or the note two higher in the scale. A value of 2 will randomly give your existing note, the note two higher in your selected scale, or the note two lower. A value of 3 will randomly select notes -2, 0, 2 or 4. A value of 4 will randomly select notes -4, -2, 0, 2 or 4. And so on. Use trig locks to really spice things up. These can be combined with random note trig params. Again, random notes are quantized to the pentatonic version of the currently selected scale to reduce the chance of dissonant harmonic interactions. This can be disabled in _Mosaic_'s param settings.

##### Chord Strum

The Chord Strum feature dynamically spaces selected chord masks using the selected step division, ensuring they align rhythmically with the channel's settings. Notes are quantized to the current scale, adjusting in real-time if the scale changes mid-strum, guaranteeing each note stays harmonious and in tune, regardless of strum duration. Each chord note is played once.

##### Chord Arpeggio

The Chord Arp feature is similar to Chord Strum, but chord masks are looped at the current step division for the length of the current step. Notes are quantized to the current scale. Empty chord masks are treated as rests, allowing for rhymic patterns. Arpeggios also honour the Chord Velocity and Chord Shape modifiers. The Chord Arpeggio param overrules the chord strum param. Chord arpeggios can also be used as ratchets if no chord masks are set.

##### Chord Acceleration

TODO

##### Chord Spread

TODO

##### Chord Velocity Modifier

The Chord Velocity Modifier incrementally adjusts the velocity of successive notes in a chord, starting from the chord's root note. This adjustment can either increase or decrease the velocity, thereby creating a "swell" effect for rising intensity or a "fade" effect for a diminishing feel.

##### Chord Shape Modifier

The Chord Shape Modifiers alters the order of the chord masks that are played using the Chord Strum and Chord Arpeggio params. 

#### Locks

Trig param values and various grid functions can be fixed to specific steps on both the channel and global scale pages of Mosaic. When a value is locked to a step, it applies for the duration of that step. This includes trig params, scales, and octave settings on the channel page, as well as global scale and transpose settings on the global scale page. Locks are set on the channel page.

To clear a grid trig lock:

1. Hold the step with the locked value.
2. Press the value that is currently locked to unlock it.

To clear all trig locks from a step:

1. Hold the step you want to clear.
2. Press K2.

Trig locks enhance your control over the sequencing process, allowing for precise adjustments and modifications at any step of your sequence.

##### Trig Param Locks

Device parameters can be locked on a per-step basis. To set a param trig lock:

1. Hold down the step you want to modify on the channel page sequencer.
2. Adjust the value that you want to lock to this step.

To clear a param trig lock:

On the Norns screen, select the parameter you want to unlock.

1. Hold the step where the param is locked and press K3.

##### Scale Locks

Scales can be set on a per-step basis. Scales persist until the end of the pattern unless another scale lock is encountered. To set a scale lock:

1. Hold down the step you want to modify on the channel page sequencer.
2. Press the desired scale slot.

To clear a grid trig lock:

1. Hold the step with the locked value.
2. Press the value that is currently locked to unlock it.

##### Transposition Locks

The transposition of your song can be set on a per-step basis from the scale page accessed in the channel editor. To set a transposition lock:

1. Hold down the step you want to modify on the channel page sequencer.
2. Press the desired transposition value.

To clear a transposition lock:

1. Hold the step with the locked value.
2. Press the zero value on the transposition fader.

##### Octave Locks

A step's current

 octave can be altered using trig locks. To lock a step's octave:

1. Hold down the step you want to modify on the channel page sequencer.
2. Press the desired octave using the octave buttons at the bottom of the channel page.

To clear an octave trig lock:

1. Hold the step with the locked value.
2. Press the value that is currently locked to unlock it.

### Song Sequencer

The Song Editor features a grid layout consisting of 90 slots. Each slot represents a unique opportunity to blend patterns, channels, rhythms, scales, and other elements into your compositions, making each Song Sequence a distinct musical creation.

#### Button Indicators

* **Dim buttons**: These are your blank slates, ready for your creative input.
* **Mid-glow buttons**: These are filled with your existing rhythms and patterns.
* **Brightly lit buttons**: This button highlights the Song Sequence currently in play.

#### Interacting with Slots

* **Selecting a Pattern**: Simply press the button corresponding to the pattern.
* **Copying Slots**: To copy one slot to another, press and hold the source slot, then the destination slot. Note: This action will overwrite the content in the target slot.
* **Erasing a Slot**: To clear a slot, copy an empty slot over it. Remember, there is no undo option, so proceed with caution.

![Song sequence selector](https://github.com/subvertnormality/mosaic/raw/main/designs/Images/song_mode_sequencer_pattern_selector.png)

#### Song Mode Operations

When "song mode" is activated, the sequencer automatically progresses to the next slot after a pattern has played its designated number of repetitions. If it encounters an empty slot, it loops back to the first filled slot within that sequence, facilitating smooth transitions between unique pattern groups. If you wish to change slots during playback, the sequencer will queue your command and execute it after the current sequence completes.

#### Adjusting Song Sequence Length

The song sequence's length can be adjusted using the fader located at the lower end of the song editor page.

* For precise control, utilize the end cap buttons.
* For broader adjustments, use the central fader buttons.
* The length can be set anywhere from 1 to 64, offering a wide range of possibilities.

![Pattern length selector](https://github.com/subvertnormality/mosaic/raw/main/designs/Images/song_mode_sequencer.png)

#### Navigating the Norns Display

**Page 1**: Here, you can set the number of repetitions for each Song Sequence. This setting dictates how sequences transition in song mode. When song mode is off, you manually control slot activation, allowing you to dictate the flow of your song.
**Page 2**: Set the tempo to match the mood you want, from a soothing lullaby to a fast-paced track.

## Save and Load

You can save and load your creations using the param menu. When you choose to save, you'll be prompted to enter a name for your creation. Remember to use a descriptive name so you can easily find and manage your projects.

The sequencer features an autosave function when it is not actively playing. If left idle, it will automatically save your work under the name "autosave" after 60 seconds. When you start Mosaic again, it automatically loads this most recent autosave.

To ensure the longevity of your work, it's important to save your creations into named slots. This prevents them from being overwritten by the autosave feature, allowing you to keep your songs indefinitely.

### Options

Various aspects of Mosaic can be configured from the param section on your Norns, under the Mosaic section. This flexibility allows you to tailor the sequencer’s behavior to match your creative needs.

#### Sequencer Options

##### Song Mode

"Song mode" is on by default. When enabled, the song sequencer will progress through sequences as dictated by the options set on the song sequencer page. When off, song sequences will only progress with manual intervention.

##### Reset at Sequence End

The "Reset at sequence end" option, which is turned on by default, ensures that the sequencer resets all channels at the end of the song sequence. This happens regardless of whether the sequencer is progressing to a new sequence, which helps maintain consistency but may limit more complex polyrhythms. If you prefer continuously evolving polyrhythms, especially when dealing with patterns of different lengths, you can turn this setting off.

##### Reset at Seq Pattern End

"Reset at seq pattern end" is set to off by default. When enabled, it resets all channels at the end of the song sequence but only if a new sequence is queued. Disabling this option allows for evolving polyrhythms.

##### Elektron Program Changes

"Elektron program changes" defaults off. By enabling this setting, your Elektron devices will automatically adjust their patterns to align with the corresponding song pattern in Mosaic. For instance, selecting song pattern one on Mosaic will trigger pattern one on your Elektron device, ensuring that both systems are perfectly in sync. This feature allows for a unified performance across your equipment, with each song pattern change on Mosaic mirrored by your Elektron devices.

##### Elektron Program Change Channel

The "Elektron program change channel" setting determines which MIDI channel to send program change messages to. The default is 10 - same as on most Elektron devices.

#### Parameter Lock Options

##### Trigless Locks

"Trigless locks" is enabled by default, meaning locks on steps with no active trig are still honored.

#### Quantizer Options

##### Quantize Note Masks

"Quantize note masks" is also on by default. With this setting enabled, note masks snap to the currently selected scale, but are not altered by scale degree or rotation adjustments.

##### Scales Lock Until Pattern End

The "Scales lock until ptn end" option, when enabled, ensures scale locks persist until the end of the channel's length. If disabled, scale locks continue only until the next trig.

##### Lock All to Pentatonic

"Lock all to pent." is off by default. Enabling this option forces all notes to adhere to the pentatonic version of the selected scale, useful for creating highly generative compositions.

##### Lock Random to Pentatonic

"Lock random to pent." is on by default. It ensures that notes altered by random trig locks adhere to the pentatonic version of the selected scale, making the random notes harmonically more pleasant.

##### Lock Merged to Pentatonic

Similarly, "Lock merged to pent." is on by default and ensures notes modified by merge modes stick to the pentatonic version of the currently selected scale.

#### MIDI Controller Options

##### Map Scale to White Keys

"Map scale to white keys" is off by default. When enabled, the selected scale is mapped to the white keys of a MIDI keyboard, starting at the C key. The mapping will automatically change when the currently selected scale changes.

##### Honor Scale Rotations

"Honor scale rotations" is off by default. Enabling this setting will allow the currently selected scale's rotation setting to affect the MIDI keyboard mapping.

##### Honor Scale Degree

"Honor scale degree" is off by default. Enabling this setting means the current scale's degree option will affect the MIDI keyboard mapping.

### Sinfonion Connect

You can sync up your Eurorack Sinfonion module to Mosaic using a DIY device called [norns2sinfonion](https://github.com/subvertnormality/norns2sinfonion).

## Development

See https://trello.com/b/kMZ4qEhk/Mosaic for backlog. Please raise bugs and issues on Github.

Make sure that the tests are passing before you open a PR.

```
./test.sh
```

Do not run the tests on your Norns device as you'll end up pulling in the Norns repository onto your device and it'll cause a conflict. If you do this by accident, simply delete `/code/mosaic/lib/tests/test_artefacts` to get your Norns back up and running.

## Device Config Template

If copying the below code, you must exclude all text appearing after "//"

```javascript
[{
  "params": [
    {
      "cc_msb": 7, // the MIDI CC number to send the command on.
      "name": "Level", // the name representing this param.
      "cc_max_value": 127, // the maximum value that can be sent over MIDI.
      "short_descriptor_1": "AMP", // the label that identifies the trigger param in _Mosaic_ at the top of the dial.
      "short_descriptor_2": "LVL", // the label that identifies the trigger param in _Mosaic_ at the bottom of the dial.
      "id": "level", // the unique ID of the param.
      "off_value": -1, // the value that determines when the param is off, usually -1.
      "cc_min_value": -1 // the lower value of the MIDI param, usually -1.
    },
    { // here a specially sequencer param "fixed note" is used to lock the note to a certain MIDI note value, which is useful for some drum devices in combination with "maps_params_automatically".
      "short_descriptor_2": "NOTE",
      "name": "Fixed Note",
      "cc_max_value": 127,
      "default": 36, // the MIDI device will only send out the value 36, regardless of note assignment.
      "cc_min_value": -1,
      "short_descriptor_1": "FIXD",
      "off_value": -1,
      "id": "fixed_note" // this identifies the param as a special "fixed note" sequencer trig param.
    }
  ],
  "type": "midi", // mandatory: leave as MIDI for custom devices.
  "unique": true, // mandatory: true if you only allow one instance of this device in use at one time, false allows multiple instances.
  "map_params_automatically": true, // mandatory: when true, the first 10 params are mapped and assigned on the device's channel trig parameters.
  "polyphonic": false, // mandatory: true if more than one note can be played at once on the device.
  "value": 8, // mandatory: arbitrary value, choose any number.
  "default_midi_device": 1, // optional: use this to set a default MIDI output device. When in use it will no longer be possible to change the output device in _Mosaic_.
  "default_midi_channel": 10, // optional: use this to set a default MIDI output channel. When in use it will no longer be possible to change the output channel in _Mosaic_.
  "name": "Your device", // mandatory: the name used to identify the device in _Mosaic_.
  "id": "a-unique-id" // mandatory: the ID used to identify the device in _Mosaic_. Must be unique.
}]
```



This program is released under the GNU license. Copyright Andrew Hillel 2024.