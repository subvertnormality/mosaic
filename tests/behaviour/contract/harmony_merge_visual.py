"""Literal framebuffer contracts which do not have a mapped UI verb yet."""


def documentation_frame(c, expected_sha256, name, stable_rows=None):
    """The live framebuffer (or its first ``stable_rows`` rows) is exactly the
    frame the named README image shows. Decorative motion (the title mark's
    lap, a character blink) is transient, so the exact frame is awaited."""
    import base64
    import hashlib

    def digest(state):
        frame = state["frame"]
        if stable_rows is None:
            return frame["sha256"]
        pixels = base64.b64decode(frame["pixels_base64"])
        return hashlib.sha256(pixels[:128 * stable_rows * 4]).hexdigest()

    seen = []
    try:
        c.wait(lambda state: seen.append(digest(state)) or seen[-1] == expected_sha256)
    except AssertionError:
        raise AssertionError(dict(frame=name, expected=expected_sha256,
                                  actual=seen[-1] if seen else None)) from None
    c.results.append(dict(kind="documentation-frame", name=name,
                          sha256=expected_sha256, passed=True))


def expect_rendered_region(c, commands, *, left=None, right=None, top=None,
                           bottom=None, regions=None):
    """Keep a literal render oracle over the exact same pixels as its caller."""
    import base64
    from frame_oracle import render

    expected = render(commands)
    selected_regions = regions or [(left, right, top, bottom)]
    indexes = [(y * 128 + x) * 4 + channel
               for region_left, region_right, region_top, region_bottom in selected_regions
               for y in range(region_top, region_bottom)
               for x in range(region_left, region_right)
               for channel in range(3)]
    c.wait(lambda state: all(
        base64.b64decode(state["frame"]["pixels_base64"])[index] == expected[index]
        for index in indexes
    ))
