"""Recipe parity for the M-TIME-006/007 semantic-input migration."""
import unittest

from ui import Ui


class InputRecorder:
    def __init__(self):
        self.recipe = []

    def action(self, **event):
        self.recipe.append(("input", event))

    def elapse(self, seconds):
        self.recipe.append(("elapse", seconds))

    def tap(self, x, y):
        self.action(type="grid", x=x, y=y, state=1)
        self.action(type="grid", x=x, y=y, state=0)
        self.elapse(.06)

    def key(self, number):
        self.action(type="key", n=number, state=1)
        self.action(type="key", n=number, state=0)
        self.elapse(.06)

    def enc(self, number, detents):
        for _ in range(abs(detents)):
            self.elapse(.05)
            self.action(type="enc", n=number,
                        delta=2 if detents > 0 else -2)
        self.elapse(.15)

    def hold_tap(self, first, last):
        self.action(type="grid", x=first[0], y=first[1], state=1)
        try:
            self.tap(*last)
        finally:
            self.action(type="grid", x=first[0], y=first[1], state=0)

    def led_values(self, cells, expected):
        self.recipe.append(("led-values", cells, expected))


def emit_raw_recipe(driver, basis=False):
    driver.tap(5, 8); driver.tap(5, 8)
    for x in range(1, 5): driver.tap(x, 7)
    driver.tap(3, 8); driver.enc(1, -1); driver.enc(3, 12); driver.key(3)
    driver.tap(6, 8); driver.hold_tap((1, 1), (2, 1))
    driver.tap(2, 1); driver.tap(3, 8)
    driver.enc(2, 1); driver.enc(3, 2); driver.key(3)
    driver.enc(2, 2 if basis else 1); driver.enc(3, 2); driver.key(3)
    driver.enc(2, -2 if basis else -1); driver.enc(3, -1); driver.key(3)
    driver.tap(11, 8); driver.tap(6, 8); driver.tap(1, 1)
    driver.tap(1, 8)
    driver.led_values([(1, 1), (2, 1)], [7, 15])
    driver.led_values([(1, 1), (2, 1)], [15, 7])
    driver.tap(1, 8)


def emit_ui_recipe(ui, basis=False):
    ui.pattern_editor(); ui.pattern_editor()
    for step in range(49, 53): ui.tap_step(step)
    ui.channel_editor(); ui.turn(1, -1); ui.turn(3, 12); ui.press_key(3)
    ui.song_editor(); ui.hold_control_tap("channel", "channel", 1, 2)
    ui.select_channel(2); ui.channel_editor()
    ui.turn(2, 1); ui.turn(3, 2); ui.press_key(3)
    ui.turn(2, 2 if basis else 1); ui.turn(3, 2); ui.press_key(3)
    ui.turn(2, -2 if basis else -1); ui.turn(3, -1); ui.press_key(3)
    ui.tap_control("shift_reset"); ui.song_editor(); ui.select_channel(1)
    ui.play()
    ui.expect_leds({("channel", 1): "alternate", ("channel", 2): "selected"})
    ui.expect_leds({("channel", 1): "selected", ("channel", 2): "alternate"})
    ui.stop()


class InactiveShuffleInputRecipeTests(unittest.TestCase):
    def test_semantic_verbs_emit_identical_direct_input_recipe(self):
        for basis in (False, True):
            with self.subTest(basis=basis):
                raw = InputRecorder()
                semantic = InputRecorder()
                emit_raw_recipe(raw, basis)
                emit_ui_recipe(Ui(semantic), basis)
                self.assertEqual(semantic.recipe, raw.recipe)

    def test_coordinate_owners_used_by_migration_are_stable(self):
        from ui_map import LED_LEVELS, control_cell

        self.assertEqual([control_cell("step", step) for step in range(49, 53)],
                         [(x, 7) for x in range(1, 5)])
        self.assertEqual(control_cell("channel_editor"), (3, 8))
        self.assertEqual(control_cell("song_editor"), (6, 8))
        self.assertEqual(control_cell("shift_reset"), (11, 8))
        self.assertEqual(control_cell("play_stop"), (1, 8))
        self.assertEqual([control_cell("channel", channel) for channel in (1, 2)],
                         [(1, 1), (2, 1)])
        self.assertEqual(LED_LEVELS["alternate"], 7)
        self.assertEqual(LED_LEVELS["selected"], 15)
