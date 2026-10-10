"""Run the real course MIDI oracle against synthetic event streams; not native qualification."""
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent/'tools'))
import manual_course_cases as course

STAGE="build-a-phrase-compare"


def scheduled_events(*,wrong=False,missing=False,late_boundary=False,extra=False):
    period,expected=course.CONTRACTS[STAGE]
    records=[]
    rows=[(cycle,row) for cycle in range(2) for row in expected]
    rows.append((2,sorted(expected,key=lambda item:item['step'])[0]))
    for cycle,row in rows:
        if missing and cycle==1 and row['step']==8:
            continue
        note=row['note']
        if wrong and cycle==0 and row['step']==4:
            note+=1
        onset_step=cycle*period+row['step']
        onset_ns=round(onset_step*1_000_000_000/6)
        if late_boundary and cycle==2:
            onset_ns+=10_000_000_000
        release_ns=onset_ns+round(row['length']*1_000_000_000/6)
        records.append((onset_ns,row['port'],[row['status'],note,row['velocity']]))
        records.append((release_ns,row['port'],[row['status']-16,note,row['velocity']]))
    if extra:
        # An unplanned onset between the first two expected notes, inside the checked window.
        onset_ns=round(2*1_000_000_000/6)
        release_ns=onset_ns+round(.5*1_000_000_000/6)
        records.extend([(onset_ns,1,[144,67,70]),(release_ns,1,[128,67,70])])
    records.sort(key=lambda item:item[0])
    return [dict(index=i+1,logical_ns=when,port=port,bytes=payload)
            for i,(when,port,payload) in enumerate(records)]


class FakeUI:
    def __init__(self,driver):self.driver=driver
    def play(self):self.driver.play()
    def stop(self):self.driver.stop()


class SyntheticDriver:
    """Public-output double: logical clock, captured MIDI, and play/stop only."""
    def __init__(self,events):
        self.clock_mode="controlled-experimental"
        self.logical_ns=0
        self.observations=[]
        self.results=[]
        self.wait_observation_limit=None
        self.events=events
        self.emitted=[]
        self.playing=False
        self.advances=[]
        self.ui=FakeUI(self)
    def play(self):self.playing=True
    def stop(self):
        self._collect_due()
        outstanding=self._outstanding()
        for port,status,note,velocity in outstanding:
            index=max((m['index'] for m in self.emitted),default=0)+1
            self.emitted.append(dict(index=index,logical_ns=self.logical_ns,port=port,
                                     bytes=[status-16,note,velocity]))
        self.playing=False
    def _collect_due(self):
        if self.playing:
            known={m['index'] for m in self.emitted}
            self.emitted.extend(m for m in self.events
                                if m['index'] not in known and m['logical_ns']<=self.logical_ns)
            self.emitted.sort(key=lambda item:item['index'])
    def _outstanding(self):
        opened={}
        for event in self.emitted:
            port,(status,note,velocity)=event['port'],event['bytes']
            if 144<=status<=159 and velocity>0:
                opened[(port,status,note)]=(port,status,note,velocity)
            elif 128<=status<=143:
                opened.pop((port,status+16,note),None)
        return list(opened.values())
    def snapshot(self):
        self._collect_due()
        state={'midi':list(self.emitted),'midi_count':len(self.emitted),
               'midi_capture':{'outstanding':self._outstanding()},'grid':[0]*128}
        self.observations.append({'state':state})
        return state
    def elapse(self,seconds):
        delta=round(seconds*1_000_000_000)
        self.advances.append(delta)
        self.logical_ns+=delta
    def wait(self,predicate,timeout=3):
        start=len(self.observations)
        logical_end=self.logical_ns+round(timeout*1_000_000_000)
        retained_limit=self.wait_observation_limit
        while True:
            state=self.snapshot()
            if retained_limit is None:
                if len(self.observations)>start+2:del self.observations[start+1:-1]
            elif len(self.observations)>start+retained_limit:
                del self.observations[start+retained_limit:]
                raise AssertionError("Wait observation retention limit exceeded")
            if predicate(state):return state
            if self.logical_ns>=logical_end:break
            self.elapse(min(.01,(logical_end-self.logical_ns)/1_000_000_000))
        raise AssertionError('Required observable output did not arrive')


