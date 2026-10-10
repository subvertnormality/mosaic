"""New feature acceptance: Doctor setup reaches actual capture/analysis.
The feature implements the formerly documented display-only BPM/Input settings.
Current README describes the consumption contract. Public ADC is real-time only.
No emulator edits or private Lua state inputs. Recording/result files supplement
visible alignment feedback and preview/paint/MIDI acceptance.
"""
import hashlib,json,math,struct,time,wave
from pathlib import Path
DETENT=2
CITATION='README.md#rhythm-doctor'
def asymmetric_stimulus(path,seconds=29):
    rate=48000;raw=bytearray(seconds*rate*4)
    for channel,bpm,hz,level in ((0,120,60,18000),(1,80,90,9000)):
        onset=1.0
        while onset+.12<seconds:
            start=round(onset*rate)
            for j in range(round(.12*rate)):
                value=round(level*math.sin(2*math.pi*hz*j/rate)*math.exp(-100*j/rate))
                struct.pack_into('<h',raw,(start+j)*4+channel*2,value)
            onset+=60/bpm
    with wave.open(str(path),'wb') as wav:
        wav.setnchannels(2);wav.setsampwidth(2);wav.setframerate(rate);wav.writeframes(raw)
    return hashlib.sha256(path.read_bytes()).hexdigest()
def key(c,n):
    action='apply_correction' if n==3 else 'discard_draft'
    c.ui.rhythm_doctor_key_edge(action,True)
    try:c.elapse(.04)
    finally:c.ui.rhythm_doctor_key_edge(action,False)
    c.elapse(.12)
def turn(c,encoder,delta):
    # norns accelerates rapid turns below30ms. Keep separate intended field
    # gestures beyond that documented native interval, in both timing lanes.
    c.elapse(.06)
    method=c.ui.rhythm_doctor_setup_field if encoder==2 else c.ui.adjust_rhythm_doctor_setup_value
    method(delta)
    c.elapse(.06)
def checkpoint(c,ident,route,label,value):
    from manual_capture import frame
    c.ui.expect_rhythm_doctor_screen(route,label,value)
    expected=dict(route=route,label=label,value=str(value))
    c.results.append(dict(kind='doctor-options-checkpoint',citation=CITATION,id=ident,expected=expected,passed=True))
    frames=getattr(c,'doctor_option_frames',[])
    frames.append(dict(id=ident,expect=expected,output=frame(c,'DOCTOR-OPTIONS',ident)))
    c.doctor_option_frames=frames
