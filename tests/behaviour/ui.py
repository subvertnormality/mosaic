"""UI-independent behaviour-test verbs over the public emulator driver."""

import base64
import contextlib
import time

from ui_map import (CHANNEL_COUNT, CHANNEL_PAGES, CHANNEL_TASKS, HEADERS, OVERVIEW_CELLS, PAGE_RINGS, RING_ALIASES, TASK_ROWS,
                    LED_LEVELS, LIVE_SCREENS, MENU, NATIVE_MENU, header_parts,
                    MOSAIC_OPTIONS, MOSAIC_OPTION_ROWS, MIDI_MAPPING_PARAMETERS,
                    NATIVE_MENU_VALUES, PATCH_PARAMETERS,
                    PATCH_PARAMETER_VALUES, RHYTHM_DOCTOR_CONTROLS,
                    RHYTHM_DOCTOR_SCREEN, SCREEN, TRIG_PARAMETERS,
                    control_cell, header_text)


class _ActionSinkDriver:
    """Native event timing for public HTTP/physical input clients."""
    def __init__(self, action, elapse, encoder_pause):
        self.sink = action
        self.elapse = elapse if elapse is not None else time.sleep
        self.encoder_pause = encoder_pause

    def action(self, **value):
        return self.sink(value)

    def tap(self, x, y):
        self.action(type='grid', x=x, y=y, state=1)
        self.action(type='grid', x=x, y=y, state=0)
        self.elapse(.06)

    def key(self, n):
        self.action(type='key', n=n, state=1)
        self.action(type='key', n=n, state=0)
        self.elapse(.06)

    def enc(self, n, delta):
        self.action(type='enc', n=n, delta=delta)
        self.elapse(self.encoder_pause)


class UiMapError(AssertionError):
    pass


