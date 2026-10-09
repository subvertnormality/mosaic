"""Publication audit tests for preserved failed audio retries."""
import json
import tempfile
import unittest
from pathlib import Path
import manual_publication_verify as publication

class RetakeAudit(unittest.TestCase):
    def make_report(self, root):
        case="ghost-note-comparison-midi-real-time"
        failed=root/case
        failed.mkdir()
        failure={"category":"timing","clock_mode":"real-time","kind":"Musical gate",
                 "packet":{"logical_ns":None,"monotonic_ns":100,"bytes":[128,60,100],"index":9},
                 "row":{"step":28,"length":0.5}}
        (failed/"lesson-failure.json").write_text(json.dumps(failure,sort_keys=True))
        receipt={"case":case,"path":str(failed),"clock_mode":"real-time","attempt":1,"max_attempts":3,
                 "error_type":"AssertionError","error":"Musical gate","retake_eligible":True,
                 "worker_failure":failure,"worker_failure_sha256":publication.digest(failed/"lesson-failure.json")}
        receipt_path=failed/"retake-receipt.json"
        receipt_path.write_text(json.dumps(receipt,sort_keys=True))
        public=dict(receipt,receipt_sha256=publication.digest(receipt_path))
        final=root/(case+"-retake-1")
        final.mkdir()
        (final/"lesson-result.json").write_text(json.dumps({"passed":True,"clock_mode":"real-time","path":str(final)}))
        lane={"clock_mode":"real-time","path":str(final),"passed":True,"retakes":[public]}
        report={"examples":[{"id":"ghost-note-comparison","musical_evidence":[lane]}]}
        return report,failed,receipt_path,final

    def test_valid_retry_and_preserved_worker_failure_pass(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);report,*_=self.make_report(root)
            result=publication.verify_audio_retake_receipts(report,root)
            self.assertEqual(result,{"lanes":1,"retakes":1,"passed":True})

    def test_missing_receipt_is_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);report,failed,receipt,final=self.make_report(root);receipt.unlink()
            with self.assertRaises(ValueError):publication.verify_audio_retake_receipts(report,root)

    def test_changed_receipt_is_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);report,failed,receipt,final=self.make_report(root);receipt.write_text(receipt.read_text()+" ")
            with self.assertRaises(ValueError):publication.verify_audio_retake_receipts(report,root)

    def test_changed_worker_failure_is_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);report,failed,receipt,final=self.make_report(root)
            (failed/"lesson-failure.json").write_text("{}")
            with self.assertRaises(ValueError):publication.verify_audio_retake_receipts(report,root)

    def test_out_of_root_attempt_is_rejected(self):
        with tempfile.TemporaryDirectory() as d, tempfile.TemporaryDirectory() as outside:
            root=Path(d);report,failed,receipt,final=self.make_report(root)
            row=report["examples"][0]["musical_evidence"][0]["retakes"][0]
            row["path"]=str(Path(outside))
            with self.assertRaises((ValueError,FileNotFoundError)):publication.verify_audio_retake_receipts(report,root)

    def test_unreported_attempt_archive_is_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);report,failed,receipt,final=self.make_report(root)
            report["examples"][0]["musical_evidence"][0].pop("retakes")
            with self.assertRaises(ValueError):publication.verify_audio_retake_receipts(report,root)

    def test_failed_archive_without_receipt_or_report_row_is_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);report,failed,receipt,final=self.make_report(root)
            receipt.unlink()
            report["examples"][0]["musical_evidence"][0].pop("retakes")
            self.assertTrue((failed/"lesson-failure.json").is_file())
            with self.assertRaises(ValueError):publication.verify_audio_retake_receipts(report,root)

    def test_legacy_single_attempt_lane_needs_no_fabricated_receipt(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);legacy=root/"ghost-note-comparison-midi-controlled-experimental";legacy.mkdir()
            report={"examples":[{"id":"ghost-note-comparison","musical_evidence":[
                {"clock_mode":"controlled-experimental","path":str(legacy),"passed":True}]}]}
            result=publication.verify_audio_retake_receipts(report,root)
            self.assertEqual(result,{"lanes":1,"retakes":0,"passed":True})

    def test_unrelated_failure_archive_is_ignored(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);legacy=root/"ghost-note-comparison-midi-controlled-experimental";legacy.mkdir()
            unrelated=root/"unrelated-tool-failure";unrelated.mkdir()
            (unrelated/"lesson-failure.json").write_text('{"category":"exception"}')
            report={"examples":[{"id":"ghost-note-comparison","musical_evidence":[
                {"clock_mode":"controlled-experimental","path":str(legacy),"passed":True}]}]}
            result=publication.verify_audio_retake_receipts(report,root)
            self.assertEqual(result,{"lanes":1,"retakes":0,"passed":True})

    def test_generated_retry_directory_without_markers_or_report_row_is_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);report,failed,receipt,final=self.make_report(root)
            receipt.unlink();(failed/"lesson-failure.json").unlink()
            report["examples"][0]["musical_evidence"][0].pop("retakes")
            self.assertTrue(failed.is_dir())
            self.assertEqual(final.name,"ghost-note-comparison-midi-real-time-retake-1")
            with self.assertRaises(ValueError):publication.verify_audio_retake_receipts(report,root)

    def test_retry_path_rejects_missing_prior_attempt_directory(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);report,failed,receipt,final=self.make_report(root)
            receipt.unlink();(failed/"lesson-failure.json").unlink()
            failed.rmdir()
            report["examples"][0]["musical_evidence"][0].pop("retakes")
            self.assertEqual(final.name,"ghost-note-comparison-midi-real-time-retake-1")
            with self.assertRaises(ValueError):publication.verify_audio_retake_receipts(report,root)

    def test_legacy_realtime_base_path_lane_remains_valid(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);legacy=root/"ghost-note-comparison-midi-real-time";legacy.mkdir()
            (legacy/"lesson-result.json").write_text(json.dumps({"passed":True,"clock_mode":"real-time","path":str(legacy)}))
            report={"examples":[{"id":"ghost-note-comparison","musical_evidence":[
                {"clock_mode":"real-time","path":str(legacy),"passed":True}]}]}
            result=publication.verify_audio_retake_receipts(report,root)
            self.assertEqual(result,{"lanes":1,"retakes":0,"passed":True})

    def test_out_of_root_success_path_does_not_hide_generated_archive(self):
        with tempfile.TemporaryDirectory() as d, tempfile.TemporaryDirectory() as outside:
            root=Path(d);archive=root/"ghost-note-comparison-midi-real-time";archive.mkdir()
            (archive/"retake-receipt.json").write_text('{}')
            external=Path(outside)/archive.name;external.mkdir()
            report={"examples":[{"id":"ghost-note-comparison","musical_evidence":[
                {"clock_mode":"real-time","path":str(external),"passed":True}]}]}
            with self.assertRaises(ValueError):publication.verify_audio_retake_receipts(report,root)

    def test_failed_base_attempt_cannot_be_reported_as_success(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);report,failed,receipt,final=self.make_report(root)
            (final/"lesson-result.json").unlink();final.rmdir()
            lane=report["examples"][0]["musical_evidence"][0]
            lane.pop("retakes");lane["path"]=str(failed)
            self.assertTrue((failed/"lesson-failure.json").is_file())
            self.assertTrue((failed/"retake-receipt.json").is_file())
            with self.assertRaises(ValueError):publication.verify_audio_retake_receipts(report,root)

    def test_controlled_lane_cannot_claim_retakes(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);report,failed,receipt,final=self.make_report(root)
            report["examples"][0]["musical_evidence"][0]["clock_mode"]="controlled-experimental"
            with self.assertRaises(ValueError):publication.verify_audio_retake_receipts(report,root)

if __name__=="__main__":unittest.main()
