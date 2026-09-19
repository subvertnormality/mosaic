"""Analytic signal fixtures; no Mosaic/player implementation used as an oracle."""
import math,struct,tempfile,unittest
from pathlib import Path
from pcm_oracle import read_wav,verify_timeline

RATE=8000
EVENTS=[dict(channel=0,note=60,onset=.20,offset=.40),dict(channel=0,note=64,onset=.55,offset=.75),dict(channel=1,note=67,onset=.90,offset=1.1)]
def signal(events=EVENTS,phase=0):
    channels=[[0.0]*round(1.4*RATE) for _ in range(2)]
    for event in events:
        start=round(event['onset']*RATE);stop=round(event['offset']*RATE)
        for i in range(start,min(stop,len(channels[0]))):
            channels[event['channel']][i]+=.12*math.sin(2*math.pi*440*2**((event['note']-69)/12)*(i-start)/RATE+phase)
    return channels
def changed(index,**kwargs):
    result=[dict(e) for e in EVENTS];result[index].update(kwargs);return result

class PCMOracle(unittest.TestCase):
    def test_correct_stereo_phrase_and_phase(self):
        for phase in (0,.8):self.assertTrue(verify_timeline(signal(phase=phase),RATE,EVENTS)['passed'])
    def reject(self,events):
        with self.assertRaisesRegex(AssertionError, 'expected'):verify_timeline(signal(events),RATE,EVENTS)
    def test_every_pitch_in_declared_domain(self):
        for note in range(48,85):
            events=[dict(channel=0,note=note,onset=.2,offset=.4)]
            with self.subTest(note=note):
                self.assertTrue(verify_timeline(signal(events),RATE,events)['passed'])
    def test_native_sample_rates(self):
        for rate in (44100,48000,96000):
            events=[dict(channel=0,note=60,onset=.1,offset=.3)]
            samples=[.12*math.sin(2*math.pi*440*2**(-9/12)*i/rate+.4) if .1<=i/rate<.3 else 0.0 for i in range(round(.4*rate))]
            with self.subTest(rate=rate):
                self.assertTrue(verify_timeline([samples],rate,events)['passed'])
    def test_wrong_pitch(self):self.reject(changed(0,note=61))
    def test_missing_note(self):self.reject(EVENTS[1:])
    def test_extra_tail(self):self.reject(changed(2,offset=1.35))
    def test_reordered_notes(self):
        events=changed(0,note=64);events[1]['note']=60;self.reject(events)
    def test_global_shift(self):self.reject([dict(e,onset=e['onset']+.1,offset=e['offset']+.1) for e in EVENTS])
    def test_wrong_duration(self):self.reject(changed(0,offset=.30))
    def test_swapped_channels(self):
        with self.assertRaises(AssertionError):verify_timeline(signal()[::-1],RATE,EVENTS)
    def test_silence(self):
        with self.assertRaises(AssertionError):verify_timeline(signal([]),RATE,EVENTS)
    def test_subwindow_note_not_silently_skipped(self):
        events=changed(0,offset=.22)
        with self.assertRaisesRegex(AssertionError,'too short'):verify_timeline(signal(events),RATE,events)
    def test_nonfinite(self):
        values=signal();values[0][100]=float('nan')
        with self.assertRaises(AssertionError):verify_timeline(values,RATE,EVENTS)
    def test_float_wav_integrity(self):
        values=signal();pcm=b''.join(struct.pack('<ff',a,b) for a,b in zip(*values))
        fmt=struct.pack('<HHIIHH',3,2,RATE,RATE*8,8,32)
        body=b'WAVEfmt '+struct.pack('<I',16)+fmt+b'data'+struct.pack('<I',len(pcm))+pcm
        wav=b'RIFF'+struct.pack('<I',len(body))+body
        with tempfile.TemporaryDirectory() as directory:
            p=Path(directory)/'capture.wav';p.write_bytes(wav)
            rate,channels=read_wav(p);self.assertEqual(rate,RATE)
            self.assertTrue(verify_timeline(channels,rate,EVENTS)['passed'])
            for corrupt in (wav[:-1],wav+b'junk',b'bad'+wav[3:]):
                p.write_bytes(corrupt)
                with self.assertRaises(AssertionError):read_wav(p)

if __name__=='__main__':unittest.main()
