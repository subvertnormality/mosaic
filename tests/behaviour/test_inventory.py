"""Traceability: every registered case and every manual requirement link to each other."""
import json,unittest
from pathlib import Path
from cases import CASES
INVENTORY=json.loads((Path(__file__).parent/'manual-inventory.json').read_text())
ISSUES=json.loads((Path(__file__).parent/'issue-mappings.json').read_text())

class InventoryTests(unittest.TestCase):
    def test_case_requirements_exist_and_list_the_case(self):
        requirements={r['id']:r for r in INVENTORY['requirements']}
        unknown=[(case,r) for case,spec in CASES.items() for r in spec.get('requirements',[]) if r not in requirements]
        missing=[(case,r) for case,spec in CASES.items() for r in spec.get('requirements',[]) if r in requirements and case not in requirements[r]['cases']]
        self.assertEqual(unknown,[]);self.assertEqual(missing,[])
    def test_inventory_cases_are_registered_for_that_requirement(self):
        wrong=[(case,r['id']) for r in INVENTORY['requirements'] for case in r['cases'] if case not in CASES or r['id'] not in CASES[case].get('requirements',[])]
        self.assertEqual(wrong,[])
    def test_issue_mappings_and_case_metadata_are_bidirectional(self):
        numbers=[issue['number'] for issue in ISSUES['issues']]
        self.assertEqual(len(numbers),len(set(numbers)))
        mapped={(issue['number'],case) for issue in ISSUES['issues'] for route in issue['routes'] for case in route['cases']}
        declared={(number,case) for case,spec in CASES.items() for number in spec.get('issues',[])}
        self.assertEqual(mapped,declared)
        self.assertTrue(all(case in CASES for _,case in mapped))
        self.assertTrue(all(issue['routes'] and all(route['cases'] and route['oracle'] for route in issue['routes']) for issue in ISSUES['issues']))
if __name__=='__main__':unittest.main()
