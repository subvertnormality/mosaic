import json
import tempfile
import unittest
from pathlib import Path

import manual_feature_bind as bind


class Catalogue(unittest.TestCase):
    def test_reader_index_is_not_a_native_scene_document(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary); generated = root / "manual/generated"; generated.mkdir(parents=True)
            (generated / "reference-a-scenes.json").write_text(json.dumps(dict(scenes=[dict(id="a")])))
            (generated / "reader-index.json").write_text(json.dumps(dict(scenes=dict(a=1))))
            (generated / "book.json").write_text("{}")
            self.assertEqual(list(bind.catalogue(root)), ["a"])


if __name__ == "__main__":
    unittest.main()
