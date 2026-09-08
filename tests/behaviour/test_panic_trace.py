import copy,unittest
from panic_trace import verify_panic_trace

class PanicTraceTests(unittest.TestCase):
    def fixture(self):
        events=[]
        for port in (1,2,3):
            for note in range(128):
                for channel in range(16):
                    n=len(events)+1
                    events.append(dict(kind=11,sequence=n,index=n,port=port,bytes=[128+channel,note,0],logical_ns=1_000_000_000))
        window=dict(type='panic',after=0,cursor=len(events),source='song',button=5,repeat=0,minimum_ns=1_000_000_000)
        return events,window
    def test_complete_dense_output(self):
        events,window=self.fixture();reports=[]
        verify_panic_trace(events,[window],11,reports)
        self.assertEqual(reports[-1]['note_events'],6144)
    def test_missing_extra_wrong_data_and_early(self):
        for mutation in ('missing','extra','port','channel','velocity','early'):
            events,window=self.fixture()
            if mutation=='missing':events.pop(12)
            elif mutation=='extra':events.append(copy.deepcopy(events[-1]))
            elif mutation=='port':events[12]['port']=2
            elif mutation=='channel':events[12]['bytes'][0]=128
            elif mutation=='velocity':events[12]['bytes'][2]=1
            else:events[12]['logical_ns']-=1
            for n,event in enumerate(events,1):event.update(sequence=n,index=n)
            window['cursor']=len(events)
            with self.assertRaises(AssertionError,msg=mutation):verify_panic_trace(events,[window],11,[])
    def test_notes_outside_window(self):
        for messages in ([[128,60,0]],[[144,60,100],[128,60,0]],[[144,60,0]]):
            events,window=self.fixture()
            for message in messages:
                n=len(events)+1;events.append(dict(kind=11,sequence=n,index=n,port=1,bytes=message,logical_ns=2_000_000_000))
            with self.assertRaises(AssertionError):verify_panic_trace(events,[window],11,[])
    def test_selected_silence_and_complete_melody(self):
        empty=dict(type='panic',after=0,cursor=0,source='channel',button=3,repeat=0,minimum_ns=0)
        verify_panic_trace([], [empty],11,[])
        events=[]
        for i in range(9):
            pitch,velocity=((60,127),(62,117),(64,107),(65,97))[i%4]
            for status in (144,128):
                n=len(events)+1;events.append(dict(kind=11,sequence=n,index=n,port=1,bytes=[status,pitch,velocity],logical_ns=n))
        windows=[empty,dict(type='melody',after=0,cursor=18)]
        verify_panic_trace(events,windows,11,[])
        events[2]['bytes'][1]=60
        with self.assertRaises(AssertionError):verify_panic_trace(events,windows,11,[])

if __name__=='__main__':unittest.main()
