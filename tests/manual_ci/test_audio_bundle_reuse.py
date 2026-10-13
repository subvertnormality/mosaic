"""CI reuse must bind an original successful recording and immutable bytes."""
import copy
import importlib.util
import hashlib
from pathlib import Path
import tempfile
import unittest
import yaml

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location(
    'audio_bundle_reuse', ROOT / '.github/scripts/audio_bundle_reuse.py')
reuse = importlib.util.module_from_spec(spec)
spec.loader.exec_module(reuse)


class AudioBundleReuseTests(unittest.TestCase):
    def test_audio_identity_includes_course_validation_inputs(self):
        workflow = yaml.safe_load((ROOT / '.github/workflows/manual-build.yml').read_text())
        steps = workflow['jobs']['record-audio']['steps']
        identity = next(s for s in steps if s.get('id') == 'audio-identity')['run']
        for dependency in ('manual/course.yaml', 'tools/manual_course_cases.py'):
            with self.subTest(dependency=dependency):
                self.assertIn(dependency, identity)

    def test_invalid_current_course_is_not_repaired_by_recording(self):
        for message in ('course stage missing', 'course contract differs from first-sound'):
            with self.subTest(message=message):
                def invalid(): raise ValueError(message)
                with self.assertRaisesRegex(ValueError, message):
                    reuse.qualify_audio(invalid, lambda: dict(passed=True))

    def test_fresh_audio_is_cached_even_after_a_stale_candidate(self):
        workflow = yaml.safe_load((ROOT / '.github/workflows/manual-build.yml').read_text())
        steps = workflow['jobs']['record-audio']['steps']
        recording = next(s for s in steps if s.get('name') == 'Lint, unit-test and record every audio example')
        upload = next(s for s in steps if s.get('name') == 'Keep this recording for identical audio inputs')
        self.assertEqual(recording.get('id'), 'audio-assets')
        self.assertEqual(upload['if'], "steps.audio-assets.outputs.audio_recorded == 'true'")

    def setUp(self):
        self.pin = dict(schema_version=1, run_id=10, run_attempt=1,
                        head_sha='b' * 40, artifact_name='manual-audio-10',
                        archive_sha256='c' * 64, tar_sha256='d' * 64,
                        report_sha256='e' * 64)
        self.run = dict(run_attempt=1, head_sha='b' * 40, event='pull_request',
                        path='.github/workflows/manual-build.yml',
                        repository=dict(full_name='subvertnormality/mosaic'),
                        head_repository=dict(full_name='subvertnormality/mosaic'))
        self.artifact = dict(name='manual-audio-10', expired=False,
                             digest='sha256:' + 'c' * 64)
        self.job = dict(name='Record manual audio assets', conclusion='success')
        self.cached = []

    def api(self, path):
        if '/actions/artifacts?' in path:
            return dict(artifacts=self.cached)
        if path.endswith('/artifacts?per_page=100'):
            return dict(artifacts=[self.artifact])
        if '/attempts/1/jobs?' in path:
            return dict(jobs=[self.job])
        return self.run

    def find(self):
        return reuse.find_bundle('subvertnormality/mosaic', 'a' * 40,
                                 self.pin, self.api)

    def test_pinned_fallback_preserves_original_run_and_name(self):
        self.assertEqual(self.find(), dict(run_id=10, artifact_name='manual-audio-10', pinned=True))

    def test_exact_input_cache_takes_precedence(self):
        self.cached = [dict(name='manual-audio-src-' + 'a' * 40, expired=False,
                            workflow_run=dict(id=20))]
        self.assertEqual(self.find(), dict(run_id=20, artifact_name=self.cached[0]['name'], pinned=False))

    def test_changed_producer_or_failed_recording_is_rejected(self):
        original = copy.deepcopy(self.run)
        mutations = [('head_sha', 'f' * 40), ('run_attempt', 2),
                     ('event', 'workflow_dispatch'), ('path', 'other.yml'),
                     ('head_repository', dict(full_name='fork/mosaic'))]
        for key, value in mutations:
            with self.subTest(key=key):
                self.run = dict(original, **{key: value})
                with self.assertRaises(ValueError): self.find()
        self.run = original
        self.job['conclusion'] = 'failure'
        with self.assertRaises(ValueError): self.find()

    def test_changed_artifact_digest_is_rejected(self):
        self.artifact['digest'] = 'sha256:' + 'f' * 64
        with self.assertRaises(ValueError): self.find()

    def test_expired_recording_is_unavailable(self):
        self.artifact['expired'] = True
        self.assertIsNone(self.find())

    def test_bundle_pin_rejects_changed_tar_or_report(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / 'audio.tar').write_bytes(b'original sealed evidence')
            (root / 'report.sha256').write_text('e' * 64 + '\n')
            pin = dict(self.pin, tar_sha256=hashlib.sha256((root / 'audio.tar').read_bytes()).hexdigest())
            reuse.verify_bundle(root, pin)
            (root / 'audio.tar').write_bytes(b'changed evidence')
            with self.assertRaises(ValueError): reuse.verify_bundle(root, pin)
            (root / 'audio.tar').write_bytes(b'original sealed evidence')
            (root / 'report.sha256').write_text('f' * 64)
            with self.assertRaises(ValueError): reuse.verify_bundle(root, pin)

    def test_changed_inputs_require_recording_but_corrupt_evidence_is_fatal(self):
        def changed(): raise ValueError('stale audio authoring')
        def corrupt(): raise ValueError('native PCM hash')
        def passed(): return dict(passed=True)
        self.assertFalse(reuse.qualify_audio(changed, passed)['reusable'])
        with self.assertRaises(ValueError): reuse.qualify_audio(corrupt, passed)
        with self.assertRaises(ValueError): reuse.qualify_audio(passed, lambda: dict(passed=False))
        self.assertTrue(reuse.qualify_audio(passed, passed)['reusable'])


if __name__ == '__main__': unittest.main()
