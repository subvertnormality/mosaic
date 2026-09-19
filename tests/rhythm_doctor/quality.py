"""Independent RD-02 scoring. Never infer reference events from predictions."""
import math

def _times(values):
    values = list(values)
    if any(isinstance(v, bool) or not isinstance(v, (int, float)) or
           not math.isfinite(v) or v < 0 for v in values):
        raise ValueError("onsets must be finite nonnegative seconds")
    return sorted(values)

def onset_score(reference, predicted, tolerance=0.050):
    """Maximum one-to-one matching for a fixed symmetric time tolerance."""
    if isinstance(tolerance, bool) or not math.isfinite(tolerance) or tolerance < 0:
        raise ValueError("invalid tolerance")
    reference, predicted = _times(reference), _times(predicted)
    i = j = tp = 0
    while i < len(reference) and j < len(predicted):
        difference = predicted[j] - reference[i]
        if abs(difference) <= tolerance + 1e-12:
            tp += 1
            i += 1
            j += 1
        elif difference < 0:
            j += 1
        else:
            i += 1
    fp, fn = len(predicted) - tp, len(reference) - tp
    denominator = 2 * tp + fp + fn
    return {"tp": tp, "fp": fp, "fn": fn,
            "f1": 2 * tp / denominator if denominator else 1.0}

def velocity_mae(independent_pairs):
    pairs = list(independent_pairs)
    if not pairs:
        raise ValueError("missing velocity evidence")
    for pair in pairs:
        if len(pair) != 2 or any(type(v) is not int or not 1 <= v <= 127 for v in pair):
            raise ValueError("velocity pairs must contain MIDI velocities 1..127")
    return sum(abs(reference - predicted) for reference, predicted in pairs) / len(pairs)