def capture_option(c,mode,input_source,bpm=100):
    if c.clock_mode!='real-time':raise ValueError('Public ADC capture is inapplicable in controlled time')
    ui=c.ui
    ui.tap_control('channel_editor');ui.open_channel_task('device');ui.set_value(1);ui.press_key(3)
    ui.tap_control('pattern_slot',1);ui.set_range(1,64);ui.tap_control('pattern_editor')
    ui.select_rhythm_doctor_algorithm('rhythm_doctor');ui.expect_rhythm_doctor_screen('R01')
    turn(c,2,-6);ui.expect_rhythm_doctor_setup_field('TEMPO','AUTO')
    if mode=='manual':turn(c,3,DETENT)
    ui.expect_rhythm_doctor_setup_field('TEMPO',mode.upper())
    turn(c,2,DETENT);turn(c,3,(bpm-120)*DETENT)
    ui.expect_rhythm_doctor_setup_field('MANUAL BPM',bpm)
    checkpoint(c,'setup-manual-bpm','R01','Manual BPM',str(bpm))
    turn(c,2,DETENT)
    if input_source!='stereo':turn(c,3,DETENT if input_source=='left' else 2*DETENT)
    ui.expect_rhythm_doctor_setup_field('INPUT',{'stereo':'STEREO','left':'L','right':'R'}[input_source])
    checkpoint(c,'setup-input-source','R01','Input',{'stereo':'STEREO','left':'L','right':'R'}[input_source])
    key(c,3)
    path=c.data_directory/'doctor-asymmetric-input.wav';stimulus_sha=asymmetric_stimulus(path)
    ui.rhythm_doctor_capture_edge(True)
    try:c.elapse(.08)
    finally:ui.rhythm_doctor_capture_edge(False)
    job=c.runtime.capture_start(29,input='mosaic/doctor-asymmetric-input.wav');c.doctor_input_job=job
    ui.expect_rhythm_doctor_screen('R02')
    # Let the whole public input clip finish before CPU inference begins.
    # The capture keeps recording; this avoids an unnecessary ADC/inference overlap.
    c.elapse(29.5)
    deadline=time.monotonic()+10
    while job['status']=='capturing' and time.monotonic()<deadline:
        job=c.runtime.capture_status(job['job_id']);time.sleep(.05)
    c.doctor_input_job=job
    assert job['status']=='complete' and job['input_sha256']==stimulus_sha,job
    assert all(job['finished'].get(k)==0 for k in ('xruns','nonfinite','server_dead')),job
    key(c,3)
    ui.expect_rhythm_doctor_screen('R04')
    from frame_oracle import live_header_matches
    title,layout=ui._rhythm_doctor_screen('R05')
    c.wait(lambda state:live_header_matches(state,title,'CH01',layout),timeout=180)
    ui.expect_rhythm_doctor_screen('R05')
    # Player-visible bank tempo: opening Alignment seeds Half tempo from the bank.
    turn(c,2,4*DETENT);ui.expect_rhythm_doctor_child_row('R05','Alignment')
    checkpoint(c,'window-lower-row','R05','Alignment','OPEN >')
    key(c,3)
    if mode=='manual':ui.expect_rhythm_doctor_screen('R06','Half tempo',str(bpm))
    else:ui.expect_rhythm_doctor_screen('R06')
    turn(c,2,4*DETENT)
    checkpoint(c,'alignment-lower-row','R06','Fine start','0ms')
    key(c,2);ui.expect_rhythm_doctor_screen('R05')
    import sys
    sys.path.insert(0,str(Path(__file__).resolve().parents[3]/'tools'))
    from manual_doctor_audit import read_softcut_pcm
    wavs=list((c.data_directory/'rhythm-doctor-captures').glob('*.wav'))
    assert len(wavs)==1,'Requires the actual owned capture, not an injected bank'
    rate,ch=read_softcut_pcm(wavs[0]);assert rate==48000 and len(ch[0])>=24*rate
    if input_source=='stereo':assert ch[0]!=ch[1],'Stereo must retain distinct ADC sources'
    else:assert ch[0]==ch[1],input_source+' must duplicate only its selected ADC'
    values=[json.loads(p.read_text()) for p in (c.data_directory/'rhythm-doctor-analysis-runtime/results').glob('*.json')]
    complete=[value for value in values if value.get('status')=='COMPLETED'];assert len(complete)==1
    value=complete[0];analysis=value['analysis']
    assert value['wav_sha256']==hashlib.sha256(wavs[0].read_bytes()).hexdigest()
    if mode=='manual':assert analysis['bpm']==bpm and analysis['tempo_mode']=='manual' and analysis['origin_sample']==0 and analysis['phrase_start_sample']==0
    else:assert analysis['tempo_mode']=='auto' and analysis['tempo_detected'] is True
    ui.select_rhythm_doctor_lane('BD');ui.tap_control('paint');ui.expect_rhythm_doctor_screen('R08')
    preview=[i+1 for i,v in enumerate(c.snapshot()['grid'][48:112]) if v in (12,15)]
    assert len(preview)>=2,'Selected input must produce a visible preview'
    ui.tap_control('paint');ui.expect_rhythm_doctor_tooltip('Pattern painted')
    assert [i+1 for i,v in enumerate(c.snapshot()['grid'][48:112]) if v==15]==preview
    ui.tap_control('channel_editor');before=c.snapshot()['midi_count'];ui.play();c.elapse(12);ui.stop();c.elapse(.2)
    state=c.snapshot();notes=[v for v in state['midi'] if v['index']>before and 144<=v['bytes'][0]<=159 and v['bytes'][2]>0]
    assert len(notes)>=len(preview) and all(v['port']==1 for v in notes),'A complete phrase must emit every painted gate on its selected output'
    c.wait(lambda state:state['midi_capture']['outstanding']==[])
    deadline=time.monotonic()+40
    while job['status']=='capturing' and time.monotonic()<deadline:
        job=c.runtime.capture_status(job['job_id']);time.sleep(.05)
    c.doctor_input_job=job
    assert job['status']=='complete' and job['input_sha256']==stimulus_sha
    assert all(job['finished'].get(k)==0 for k in ('xruns','nonfinite','server_dead'))
    c.results.append(dict(kind='doctor-backend-options',citation=CITATION,mode=mode,manual_bpm=bpm,input_source=input_source,
        captured_sha256=value['wav_sha256'],stimulus_sha256=stimulus_sha,analysis=analysis,preview_steps=preview,
        midi_start_index=before,midi_end_index=state['midi_count'],notes=notes,passed=True))
