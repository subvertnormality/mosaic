"""Mask MIDI packet parsing regression against preserved native packet rows."""
import copy
import importlib.util
import json
import os
from pathlib import Path
import sys
import unittest

ROOT=Path(os.environ.get('MOSAIC_REPO_ROOT',Path(__file__).resolve().parents[2])).resolve()
CASE_SOURCE=Path(os.environ.get('MOSAIC_MASK_CLEARING_CASE',ROOT/'tests/behaviour/mask_clearing.py')).resolve()
sys.path.insert(0,str(ROOT/'tools'))
sys.path.insert(0,str(ROOT/'tests/behaviour'))
from note_accounting import note_pairs

spec=importlib.util.spec_from_file_location('mask_clearing_under_test',CASE_SOURCE)
mask_case=importlib.util.module_from_spec(spec);spec.loader.exec_module(mask_case)
FIXTURE=json.loads((Path(__file__).parent/'fixtures/mask-midi-packets.json').read_text())
FULL_HISTORY=FIXTURE['full_history_snapshot']

def events(section):return [copy.deepcopy(row['event']) for row in FIXTURE[section]]
def note_on(event):return 144<=event['bytes'][0]<=159 and event['bytes'][2]>0

class MaskClearingMidiPacketTests(unittest.TestCase):
    def test_fixture_is_bound_to_preserved_failure_and_successful_control(self):
        proof=FIXTURE['provenance']
        self.assertEqual(proof['failed_run'],'a2266acb2b39422bac13f270e0649de8')
        self.assertEqual(proof['failed_report_sha256'],'4080732c460283bb0d225df9bb21ee0718fe60a150cd5cc63fd2eb796ba8973e')
        self.assertEqual(proof['failed_observations_sha256'],'45ee418bc8e766d804e1c385f6a08115dfdc4d85d7fcc8911579b049921a20ca')
        self.assertEqual(proof['successful_control_case'],'M-MASK-007')
        self.assertEqual(proof['successful_control_observations_sha256'],'36cfd922910b42231a672b9d4f98b6b3e55472723149b082129f78161902d324')
        self.assertEqual(proof['session_id'],'9a3d7fcd04514d5c9b38d0549992a576')
        self.assertEqual(FULL_HISTORY['observation_sha256'],proof['failed_observations_sha256'])
        self.assertEqual(FULL_HISTORY['observation_index'],30)
        self.assertEqual(FULL_HISTORY['midi_count'],FULL_HISTORY['midi_capture']['count'])
        self.assertEqual(FULL_HISTORY['midi'][0]['index'],FULL_HISTORY['midi_capture']['tail_start'])
        self.assertEqual(FULL_HISTORY['midi'][-1]['index'],FULL_HISTORY['midi_count'])

    def test_saved_coalesced_packet_explains_baseline_failure(self):
        packets=events('coalesced_chord_packets')
        on_packets=[packet for packet in packets if note_on(packet)]
        self.assertEqual([packet['index'] for packet in on_packets],[18,24])
        self.assertTrue(all(len(packet['bytes'])==6 for packet in on_packets))
        decoded=[(packet['port'],[144,*message['data']])
                 for packet in on_packets for message in packet['decoded']]
        self.assertEqual(decoded,[(1,[144,60,127]),(1,[144,67,127]),(1,[144,62,117]),(1,[144,71,117])])
        # This is Driver.playback's baseline packet-level comparison: a packet
        # is counted once and its entire bytes array is compared to one message.
        raw_actual=[(packet['port'],packet['bytes']) for packet in on_packets]
        wanted=decoded[:len(raw_actual)]
        self.assertNotEqual(raw_actual,wanted)
        self.assertEqual(FIXTURE['baseline_failure']['reported_expected_messages'],25)
        self.assertEqual(FIXTURE['baseline_failure']['reported_actual_packets'],25)
        self.assertEqual(FIXTURE['baseline_failure']['actual_packet_note_message_count'],2)

    def test_strict_parser_expands_saved_chord_packets_and_preserves_gates(self):
        packets=events('coalesced_chord_packets')
        expanded=mask_case._expanded_mask_note_events(packets,after_index=17)
        self.assertEqual([event['bytes'] for event in expanded],[
            [144,60,127],[144,67,127],[128,60,127],[128,67,127],
            [144,62,117],[144,71,117],[128,62,117],[128,71,117],
        ])
        self.assertEqual([event['packet_index'] for event in expanded],[18,18,19,19,24,24,25,25])
        pairs=note_pairs(expanded)
        self.assertEqual([(on['bytes'][1],on['bytes'][2]) for on,off in pairs],[(60,127),(67,127),(62,117),(71,117)])
        self.assertTrue(all(abs((off['logical_ns']-on['logical_ns'])/1e9-1/6)<1e-8 for on,off in pairs))
        self.assertEqual([(on['logical_ns'],on['bytes'][1]) for on,off in pairs],[(11280000000,60),(11280000000,67),(11446666666,62),(11446666666,71)])

    def test_saved_single_message_packets_keep_the_original_shape(self):
        packets=events('single_message_packets')
        on_packets=[packet for packet in packets if note_on(packet)]
        expanded=mask_case._expanded_mask_note_events(packets,after_index=17)
        self.assertEqual([packet['bytes'] for packet in on_packets],[[144,72,127],[144,74,117]])
        self.assertEqual([(event['port'],event['bytes']) for event in expanded if note_on(event)],
                         [(1,[144,72,127]),(1,[144,74,117])])
        self.assertEqual(len(note_pairs(expanded)),2)
        baseline_actual=[(packet['port'],packet['bytes']) for packet in on_packets]
        self.assertEqual(baseline_actual,[(1,[144,72,127]),(1,[144,74,117])])


    def test_actual_full_history_with_nonzero_marker_filters_only_new_packets(self):
        state={key:copy.deepcopy(FULL_HISTORY[key]) for key in ('midi_count','midi_capture','midi')}
        self.assertGreater(state['midi_count'],17)
        self.assertEqual(state['midi_capture']['tail_start'],1)
        self.assertEqual(state['midi'][0]['index'],1)
        expanded=mask_case._expanded_mask_state(state,after_index=17)
        self.assertTrue(expanded)
        self.assertTrue(all(event['packet_index']>17 for event in expanded))
        self.assertEqual([event['index'] for event in expanded],sorted(event['index'] for event in expanded))
        self.assertEqual([event['bytes'] for event in expanded[:4]],[
            [144,60,127],[144,67,127],[128,60,127],[128,67,127]])

    def test_capture_tail_loss_and_discontinuity_are_rejected(self):
        state={key:copy.deepcopy(FULL_HISTORY[key]) for key in ('midi_count','midi_capture','midi')}
        state['midi_capture']['tail_start']=11
        state['midi_capture']['tail_limit']=152  # synthetic bounded-tail negative case
        state['midi']=state['midi'][10:]
        with self.assertRaisesRegex(AssertionError,'tail starts after playback marker'):
            mask_case._expanded_mask_state(state,after_index=9)
        state={key:copy.deepcopy(FULL_HISTORY[key]) for key in ('midi_count','midi_capture','midi')}
        state['midi'].pop(4)
        with self.assertRaisesRegex(AssertionError,'incomplete or unordered'):
            mask_case._expanded_mask_state(state,after_index=17)

    def test_malformed_or_mismatched_packets_are_rejected(self):
        for packet in (
            {'index':1,'port':1,'bytes':[144,60]},
            {'index':1,'port':1,'bytes':[144,60,127,61,100]},
            {'index':1,'port':1,'bytes':[144,60,256]},
            {'index':1,'port':1,'bytes':[144,60,127], 'decoded':[{'type':'note_on','channel':1,'data':[61,127]}]},
        ):
            with self.subTest(packet=packet),self.assertRaises(AssertionError):
                mask_case._strict_midi_messages(packet)

    def test_oversized_message_packets_are_rejected(self):
        # A malformed or runaway packet cannot bypass exact event counting.
        packet={'index':1,'port':1,'bytes':([0xF8]*64)}
        with self.assertRaises(AssertionError):mask_case._strict_midi_messages(packet)

if __name__=='__main__':unittest.main()