class Ui:
    def __init__(self, driver):
        self.driver = driver

    # Physical-backend transport timing and observations live at the UI layer.
    def hardware_tap(self, x, y):
        press = self.driver.action(type="grid", x=x, y=y, state=1)
        self.driver.elapse(.04)
        release = self.driver.action(type="grid", x=x, y=y, state=0)
        self.driver.elapse(.12)
        return {"press": press, "release": release}

    def hardware_key(self, number):
        self.driver.action(type="key", n=number, state=1)
        self.driver.action(type="key", n=number, state=0)
        self.driver.elapse(.06)

    def hardware_turn(self, number, steps):
        for _ in range(abs(steps)):
            self.driver.action(type="enc", n=number,
                               delta=1 if steps > 0 else -1)
            self.driver.elapse(.05)
        self.driver.elapse(.15)

    def hardware_hold_tap(self, first, last):
        self.control_edge("cell", True, first)
        try:
            self.hardware_tap(*last)
        finally:
            self.control_edge("cell", False, first)

    def hardware_led_values(self, cells, expected):
        indexes = [(y - 1) * CHANNEL_COUNT + x - 1 for x, y in cells]
        state = self.driver.wait(
            lambda snapshot: [snapshot["grid"][i] for i in indexes] == expected
        )
        self.driver.results.append({
            "kind": "grid", "cells": cells, "expected": expected,
            "actual": [state["grid"][i] for i in indexes],
        })

    @classmethod
    def for_action_sink(cls, action, elapse=None, encoder_pause=.03):
        """Adapt a native dictionary-action sink without changing its timing.

        Performance HTTP clients record latency around each action themselves.
        This adapter adds no observation or wait to edge/event methods; its
        timed taps/keys and one-event turns retain the client's original tails.
        """
        return cls(_ActionSinkDriver(action, elapse, encoder_pause))

    def performance_gesture(self, kind, a, b):
        """One zero-delay performance stimulus from the semantic schedule."""
        if kind == 'control':
            self.control_edge(a, True, b)
            self.control_edge(a, False, b)
        elif kind == 'encoder':
            self.encoder_event(a, b)
        else:
            raise ValueError('unknown performance gesture: ' + str(kind))

    def performance_external_clock_port_one(self, diagnostics):
        """Preserve the performance runner's native CLOCK traversal exactly."""
        self.press_key(1)
        for _ in range(4):
            self.turn(1, 2)
        self.press_key(3)
        roots = diagnostics['parameter_roots']
        position = next(index for index, root in enumerate(roots)
                        if root['name'] == NATIVE_MENU['clock_root_name'])
        for _ in range(position):
            self.turn(2, 2)
        self.press_key(3)
        self.turn(3, 2)
        for _ in range(11):
            self.turn(2, 2)
        self.turn(3, 2)

    def play(self):
        return self.tap_control("play_stop")

    def stop(self):
        return self.tap_control("play_stop")

    def menu(self, button):
        self.tap_control(button)

    def channel_page(self, page, from_page=None, channel=1, confirm=True, saturate=False):
        """Open a Channel screen through Channel Tasks (E1 to tasks, E2 row, K3).

        ``from_page`` and ``saturate`` described the retired E1 page ring; the
        live UI reaches every Channel screen through its named task instead.
        """
        try:
            task = LIVE_SCREENS[page]["task"]
        except KeyError as error:
            raise UiMapError("unknown channel page: %s" % error) from error
        self.open_channel_task(task)
        if confirm:
            self.confirm_header(page, channel=channel)

    def open_channel_task(self, task):
        """E1 reaches Channel Tasks from any Channel screen; E2 picks the row; K3 opens it."""
        try:
            row = CHANNEL_TASKS.index(task)
        except ValueError as error:
            raise UiMapError("unknown channel task: %s" % task) from error
        self.driver.enc(1, 3)
        self.driver.enc(2, -len(CHANNEL_TASKS))
        if row:
            self.driver.enc(2, row)
        self.press_key(3)

    def pattern_editor(self, view="trigger", from_view=None):
        order = ["trigger", "note", "velocity"]
        taps = 1 if from_view is None else (order.index(view) - order.index(from_view)) % len(order)
        for _ in range(taps):
            self.tap_control("pattern_editor")

    def open_task(self, context, task):
        """Open a task row of a non-Channel context's navigator (E1, E2 row, K3)."""
        rows = TASK_ROWS[context]
        self.driver.enc(1, 1)
        self.driver.enc(2, -len(rows))
        if rows.index(task):
            self.driver.enc(2, rows.index(task))
        self.press_key(3)

    def view_channel(self, delta):
        """Move a pattern page's viewed channel (E3 on View channel); the
        selected channel does not change."""
        return self.turn(3, delta)

    def trig_options(self):
        """Open Trig options (P02), where E3 sets the tresillo multiplier."""
        self.open_task("Trig", "options")
        self.wait_for_header("trigger_editor_confirmation")

    def song_editor(self):
        self.tap_control("song_editor")

    def channel_editor(self):
        self.tap_control("channel_editor")

    def scale_editor(self):
        self.tap_control("scale_editor")

    def select_channel(self, channel):
        self.tap_control("channel", channel)
        self._channel = channel

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
        self._after_key1 = number == 1

    def turn(self, encoder, detents):
        after_key1, self._after_key1 = getattr(self, "_after_key1", False), False
        if encoder == 1 and detents:
            # A bare K1 opens or closes the native menu. Let the mode settle
            # before reading the page ring: a Mosaic screen not yet covered (or
            # a menu not yet closed) must not decide what this E1 means.
            if after_key1 and self._native_menu_opened():
                return self.driver.enc(encoder, detents)
            if self._turn_channel_ring(detents) or self._turn_other_ring(detents):
                return None
        return self.driver.enc(encoder, detents)

    def _native_menu_opened(self, polls=4, timeout=1.5):
        """Real time only: after a bare K1, wait until the native menu mode reads
        the same on ``polls`` consecutive observations; True if it is open.

        A controlled snapshot already reflects the key, so the ring
        observation itself stands down in the menu; recipe doubles keep
        their recorded calls."""
        if getattr(self.driver, "clock_mode", None) != "real-time" or not hasattr(self.driver, "wait"):
            return False
        seen = []

        def settled(state):
            seen.append(state.get("diagnostics", {}).get("menu_mode"))
            return len(seen) >= polls and len(set(seen[-polls:])) == 1
        try:
            self.driver.wait(settled, timeout=timeout)
        except (AssertionError, KeyError, TypeError, StopIteration):
            return False
        return seen[-1] is True

    def _observed_channel_page(self, timeout=1):
        """The Channel page ring key whose live header is showing, or None."""
        pages = list(CHANNEL_PAGES)
        found = []

        def settled(state):
            # Recipe doubles carry no framebuffer; the physical E1 stands.
            if "frame" not in state or state.get("diagnostics", {}).get("menu_mode"):
                return True
            for page in pages:
                if self._header_matches(state, page, {"channel": self._channel_hint(state)}):
                    found.append(page)
                    return True
            return False
        # Recipe doubles without observation keep the physical E1.
        if not (hasattr(self.driver, "wait") and hasattr(self.driver, "snapshot")):
            return None
        try:
            self.driver.wait(settled, timeout=timeout)
        except (AssertionError, KeyError, TypeError):
            return None
        return found[-1] if found else None

    def _channel_hint(self, state):
        return getattr(self, "_channel", 1)

    def _observed_ring(self, timeout=1):
        """(context, ring index) of a showing non-Channel ring screen, or None."""
        from frame_oracle import live_header_matches
        found = []

        def settled(state):
            if "frame" not in state or state.get("diagnostics", {}).get("menu_mode"):
                return True
            for context, ring in PAGE_RINGS.items():
                candidates = [(index, entry[:3]) for index, entry in enumerate(ring)]
                for index, aliases in RING_ALIASES.get(context, {}).items():
                    candidates += [(index, alias) for alias in aliases]
                for index, (screen, title, layout) in candidates:
                    scope = self._ring_scope(context, screen)
                    if live_header_matches(state, title, scope, layout):
                        found.append((context, index, screen))
                        return True
            return False
        if not (hasattr(self.driver, "wait") and hasattr(self.driver, "snapshot")):
            return None
        try:
            self.driver.wait(settled, timeout=timeout)
        except (AssertionError, KeyError, TypeError):
            return None
        return found[-1] if found else None

    def _ring_scope(self, context, screen=None):
        from ui_map import live_scope
        if screen in ("P01", "P03", "P04", "P08"):
            # The pattern editor names the edited pattern before the viewed channel.
            return live_scope("pattern", channel=getattr(self, "_channel", 1),
                              pattern=getattr(self, "_pattern", 1))
        if context == "Scale":
            return live_scope("scale", slot=getattr(self, "_scale_slot", 1))
        if context == "Song":
            return live_scope("song", song_slot=getattr(self, "_song_slot", 1))
        return live_scope("channel", channel=getattr(self, "_channel", 1))

    def _turn_other_ring(self, detents):
        """E1 on a Scale, Song or Trig page moves along that page ring (clamped):
        the target page opens through the context's task navigator."""
        observed = self._observed_ring()
        if observed is None:
            return False
        context, index, showing = observed
        ring = PAGE_RINGS[context]
        target = max(0, min(len(ring) - 1, index + detents))
        if ring[target][0] != showing:
            self.open_task(context, ring[target][3])
        return True

    def _turn_channel_ring(self, detents):
        """E1 on a Channel page moves along the page ring the case was written
        for (Masks .. Harmony, clamped at both ends). The live UI reaches each
        page through Channel Tasks, so the same musical page is opened.
        Native menus and every other screen keep the physical E1."""
        page = self._observed_channel_page()
        if page is None:
            return False
        ring = list(CHANNEL_PAGES)
        index = ring.index(page)
        target = max(0, min(len(ring) - 1, index + detents))
        if target != index:
            self.channel_page(ring[target], confirm=False)
            self.wait_for_header(ring[target], channel=self._channel_hint(None))
        return True

    def encoder_event(self, encoder, delta):
        """Emit one native encoder event with no synthetic detent timing."""
        return self.driver.action(type="enc", n=encoder, delta=delta)

    def control_edge(self, control, pressed, index=None):
        """Emit one mapped grid edge without adding time between gestures."""
        x, y = control_cell(control, index)
        return self.driver.action(type="grid", x=x, y=y,
                                  state=1 if pressed else 0)

    def control_cell(self, control, index=None):
        """Return a control's mapped cell for result diagnostics."""
        return control_cell(control, index)

    def key_edge(self, number, pressed):
        """Emit one norns key edge without adding synthetic hold time."""
        return self.driver.action(type="key", n=number,
                                  state=1 if pressed else 0)

    def set_value(self, delta):
        return self.turn(3, delta)

    def tap_control(self, control, index=None):
        if control == "pattern_select" and index is not None:
            self._pattern = index  # the pattern editor's scope names it (PAT02 CH01)
        return self.driver.tap(*control_cell(control, index))

    def tap_step(self, step):
        self.tap_control("step", step)

    def tap_pattern_note_position(self, position):
        self.tap_control("pattern_note_position", position)

    def set_channel_octave(self, octave):
        self.tap_control("channel_octave", octave)

    def set_step_octave(self, step, octave):
        self.hold_control_tap("step", "channel_octave", step, octave)

    def select_pattern_note_page(self, page):
        self.tap_control("pattern_note_page", page)

    def tap_pattern_note_fader(self, step, position):
        self.tap_control("pattern_note_fader", (step, position))

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
    def hold_control(self, control, index=None):
        """Hold a mapped grid control across caller-controlled elapsed time."""
        cell = control_cell(control, index)
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

    def grid_events_at(self, events, schedule_id=1):
        """Emit ordered mapped grid edges at exact lane-specific timestamps.

        Events are (timestamp_ns, control, index, state). Controlled time
        advances before each edge; real time submits all edges together to the
        native scheduler, so press latency cannot shift the release deadline.
        """
        mapped = []
        for at_ns, control, index, state in events:
            x, y = control_cell(control, index)
            mapped.append((at_ns, x, y, state))
        if self.driver.clock_mode == "real-time":
            return self.driver.action(
                type="native_input_schedule", schedule_id=schedule_id,
                events=[dict(type="grid", x=x, y=y, state=state,
                             at_monotonic_ns=at_ns)
                        for at_ns, x, y, state in mapped],
            )
        for at_ns, x, y, state in mapped:
            self.driver.elapse((at_ns - self.driver.logical_ns) / 1e9)
            self.driver.action(type="grid", x=x, y=y, state=state)

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

    def record_key(self, step, note, velocity, hold_seconds=0.0):
        with self.hold_step(step):
            self.driver.action(type="midi", port=1, bytes=[144, note, velocity])
            if hold_seconds:
                self.driver.elapse(hold_seconds)
            self.driver.action(type="midi", port=1, bytes=[128, note, 0])

    def record_midi_mask_on_step(self, step, note, velocity,
                                 hold_seconds=.05, release_tail_seconds=.1):
        """Record one external MIDI note while its mapped mask step is held."""
        with self.hold_step(step):
            self.driver.action(type="midi", port=1, bytes=[144, note, velocity])
            self.driver.elapse(hold_seconds)
            self.driver.action(type="midi", port=1, bytes=[128, note, 0])
        self.driver.elapse(release_tail_seconds)

    def configure(self):
        """Canonical four-note setup: the Device screen's device map moves one entry and applies."""
        self.tap_control("channel_editor")
        self.open_channel_task("device")
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
        # Assigning pattern 1 shows Merge detail (C09) focused on Patterns, and
        # the range gesture keeps it (usability audit 25 September 2026); E1
        # opens Channel tasks from it, and the setup ends on Device as the
        # recipes that follow it expect.
        self.expect_header("merge_detail", channel=1)
        self.channel_page("midi_config", confirm=False)
        self.expect_header("midi_config", channel=1)

    def set_mosaic_option_keys(self, options):
        """Resolve stable option keys before the observed-label native UI recipe."""
        mapped = []
        for key, enabled in options:
            try:
                mapped.append((MOSAIC_OPTIONS[key], enabled))
            except KeyError as error:
                raise UiMapError("unknown Mosaic option: " + str(key)) from error
        self.set_mosaic_options(mapped)

    def set_mosaic_number(self, parameter, delta, shown):
        """Set a mapped numeric Mosaic option through its observed menu row."""
        from frame_oracle import selected_line

        try:
            label = NATIVE_MENU[parameter]
        except KeyError as error:
            raise UiMapError("unknown Mosaic numeric option: " + str(parameter)) from error

        self.press_key(1)
        self.turn(1, 4)
        self.press_key(3)
        self.expect_native_menu_label("levels_root")
        position = next(
            index for index, value in enumerate(
                self.driver.snapshot()["diagnostics"]["parameter_roots"]
            ) if value["id"] == "mosaic"
        )
        self.turn(2, position)
        self.press_key(3)
        self.turn(2, -60)
        for _ in range(40):
            if selected_line(self.driver.snapshot(), label):
                break
            self.turn(2, 1)
        else:
            raise UiMapError("Required Mosaic option not reached: " + label)
        self.turn(3, delta)
        self.expect_menu_option_row(label, shown, top=22)
        self.driver.results.append(
            dict(kind="mosaic-number-input", label=label, value=shown)
        )
        self.press_key(2)
        self.turn(2, -60)
        self.expect_native_menu_label("levels_root")
        self.press_key(2)
        self.press_key(1)

    def set_mosaic_options(self, options):
        """Seek Mosaic's native parameter submenu by observed labels."""
        from frame_oracle import selected_line

        self.press_key(1)
        self.turn(1, 4)
        self.press_key(3)
        self.expect_menu_label(NATIVE_MENU["levels_root"])
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
        self.expect_menu_label(NATIVE_MENU["levels_root"])
        self.press_key(2)
        self.press_key(1)

    def enter_native_menu(self):
        """Open the native menu and observe the public mode transition."""
        self.press_key(1)
        return self._observe_native_menu_mode(True)

    def leave_native_menu(self):
        """Close the native menu and observe the public mode transition."""
        self.press_key(1)
        return self._observe_native_menu_mode(False)

    def _observe_native_menu_mode(self, expected):
        """Confirm a key-driven mode change without advancing controlled time."""
        self._after_key1 = False  # the mode is observed here; E1 needs no second look
        predicate = lambda state: state["diagnostics"]["menu_mode"] is expected
        if self.driver.clock_mode == "real-time":
            return self.driver.wait(predicate, timeout=1)
        state = self.driver.snapshot()
        if not predicate(state):
            raise UiMapError(
                "native menu mode is %r, expected %r" %
                (state["diagnostics"]["menu_mode"], expected)
            )
        return state

    def open_native_parameters(self, observe_entry=True):
        """Open PARAMETERS, optionally preserving an existing immediate-entry recipe."""
        if observe_entry:
            self.enter_native_menu()
        else:
            self.press_key(1)
        self.turn(1, 4)
        self.press_key(3)
        self.expect_menu_label(NATIVE_MENU["levels_root"])

    def seek_native_mapping_parameter(self, parameter):
        """Find a mapped norns parameter with the historical twelve-check scan."""
        from frame_oracle import selected_line

        try:
            spec = MIDI_MAPPING_PARAMETERS[parameter]
        except KeyError as error:
            raise UiMapError("unknown mapping parameter: " + str(parameter)) from error
        self.press_key(1)
        self.turn(1, 4)
        self.press_key(3)
        self.expect_menu_label(NATIVE_MENU["levels_root"])
        position = next(
            index for index, value in enumerate(
                self.driver.snapshot()["diagnostics"]["parameter_roots"]
            ) if value["id"] == spec["root_id"]
        )
        self.turn(2, position)
        self.press_key(3)
        for _ in range(spec["scan_limit"]):
            state = self.driver.snapshot()
            if (selected_line(state, spec["label"], top=spec["first_row_top"])
                    or selected_line(state, spec["label"])):
                break
            self.turn(2, 1)
        else:
            raise AssertionError("Mapping parameter not reached")

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

    def assign_trig_parameter_key(self, parameter, offset=None):
        """Assign a trig parameter through a stable semantic key."""
        try:
            label = TRIG_PARAMETERS[parameter]
        except KeyError as error:
            raise UiMapError("unknown trig parameter: " + str(parameter)) from error
        return self.assign_trig_parameter(label, offset=offset)

    def trig_parameter_label(self, parameter):
        """Return the mapped native label for a stable trig parameter key."""
        try:
            return TRIG_PARAMETERS[parameter]
        except KeyError as error:
            raise UiMapError("unknown trig parameter: " + str(parameter)) from error

    def assign_stored_patch_control(self, slot):
        if type(slot) is not int or not 1 <= slot <= 10:
            raise UiMapError("stored patch-control slot must be in 1..10")
        return self.assign_trig_parameter_key(
            "stored_patch_cc%d" % slot
        )

    def expect_trig_parameter_visible(self, parameter, wait=True):
        try:
            label = TRIG_PARAMETERS[parameter]
        except KeyError as error:
            raise UiMapError("unknown trig parameter: " + str(parameter)) from error
        return self.expect_list_label(label, wait=wait)

    def open_patch_control(self, configured=False, setup=True):
        """Open channel 1's stored patch control with the legacy scan recipe."""
        from frame_oracle import selected_line

        if setup:
            self.driver.configure()
            if configured:
                self.turn(3, 1)
                self.press_key(3)
        self.press_key(1)
        self.turn(1, 4)
        self.press_key(3)
        self.expect_menu_label(NATIVE_MENU["levels_root"])
        roots = self.driver.snapshot()["diagnostics"]["parameter_roots"]
        position = next(
            index for index, row in enumerate(roots)
            if row["id"] == "midi_device_params_group_channel_1"
        )
        self.turn(2, position)
        self.press_key(3)
        label_key = "patch_control_configured" if configured else "patch_control_default"
        label = NATIVE_MENU[label_key]
        for _ in range(180):
            if selected_line(self.driver.snapshot(), label):
                break
            self.turn(2, 1)
        else:
            raise AssertionError("Configured patch control not reachable: " + label)
        self.expect_menu_label(label)
        return label

    def seek_patch_parameter(self, parameter, configured=False, attempts=180,
                             open_control=True):
        """Open a patch control and seek a mapped parameter by observed state."""
        from frame_oracle import selected_line

        try:
            data = PATCH_PARAMETERS[parameter]
        except KeyError as error:
            raise UiMapError("unknown patch parameter: " + str(parameter)) from error
        if open_control:
            self.open_patch_control(configured=configured)
        for _ in range(attempts):
            if selected_line(self.driver.snapshot(), data["label"]):
                break
            self.turn(2, 1)
        else:
            raise AssertionError(data["failure"])
        self.expect_menu_label(data["label"])

    def expect_patch_value(self, value):
        """Observe a patch value from a stable state key or an integer value."""
        if isinstance(value, int):
            rendered = str(value)
        else:
            try:
                rendered = PATCH_PARAMETER_VALUES[value]
            except KeyError as error:
                raise UiMapError("unknown patch parameter value: " + str(value)) from error
        self.expect_menu_value(rendered)

    def seek_current_patch_parameter(self, parameter, attempts=180, failure=None,
                                     confirm=True):
        """Seek from the current native row, retaining its observed-state recipe."""
        from frame_oracle import selected_line

        try:
            spec = PATCH_PARAMETERS[parameter]
        except KeyError as error:
            raise UiMapError("unknown patch parameter: " + str(parameter)) from error
        for _ in range(attempts):
            if selected_line(self.driver.snapshot(), spec['label']):
                break
            self.turn(2, 1)
        else:
            raise AssertionError(spec['failure'] if failure is None else failure)
        if confirm:
            self.expect_patch_parameter(parameter)

    def expect_patch_parameter(self, parameter):
        """Assert the selected row for a stable stored-patch parameter key."""
        self.expect_menu_label(PATCH_PARAMETERS[parameter]['label'])

    def turn_patch_control(self, steps):
        """Keep native acceleration disabled and retain the historical settling time."""
        assert -63 <= steps <= 63 and steps
        self.driver.elapse(.05)
        self.encoder_event(3, 2 * steps)
        self.driver.elapse(.03)

    def select_midi_clock_source(self):
        """Seek the native CLOCK root and change its source from internal to MIDI."""
        self.configure()
        self.press_key(1)
        self.turn(1, 4)
        self.press_key(3)
        self.select_midi_clock_source_from_levels()

    def enter_native_levels_menu(self):
        """Open the native LEVELS root using the established norns recipe."""
        self.press_key(1)
        self.turn(1, 4)
        self.press_key(3)

    def select_native_parameter_group(self, group):
        """Select a stable native parameter root from the LEVELS menu."""
        self.expect_native_menu_label("levels_root")
        self.seek_native_parameter_root(group)
        self.press_key(3)
        if group == "clock":
            self.expect_native_menu_label("clock_source")
        return group

    def route_fixed_note_from_modulation_source(self, source):
        """Route a Matrix Fixed Note target from a mapped toolkit mod source."""
        from ui_map import NATIVE_MODULATION_SOURCES

        try:
            source_spec = NATIVE_MODULATION_SOURCES[source]
        except KeyError as error:
            raise UiMapError("unknown modulation source: " + str(source)) from error
        self.press_key(1)
        self.turn(2, 1)
        self.press_key(3)
        self.expect_native_menu_label("mod_devices_root")
        self.turn(2, 2)
        self.expect_native_menu_label("mod_mods_root")
        self.press_key(3)
        self.expect_native_menu_label("mod_matrix_root")
        self.press_key(3)
        self.expect_native_menu_label("levels_root")
        self.seek_native_parameter_root("channel_1_device_parameters")
        self.press_key(3)
        self.expect_native_menu_label("mod_fixed_note")
        self.press_key(3)
        self.expect_native_menu_label("mod_source_rhythm_1")
        self.turn(2, source_spec["offset"])
        self.expect_native_menu_label(source_spec["menu_label"])
        self.turn(3, 100)
        self.expect_menu_value("1.00")

    def select_midi_clock_source_from_levels(self):
        """Select the CLOCK source after opening the native LEVELS root."""
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

    def expect_channel_octave(self, octave):
        self.expect_leds({("channel_octave", value):
                          ("selected" if value == octave else "off")
                          for value in range(-2, 3)})

    def select_rhythm_doctor_algorithm(self, algorithm):
        """Select a named algorithm from Mosaic's rhythm-tool chooser."""
        names = {
            "drum": "legacy_drum_algorithm",
            "tresillo": "legacy_tresillo_algorithm",
            "euclidean": "legacy_euclidean_algorithm",
            "numeric_repetitor": "legacy_numeric_repetitor_algorithm",
            "rhythm_doctor": "algorithm",
        }
        try:
            self.tap_control(names[algorithm])
        except KeyError as error:
            raise UiMapError("unknown Rhythm Doctor algorithm %r" % algorithm) from error

    def select_rhythm_doctor_lane(self, lane):
        names = {"BD": "lane_bd", "SD": "lane_sd", "CYM": "lane_cym"}
        try:
            self.tap_control(names[lane])
        except KeyError as error:
            raise UiMapError("unknown Rhythm Doctor lane %r" % lane) from error

    def tap_rhythm_doctor_phrase_button(self, direction):
        names = {"left": "phrase_left", "centre": "phrase_centre", "right": "phrase_right"}
        try:
            self.tap_control(names[direction])
        except KeyError as error:
            raise UiMapError("unknown Rhythm Doctor phrase button %r" % direction) from error

    def rhythm_doctor_setup_field(self, delta):
        """Send the original native E2 encoder delta while editing setup."""
        self.encoder_event(2, delta)

    def adjust_rhythm_doctor_setup_value(self, delta):
        """Send the original native E3 encoder delta while editing setup."""
        self.encoder_event(3, delta)

    def rhythm_doctor_key_edge(self, key, pressed):
        if key not in {"discard_draft", "apply_correction"}:
            raise UiMapError("unknown Rhythm Doctor key action %r" % key)
        self.key_edge({"discard_draft": 2, "apply_correction": 3}[key], pressed)

    def rhythm_doctor_capture_edge(self, pressed):
        self.control_edge("capture", pressed)

    def expect_rhythm_doctor_lanes(self, states):
        """Assert the named lane, reserved, withdrawn and retired LED cells."""
        names = {
            "reserved": "reserved_lane", "BD": "lane_bd", "SD": "lane_sd",
            "CYM": "lane_cym", "withdrawn_BASS": "withdrawn_lane_bass",
            "retired": "retired_lane",
        }
        mapped = {}
        for lane, state in states.items():
            try:
                mapped[(names[lane], None)] = state
            except KeyError as error:
                raise UiMapError("unknown Rhythm Doctor lane LED %r" % lane) from error
        self.expect_leds(mapped)

    def _wait_rhythm_doctor_render(self, commands, region):
        """Keep exact framebuffer comparisons (RGB, alpha ignored) behind the page-level UI API."""
        from frame_oracle import render

        expected = render(commands)
        indices = [(y * 128 + x) * 4 + channel
                   for y in range(region["top"], region["bottom"])
                   for x in range(region["left"], region["right"])
                   for channel in range(3)]

        def matches(state):
            actual = base64.b64decode(state["frame"]["pixels_base64"])
            return all(actual[index] == expected[index] for index in indices)

        return self.driver.wait(matches)

    @staticmethod
    def _rhythm_doctor_screen(route):
        try:
            return RHYTHM_DOCTOR_SCREEN["screens"][route]
        except KeyError as error:
            raise UiMapError("unknown Rhythm Doctor screen %r" % route) from error

    def expect_rhythm_doctor_header(self, route="R01", channel=1):
        """A Doctor screen's live title row: its doctor_routes title and the channel scope.

        The fifth algorithm with no bank opens R01 (RHYTHM DR); a READY bank opens R05."""
        from frame_oracle import live_header_matches

        title, layout = self._rhythm_doctor_screen(route)
        scope = "CH%02d" % channel
        return self.driver.wait(lambda state: live_header_matches(state, title, scope, layout))

    def expect_rhythm_doctor_tooltip(self, text):
        """The Doctor's tooltip owns the live footer row, and nothing else is on it."""
        from frame_oracle import fit

        self._wait_rhythm_doctor_render(
            [(1, 63, 9, fit(text, 126))], RHYTHM_DOCTOR_SCREEN["footer"])

    def expect_rhythm_doctor_screen(self, route, label=None, value=None, channel=1):
        """Exact title row of Doctor screen `route` and its selected field's label/value.

        Most Doctor screens are focused with the doctor art, so only the
        selected field is on screen: its label at (1,28) and its value large at
        (1,48) within x1..71. Detail Doctor screens (R07 ...) mark it with '>'."""
        from frame_oracle import live_header_matches, selected_field_matches

        title, layout = self._rhythm_doctor_screen(route)
        scope = "CH%02d" % channel
        return self.driver.wait(lambda state: live_header_matches(state, title, scope, layout)
                                and selected_field_matches(state, layout, label, value, art=True))

    def expect_rhythm_doctor_setup_field(self, field, value):
        """R01 with setup field `field` (TEMPO / MANUAL BPM / INPUT) selected, showing `value`.

        The old setup screen listed all three rows; the live R01 shows only the
        selected one, so a recipe asserts each value while its field is selected."""
        try:
            label = RHYTHM_DOCTOR_SCREEN["setup_labels"][field]
        except KeyError as error:
            raise UiMapError("unknown Rhythm Doctor setup field %r" % field) from error
        return self.expect_rhythm_doctor_screen("R01", label, str(value))

    def wait_for_header(self, page, **params):
        """Wait for an exact mapped live header without adding a result record."""
        from frame_oracle import live_header_matches

        title, scope, layout = header_parts(page, **params)
        return self.driver.wait(lambda state: live_header_matches(state, title, scope, layout))

    def expect_header(self, page, **params):
        text = header_text(page, **params)
        self.wait_for_header(page, **params)
        self.driver.results.append(dict(kind="screen-header", expected=text, matched=True))

    def expect_header_surface(self, page, **params):
        """Check the mapped live header (title row and scope)."""
        self.expect_header(page, **params)

    def expect_scale_slot_header(self, slot):
        """Wait for the Scale screen header naming the selected scale slot."""
        self.wait_for_header("scale", slot=slot)

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

    def expect_menu_label(self, label, x=None, width=None, top=None):
        from frame_oracle import selected_line

        geometry = SCREEN["menu_label"]
        x = geometry["x"] if x is None else x
        width = geometry["width"] if width is None else width
        top = geometry["top"] if top is None else top
        self.driver.wait(lambda state: selected_line(
            state, label, x=x, width=width, top=top
        ))
        self.driver.results.append(dict(kind="selected-menu-label", text=label))

    def expect_trig_parameter(self, parameter):
        try:
            label = TRIG_PARAMETERS[parameter]
        except KeyError as error:
            raise UiMapError("unknown trig parameter: " + str(parameter)) from error
        self.expect_menu_label(label)

    def select_project_action(self, action, returning=False, activate=True):
        project = SCREEN["project_menu"]
        actions = project["actions"]
        try:
            spec = actions[action]
        except KeyError as error:
            raise UiMapError("unknown project action: " + str(action)) from error
        save = actions["save"]

        self.press_key(1)
        if not returning:
            self.turn(1, 4)
            self.press_key(3)
            self.expect_menu_label(NATIVE_MENU["levels_root"])
            position = next(
                index for index, value in enumerate(
                    self.driver.snapshot()["diagnostics"]["parameter_roots"]
                ) if value["id"] == project["root_id"]
            )
            self.turn(2, position)
            self.press_key(3)
        self.turn(2, -60)
        self.turn(2, 1)
        self.expect_menu_label(save["label"], x=save["x"],
                               width=save["width"], top=save["top"])
        if spec["offset"]:
            self.turn(2, spec["offset"])
            self.expect_menu_label(spec["label"], x=spec["x"],
                                   width=spec["width"], top=spec["top"])
        if activate:
            self.press_key(3)

    def select_project_file(self, name, returning=False):
        """Select a saved project through the native load menu."""
        from frame_oracle import selected_line

        self.select_project_action("load", returning=returning)
        self.encoder_event(2, -100)
        for _ in range(30):
            if selected_line(self.driver.snapshot(), name):
                return
            self.encoder_event(2, 1)
            self.driver.elapse(.03)
        raise AssertionError("Project file not reached: " + name)

    def expect_menu_value(self, value):
        from frame_oracle import selected_value

        self.driver.wait(lambda state: selected_value(state, value))
        self.driver.results.append(dict(kind="selected-menu-value", text=value))

    def wait_memory_position(self, current, total):
        """Wait for Memory's selected Position row to read "<current> of <total>"."""
        from frame_oracle import selected_field_matches

        return self.driver.wait(lambda state: selected_field_matches(
            state, "detail", "Position", "%d of %d" % (current, total)))

    def expect_memory_position(self, current, total, channel=None):
        self.wait_memory_position(current, total)
        result = dict(kind="memory-position", current=current, total=total,
                      frame_matched=True)
        if channel is not None:
            result["channel"] = channel
        self.driver.results.append(result)

    def expect_native_menu_label(self, parameter):
        try:
            rendered = NATIVE_MENU[parameter]
        except KeyError as error:
            raise UiMapError("unknown native menu label %s" % parameter) from error
        from ui_map import NATIVE_MENU_LABEL_GEOMETRY

        self.expect_menu_label(rendered, **NATIVE_MENU_LABEL_GEOMETRY.get(parameter, {}))

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
        """Wait for an overview cell's own label and value (Masks: C01)."""
        from frame_oracle import overview_cell_matches
        try:
            index, short_label = OVERVIEW_CELLS[field]
        except KeyError as error:
            raise UiMapError("unknown field oracle: " + str(field)) from error
        self.driver.wait(lambda state: overview_cell_matches(state, "overview_masks", index, short_label, value))
        self.driver.results.append(dict(kind="length-mask-display" if field == "length" else "overview-cell",
                                        field=field, label=value, passed=True))

    def expect_task_row(self, label):
        """The task list's selected row ('>' marker) is ``label``; task rows carry no value."""
        self.expect_selected_field("detail", label=label, value="")

    def expect_list_label(self, label, wait=True):
        """The picker cursor row (C07) shows ``label``; the row value is blank or CURRENT."""
        from frame_oracle import selected_field_matches

        def matches(state):
            return any(selected_field_matches(state, "detail", label, value) for value in ("", "CURRENT"))

        if not wait:
            return matches(self.driver.snapshot())
        self.driver.wait(matches)
        self.driver.results.append(dict(kind="parameter-list-label", label=label, passed=True))
        return True

    def pick_device(self, name):
        """Turn the Device screen's (C05) selected Device row with E3 until it
        shows ``name`` exactly (detail row: '>' marker, label, whole value),
        then apply with K3."""
        for _ in range(40):
            if self.shown_device([name]) == name:
                break
            self.turn(3, 1)
        else:
            raise UiMapError("Device not visible in picker: " + name)
        self.press_key(3)
        self.driver.results.append(dict(kind="device-picker-frame", label=name, matched=True))

    def shown_device(self, candidates, state=None):
        """The one candidate the selected Device row (C05) shows exactly; '?'
        when none (or more than one) matches."""
        from frame_oracle import selected_field_matches

        state = self.driver.snapshot() if state is None else state
        hits = [name for name in candidates
                if selected_field_matches(state, "detail", "Device", name)]
        return hits[0] if len(hits) == 1 else "?"

    def _header_matches(self, state, page, params):
        from frame_oracle import live_header_matches

        title, scope, layout = header_parts(page, **params)
        return live_header_matches(state, title, scope, layout)

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
            # A newly opened screen's body (scope line included) is uncovered
            # by a short decorative wipe drawn frame by frame (ui_motion
            # WIPE_FRAMES); let at most one logical second run for it.
            for _ in range(33):
                if self._header_matches(state, page, params):
                    break
                self.driver.elapse(.03)
                state = self.driver.snapshot()
            else:
                raise UiMapError("expected %r, observed %r" % (expected, self._observed_title(state)))
        self.driver.results.append(dict(kind="ui-confirm", page=page, **params))
    def seek_native_parameter_root(self, root):
        """Position E2 at a mapped native parameter root."""
        from ui_map import NATIVE_PARAMETER_ROOTS

        try:
            spec = NATIVE_PARAMETER_ROOTS[root]
        except KeyError as error:
            raise UiMapError("unknown native parameter root: " + str(root)) from error
        roots = self.driver.snapshot()["diagnostics"]["parameter_roots"]
        position = next(index for index, value in enumerate(roots)
                        if value[spec["field"]] == spec["value"])
        self.turn(2, position)
        return position

    def seek_native_menu_parameter(self, parameter, attempts=180, failure=None):
        """Seek a mapped native menu row through observed selected-line state."""
        from frame_oracle import selected_line
        from ui_map import NATIVE_MENU_PARAMETERS

        try:
            spec = NATIVE_MENU_PARAMETERS[parameter]
        except KeyError as error:
            raise UiMapError("unknown native menu parameter: " + str(parameter)) from error
        for _ in range(attempts):
            label_geometry = SCREEN["menu_label"]
            if selected_line(self.driver.snapshot(), spec["label"],
                             x=label_geometry["x"], width=label_geometry["width"],
                             top=label_geometry["top"]):
                return
            self.turn(2, 1)
        raise AssertionError(failure or spec["failure"])

    def seek_mosaic_option(self, option, failure=None):
        """Seek an option with the native saturation used by live recording."""
        from frame_oracle import selected_line
        from ui_map import MOSAIC_OPTION_ROWS

        try:
            label = MOSAIC_OPTIONS[option]
            top = MOSAIC_OPTION_ROWS[option]
        except KeyError as error:
            raise UiMapError("unknown Mosaic option: " + str(option)) from error
        self.encoder_event(2, -126)
        self.driver.elapse(.15)
        for _ in range(40):
            if selected_line(self.driver.snapshot(), label, top=top):
                return
            self.turn(2, 1)
        raise AssertionError(failure or "Required Mosaic option not reached: " + label)

    def seek_mosaic_option_from_current(self, option, attempts=40, failure=None):
        """Scan forward from the current row, preserving the caller's recipe."""
        from frame_oracle import selected_line
        from ui_map import MOSAIC_OPTIONS, MOSAIC_OPTION_ROWS

        try:
            label = MOSAIC_OPTIONS[option]
            top = MOSAIC_OPTION_ROWS.get(option)
        except KeyError as error:
            raise UiMapError("unknown Mosaic option: " + str(option)) from error
        for _ in range(attempts):
            if selected_line(self.driver.snapshot(), label, top=top):
                return
            self.turn(2, 1)
        raise AssertionError(failure or "Required Mosaic option not reached: " + label)

    def expect_mosaic_option_label(self, option):
        try:
            label = MOSAIC_OPTIONS[option]
        except KeyError as error:
            raise UiMapError("unknown Mosaic option: " + str(option)) from error
        self.expect_menu_label(label, top=MOSAIC_OPTION_ROWS.get(option))

    def expect_mosaic_option_value(self, enabled):
        from ui_map import MOSAIC_OPTION_VALUES

        try:
            value = MOSAIC_OPTION_VALUES[enabled]
        except KeyError as error:
            raise UiMapError("unknown Mosaic option value: " + str(enabled)) from error
        self.expect_menu_value(value)

    def expect_mosaic_option(self, option, enabled):
        """Retain the selected option's exact historical row and result entry."""
        from ui_map import MOSAIC_OPTION_ROWS, MOSAIC_OPTION_VALUES

        try:
            label = MOSAIC_OPTIONS[option]
            top = MOSAIC_OPTION_ROWS[option]
            value = MOSAIC_OPTION_VALUES[enabled]
        except KeyError as error:
            raise UiMapError("unknown Mosaic option/value: " + str(option)) from error
        self.expect_menu_option_row(label, value, top=top)

    # ---- Harmony / Merge Shape family (live feature screens M02..M14, H01..H19) ----
    # The feature editors own their routes; the live UI shows them as focused
    # (one selected row) or detail (rows) screens and remembers each screen's
    # focus, so recipes select a row from a saturated position.

    def feature_root(self):
        """E1 on a Merge Shape/Harmony child (or a dirty root) returns to the
        clean feature root, discarding an unapplied draft (one detent)."""
        self.driver.enc(1, 1)

    def select_row(self, name, row):
        """Select a detail/focused screen's ``row`` (0-based) from its first row."""
        self.select_field(name, saturate=-24, then=row)

    def expect_selected_field(self, layout, label=None, value=None, art=False):
        """The selected field shows ``label``/``value`` on its layout's exact route."""
        from frame_oracle import selected_field_matches

        self.driver.wait(lambda state: selected_field_matches(
            state, layout, label, value, art))
        self.driver.results.append(dict(kind="selected-field", layout=layout,
                                        label=label, value=value, matched=True))

    # ---- Output (C06) verbs; channel select and Masks value line (dashboard/mask/map family) ----
    def select_channel_on_page(self, channel, page):
        """Select ``channel`` on the grid and keep working on Channel ``page``.

        The retired UI kept the showing Channel page across a grid channel
        select; the live UI returns to the remembered family (C01/C02). The
        same page is reopened through Channel Tasks and its header confirmed.
        """
        self.select_channel(channel)
        self.channel_page(page, channel=channel, confirm=False)
        # A waited header: the controlled clock redraws only as time advances.
        self.expect_header(page, channel=channel)

    def _output_row(self, field):
        """(1-based dashboard row, label) of a C06 OUTPUT row."""
        from ui_map import OUTPUT_FIELDS
        try:
            return list(OUTPUT_FIELDS).index(field) + 1, OUTPUT_FIELDS[field]
        except (KeyError, ValueError) as error:
            raise UiMapError("unknown output field: " + str(field)) from error

    def expect_output_field(self, field, value):
        """C06 OUTPUT is a dashboard: wait for ``field``'s own row to show its exact
        label and whole ``value`` (e.g. note 'C3 X X X X', vel_len '110 / 4.0')."""
        from frame_oracle import dashboard_row_matches
        index, label = self._output_row(field)
        self.driver.wait(lambda state: dashboard_row_matches(state, index, label, value))
        self.driver.results.append(dict(kind="output-field", field=field, label=label, value=str(value), passed=True))

    def output_field_value(self, field, candidates):
        """The one candidate ``field``'s C06 row shows exactly ('?' none, 'a|b' several)."""
        from frame_oracle import dashboard_row_matches
        index, label = self._output_row(field)
        state = self.driver.snapshot()
        hits = [str(v) for v in candidates if dashboard_row_matches(state, index, label, v)]
        return hits[0] if len(hits) == 1 else ("?" if not hits else "|".join(hits))

    def _mask_label(self, field):
        from ui_map import MASK_LABELS
        try:
            return MASK_LABELS[field]
        except KeyError as error:
            raise UiMapError("unknown mask field: " + str(field)) from error

    def selected_mask_value(self, field, candidates):
        """The one candidate on C01's selected value line for ``field`` ('?' when
        ``field`` is not selected or shows none; 'a|b' when several match)."""
        from frame_oracle import selected_field_matches
        label = self._mask_label(field)
        state = self.driver.snapshot()
        hits = [str(v) for v in candidates if selected_field_matches(state, "overview_masks", label, v)]
        return hits[0] if len(hits) == 1 else ("?" if not hits else "|".join(hits))

    def expect_selected_mask(self, field, value):
        """C01 has ``field`` selected and its value line shows ``value`` exactly."""
        from frame_oracle import selected_field_matches
        label = self._mask_label(field)
        self.driver.wait(lambda state: selected_field_matches(state, "overview_masks", label, value))
        self.driver.results.append(dict(kind="selected-mask", field=field, label=label, value=str(value), passed=True))

    # ---- Recording / Memory / numeric merging family ----

    def leave_merge_detail(self, channel=1):
        """Leave Merge detail (C09) for the Channel family with the Channel button.

        A held merge-mode button + pattern tap (flow G19) follows to Merge
        detail and it stays after the release (acceptance A10); the retired UI
        stayed on the Channel page. The Channel button (G01) returns to the
        remembered family and clears the return frames: K2 on C09 pops one
        frame per follow, and a second follow from C09 pushes C09 itself."""
        self.wait_for_header("merge_detail", channel=channel)
        self.tap_control("channel_editor")

    def channel_page_promptly(self, page, channel=1):
        """Open Channel ``page`` through Tasks inside a musical deadline.

        As channel_page, but the Tasks list is saturated to its first row by
        one native E2 event (the navigator clamps a large delta) rather than
        one detent per row, so the route costs a fixed ~0.2 s."""
        try:
            row = CHANNEL_TASKS.index(LIVE_SCREENS[page]["task"])
        except (KeyError, ValueError) as error:
            raise UiMapError("unknown channel page: %s" % page) from error
        self.driver.enc(1, 3)
        self.encoder_event(2, -2 * len(CHANNEL_TASKS))
        self.driver.elapse(.15)
        if row:
            self.driver.enc(2, row)
        self.press_key(3)
        self.wait_for_header(page, channel=channel)

    def assign_trig_parameter_promptly(self, parameter, offset):
        """Assign a trig parameter at a verified picker offset inside a musical
        deadline: one native E3 event saturates the picker at its first row
        (as assign_trig_parameter's 50 detents do), then ``offset`` detents."""
        label = self.trig_parameter_label(parameter)
        self.press_key(2)
        self.encoder_event(3, -126)
        self.driver.elapse(.15)
        if offset:
            self.turn(3, offset)
        self.expect_list_label(label)
        self.press_key(3)
        self.press_key(2)
        return offset


    # ---- Owner feedback 25 September 2026: dashboards, task rows (live_ui_feedback family) ----
    # Information-only screens (S03, A03, F02, F07, H05, H12, M05, P07) use the
    # dashboard layout: every field at once, label left, value right, no cursor.

    def expect_dashboard_row(self, label, value):
        """Some dashboard row shows exactly ``label`` and ``value``; returns its 1-based index."""
        from frame_oracle import DASHBOARD_ROWS, dashboard_row_matches
        found = []

        def matches(state):
            for index in range(1, len(DASHBOARD_ROWS) + 1):
                if dashboard_row_matches(state, index, label, value):
                    found.append(index)
                    return True
            return False
        self.driver.wait(matches)
        self.driver.results.append(dict(kind="dashboard-row", label=label, value=value,
                                        row=found[-1], passed=True))
        return found[-1]

    def expect_dashboard(self, page, rows, **params):
        """The whole dashboard ``page`` (a ui_map header key) shows its title row and
        exactly ``rows`` ((label, value) in order), nothing else and no cursor."""
        from frame_oracle import dashboard_matches
        title, scope, layout = header_parts(page, **params)
        if layout != "dashboard":
            raise UiMapError("%s is not a dashboard screen" % page)
        rows = [(label, str(value)) for label, value in rows]
        self.driver.wait(lambda state: dashboard_matches(state, title, scope, rows))
        self.driver.results.append(dict(kind="dashboard", title=title, scope=scope,
                                        rows=[list(row) for row in rows], passed=True))