def manual_stereo(c):capture_option(c,'manual','stereo',100)
def manual_left(c):capture_option(c,'manual','left',100)
def retained_alignment(c,bpm=120):
    from contract.rhythm_doctor_options import _select
    from frame_oracle import live_header_matches
    ui=c.ui;ui.tap_control('pattern_editor')
    # Selecting an already active algorithm is deliberately inert. Reopen the
    # existing bank through its public Trig Tasks entry, as the player does.
    ui.open_task('Trig','rhythm_doctor')
    ui.expect_rhythm_doctor_screen('R05')
    _select(c,'R05','Alignment');key(c,3)
    turn(c,2,2*DETENT)
    turn(c,3,(bpm-100)*DETENT)
    checkpoint(c,'alignment-edited-then-cancelled','R06','Exact BPM',str(bpm))
    key(c,2)
    _select(c,'R05','Alignment');key(c,3)
    ui.expect_rhythm_doctor_screen('R06','Half tempo','100')
    turn(c,2,2*DETENT)
    turn(c,3,(bpm-100)*DETENT)
    checkpoint(c,'alignment-confirmed-draft','R06','Exact BPM',str(bpm))
    key(c,3)
    title,layout=ui._rhythm_doctor_screen('R05')
    c.wait(lambda state:live_header_matches(state,title,'CH01',layout),timeout=90)
    _select(c,'R05','Alignment');key(c,3)
    checkpoint(c,'alignment-reanalysis-ready','R06','Half tempo',str(bpm))
    key(c,2)
    results=[json.loads(p.read_text()) for p in (c.data_directory/'rhythm-doctor-analysis-runtime/results').glob('*.json')]
    complete=sorted((v for v in results if v.get('status')=='COMPLETED'),key=lambda v:v['analysis_revision'])
    assert len(complete)==2 and complete[-1]['analysis']['bpm']==bpm
    assert complete[-1]['wav_sha256']==complete[0]['wav_sha256'],'Correction must use the same retained public take'
    assert complete[-1]['analysis_revision']==complete[0]['analysis_revision']+1
    c.doctor_ready_analysis=complete[-1]
    c.results.append(dict(kind='doctor-retained-alignment',citation=CITATION,passed=True,
        initial_bpm=100,confirmed_bpm=bpm,captured_sha256=complete[-1]['wav_sha256'],analysis=complete[-1]['analysis']))
def manual_right(c):
    capture_option(c,'manual','right',100)
    retained_alignment(c,120)
def auto_stereo(c):capture_option(c,'auto','stereo',100)

def auto_left(c):capture_option(c,'auto','left',100)
def auto_right(c):capture_option(c,'auto','right',100)
