"""Build independently scheduled RD held fixtures from pinned licensed samples.

Requires numpy, scipy and soundfile from the analysis requirements. Output must
be new. The source descriptor includes every instrument's license, not just drums.
No detector is imported, run, or used to create reference labels.
"""
import argparse
import copy
import hashlib
import json
import math
from pathlib import Path
import random
import tarfile
import io

import numpy as np
import soundfile as sf
from scipy.signal import resample_poly

LANES = ('BD', 'SD', 'HH', 'TOM', 'BASS')
RATE = 16000
SEED = 2026091901


def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


class Renderer:
    def __init__(self, cache, output):
        self.root, self.out = cache.resolve(), output.resolve()
        self.out.mkdir(parents=True, exist_ok=False)
        for name in ('audio', 'annotations', 'recipes', 'timbres', 'sources'):
            (self.out/name).mkdir()
        base = json.loads((self.root/'rd02-preliminary-v7/manifest.json').read_text())
        self.manifest = dict(schema_version=1, corpus_id='rd02-scheduled-v11',
                             sources=[s for s in base['sources'] if s['id'] != 'avp-lvt-v1'],
                             clips=[c for c in base['clips'] if c['split'] == 'development'])
        assert len(self.manifest['clips']) == 40
        self.assets = [
            dict(BD='hydrogen/gm/Kick-Med.wav', SD='hydrogen/gm/Snare-Med.wav',
                 HH='hydrogen/gm/HatClosed-Med.wav', TOM='hydrogen/gm/Tom1-Med.wav',
                 BASS='freepats/electric-bass-YR/samples/finger/E.flac'),
            dict(BD='hydrogen/tr808/808_Kick_Short.flac', SD='hydrogen/tr808/808_Snare_1.flac',
                 HH='hydrogen/tr808/808_Hat_Closed.flac', TOM='hydrogen/tr808/808_Tom_Hi.flac',
                 BASS='freepats/synth-bass-2/samples/C2.flac')]
        self.samples = [{lane: self.read_sample(self.root/path) for lane, path in kit.items()}
                        for kit in self.assets]
        self.source_ids = [('hydrogen-gmrock', 'freepats-electric-bass-YR'),
                           ('hydrogen-tr808', 'freepats-synth-bass-2')]
        for kit, folder in enumerate(('electric-bass-YR', 'synth-bass-2')):
            source = next(s for s in self.manifest['sources'] if s['id'] == self.source_ids[kit][1])
            archive = self.out/'sources'/(folder+'.tar')
            members = [self.root/self.assets[kit]['BASS'], self.root/'freepats'/folder/'README.txt',
                       self.root/'freepats'/folder/'LICENSE.txt']
            with tarfile.open(archive, 'w') as tar:
                for path in members:
                    data = path.read_bytes()
                    entry = tarfile.TarInfo(path.relative_to(self.root/'freepats'/folder).as_posix())
                    entry.size, entry.mtime, entry.mode = len(data), 0, 0o644
                    tar.addfile(entry, io.BytesIO(data))
            source['archive'] = self.desc(archive)
            source['license'] = dict(spdx='CC0-1.0', url='https://creativecommons.org/publicdomain/zero/1.0/')
            source['license_evidence'] = self.desc(members[-1])
        self.hashes = set()

    def desc(self, path):
        return dict(path=path.relative_to(self.root).as_posix(), sha256=digest(path))

    def write_json(self, folder, name, value):
        path = self.out/folder/(name+'.json')
        path.write_text(json.dumps(value, sort_keys=True, indent=2)+'\n', encoding='utf-8')
        return self.desc(path)

    @staticmethod
    def read_sample(path):
        pcm, rate = sf.read(path, dtype='float64', always_2d=True)
        # These are source samples, not captured mixtures. Preserve their channels
        # as energy-safe independent lanes before deterministic stereo panning.
        pcm = pcm[:, 0]
        divisor = math.gcd(rate, RATE)
        pcm = resample_poly(pcm, RATE//divisor, rate//divisor)
        pcm = pcm[:round(.75*RATE)].copy()
        assert len(pcm) and np.max(np.abs(pcm)) > 0, path
        pcm *= .18 / np.max(np.abs(pcm))
        fade = min(len(pcm), round(.02*RATE))
        pcm[-fade:] *= np.linspace(1, 0, fade)
        return pcm

    def schedule(self, seed, bpm, duration, active, intro=0, phase=0, changing=False, ladder=False):
        rng = random.Random(seed)
        events = {lane: [] for lane in LANES}
        step, when = 0, intro + phase
        while when < duration - .1:
            for lane in active:
                if ladder:
                    hit = step % 8 == 0
                else:
                    anchors = {'BD': (0, 8), 'SD': (4, 12), 'HH': tuple(range(0,16,2)),
                               'TOM': (14,), 'BASS': (0, 6, 10)}[lane]
                    hit = step % 16 in anchors or rng.random() < .065
                if hit and when >= 0:
                    velocity = min(120, 24+16*(step//8)) if ladder else rng.randint(48, 120)
                    events[lane].append(dict(time_seconds=round(round(when*RATE)/RATE, 8), velocity=velocity))
            tempo = bpm if not changing or when < duration/2 else bpm*1.25
            when += 15/tempo
            step += 1
        return events

    def clip(self, name, kit, bpm=120, active=LANES, stratum='full_mix', split='held_out',
             duration=None, seed=0, tags=(), intro=0, phase=0, changing=False,
             clipped=False, inverted=False, ladder=False, accompaniment=True):
        duration = duration or 960/bpm
        events = self.schedule(seed, bpm, duration, active, intro, phase, changing, ladder)
        pcm = np.zeros((round(duration*RATE), 2), dtype=np.float64)
        for index, lane in enumerate(LANES):
            pan = -.35 + .7*index/4
            stereo = np.array([math.sqrt((1-pan)/2), math.sqrt((1+pan)/2)])
            for event in events[lane]:
                offset = round(event['time_seconds']*RATE)
                sample = self.samples[kit][lane][:len(pcm)-offset]
                pcm[offset:offset+len(sample)] += sample[:, None]*stereo*(event['velocity']/127)
        if accompaniment and stratum == 'full_mix' and active:
            # Additional pitched accompaniment challenges full-mixture separation;
            # it is not a reference BASS event and is declared in the render recipe.
            t = np.arange(len(pcm))/RATE
            signal = sum(np.sin(2*np.pi*f*t) for f in (330, 415.3, 493.9))*.012
            signal[t < max(0, intro)] = 0
            pcm += signal[:, None]
        if clipped:
            pcm = np.clip(pcm*12, -1, 1)
        if inverted:
            mono = np.rint(np.clip(pcm[:, 0], -1, 1) * 32767).astype(np.int16)
            pcm = np.column_stack((mono, -mono))
        audio = self.out/'audio'/(name+'.wav')
        sf.write(audio, pcm, RATE, subtype='PCM_16')
        descriptor = self.desc(audio)
        if active and descriptor['sha256'] in self.hashes:
            raise ValueError('duplicate non-silent PCM '+name)
        self.hashes.add(descriptor['sha256'])
        kind = 'isolated_stem' if len(active) <= 1 else 'frozen_submix'
        timbre = 'acoustic' if kit == 0 else 'electronic'
        timbres = {lane: timbre if lane in active else 'unverified' for lane in LANES}
        proofs = {}
        for lane in LANES:
            source = self.source_ids[kit][int(lane == 'BASS')]
            proofs[lane] = dict(timbre=timbres[lane], basis='source_render_spec',
                                source=(source+': recorded strings/Pearl DX' if kit == 0 else source+': FM/basic-wave synthesis')
                                if lane in active else 'absent by render schedule')
        annotation = self.write_json('annotations', name, dict(reference_origin='independent_render_metadata',
                           annotator_id='frozen-sample-schedule-v11', events=events))
        recipe = self.write_json('recipes', name, dict(kind=kind, seed=seed, sample_rate=RATE,
            source_assets={lane: self.desc(self.root/self.assets[kit][lane]) for lane in active},
            source_ids=self.source_ids[kit], events=events, intro_seconds=intro, record_phase_seconds=phase,
            velocity_mapping='sample peak normalized to .18, multiplied by MIDI velocity / 127',
            bass_timbre_definition='acoustic means recorded physical strings (electric bass guitar), not an upright bass',
            accompaniment='quiet sustained 330/415.3/493.9 Hz triad' if accompaniment and stratum=='full_mix' else None,
            tempo_changes=[dict(time_seconds=duration/2, bpm=bpm*1.25)] if changing else [],
            clipped_gain=12 if clipped else 1, phase_inverted_right=inverted,
            operation='frozen independent sample schedule, no classifier or model separation'))
        evidence = self.write_json('timbres', name, dict(lanes=proofs))
        clip = dict(id=name, split=split, source_id=self.source_ids[kit][0],
            additional_source_ids=[self.source_ids[kit][1]], source_song_id=name, kit_id=self.source_ids[kit][0],
            source_start_seconds=0, render=dict(kind=kind, recipe=recipe), audio=descriptor,
            annotation=annotation, timbre_evidence=evidence, duration_seconds=duration, bpm=bpm,
            stratum=stratum, timbres=timbres, tags=list(tags)+['independent_render_metadata','rendered_domain'])
        self.manifest['clips'].append(clip)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cache-root', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    r = Renderer(args.cache_root, args.output)
    for n in range(40):
        r.clip('v11-full-%02d'%n, n%2, seed=SEED+n, tags=['clean_held','straight_sixteenth'])
    for kit in (0,1):
        for index, lane in enumerate(LANES):
            r.clip('v11-isolated-%d-%s'%(kit,lane), kit, active=(lane,), stratum='isolated',
                   seed=SEED+100+kit*10+index, ladder=True, tags=['gain_ladder','independent_velocity'])
            pair = (lane, LANES[(index+1)%len(LANES)])
            r.clip('v11-sparse-%d-%s'%(kit,lane), kit, active=pair, stratum='sparse',
                   seed=SEED+200+kit*10+index, tags=['straight_sixteenth'])
    for n,bpm in enumerate((40,60,120)):
        r.clip('v11-silence-%d'%n, 0, bpm=bpm, active=(), stratum='isolated', tags=['silence'])
    r.clip('v11-clipped',0,seed=SEED+300,clipped=True,tags=['clipping'])
    r.clip('v11-phase',1,seed=SEED+301,inverted=True,tags=['phase_inverted_stereo'])
    r.clip('v11-unison',0,seed=SEED+302,active=('BD','BASS'),stratum='sparse',tags=['kick_bass_unison'])
    for n,bpm in enumerate((40,60,120,180,240)):
        r.clip('v11-acquisition-%d'%bpm,n%2,bpm=bpm,duration=45,split='acquisition',
               seed=SEED+400+n,intro=2.1,phase=.137,tags=['random_record_phase','silence_or_intro','syncopation'])
    r.clip('v11-acquisition-drift',0,bpm=120,duration=45,split='acquisition',seed=SEED+410,
           changing=True,tags=['changing_tempo'])
    r.clip('v11-acquisition-ambiguous',1,bpm=60,duration=45,split='acquisition',seed=SEED+411,
           active=('HH',),stratum='isolated',tags=['half_double_ambiguous','uncertain_downbeat'])
    r.write_json('.', 'manifest', r.manifest)
    r.write_json('.', 'build-identity', dict(renderer_sha256=digest(Path(__file__)), seed=SEED,
        unique_audio_hashes=len(r.hashes), output_clips=len(r.manifest['clips']),
        accepted=False, scope='inventory pending independent validator; not model quality evidence'))
    print(str(r.out/'manifest.json'))


if __name__ == '__main__':
    main()
