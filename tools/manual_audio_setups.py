"""Reviewed public-input setups for manual audio examples.

An example names one with `setup: <id>`. manual_audio.configure() calls
SETUPS[id](c, example, tracks, witnesses, midi_only) after its routing and
mask programming, so a setup only adds the example's further public edits
(song slots, merge modes, swing, ...). validate() rejects unknown ids.

Song sections: slot 1 is the example as configured plus its listed changes; each
later slot is a copy of the previous slot (hold the source, tap the destination)
with its own global length and listed changes. Every change is made through the
grid, keys and encoders on the voice channel and, in a witness session, on its
MIDI witness channel (14 + channel) too.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tests/behaviour"))
from channel_gestures import set_channel_swing, shift_mute_channel, set_global_pattern_length

SETUPS={}

def register(name):
    def add(function):
        if name in SETUPS:raise ValueError("duplicate audio setup "+name)
        SETUPS[name]=function
        return function
    return add

# Proven public sequences (cases M-NUMERIC-MERGE / composition_workflow): the merge buttons cycle.
NOTE_MERGE_ORDER=("average","higher","lower")
NOTE_MERGE_LED={"average":"off","higher":"in_range","lower":"medium"}
TRIG_MERGE_TAPS={("skip","all"):2}
WITNESS_OFFSET=14

def channels_of(tracks,witnesses,authored=None):
    """Channels one edit must reach: each authored channel (or just `authored`) and its witness."""
    wanted=[t["channel"] for t in tracks if authored is None or t["channel"]==authored]
    if authored is not None and not wanted:raise ValueError("section change names unknown channel "+str(authored))
    return wanted+([WITNESS_OFFSET+v for v in wanted] if witnesses else [])

class SlotState:
    """What the previous slot left on each channel; each slot starts as a copy of it."""
    def __init__(self,tracks,witnesses,midi_only=False):
        self.midi_only=midi_only
        self.octave={};self.velocity={};self.muted={}
        for track in tracks:
            for channel in channels_of(tracks,witnesses,track["channel"]):
                self.octave[channel]=track.get("octave",0);self.velocity[channel]=track["velocity"];self.muted[channel]=False
        self.note_merge="average";self.trig_merge="skip"

def verify_channel(c,channel,slot,state):
    """README Muting Channels / Octave: the Masks scope names the slot, MUTE and the octave."""
    c.ui.channel_page("masks",channel=channel,confirm=False)
    c.ui.expect_header("masks",channel=channel,song_slot=slot,mute=state.muted[channel],octave=state.octave[channel])

def apply_swing(c,change,tracks,witnesses,slot,state):
    for channel in channels_of(tracks,witnesses,change.get("channel")):
        c.ui.select_channel(channel);set_channel_swing(c.ui,channel,change["amount"],from_top=True)
        c.ui.expect_header("clock_mods",channel=channel,song_slot=slot,mute=state.muted[channel],octave=state.octave[channel])
        c.ui.expect_selected_field("vertical_list","Swing",str(change["amount"]))

def apply_trig_merge(c,change,tracks,witnesses,slot,state):
    taps=TRIG_MERGE_TAPS.get((state.trig_merge,change["mode"]))
    if taps is None:raise ValueError("section change trig_merge %s to %s is not a proven sequence"%(state.trig_merge,change["mode"]))
    for channel in channels_of(tracks,witnesses,change.get("channel")):
        c.ui.select_channel(channel)
        for _ in range(taps):c.ui.tap_control("trig_merge_mode")
        c.ui.expect_leds({("trig_merge_mode",None):"medium"})
    state.trig_merge=change["mode"]

def apply_note_merge(c,change,tracks,witnesses,slot,state):
    if change["mode"] not in NOTE_MERGE_ORDER:raise ValueError("section change note_merge mode "+str(change["mode"]))
    taps=(NOTE_MERGE_ORDER.index(change["mode"])-NOTE_MERGE_ORDER.index(state.note_merge))%len(NOTE_MERGE_ORDER)
    for channel in channels_of(tracks,witnesses,change.get("channel")):
        c.ui.select_channel(channel)
        for _ in range(taps):c.ui.tap_control("note_merge_mode")
        c.ui.expect_leds({("note_merge_mode",None):NOTE_MERGE_LED[change["mode"]]})
    state.note_merge=change["mode"]

def apply_mute(c,change,tracks,witnesses,slot,state):
    """Shift press toggles: the channel's mute flips relative to the slot it was copied from."""
    for channel in channels_of(tracks,witnesses,change["channel"]):
        c.ui.select_channel(channel);shift_mute_channel(c,channel)
        state.muted[channel]=not state.muted[channel]
        verify_channel(c,channel,slot,state)

