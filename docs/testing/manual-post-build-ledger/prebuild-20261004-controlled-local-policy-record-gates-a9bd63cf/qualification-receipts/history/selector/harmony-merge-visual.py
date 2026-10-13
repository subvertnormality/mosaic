"""Literal framebuffer contracts which do not have a mapped UI verb yet."""


# Only these durable README frames have a separately authored v2 mini-header
# contract. Their old pixels remain the baseline for every pixel outside the
# exact atlas sprite; unlisted documentation checks stay on the strict path.
_MINI_DOCUMENTATION_FRAMES = {
    'images/harmony-tone-map.png': (
        '9ada7d5dfae6b9d849e19f4228b1475459595d3f9eefe57af08ef87904e6f823',
        'c6d2c5bba8503166a2abeb5f728091e01227f397e6656cee555625433824227b', 'H11'),
    'images/harmony-no-voicing.png': (
        'f55f4b3fb68a92d1721a928b3e587ba0716dc174ab05a9cf1e4bb6d094eac7ea',
        '52c9016ad80d1d7c92a9e6d8b97109f21b5450f6453cff5758774e552b5eeef2', 'H05'),
    'images/merge-shape-foundation.png': (
        '1dac205f0379af973f62703cc49507cddacea68d019fcac9a172d46ec7ea9850',
        '49ddaad6ba1a77775be8ce7e8d32ff61670f25bacd664560166d019787970463', 'M03'),
    'images/merge-shape-fragments.png': (
        '7984c43100cc0c290f1f9639d32ed0aae7102f10c0d7efa03e8c3f3afa6f014a',
        '760b9f276791a959a98a73441d88f534d9f77730fad051d93dd890841581689b', 'M15'),
    'images/merge-shape-interlock.png': (
        '533d8bbbb5553040db390a0dd79c89873fd58a37b1f8d8a1a218c62bbbb5f4e2',
        'de6e77eb93ebd84d696def4c0862dd49140f3447b745fd92d445ab3c014615a7', 'M16'),
    'images/merge-shape-structure.png': (
        '4fbf43e3e5a53b6ba8a92116f3e006432b7a1329e2f2437565b649ffce7bb223',
        'f2250df79def76419e0054c5295e2183b3f889513bc2bce77bed46af702f8095', 'M18'),
}