def run_musical(events,old_polling):
    driver=SyntheticDriver(events)
    if old_polling:
        def legacy_wait(context,predicate,timeout):
            return context.wait(predicate,timeout)
        poll_patch=patch.object(course,'course_audition_wait',side_effect=legacy_wait)
    else:
        poll_patch=patch.object(course,'course_audition_wait',wraps=course.course_audition_wait)
    with patch.object(course,'playing_frame'), patch.object(course.time,'monotonic',return_value=0), poll_patch:
        try:
            course.musical(driver,STAGE,later=('masks',{'channel':1}))
        except AssertionError as error:
            return False,str(error),driver
    return True,None,driver


class CourseAuditionPollingTests(unittest.TestCase):
    def test_actual_musical_oracle_accepts_same_exact_two_cycles_under_both_polls(self):
        events=scheduled_events()
        old_ok,old_error,old=run_musical(events,old_polling=True)
        new_ok,new_error,new=run_musical(events,old_polling=False)
        self.assertTrue(old_ok,old_error)
        self.assertTrue(new_ok,new_error)
        self.assertEqual(new.results,old.results)
        self.assertEqual(new.results[0]['kind'],'manual-course-midi')
        self.assertEqual(new.results[0]['midi_end_index'],old.results[0]['midi_end_index'])
        self.assertLess(len(new.advances),len(old.advances))
        self.assertTrue(all(0<advance<=100_000_000 for advance in new.advances))

    def test_actual_musical_oracle_rejects_wrong_pitch_with_both_polls(self):
        for old_polling in (True,False):
            accepted,error,_=run_musical(scheduled_events(wrong=True),old_polling)
            self.assertFalse(accepted)
            self.assertIn(STAGE,error)

    def test_actual_musical_oracle_rejects_missing_note_with_both_polls(self):
        for old_polling in (True,False):
            accepted,error,driver=run_musical(scheduled_events(missing=True),old_polling)
            self.assertFalse(accepted)
            self.assertEqual(error,'Required observable output did not arrive')
            self.assertEqual(error,'Required observable output did not arrive')

    def test_actual_musical_oracle_rejects_boundary_after_deadline_with_both_polls(self):
        for old_polling in (True,False):
            accepted,error,_=run_musical(scheduled_events(late_boundary=True),old_polling)
            self.assertFalse(accepted)
            self.assertEqual(error,'Required observable output did not arrive')

    def test_actual_musical_oracle_rejects_extra_in_window_note_with_both_polls(self):
        for old_polling in (True,False):
            accepted,error,_=run_musical(scheduled_events(extra=True),old_polling)
            self.assertFalse(accepted)

    def test_controlled_poll_respects_logical_deadline_and_100ms_bound(self):
        driver=SyntheticDriver([])
        with patch.object(course.time,'monotonic',return_value=0):
            with self.assertRaisesRegex(AssertionError,'Required observable output'):
                course.course_audition_wait(driver,lambda state:False,timeout=.25)
        self.assertEqual(driver.logical_ns,250_000_000)
        self.assertTrue(all(0<advance<=100_000_000 for advance in driver.advances))

    def test_controlled_poll_keeps_observation_retention_guard(self):
        driver=SyntheticDriver([])
        driver.wait_observation_limit=1
        with patch.object(course.time,'monotonic',return_value=0):
            with self.assertRaisesRegex(AssertionError,'retention limit exceeded'):
                course.course_audition_wait(driver,lambda state:False,timeout=1)
        self.assertEqual(len(driver.observations),1)

    def test_real_time_delegates_to_shared_driver_wait(self):
        sentinel=object()
        calls=[]
        driver=type('RealtimeDriver',(),{})()
        driver.clock_mode='real-time'
        driver.wait=lambda predicate,timeout:(calls.append((predicate,timeout)),sentinel)[1]
        self.assertIs(course.course_audition_wait(driver,lambda state:True,timeout=2.5),sentinel)
        self.assertEqual(len(calls),1)
        self.assertEqual(calls[0][1],2.5)


if __name__=='__main__':
    unittest.main()
