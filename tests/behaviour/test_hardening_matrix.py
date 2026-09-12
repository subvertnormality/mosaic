import hashlib
import json
import os
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]
MATRIX_PATH = ROOT / "docs/testing/unit-integration-hardening-matrix.json"
INVENTORY_PATH = ROOT / "tests/behaviour/manual-inventory.json"


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


class HardeningMatrixTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.matrix = json.loads(MATRIX_PATH.read_text())
        cls.inventory = json.loads(INVENTORY_PATH.read_text())
        os.environ.setdefault("MONOME_EMULATOR", str(ROOT.parent / "monome-emulator-midi-clock"))
        import sys
        sys.path.insert(0, str(ROOT / "tests/behaviour"))
        from cases import CASES
        cls.cases = CASES

    def test_matrix_is_bound_to_the_current_manual_and_inventory(self):
        self.assertEqual(self.matrix["schema_version"], 1)
        self.assertEqual(self.matrix["manual_sha256"], self.inventory["manual_sha256"])
        self.assertEqual(digest(ROOT / self.matrix["manual"]), self.matrix["manual_sha256"])
        self.assertEqual(self.matrix["inventory"], "tests/behaviour/manual-inventory.json")
        self.assertEqual(digest(INVENTORY_PATH), self.matrix["inventory_sha256"])

    def test_every_requirement_module_and_test_file_has_an_owner(self):
        expected_requirements = {row["id"] for row in self.inventory["requirements"]}
        actual_requirements = {value for row in self.matrix["domains"] for value in row["requirement_ids"]}
        self.assertEqual(expected_requirements, actual_requirements)
        expected_modules = {p.relative_to(ROOT).as_posix() for p in (ROOT / "lib").rglob("*.lua")
                            if "/tests/" not in p.as_posix()}
        actual_modules = {value for row in self.matrix["domains"] for value in row["production_modules"]}
        self.assertEqual(expected_modules, actual_modules)
        expected_tests = {p.relative_to(ROOT).as_posix() for p in (ROOT / "lib/tests/lib").rglob("*.lua")}
        actual_tests = {value for row in self.matrix["domains"] for value in row["existing_unit_integration_files"]}
        self.assertEqual(expected_tests, actual_tests)
        self.assertEqual(self.matrix["counts"], {"requirements": len(expected_requirements),
            "production_lua_modules": len(expected_modules), "unit_integration_files": len(expected_tests),
            "domains": len(self.matrix["domains"])})

    def test_references_and_finite_axis_claims_are_live_and_explicit(self):
        requirement_ids = {row["id"] for row in self.inventory["requirements"]}
        domain_ids = [row["id"] for row in self.matrix["domains"]]
        self.assertEqual(len(domain_ids), len(set(domain_ids)))
        for row in self.matrix["domains"]:
            self.assertTrue(row["requirement_ids"], row["id"])
            self.assertTrue(row["production_modules"], row["id"])
            self.assertTrue(row["existing_unit_integration_files"], row["id"])
            self.assertTrue(row["interaction_strategy"].strip(), row["id"])
            self.assertTrue(row["residual_gaps"], row["id"])
            self.assertTrue(set(row["requirement_ids"]) <= requirement_ids, row["id"])
            self.assertTrue(set(row["linked_behaviour_cases"]) <= set(self.cases), row["id"])
            for path in row["production_modules"] + row["existing_unit_integration_files"]:
                self.assertTrue((ROOT / path).is_file(), path)
            for axis in row["finite_axes"]:
                self.assertIs(type(axis["cardinality"]), int, (row["id"], axis))
                self.assertGreater(axis["cardinality"], 0, (row["id"], axis))
                self.assertTrue(axis["coverage"].strip(), (row["id"], axis))
                if "values" in axis:
                    self.assertEqual(len(axis["values"]), axis["cardinality"], (row["id"], axis))


if __name__ == "__main__":
    unittest.main()