def _decode_documentation_png(path):
    """Decode the repository's authored 3x/4x grayscale documentation PNG."""
    import struct
    import zlib

    raw = path.read_bytes()
    assert raw[:8] == b'\x89PNG\r\n\x1a\n'
    at = 8
    compressed = bytearray()
    width = height = color = depth = interlace = None
    while at < len(raw):
        size = struct.unpack('>I', raw[at:at + 4])[0]
        kind = raw[at + 4:at + 8]
        data = raw[at + 8:at + 8 + size]
        at += size + 12
        if kind == b'IHDR':
            width, height, depth, color, _, _, interlace = struct.unpack('>IIBBBBB', data)
        elif kind == b'IDAT':
            compressed.extend(data)
        elif kind == b'IEND':
            break
    assert depth == 8 and color == 0 and interlace == 0, \
        'Pinned documentation frame must remain a non-interlaced grayscale PNG'
    assert width % 128 == 0 and height % 64 == 0 and width // 128 == height // 64, \
        'Pinned documentation frame must have an integer isotropic scale'
    scale = width // 128
    assert scale in (3, 4), 'Pinned documentation frame scale changed'
    encoded = zlib.decompress(bytes(compressed))
    stride = width
    rows = []
    previous = bytearray(stride)
    offset = 0
    for _ in range(height):
        filter_kind = encoded[offset]
        scan = bytearray(encoded[offset + 1:offset + 1 + stride])
        offset += stride + 1
        for x in range(stride):
            left = scan[x - 1] if x else 0
            above = previous[x]
            upper_left = previous[x - 1] if x else 0
            if filter_kind == 1:
                scan[x] = (scan[x] + left) & 255
            elif filter_kind == 2:
                scan[x] = (scan[x] + above) & 255
            elif filter_kind == 3:
                scan[x] = (scan[x] + ((left + above) // 2)) & 255
            elif filter_kind == 4:
                predictor = left + above - upper_left
                pa, pb, pc = abs(predictor - left), abs(predictor - above), abs(predictor - upper_left)
                nearest = left if pa <= pb and pa <= pc else (above if pb <= pc else upper_left)
                scan[x] = (scan[x] + nearest) & 255
            else:
                assert filter_kind == 0, 'Unsupported PNG filter in pinned documentation frame'
        rows.append(scan)
        previous = scan
    # Infer the authored integer scale and prove each expanded source pixel
    # is a uniform nearest-neighbour block before reducing it.
    frame = bytearray(128 * 64 * 4)
    for y in range(64):
        source_row = rows[y * scale]
        for x in range(128):
            value = source_row[x * scale]
            assert all(rows[y * scale + dy][x * scale + dx] == value
                       for dy in range(scale) for dx in range(scale)), \
                'Pinned documentation frame is no longer an exact nearest-neighbour scale'
            i = (y * 128 + x) * 4
            frame[i:i + 4] = bytes((value, value, value, 255 if value else 0))
    return bytes(frame)


def _documented_mini_variants(expected_sha256, name):
    """Return exact top-55 frames: immutable old image plus authored v2 poses."""
    import hashlib
    from pathlib import Path
    from contract.mini_header_animation_ui import atlas
    from contract.mini_header_ui import literal_pixels

    image_sha, baseline_sha, page = _MINI_DOCUMENTATION_FRAMES[name]
    assert expected_sha256 == baseline_sha, 'Static documentation frame oracle changed'
    image = Path(__file__).resolve().parents[3] / name
    assert hashlib.sha256(image.read_bytes()).hexdigest() == image_sha, \
        'Pinned documentation image changed'
    baseline = _decode_documentation_png(image)
    baseline_top = baseline[:128 * 55 * 4]
    assert hashlib.sha256(baseline_top).hexdigest() == baseline_sha, \
        'Pinned documentation image no longer reconstructs its original framebuffer oracle'

    spec = atlas()[page]
    variants = []
    for pose, rows in enumerate(spec['frames']):
        data = bytearray(baseline_top)
        sprite = literal_pixels(spec, rows)
        x, y = spec['origin']
        for yy in range(y, y + 8):
            for xx in range(x, 128):
                i = (yy * 128 + xx) * 4
                data[i:i + 3] = sprite[i:i + 3]
                data[i + 3] = 255 if sprite[i] or sprite[i + 1] or sprite[i + 2] else 0
        variants.append((pose, bytes(data)))
    return baseline_sha, page, variants


def documentation_frame(c, expected_sha256, name, stable_rows=None):
    """The live framebuffer (or its first ``stable_rows`` rows) is exactly the
    frame the named README image shows. Decorative motion (the title mark's
    lap, a character blink) is transient, so the exact frame is awaited."""
    import base64
    import hashlib

    variants = None
    baseline_sha = None
    page = None
    if stable_rows == 55 and name in _MINI_DOCUMENTATION_FRAMES:
        baseline_sha, page, variants = _documented_mini_variants(expected_sha256, name)

    def digest(state):
        frame = state["frame"]
        if stable_rows is None:
            return frame["sha256"]
        pixels = base64.b64decode(frame["pixels_base64"])
        return hashlib.sha256(pixels[:128 * stable_rows * 4]).hexdigest()

    seen = []
    try:
        if variants is None:
            c.wait(lambda state: seen.append(digest(state)) or seen[-1] == expected_sha256)
        else:
            allowed = {hashlib.sha256(data).hexdigest() for _, data in variants}
            c.wait(lambda state: seen.append(digest(state)) or seen[-1] in allowed)
    except AssertionError:
        raise AssertionError(dict(frame=name, expected=expected_sha256,
                                  actual=seen[-1] if seen else None)) from None
    result = dict(kind="documentation-frame", name=name,
                  sha256=seen[-1] if variants is not None else expected_sha256,
                  passed=True)
    if variants is not None:
        result.update(dict(validation="pinned-v2-mini-pose", page=page,
                           baseline_sha256=baseline_sha,
                           atlas_sha256='4b1623dd87cabd4a98b3ed5d2e47b32455221c360054f1eb5dd8783eb5278c46',
                           matching_poses=[pose for pose, data in variants
                                           if hashlib.sha256(data).hexdigest() == seen[-1]]))
    c.results.append(result)


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
