import unittest

import manual_plan_lint as lint


def plan(*steps):
    return dict(id="scene", steps=[dict(id=step_id, assertion=assertion, **extra)
                                    for step_id, assertion, extra in steps])


READOUT = dict(kind="selected-param", slot=2, value="0", marker=None, passed=True)


class AmbiguousBooleans(unittest.TestCase):
    def test_flags_unquoted_yes_no_on_off(self):
        text = "a: off\nb: [Off, On]\nc: yes\n"
        self.assertEqual([value for _, value in lint.ambiguous_booleans(text)], ["off", "Off", "On", "yes"])

    def test_allows_true_false_and_quoted_words(self):
        self.assertEqual(lint.ambiguous_booleans("a: true\nb: False\nc: 'off'\nd: [\"On\"]\n"), [])

    def test_reports_line(self):
        self.assertEqual(lint.ambiguous_booleans("a: 1\nstate: off\n"), [(2, "off")])


class DuplicateSelectors(unittest.TestCase):
    def test_repeat_without_occurrence_is_reported(self):
        problems = lint.unordered_duplicate_selectors(plan(
            ("first", READOUT, {}), ("other", dict(kind="x"), {}), ("again", READOUT, {})))
        self.assertEqual(problems, [("again", "first", 1)])

    def test_increasing_occurrences_pass(self):
        self.assertEqual(lint.unordered_duplicate_selectors(plan(
            ("first", READOUT, {}), ("again", READOUT, dict(occurrence=2)),
            ("third", READOUT, dict(occurrence=3)))), [])

    def test_decreasing_occurrence_is_reported(self):
        problems = lint.unordered_duplicate_selectors(plan(
            ("a", READOUT, dict(occurrence=3)), ("b", READOUT, dict(occurrence=2))))
        self.assertEqual(problems, [("b", "a", 2)])

    def test_alternatives_distinguish_selectors(self):
        self.assertEqual(lint.unordered_duplicate_selectors(plan(
            ("a", READOUT, {}), ("b", READOUT, dict(assertion_alternatives=[dict(kind="y")])))), [])

    def test_before_finish_steps_are_exempt(self):
        self.assertEqual(lint.unordered_duplicate_selectors(plan(
            ("a", READOUT, {}), ("b", READOUT, dict(capture_stage="before-finish")))), [])


class AuthoredPlans(unittest.TestCase):
    def test_every_scene_plan_is_clean(self):
        files = lint.plan_files()
        self.assertTrue(files)
        errors = [error for path in files for error in lint.lint_plan_file(path)]
        self.assertEqual(errors, [], "\n".join(errors))


if __name__ == "__main__":
    unittest.main()
