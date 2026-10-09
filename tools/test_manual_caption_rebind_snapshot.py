import json
import tempfile
import unittest
from pathlib import Path

import manual_caption_rebind as rebind


class NativeSnapshot(unittest.TestCase):
    def test_derived_reader_artifacts_are_not_native_publications(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary); generated = root / "manual/generated"; generated.mkdir(parents=True)
            (generated / "reference-a-scenes.json").write_text(json.dumps(dict(scenes=[dict(id="a")])))
            (generated / "reader-index.json").write_text(json.dumps(dict(scenes=dict(a=1))))
            (generated / "book.json").write_text("{}")
            snapshot = rebind.native_snapshot(root)
            self.assertEqual(list(snapshot), ["manual/generated/reference-a-scenes.json"])
            self.assertEqual(list(rebind.catalogue(snapshot)), ["a"])


if __name__ == "__main__":
    unittest.main()
