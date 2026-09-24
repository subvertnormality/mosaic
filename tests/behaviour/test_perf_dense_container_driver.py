"""Container performance harness reuses the named-save acceptance case."""

import ast
import sys
import tempfile
import unittest
from pathlib import Path


BEHAVIOUR = Path(__file__).resolve().parent
if str(BEHAVIOUR) not in sys.path:
    sys.path.insert(0, str(BEHAVIOUR))


class ContainerDriverUiTests(unittest.TestCase):
    def test_container_driver_initializes_the_same_ui_facade_as_driver(self):
        # Isolate the class definition from Docker/emulator imports at module load.
        import driver
        from ui import Ui

        source = BEHAVIOUR / "perf_dense.py"
        node = next(item for item in ast.parse(source.read_text()).body
                    if isinstance(item, ast.ClassDef) and item.name == "ContainerDriver")
        namespace = {"driver": driver}
        exec(compile(ast.Module(body=[node], type_ignores=[]), str(source), "exec"), namespace)
        container = namespace["ContainerDriver"](Path(tempfile.gettempdir()), object())
        self.assertIsInstance(container.ui, Ui)
        self.assertIs(container.ui.driver, container)


if __name__ == "__main__":
    unittest.main()
