"""A mapped CC's page switch returns on every MIDI channel (suspected defect S10, human
decision 2026-09-11: "the page return should work on MIDI channels 1-16").

README 197-211 documents mapping "selected channel parameters" through the norns MIDI
map; it does not describe the page switch or the return, so both are characterisation,
not manual text, and the return on channels 2-16 rests on the recorded human decision.

Three selected-channel mask maps, each with the documented settings (input 1..2, output
-1..1, accumulation on), listen on MIDI channels 1, 2 and 16. From the Device Config page
of the channel editor, one relative CC on each channel brings the Note Masks page up, and
two seconds later the channel editor returns to Device Config.
"""
import shutil
from driver import Driver, REPO

MAPS = ((1, 'sel_ch_vel', 6), (2, 'sel_ch_note', 5), (16, 'sel_ch_len', 7))


def map_line(param, cc, channel):
    return '"%s":"{cc=%d, ch=%d, dev=1, in_lo=1, in_hi=2, out_lo=-1, out_hi=1, accum=true, echo=false, value=2}"\n' % (param, cc, channel)


def midi_cc_page_return(c):
    from frame_oracle import header, matches
    c.configure(); c.finish()
    seed = c.out/'mapping-seed'; (seed/'config').mkdir(parents=True)
    shutil.copy(REPO/'tests/behaviour/config/emu-midi.json', seed/'config/emu-midi.json')
    (seed/'mosaic.pmap').write_text(''.join(map_line(param, cc, channel) for channel, param, cc in MAPS))
    out = c.out/'mapping'; out.mkdir()
    e = Driver(out, project_seed=seed, **c.launch_options)
    try:
        e.configure()                                   # ends on the Device Config page
        for channel, param, cc in MAPS:
            e.action(type='midi', port=1, bytes=[175 + channel, cc, 65])
            # characterisation, not manual text: a selected-channel mask map shows the mask page.
            e.screen_header('Ch. 1 Note Masks')
            e.elapse(2.5)
            # characterisation, not manual text (human decision 2026-09-11 for channels 2-16):
            # two seconds after the CC the channel editor returns to the page it was on.
            returned = matches(e.snapshot(), header('Ch. 1 Device Config'))
            e.results.append(dict(kind='cc-page-return', midi_channel=channel, param=param, cc=cc, returned=returned))
            assert returned, 'CC %d on MIDI channel %d switched to Note Masks and never returned to Device Config' % (cc, channel)
    finally:
        e.finish()
    c.results.append(dict(kind='cc-page-return-session', nested=str(out), channels=[m[0] for m in MAPS], passed=True))
