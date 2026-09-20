"""Independent sample-authoritative grid oracle; no production Bank imports."""
import math

def finite(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)

def grid_score(ref, pred, sr, bpm, origin=0., end=8.):
    if not finite(sr) or sr != int(sr) or not 8000 <= sr <= 192000:
        raise ValueError('invalid sample rate')
    if not finite(bpm) or not 40 <= bpm <= 240:
        raise ValueError('invalid BPM')
    if not finite(origin) or not finite(end) or not 0 <= origin < end:
        raise ValueError('invalid capture bounds')
    # Timestamp conversion occurs exactly once, ties to the later sample.
    start = math.floor(origin * sr + .5)
    stop = math.floor(end * sr + .5)
    width = sr * 15 / bpm
    count = math.floor((stop - start) / width)
    if count < 64:
        raise ValueError('no complete four-bar window')
    def cells(events):
        samples = []
        for event in events:
            if not finite(event):
                raise ValueError('invalid onset')
            samples.append(math.floor(event * sr + .5))
        return {min(count - 1, math.floor((sample - start) / width + .5))
                for sample in samples if start <= sample < start + count * width}
    expected, actual = cells(ref), cells(pred)
    tp = len(expected & actual)
    return {'tp': tp, 'fp': len(actual - expected), 'fn': len(expected - actual),
            'f1': 2 * tp / (len(expected) + len(actual)) if expected or actual else 1.}
