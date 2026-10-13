"""Compiler catalogue characterisation outside the instrument manual."""
import importlib.util,json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[2]
spec=importlib.util.spec_from_file_location('manual_book_catalogue',ROOT/'tools/manual_book.py')
book=importlib.util.module_from_spec(spec);spec.loader.exec_module(book)
class CaptureCatalogue(unittest.TestCase):
 def test_reader_projection_is_not_a_native_capture(self):
  with tempfile.TemporaryDirectory() as folder:
   manual=Path(folder);generated=manual/'generated';generated.mkdir()
   (generated/'reference-scenes.json').write_text(json.dumps({'scenes':[{'id':'phrase','steps':[]}]}))
   (generated/'reader-index.json').write_text(json.dumps({'scenes':{'phrase':{'path':'reader-chunks/scenes/phrase-hash.json','sha256':'hash'}}}))
   (generated/'book.json').write_text(json.dumps({'scenes':{'phrase':{'id':'phrase'}}}))
   with patch.object(book,'MANUAL',manual):
    result=book.capture_catalogue()
   self.assertEqual(set(result),{'phrase'})
   self.assertEqual(result['phrase']['data_path'],'generated/reference-scenes.json')
 def test_duplicate_native_captures_are_still_rejected(self):
  with tempfile.TemporaryDirectory() as folder:
   manual=Path(folder);generated=manual/'generated';generated.mkdir()
   for name in ('first-scenes.json','second-scenes.json'):
    (generated/name).write_text(json.dumps({'scenes':[{'id':'phrase','steps':[]}]}))
   with patch.object(book,'MANUAL',manual),self.assertRaisesRegex(ValueError,'Duplicate captured scene'):
    book.capture_catalogue()
if __name__=='__main__':unittest.main()