def apply_octave(c,change,tracks,witnesses,slot,state):
    for channel in channels_of(tracks,witnesses,change["channel"]):
        c.ui.select_channel(channel);c.ui.set_channel_octave(change["value"])
        state.octave[channel]=change["value"]
        verify_channel(c,channel,slot,state)

def apply_mask(c,change,tracks,witnesses,slot,state):
    """Velocity mask of the channel (README Masks), set absolutely from the slot it was copied from."""
    if change["field"]!="velocity":raise ValueError("section change mask field "+str(change["field"]))
    from manual_capture import set_mask_field
    for channel in channels_of(tracks,witnesses,change["channel"]):
        c.ui.select_channel(channel);c.ui.channel_page("masks",channel=channel,confirm=False)
        set_mask_field(c,2,change["value"]-state.velocity[channel])
        c.ui.expect_field_value("velocity",str(change["value"]))
        state.velocity[channel]=change["value"]

def lock_step(c,change,lock):
    """README Trig Param Locks: hold the step, then adjust the parameter. The first E3 burst saturates
    to the lowest value of the parameter (a CC's Off, a stock parameter's minimum); ``lock`` is
    [step, detents] or [step, detents, shown]: turn ``detents`` up from there and, when ``shown`` is
    given, read it back in the held step's slot with the lock marker (the gesture of
    tests/behaviour/parameter_lock_domain.py)."""
    with c.ui.hold_step(lock[0]):
        c.elapse(.05);c.ui.encoder_event(3,-126);c.elapse(.15)
        c.ui.turn(3,lock[1])
        if len(lock)>2:c.ui.expect_selected_param(change["slot"],lock[2],"L",change["label"])
    c.elapse(.15)

def apply_trig_param(c,change,tracks,witnesses,slot,state):
    """README Trig Param Locks / Sequencer Params: on the Trig params screen of the channel put the
    parameter (key ``param`` or picker ``label``) into picker slot ``slot``. Without ``locks`` (no step
    held) turn the channel value ``value`` detents from Off and read it back as ``shown``; with ``locks``
    lock each listed step. ``target`` limits it to the ``voice`` channel or the ``midi``
    channel (a MIDI-routed channel: the witness copy, or every channel in the controlled MIDI lane)."""
    for channel in channels_of(tracks,witnesses,change.get("channel")):
        midi=state.midi_only or channel>WITNESS_OFFSET
        if change.get("target") not in (None,"midi" if midi else "voice"):continue
        c.ui.select_channel(channel);c.ui.channel_page("trig_locks",channel=channel,confirm=False)
        c.ui.select_field("param_slot",saturate=-12,then=change["slot"]-1)
        if "param" in change:c.ui.assign_trig_parameter_key(change["param"]);label=c.ui.trig_parameter_label(change["param"])
        else:c.ui.assign_trig_parameter(change["label"]);label=change["label"]
        if "locks" in change:
            for lock in change["locks"]:lock_step(c,dict(change,label=label),lock)
        else:
            c.ui.set_value(change["value"])
            c.ui.expect_selected_field("overview_params",label,change["shown"])

def apply_harmony(c,change,tracks,witnesses,slot,state):
    """README.md#harmony: set the channel's Harmony Mode to Revoice and apply it (K3). Revoice is the
    first mode after Off, one detent. The Revoice lesson's bass rule is claimed only after the screen
    shows Bass Mode ROOT (the default is not stated in the README)."""
    if change.get("mode")!="revoice":raise ValueError("section change harmony mode "+str(change.get("mode")))
    for channel in channels_of(tracks,witnesses,change.get("channel")):
        c.ui.select_channel(channel);c.ui.channel_page("harmony",channel=channel,confirm=False)
        c.ui.expect_header("harmony",channel=channel,song_slot=slot,mute=state.muted[channel],octave=state.octave[channel])
        c.ui.select_row("mode",0);c.ui.set_value(1)
        c.ui.expect_selected_field("detail","Mode","REVOICE")
        c.ui.press_key(3);c.ui.expect_footer_text("APPLIED")
        c.ui.select_row("bass",4);c.ui.press_key(3)
        c.ui.expect_selected_field("detail","Mode","ROOT");c.ui.press_key(2)

APPLIERS={"harmony":apply_harmony,"swing":apply_swing,"trig_param":apply_trig_param,"trig_merge":apply_trig_merge,"note_merge":apply_note_merge,
          "mute":apply_mute,"octave":apply_octave,"mask":apply_mask}

