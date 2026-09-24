"""Opt-in RD-02 held-corpus regressions; require a frozen BabySlakh mount."""
import hashlib
import os
import pathlib
import struct
import unittest
import wave

from tests.rhythm_doctor.test_tempo_native import TempoNativeHarness


def midi_tempo_events(path):
    """Use mido where present, with a standard-MIDI reader for the local lane."""
    try:
        import mido
    except ImportError:
        mido = None
    if mido is not None:
        return [mido.tempo2bpm(event.tempo) for track in mido.MidiFile(path).tracks
                for event in track if event.type == "set_tempo"]
    data = path.read_bytes()
    if data[:4] != b"MThd" or len(data) < 14:
        raise ValueError("not a standard MIDI file")
    tracks = int.from_bytes(data[10:12], "big")
    position, result = 14, []

    def variable_length(offset):
        value = 0
        while True:
            byte = data[offset]
            offset += 1
            value = (value << 7) | (byte & 0x7f)
            if not byte & 0x80:
                return value, offset

    for _ in range(tracks):
        if data[position:position + 4] != b"MTrk":
            raise ValueError("missing MIDI track")
        length = int.from_bytes(data[position + 4:position + 8], "big")
        end, position, running = position + 8 + length, position + 8, None
        while position < end:
            _, position = variable_length(position)
            status = data[position]
            if status & 0x80:
                position += 1
                if status < 0xf0:
                    running = status
            elif running is not None:
                status = running
            else:
                raise ValueError("MIDI running status without status")
            if status == 0xff:
                event_type = data[position]
                length, position = variable_length(position + 1)
                payload, position = data[position:position + length], position + length
                if event_type == 0x51 and len(payload) == 3:
                    result.append(60000000.0 / int.from_bytes(payload, "big"))
            elif status in (0xf0, 0xf7):
                length, position = variable_length(position)
                position += length
            else:
                position += 1 if (status >> 4) in (0xc, 0xd) else 2
    return result


class TempoCorpusTests(TempoNativeHarness, unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        root = os.environ.get("RD_TEMPO_CORPUS_ROOT")
        if not root:
            raise RuntimeError("RD_TEMPO_CORPUS_ROOT is required for test_tempo_corpus.py")
        cls.corpus = pathlib.Path(root)
        needed = ("Track00001/mix.wav", "Track00001/MIDI/S01.mid",
                  "Track00005/mix.wav", "Track00005/MIDI/S01.mid")
        missing = [relative for relative in needed if not (cls.corpus / relative).is_file()]
        if missing:
            raise RuntimeError(f"RD_TEMPO_CORPUS_ROOT lacks frozen files: {', '.join(missing)}")
        super().setUpClass()

    def pcm_window(self, track):
        audio = self.corpus / track / "mix.wav"
        with wave.open(str(audio), "rb") as source:
            self.assertEqual((source.getnchannels(), source.getsampwidth()), (1, 2))
            rate = source.getframerate()
            pcm = source.readframes(min(source.getnframes(), rate * 45))
        return rate, [value / 32768.0 for value in struct.unpack("<" + "h" * (len(pcm) // 2), pcm)]

    def test_single_midi_tempo_failure_is_preserved_without_audio_label(self):
        audio = self.corpus / "Track00001" / "mix.wav"
        midi = self.corpus / "Track00001" / "MIDI" / "S01.mid"
        self.assertEqual(hashlib.sha256(audio.read_bytes()).hexdigest(),
                         "e6590a50b9c4d6aa84d67e03368b42e0d79d56ba4b1244c26c5b9d6ecab89f34")
        self.assertEqual(hashlib.sha256(midi.read_bytes()).hexdigest(),
                         "1fd7413b8f01be812d8b45ab9c7926fa849bdcfd6f6b1fe8763d59a53019bcfb")
        tempos = midi_tempo_events(midi)
        self.assertEqual(len(set(round(value, 6) for value in tempos)), 1)
        self.assertEqual(tempos[0], 80.01002792349975)
        rate, samples = self.pcm_window("Track00001")
        result = self.analyse(samples, rate, method="onset-ac")
        self.assertEqual((result["candidate"]["status"], result["candidate"]["reason"]),
                         ("UNCERTAIN", "phase-fit"))
        self.assertAlmostEqual(result["reported_bpm"], 41.959461, places=5)

    def test_finite_midi_tempo_changes_remain_uncertain(self):
        audio = self.corpus / "Track00005" / "mix.wav"
        midi = self.corpus / "Track00005" / "MIDI" / "S01.mid"
        self.assertEqual(hashlib.sha256(audio.read_bytes()).hexdigest(),
                         "2ada57d35631b349283bde7e6fa8339091520c956d5cd5f9920651280d63919f")
        self.assertEqual(hashlib.sha256(midi.read_bytes()).hexdigest(),
                         "12b2bc0eeb61e1a25d86bc126c9a71dae231596df501b0932c3e278b67caab29")
        tempos = midi_tempo_events(midi)
        self.assertGreater(len(set(round(value, 6) for value in tempos)), 1)
        rate, samples = self.pcm_window("Track00005")
        result = self.analyse(samples, rate, method="onset-ac")
        self.assertEqual((result["candidate"]["status"], result["candidate"]["reason"]),
                         ("UNCERTAIN", "unstable-estimates"))


if __name__ == "__main__":
    unittest.main()
