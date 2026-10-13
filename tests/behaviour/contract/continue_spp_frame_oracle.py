"""Exact screen comparison outside a declared authored mini-header footprint."""
import base64


def outside_mini(frame, spec):
    """Return every framebuffer byte outside the exact atlas rectangle."""
    if isinstance(frame, dict):
        frame = base64.b64decode(frame["frame"]["pixels_base64"])
    if len(frame) != 128 * 64 * 4:
        raise AssertionError("Expected the complete 128x64 RGBA framebuffer")
    x, y = spec["origin"]
    width, height = spec["width"], spec["height"]
    if not (0 <= x < 128 and 0 <= y < 64 and 0 < width <= 128 - x and 0 < height <= 64 - y):
        raise AssertionError("Invalid authored mini-header footprint")
    return b"".join(
        frame[(row * 128 + col) * 4:(row * 128 + col + 1) * 4]
        for row in range(64)
        for col in range(128)
        if not (x <= col < x + width and y <= row < y + height)
    )


def assert_same_outside_mini(actual, expected, spec):
    if outside_mini(actual, spec) != outside_mini(expected, spec):
        raise AssertionError("Screen pixels outside the authored mini-header changed")
