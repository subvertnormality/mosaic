"""Regression for preserving the dense harness's public input recipes."""
import contextlib
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))
from dense_workload import build_project
from ui import Ui


class TraceDriver:
    def __init__(self):
        self.recipe = []
        self.label_probes = {}
        self.confirmed_labels = []
        self.ui = Ui(self)
        self.ui.expect_list_label = self.expect_list_label

    def expect_list_label(self, label, wait=True):
        if wait:
            self.confirmed_labels.append(label)
            self.label_probes[label] = 0
            return True
        probes = self.label_probes.get(label, 0)
        self.label_probes[label] = probes + 1
        return probes >= 2

    def action(self, **event):
        self.recipe.append(event)

    def elapse(self, seconds):
        self.action(type="advance", nanoseconds=round(seconds * 1e9))

    def tap(self, x, y):
        self.action(type="grid", x=x, y=y, state=1)
        self.action(type="grid", x=x, y=y, state=0)
        self.elapse(.06)

    def key(self, n):
        self.action(type="key", n=n, state=1)
        self.action(type="key", n=n, state=0)
        self.elapse(.06)

    def enc(self, n, steps):
        for _ in range(abs(steps)):
            self.elapse(.05)
            self.action(type="enc", n=n, delta=2 if steps > 0 else -2)
        self.elapse(.15)

    @contextlib.contextmanager
    def hold_tap(self, first, last):
        self.action(type="grid", x=first[0], y=first[1], state=1)
        try:
            self.tap(*last)
        finally:
            self.action(type="grid", x=first[0], y=first[1], state=0)


def raw_select_parameter(driver, label):
    """Historical cases.assign_trig_parameter physical scan, without rendering."""
    driver.key(2)
    driver.enc(3, -50)
    for _ in range(50):
        if driver.ui.expect_list_label(label, wait=False):
            break
        driver.enc(3, 1)
    else:
        raise AssertionError("Parameter unavailable: " + label)
    driver.ui.expect_list_label(label)
    driver.key(3)
    driver.key(2)


def raw_recipe(driver, channels, workload, selector=raw_select_parameter):
    """Pre-migration input recipe frozen with raw coordinates."""
    driver.tap(5, 8)
    driver.tap(1, 1)
    for x in range(1, 17, 2 if workload == "extreme" else 1):
        driver.tap(x, 4)
    driver.tap(3, 8)
    driver.enc(1, 4)
    for channel in range(1, channels + 1):
        driver.tap(channel, 1)
        driver.enc(3, 1)
        driver.enc(2, 1)
        if channel > 1:
            driver.enc(3, channel - 1)
        driver.key(3)
        driver.tap(1, 2)
        driver.hold_tap((1, 4), (16, 4))
        # The pattern slot tap shows Merge detail (25 September 2026); Device reopens
        # through Channel tasks (E1, E2 to the top, E2 to Device, K3).
        driver.enc(1, 3)
        driver.enc(2, -10)
        driver.enc(2, 6)
        driver.key(3)

        def step_value(step, value):
            driver.action(type="grid", x=step, y=4, state=1)
            try:
                driver.elapse(.05)
                driver.action(type="enc", n=3, delta=-126)
                driver.elapse(.15)
                driver.enc(3, value + 1)
            finally:
                driver.action(type="grid", x=step, y=4, state=0)
            driver.elapse(.1)

        if workload == "slides":
            driver.enc(1, -3)
            selector(driver, "CC 1")
            step_value(1, 0)
            step_value(9, 127)
            driver.key(3)
            driver.enc(1, 3)
        if workload in ("locks", "extreme"):
            if workload == "extreme":
                driver.enc(1, -4)
                for turns in (2, 4, 5, 7):
                    driver.enc(2, 1)
                    driver.enc(3, turns)
                driver.enc(2, -4)
                driver.enc(1, 4)
                parameters = (1, 2, 3)
            else:
                parameters = (1, 2, 3, 4)
            driver.enc(1, -3)
            defaults = {1: 20, 2: 40, 3: 60, 4: 80}
            for index, parameter in enumerate(parameters):
                if index:
                    driver.enc(2, 1)
                selector(driver, "CC %d" % parameter)
                driver.enc(3, defaults[parameter] + 1)
                step_value(1, 100 + parameter)
                step_value(9, 10 + parameter)
            if workload == "extreme":
                driver.enc(2, 1)
                selector(driver, "CC 4")
                step_value(1, 0)
                step_value(9, 127)
                driver.enc(2, -3)
            else:
                driver.enc(2, -3)
            driver.enc(1, 3)
    driver.tap(1, 1)


class DenseWorkloadUiRecipeTests(unittest.TestCase):
    def test_dense_slides_locks_extreme_actions_and_delays_match_raw_recipe(self):
        for channels in (1, 4):
            for workload in ("dense", "slides", "locks", "extreme"):
                with self.subTest(channels=channels, workload=workload):
                    raw, semantic = TraceDriver(), TraceDriver()
                    raw_recipe(raw, channels, workload)
                    build_project(semantic, channels, workload)
                    self.assertEqual(semantic.recipe, raw.recipe)
                    self.assertEqual(
                        [event["nanoseconds"] for event in semantic.recipe
                         if event.get("type") == "advance"],
                        [event["nanoseconds"] for event in raw.recipe
                         if event.get("type") == "advance"],
                    )
                    self.assertEqual(semantic.confirmed_labels, raw.confirmed_labels)
                    if workload == "slides":
                        self.assertEqual(raw.confirmed_labels, ["CC 1"] * channels)
                    if workload == "locks":
                        self.assertEqual(
                            raw.confirmed_labels,
                            ["CC 1", "CC 2", "CC 3", "CC 4"] * channels,
                        )
                    if workload == "extreme":
                        self.assertEqual(
                            raw.confirmed_labels,
                            ["CC 1", "CC 2", "CC 3", "CC 4"] * channels,
                        )
                        step_presses = sum(
                            event.get("type") == "grid" and event.get("y") == 4
                            and event.get("state") == 1 for event in semantic.recipe
                        )
                        self.assertEqual(step_presses, 8 + 10 * channels)

    def test_oracle_detects_intentionally_shifted_step_mapping(self):
        raw, wrong = TraceDriver(), TraceDriver()
        raw_recipe(raw, 1, "dense")
        import ui
        original = ui.control_cell

        def shifted(name, index=None):
            return (2, 4) if name == "step" and index == 1 else original(name, index)

        with patch("ui.control_cell", shifted):
            build_project(wrong, 1, "dense")
        self.assertNotEqual(wrong.recipe, raw.recipe)


if __name__ == "__main__":
    unittest.main()
