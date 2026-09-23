"""Literal framebuffer contracts which do not have a mapped UI verb yet."""


def documentation_frame(c, expected_sha256, name, stable_rows=None):
    import base64
    import hashlib

    frame = c.snapshot()["frame"]
    if stable_rows is None:
        actual = frame["sha256"]
    else:
        pixels = base64.b64decode(frame["pixels_base64"])
        actual = hashlib.sha256(pixels[:128 * stable_rows * 4]).hexdigest()
    assert actual == expected_sha256, dict(
        frame=name, expected=expected_sha256, actual=actual
    )
    c.results.append(dict(kind="documentation-frame", name=name,
                          sha256=actual, passed=True))


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
