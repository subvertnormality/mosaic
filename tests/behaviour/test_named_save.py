"""Deterministic result records for the named-save behaviour case."""

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from driver import digest
from named_save import named_save_load


class FakeUi:
    def __init__(self, case):
        self.case = case
        self.pending_save = False
        self.typed = False
        self.key3_count = 0

    def tap_control(self, control, index=None):
        if control == "pattern_note_degree":
            self.case.edited = True

    def select_project_action(self, action, returning=False):
        assert action == "save"
        self.pending_save = True
        self.typed = False
        self.key3_count = 0

    def select_project_file(self, name, returning=False):
        assert name in ("newB.ptn", "new.ptn")

    def turn(self, encoder, detents):
        if self.pending_save and encoder == 2 and detents == 1:
            self.typed = True

    def press_key(self, key):
        if key == 2:
            self.pending_save = False
        elif key == 3 and self.pending_save:
            self.key3_count += 1
            if not self.typed or self.key3_count == 2:
                name = "newB" if self.typed else "new"
                self.case.write_pair(name)
                self.pending_save = False


class FakeCase:
    def __init__(self, directory, salt, tamper_after_idle=False):
        self.data_directory = Path(directory)
        self.salt = salt
        self.tamper_after_idle = tamper_after_idle
        self.results = []
        self.ui = FakeUi(self)
        self.edited = False
        self.elapsed = 0
        self.autosaved = False

    def tap(self, x, y):
        if (x, y) == (4, 3):
            self.edited = True

    def key(self, key):
        self.ui.press_key(key)

    def enc(self, encoder, detents):
        self.ui.turn(encoder, detents)

    def configure(self):
        pass

    def playback(self, expected):
        pass

    def write_pair(self, name):
        content = "B" if self.edited else "A"
        (self.data_directory / (name + ".ptn")).write_bytes(
            ("%s:%s:%s" % (self.salt, name, content)).encode()
        )
        (self.data_directory / (name + ".pset")).write_bytes(
            ("%s:settings" % name).encode()
        )

    def elapse(self, seconds):
        self.elapsed += seconds
        if self.elapsed >= 61.5 and not self.autosaved:
            self.write_pair("autosave")
            self.autosaved = True
            if self.tamper_after_idle:
                (self.data_directory / "newB.ptn").write_bytes(b"tampered")


class NamedSaveResultTests(unittest.TestCase):
    def run_case(self, salt, tamper_after_idle=False):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        case = FakeCase(directory.name, salt, tamper_after_idle)
        # The raw-UI baseline imports these navigation helpers inside the case.
        # The fake only models their save/load effect; both source variants
        # retain their own tap/key/encoder sequence in production.
        with patch("persisted_ranges.select_project_action",
                   side_effect=lambda c, offset, returning=False:
                       c.ui.select_project_action("save", returning=returning)), \
             patch("persisted_ranges.select_project_file",
                   side_effect=lambda c, name, returning=False:
                       c.ui.select_project_file(name, returning=returning)):
            named_save_load(case)
        return case

    def test_result_records_describe_relationships_across_distinct_raw_hashes(self):
        first = self.run_case("first")
        second = self.run_case("second")
        self.assertNotEqual(
            digest(first.data_directory / "new.ptn"),
            digest(second.data_directory / "new.ptn"),
        )
        self.assertEqual(first.results, second.results)
        by_stage = {entry["stage"]: entry for entry in first.results}
        self.assertEqual(by_stage["save-default-name"]["files_state"], "created")
        self.assertEqual(by_stage["save-typed-name"]["files_state"], "created")
        self.assertEqual(by_stage["autosave-preserves-named"]["autosave_state"], "created")
        self.assertEqual(by_stage["autosave-preserves-named"]["named_saves"], "unchanged")
        self.assertEqual(by_stage["overwrite-default-name"]["files_state"], "changed")
        self.assertEqual(by_stage["overwrite-default-name"]["typed_save"], "unchanged")
        for entry in first.results:
            self.assertNotIn("files", entry)
            self.assertNotIn("autosave", entry)

    def test_raw_digest_assertion_still_catches_named_save_tampering(self):
        with self.assertRaisesRegex(AssertionError, "Autosave overwrote a named save"):
            self.run_case("tampered", tamper_after_idle=True)


if __name__ == "__main__":
    unittest.main()
