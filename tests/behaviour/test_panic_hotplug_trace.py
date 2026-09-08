import copy,unittest
from panic_hotplug_trace import verify_hotplug_sweep
def fixture(before=False,during=True):
    off=-1 if before else 40000-2;on=104000-2 if during else 204800
    rows=[dict(kind=18,port=1,connected=False,monotonic_ns=off),dict(kind=18,port=1,connected=True,monotonic_ns=on)]
    for i in range(2048):
        for port in (1,2,3):
            when=i*100+port
            if port==1 and (before or off<=when<on):continue
            rows.append(dict(kind=3,port=port,bytes=[128+i%16,i//16,0],monotonic_ns=when))
    return sorted(rows,key=lambda e:e['monotonic_ns'])
class Hotplug(unittest.TestCase):
    def test_four_intervals(self):
        for before in (False,True):
            for during in (False,True):self.assertTrue(verify_hotplug_sweep(fixture(before,during),before,during)['passed'])
    def test_missing_extra_or_wrong_message(self):
        base=fixture();index=next(i for i,e in enumerate(base) if e.get('kind')==3 and e['port']==1 and e['bytes']==[128,3,0])
        variants=[base[:index]+base[index+1:],base[:index]+[base[index]]+base[index:]]
        changed=copy.deepcopy(base);changed[index]['bytes']=[144,3,100];variants.append(changed)
        for rows in variants:
            with self.assertRaises(AssertionError):verify_hotplug_sweep(rows,False,True)
    def test_absent_port_and_replay(self):
        rows=fixture();rows.append(dict(kind=3,port=1,bytes=[128,30,0],monotonic_ns=50000))
        with self.assertRaises(AssertionError):verify_hotplug_sweep(rows,False,True)
        rows=fixture(True,True);rows.append(dict(kind=3,port=1,bytes=[128,70,0],monotonic_ns=110000))
        with self.assertRaises(AssertionError):verify_hotplug_sweep(rows,True,True)
    def test_unaffected_port_loss(self):
        rows=fixture();rows.pop(next(i for i,e in enumerate(rows) if e.get('kind')==3 and e['port']==2))
        with self.assertRaises(AssertionError):verify_hotplug_sweep(rows,False,True)
    def test_missed_overlap(self):
        with self.assertRaises(AssertionError):verify_hotplug_sweep(fixture(False,False),False,True)
    def test_missing_one_or_sixteen_prefix_tail_messages(self):
        for count in (1,16):
            with self.subTest(count=count):
                rows=fixture();off=next(e['monotonic_ns'] for e in rows if e.get('kind')==18 and not e['connected'])
                prefix=[e for e in rows if e.get('kind')==3 and e['port']==1 and e['monotonic_ns']<off]
                missing={id(e) for e in prefix[-count:]};rows=[e for e in rows if id(e) not in missing]
                with self.assertRaises(AssertionError):verify_hotplug_sweep(rows,False,True)
    def test_truncated_connected_edge(self):
        rows=fixture();rows=[e for e in rows if not(e.get('kind')==3 and e['port']==1 and 38000<e['monotonic_ns']<40000)]
        with self.assertRaises(AssertionError):verify_hotplug_sweep(rows,False,True)
if __name__=='__main__':unittest.main()
