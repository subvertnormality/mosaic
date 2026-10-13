# Quick-reference migration coverage

Reviewed all **77** gesture/result and behaviour rows from the preserved 1.4.0 cheat sheet against current YAML authoring: 54 preserved and 23 clarified. No row is credited merely because the old archive still exists.

The detailed JSON records the old line/text, stable feature ID, exact authored excerpts and linked code/case sources. Some behaviour explanations belong in reference prose rather than a condensed gesture row. This is documentation migration coverage; it does not claim exhaustive behaviour acceptance.

The pre-authority coverage receipt is preserved at `manual/evidence/quick-reference-coverage-before-authority-8be1e29ac7491bb628401cff2268e9bd9d53cd7cd942ab3715c1e5e93cbbbc26.json`. Current excerpts were rechecked against revised vertical-list controls, Record and Doctor workflows, and the shared Strategy selector; previous excerpts remain in each changed row. This does not promote native review status.

Source corrections resolved during this audit:

- Channel scale indicator and octave fader are now explicit; octave applies to the selected channel, with centre zero.
- Algorithm bank and both parameter faders specify algorithm-dependent ranges and availability.
- K1 fine input is scoped to device parameters; it is not promised for every field.
- Plain MIDI audition is explicit with Record off and no held grid step.
- Shared Strategy now selects Skip, Only, All, Foundation and Fragments. Fragments marks retained attribute settings SAVED and inactive; strategy requests are immediate, while parameter drafts still need Apply.
- Existing corrections retain ready-bank Rhythm Doctor playback, workspace-specific clearing, optional white-key mapping and suspended autosave after a rejected load.

| Old line | Destination | Outcome |
| --- | --- | --- |
| 794 | [ sequencer-start-and-stop ](./#sequencer-start-and-stop) | preserved |
| 798 | [ arm-live-record ](./#arm-live-record) | preserved |
| 802 | [ grid-menu-navigation ](./#grid-menu-navigation) | preserved |
| 806 | [ grid-menu-navigation ](./#grid-menu-navigation) | preserved |
| 810 | [ grid-menu-navigation ](./#grid-menu-navigation) | preserved |
| 814 | [ grid-menu-navigation ](./#grid-menu-navigation) | preserved |
| 822 | [ muting-channels ](./#muting-channels) | preserved |
| 826 | [ adding-patterns-to-channels ](./#adding-patterns-to-channels) | preserved |
| 830 | [ channel-editor ](./#channel-editor) | preserved |
| 834 | [ channel-length ](./#channel-length) | clarified |
| 838 | [ channel-editor ](./#channel-editor) | clarified |
| 842 | [ merge-modes ](./#merge-modes) | clarified |
| 866 | [ adding-trigs ](./#adding-trigs) | preserved |
| 870 | [ adding-trigs ](./#adding-trigs) | preserved |
| 873 | [ rhythm-doctor ](./#rhythm-doctor) | clarified |
| 876 | [ rhythm-doctor ](./#rhythm-doctor) | preserved |
| 879 | [ rhythm-doctor ](./#rhythm-doctor) | preserved |
| 883 | [ adding-trigs ](./#adding-trigs) | clarified |
| 888 | [ adding-trigs ](./#adding-trigs) | clarified |
| 892 | [ adding-trigs ](./#adding-trigs) | clarified |
| 896 | [ adding-trigs ](./#adding-trigs) | preserved |
| 900 | [ adding-trigs ](./#adding-trigs) | preserved |
| 904 | [ adding-trigs ](./#adding-trigs) | preserved |
| 913 | [ scale-editor ](./#scale-editor) | preserved |
| 917 | [ scale-locks ](./#scale-locks) | preserved |
| 921 | [ transposition ](./#transposition) | preserved |
| 941 | [ interacting-with-slots ](./#interacting-with-slots) | preserved |
| 945 | [ adjusting-song-sequence-length ](./#adjusting-song-sequence-length) | preserved |
| 954 | [ norns-menu-navigation ](./#norns-menu-navigation) | clarified |
| 955 | [ norns-menu-navigation ](./#norns-menu-navigation) | preserved |
| 956 | [ norns-menu-navigation ](./#norns-menu-navigation) | preserved |
| 957 | [ trig-parameters ](./#trig-parameters) | clarified |
| 958 | [ removing-masks ](./#removing-masks) | clarified |
| 959 | [ removing-masks ](./#removing-masks) | clarified |
| 964 | [ trig-param-locks ](./#trig-param-locks) | preserved |
| 965 | [ scale-locks ](./#scale-locks) | preserved |
| 966 | [ transposition-locks ](./#transposition-locks) | preserved |
| 967 | [ octave-locks ](./#octave-locks) | preserved |
| 972 | [ adding-trig-masks ](./#adding-trig-masks) | preserved |
| 973 | [ masks ](./#masks) | preserved |
| 987 | [ adding-trig-masks ](./#adding-trig-masks) | preserved |
| 988 | [ removing-masks ](./#removing-masks) | clarified |
| 989 | [ removing-masks ](./#removing-masks) | clarified |
| 990 | [ masks ](./#masks) | clarified |
| 991 | [ trig-parameters ](./#trig-parameters) | preserved |
| 992 | [ norns-menu-navigation ](./#norns-menu-navigation) | preserved |
| 993 | [ norns-menu-navigation ](./#norns-menu-navigation) | preserved |
| 998 | [ adding-trig-masks ](./#adding-trig-masks) | preserved |
| 999 | [ masks ](./#masks) | preserved |
| 1000 | [ masks ](./#masks) | preserved |
| 1001 | [ masks ](./#masks) | preserved |
| 1002 | [ adding-chords ](./#adding-chords) | clarified |
| 1007 | [ adding-chords ](./#adding-chords) | preserved |
| 1008 | [ chord-strum ](./#chord-strum) | preserved |
| 1009 | [ chord-velocity-modifier ](./#chord-velocity-modifier) | preserved |
| 1010 | [ chord-shape-modifier ](./#chord-shape-modifier) | preserved |
| 1011 | [ chord-spread ](./#chord-spread) | preserved |
| 1012 | [ chord-acceleration ](./#chord-acceleration) | preserved |
| 1013 | [ chord-arpeggio ](./#chord-arpeggio) | preserved |
| 1019 | [ midi-keyboard-input ](./#midi-keyboard-input) | preserved |
| 1020 | [ midi-keyboard-input ](./#midi-keyboard-input) | clarified |
| 1021 | [ map-scale-to-white-keys ](./#map-scale-to-white-keys) | clarified |
| 1022 | [ arm-live-record ](./#arm-live-record) | preserved |
| 1029 | [ save-and-load ](./#save-and-load) | clarified |
| 1038 | [ norns-menu-navigation ](./#norns-menu-navigation) | clarified |
| 1039 | [ musical-merge-and-voice-leading ](./#musical-merge-and-voice-leading) | clarified |
| 1043 | [ merge-shape ](./#merge-shape) | clarified |
| 1047 | [ fragments ](./#fragments) | clarified |
| 1051 | [ interlock ](./#interlock) | preserved |
| 1055 | [ structure ](./#structure) | preserved |
| 1059 | [ merge-shape ](./#merge-shape) | preserved |
| 1063 | [ harmony ](./#harmony) | preserved |
| 1064 | [ harmony ](./#harmony) | preserved |
| 1065 | [ harmony ](./#harmony) | preserved |
| 1069 | [ musical-merge-and-voice-leading ](./#musical-merge-and-voice-leading) | preserved |
| 1073 | [ harmony ](./#harmony) | clarified |
| 1130 | [ lock-lead-time ](./#lock-lead-time) | preserved |