def apply_sections(c,example,tracks,witnesses,midi_only=False):
    """Build the song: slot n is slot n-1 copied, then given its global length and changes."""
    authored_tracks=example.get("tracks",tracks)
    authored_channels={track["channel"] for track in authored_tracks}
    active_channels={track["channel"] for track in tracks}
    for channel in active_channels:
        if channel not in authored_channels:raise ValueError("active section channel is not authored: "+str(channel))
    # Validate every declared target against the complete example before the first public input.
    # A solo take can omit a valid scene channel, but cannot make a genuinely unknown target valid.
    for section in example["sections"]:
        for change in section["changes"]:
            if change["kind"] not in APPLIERS:raise ValueError("section change %s has no public-input setup"%change["kind"])
            channel=change.get("channel")
            if channel is not None:channels_of(authored_tracks,witnesses,channel)
    state=SlotState(tracks,witnesses,midi_only)
    for section in example["sections"]:
        slot=section["slot"]
        c.ui.song_editor()
        if slot>1:
            c.ui.copy_slot(slot-1,slot,control="song_pattern_slot")
            c.ui.tap_control("song_pattern_slot",slot)
        set_global_pattern_length(c.ui,section["global_length"])
        c.ui.channel_editor()
        for change in section["changes"]:
            channel=change.get("channel")
            if channel is not None and channel not in active_channels:continue
            APPLIERS[change["kind"]](c,change,tracks,witnesses,slot,state)
    c.ui.song_editor();c.ui.tap_control("song_pattern_slot",1);c.ui.channel_editor()

@register("swing-comparison")
def swing_comparison(c,example,tracks,witnesses,midi_only):
    """Slot 1 straight, slot 2 Swing 25 on every channel."""
    apply_sections(c,example,tracks,witnesses)

@register("note-merge-modes")
def note_merge_modes(c,example,tracks,witnesses,midi_only):
    """Plain (non-pentatonic) merged pitches: Average in slot 1, Higher in slot 2, all trigs."""
    c.ui.set_mosaic_options([("Lock merged to pent.",False)])
    apply_sections(c,example,tracks,witnesses)

@register("song-sections")
def song_sections(c,example,tracks,witnesses,midi_only):
    """Slots of different length that differ by mute, octave and a velocity mask."""
    apply_sections(c,example,tracks,witnesses)

@register("harmony-strum-arp")
def harmony_strum_arp(c,example,tracks,witnesses,midi_only):
    """Slot 1 block chords, slot 2 Strum with Spread and Acceleration, slot 3 adds Arp (which overrules Strum)."""
    apply_sections(c,example,tracks,witnesses,midi_only)

@register("param-lock-comparison")
def param_lock_comparison(c,example,tracks,witnesses,midi_only):
    """Slot 1 plays without locks; slot 2 locks a voice parameter and, on the MIDI channel, CC 1 on the same steps."""
    apply_sections(c,example,tracks,witnesses,midi_only)

@register("voice-leading-revoice")
def voice_leading_revoice(c,example,tracks,witnesses,midi_only):
    """Slot 1 Harmony Off (block triads as written); slot 2, a copy of slot 1, Harmony Revoice."""
    apply_sections(c,example,tracks,witnesses,midi_only)

class StageReached(Exception):
    """The replayed course arrived at the listening stage; its project is left as the course had it."""

@register("course-stage")
def course_stage(c,example,tracks,witnesses,midi_only):
    """Reproduce a course stage in a fresh session through the public inputs: replay the course itself
    (tools/manual_course_cases.course, unmodified) from the empty project, skipping each earlier listening
    step and stopping at the one this example plays (its ``course.contract_key``), where the project is the
    course's own state for that stage. Characterisation: the course's earlier listening is not repeated,
    only its edits; the stage's music is then played and judged by the example's midi_contract, which the
    validator ties to the course's independent CONTRACTS entry.

    The state is MIDI-routed as the course leaves it, and it stays that way here: an audio session does not
    add witness channels (they would change the state it is meant to play). It proves the stage on MIDI before
    and after its voice-routed take instead (manual_audio.course_before_after), so witnesses=True is refused."""
    if witnesses:raise ValueError("course-stage audio sessions use the before/after MIDI check, not witness channels")
    import manual_course_cases as cases
    target=example["course"]["contract_key"]
    if target not in cases.CONTRACTS:raise ValueError("course contract_key "+str(target))
    def listen(driver,stage,*args,**kwargs):
        if stage==target:raise StageReached(stage)
    original=cases.musical
    cases.musical=listen
    try:cases.course(c)
    except StageReached:return
    finally:cases.musical=original
    raise AssertionError("course never reached "+target)

