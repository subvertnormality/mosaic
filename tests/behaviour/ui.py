"""UI-independent behaviour-test verbs over the public emulator driver."""

import base64
import contextlib
import time

from ui_map import (CHANNEL_PAGES, HEADERS, LED_LEVELS, MENU, NATIVE_MENU,
                    NATIVE_MENU_VALUES, SCREEN, control_cell, header_text)


class UiMapError(AssertionError):
    pass


class Ui:
    def __init__(self, driver):
        self.driver = driver

    def play(self):
        self.tap_control("play_stop")

    def stop(self):
        self.tap_control("play_stop")

    def menu(self, button):
        self.tap_control(button)

    def channel_page(self, page, from_page, channel=1, confirm=True, saturate=False):
        names = list(CHANNEL_PAGES)
        try:
            target = names.index(page)
            origin = names.index(from_page)
        except ValueError as error:
            raise UiMapError("unknown channel page: %s" % error) from error
        delta = target - origin
        if saturate:
            if target == 0 and delta < 0:
                delta -= 1
            elif target == len(names) - 1 and delta > 0:
                delta += 1
            else:
                raise UiMapError("saturating channel navigation needs a boundary target")
        if delta:
            self.driver.enc(1, delta)
        if confirm:
            self.confirm_header(page, channel=channel)

    def pattern_editor(self, view="trigger", from_view=None):
        order = ["trigger", "note", "velocity"]
        taps = 1 if from_view is None else (order.index(view) - order.index(from_view)) % len(order)
        for _ in range(taps):
            self.tap_control("pattern_editor")

    def song_editor(self):
        self.tap_control("song_editor")

    def scale_editor(self):
        self.tap_control("scale_editor")

    def select_channel(self, channel):
        self.tap_control("channel", channel)

    def select_song_slot(self, slot):
        self.tap_control("song_slot", slot)

    def select_field(self, name, **path):
        """Preserve an explicitly declared field-navigation path.

        Callers use ``saturate``/``then`` when the clamp is part of the
        behaviour under test, or ``offset`` for an ordinary relative move.
        The stable field name is retained in the call even though the emitted
        recipe contains only the physical E2 movements.
        """
        if "saturate" in path:
            self.turn(2, path["saturate"])
            if path.get("then"):
                self.turn(2, path["then"])
            return
        if "offset" in path:
            self.turn(2, path["offset"])
            return
        raise UiMapError("field %r needs an explicit navigation path" % name)

    def press_key(self, number):
        self.driver.key(number)

    def turn(self, encoder, detents):
        self.driver.enc(encoder, detents)

    def encoder_event(self, encoder, delta):
        """Emit one native encoder event with no synthetic detent timing."""
        return self.driver.action(type="enc", n=encoder, delta=delta)

    def set_value(self, delta):
        self.turn(3, delta)

    def tap_control(self, control, index=None):
        self.driver.tap(*control_cell(control, index))

    def tap_step(self, step):
        self.tap_control("step", step)

    def step(self, step):
        return control_cell("step", step)

    @contextlib.contextmanager
    def hold_step(self, step):
        cell = self.step(step)
        self.driver.action(type="grid", x=cell[0], y=cell[1], state=1)
        try:
            yield self
        finally:
            self.driver.action(type="grid", x=cell[0], y=cell[1], state=0)

    @contextlib.contextmanager
    def hold_keys(self, *keys):
        for number in keys:
            self.driver.action(type="key", n=number, state=1)
        try:
            yield self
        finally:
            for number in reversed(keys):
                self.driver.action(type="key", n=number, state=0)

    def gesture(self, presses, releases):
        for control, index in presses:
            x, y = control_cell(control, index)
            self.driver.action(type="grid", x=x, y=y, state=1)
        for control, index in releases:
            x, y = control_cell(control, index)
            self.driver.action(type="grid", x=x, y=y, state=0)

    def set_range(self, first, last):
        start, end = self.step(first), self.step(last)
        self.driver.action(type="grid", x=start[0], y=start[1], state=1)
        try:
            self.driver.tap(*end)
        finally:
            self.driver.action(type="grid", x=start[0], y=start[1], state=0)

    def copy_slot(self, source, destination, control="pattern_slot"):
        first = control_cell(control, source)
        last = control_cell(control, destination)
        self.driver.action(type="grid", x=first[0], y=first[1], state=1)
        try:
            self.driver.tap(*last)
        finally:
            self.driver.action(type="grid", x=first[0], y=first[1], state=0)

    def hold_control_tap(self, held_control, target_control,
                         held_index=None, target_index=None):
        held = control_cell(held_control, held_index)
        target = control_cell(target_control, target_index)
        self.driver.action(type="grid", x=held[0], y=held[1], state=1)
        try:
            self.driver.tap(*target)
        finally:
            self.driver.action(type="grid", x=held[0], y=held[1], state=0)

    def record_key(self, step, note, velocity):
        with self.hold_step(step):
            self.driver.action(type="midi", port=1, bytes=[144, note, velocity])
            self.driver.action(type="midi", port=1, bytes=[128, note, 0])

    def configure(self):
        """Canonical four-note setup, preserving the historical input recipe."""
        self.tap_control("channel_editor")
        self.turn(1, 4)
        self.set_value(1)
        self.press_key(3)
        self.tap_control("pattern_editor")
        for step in range(1, 5):
            self.tap_step(step)
        self.tap_control("pattern_editor")
        for step in (49, 34, 19, 4):
            self.tap_step(step)
        self.tap_control("pattern_editor")
        for cell in ((1, 1), (2, 2), (3, 3), (4, 4)):
            self.tap_control("cell", cell)
        self.tap_control("channel_editor")
        self.tap_control("pattern_slot", 1)
        start, end = self.step(1), self.step(4)
        self.driver.hold_tap(start, end)
        self.expect_leds({("pattern_slot", 1): "selected"})
        self.expect_header("midi_config", channel=1)

    def set_mosaic_options(self, options):
        """Seek Mosaic's native parameter submenu by observed labels."""
        from frame_oracle import selected_line

        self.press_key(1)
        self.turn(1, 4)
        self.press_key(3)
        self.expect_menu_label("LEVELS >")
        position = next(
            index for index, value in enumerate(
                self.driver.snapshot()["diagnostics"]["parameter_roots"]
            ) if value["id"] == "mosaic"
        )
        self.turn(2, position)
        self.press_key(3)
        for label, enabled in options:
            top = 23 if label in (
                "Trigless locks", "Snap note masks to scale", "Map scale to white keys"
            ) else 22
            self.turn(2, -60)
            for _ in range(40):
                if selected_line(self.driver.snapshot(), label, top=top):
                    break
                self.turn(2, 1)
            else:
                raise UiMapError("Required Mosaic option not reached: " + label)
            self.turn(3, 3 if enabled else -3)
            self.expect_menu_option_row(label, "On" if enabled else "Off", top=top)
            self.driver.results.append(
                dict(kind="mosaic-option-input", label=label, enabled=enabled)
            )
        self.press_key(2)
        self.turn(2, -60)
        self.expect_menu_label("LEVELS >")
        self.press_key(2)
        self.press_key(1)

    def assign_trig_parameter(self, label, offset=None):
        """Assign by the historical scan or a previously verified list offset."""
        self.press_key(2)
        self.turn(3, -50)
        if offset is None:
            for offset in range(50):
                if self.expect_list_label(label, wait=False):
                    break
                self.turn(3, 1)
            else:
                raise UiMapError("Parameter unavailable through native UI: " + label)
        elif offset:
            self.turn(3, offset)
        self.expect_list_label(label)
        self.press_key(3)
        self.press_key(2)
        return offset

    def select_midi_clock_source(self):
        """Seek the native CLOCK root and change its source from internal to MIDI."""
        self.configure()
        self.press_key(1)
        self.turn(1, 4)
        self.press_key(3)
        self.expect_menu_label(NATIVE_MENU["levels_root"])
        position = next(
            index for index, value in enumerate(
                self.driver.snapshot()["diagnostics"]["parameter_roots"]
            ) if value["name"] == "CLOCK"
        )
        self.turn(2, position)
        self.press_key(3)
        self.expect_menu_label(NATIVE_MENU["clock_source"])
        values = NATIVE_MENU_VALUES["clock_source"]
        self.expect_menu_value(values["internal"])
        self.turn(3, 1)
        self.expect_menu_value(values["midi"])

    def expect_leds(self, states):
        cells, levels = [], []
        for (control, index), state in states.items():
            cells.append(control_cell(control, index))
            try:
                levels.append(LED_LEVELS[state])
            except KeyError as error:
                raise UiMapError("unknown LED state %r" % state) from error
        self.driver.led_values(cells, levels)

    def expect_steps(self, states):
        self.expect_leds({("step", step): state for step, state in states.items()})

    def wait_for_header(self, page, **params):
        """Wait for an exact mapped header without adding a result record."""
        from frame_oracle import header, matches

        data = HEADERS[page]
        text = header_text(page, **params)
        expected = header(text, selected=data["selected"], tabs=data["tabs"])
        return self.driver.wait(lambda state: matches(state, expected))

    def expect_header(self, page, **params):
        text = header_text(page, **params)
        self.wait_for_header(page, **params)
        self.driver.results.append(dict(kind="screen-header", expected=text, matched=True))

    def expect_scale_slot_header(self, slot):
        """Wait for the exact scale-slot header without adding a result record."""
        from frame_oracle import header, matches

        text = "Scale slot %d " % slot
        expected = header(text, selected=1, tabs=3)
        self.driver.wait(lambda state: matches(state, expected))

    def matches_header(self, page, **params):
        return self._header_matches(self.driver.snapshot(), page, params)

    def _expect_render(self, commands, region, result):
        from frame_oracle import render

        expected = render(commands)
        indices = [(y * 128 + x) * 4 + channel
                   for y in range(region["top"], region["bottom"])
                   for x in range(region["left"], region["right"])
                   for channel in range(3)]

        def matches(state):
            actual = base64.b64decode(state["frame"]["pixels_base64"])
            return all(actual[index] == expected[index] for index in indices)

        state = self.driver.wait(matches)
        self.driver.results.append(result)
        return state

    def expect_menu_label(self, label, x=0):
        from frame_oracle import selected_line

        self.driver.wait(lambda state: selected_line(state, label, x))
        self.driver.results.append(dict(kind="selected-menu-label", text=label))

    def expect_menu_value(self, value):
        from frame_oracle import selected_value

        self.driver.wait(lambda state: selected_value(state, value))
        self.driver.results.append(dict(kind="selected-menu-value", text=value))

    def expect_native_menu_value(self, parameter, value):
        try:
            rendered = NATIVE_MENU_VALUES[parameter][value]
        except KeyError as error:
            raise UiMapError("unknown native menu value %s.%s" % (parameter, value)) from error
        self.expect_menu_value(rendered)

    def expect_menu_option_row(self, label, value, top=None):
        row = dict(SCREEN["menu_option_row"])
        if top is not None:
            row["top"] = top
        selected = SCREEN["selected_row"]
        return self._expect_render(
            [(0, selected["baseline"], selected["level"], label),
             (None, selected["baseline"], selected["level"], value)],
            row,
            dict(kind="selected-menu-option-row", label=label, value=value, matched=True),
        )

    def expect_field_value(self, field, value):
        if field != "length":
            raise UiMapError("unknown field oracle: " + str(field))
        data = SCREEN["length_field"]
        return self._expect_render(
            [(data["x"], data["label_baseline"], data["level"], data["label"]),
             (data["x"], data["value_baseline"], data["level"], value)],
            data,
            dict(kind="length-mask-display", label=value, passed=True),
        )

    def expect_list_label(self, label, wait=True):
        from frame_oracle import render

        data = SCREEN["parameter_list"]
        expected = render([(data["x"], data["baseline"], data["level"], label)])
        indices = [(y * 128 + x) * 4 + channel
                   for y in range(data["top"], data["bottom"])
                   for x in range(data["left"], data["right"])
                   for channel in range(3)]

        def matches(state):
            actual = base64.b64decode(state["frame"]["pixels_base64"])
            return all(actual[index] == expected[index] for index in indices)

        if not wait:
            return matches(self.driver.snapshot())
        self.driver.wait(matches)
        self.driver.results.append(dict(kind="parameter-list-label", label=label, passed=True))
        return True

    def pick_device(self, name):
        from frame_oracle import render

        data = SCREEN["device_picker"]
        expected = render([(data["x"], data["baseline"], data["level"], name)])
        indices = [(y * 128 + x) * 4 + channel
                   for y in range(data["top"], data["bottom"])
                   for x in range(data["left"], data["right"])
                   for channel in range(3)]
        def visible(state):
            pixels = base64.b64decode(state["frame"]["pixels_base64"])
            return all(pixels[index] == expected[index] for index in indices)
        for _ in range(40):
            if visible(self.driver.snapshot()):
                break
            self.turn(3, 1)
        else:
            raise UiMapError("Device not visible in picker: " + name)
        self.press_key(3)
        self.driver.results.append(dict(kind="device-picker-frame", label=name, matched=True))

    def _header_matches(self, state, page, params):
        from frame_oracle import header, matches

        data = HEADERS[page]
        expected = header(header_text(page, **params), selected=data["selected"], tabs=data["tabs"])
        return matches(state, expected)

    def _observed_title(self, state):
        return "<unmatched framebuffer>"

    def confirm_header(self, page, **params):
        expected = header_text(page, **params)
        if self.driver.clock_mode == "real-time":
            deadline = time.monotonic() + 1
            state = None
            while time.monotonic() < deadline:
                state = self.driver.snapshot()
                if self._header_matches(state, page, params):
                    break
                time.sleep(.03)
            else:
                raise UiMapError("expected %r, observed %r" % (expected, self._observed_title(state)))
        else:
            state = self.driver.snapshot()
            if not self._header_matches(state, page, params):
                raise UiMapError("expected %r, observed %r" % (expected, self._observed_title(state)))
        self.driver.results.append(dict(kind="ui-confirm", page=page, **params))
