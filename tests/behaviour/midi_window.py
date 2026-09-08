"""Loss-detecting MIDI collection from the emulator's bounded public snapshots."""
class MidiWindow:
    def __init__(self,after):
        assert type(after) is int and after>=0
        self.after=after;self.cursor=after;self.events=[]

    def extend(self,state):
        capture=state['midi_capture'];count=state['midi_count']
        assert capture['dropped']==0,'MIDI capture reported dropped events'
        assert count==capture['count'] and count>=self.cursor,'MIDI capture count regressed or disagrees'
        assert capture['tail_start']<=self.cursor+1,'MIDI snapshot retention gap: observe more frequently'
        fresh=[event for event in state['midi'] if event['index']>self.cursor]
        assert [event['index'] for event in fresh]==list(range(self.cursor+1,count+1)),'MIDI capture has missing or unordered events'
        self.events.extend(fresh);self.cursor=count
        return self

    def note_ons(self):
        return [event for event in self.events if 144<=event['bytes'][0]<=159 and event['bytes'][2]>0]
