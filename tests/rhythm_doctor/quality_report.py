"""RD-02 gates over independent measured counts, never detector self-labels.

Corpus licensing, partition integrity and raw-evidence hashes are separate gates.
A green score report alone is not full RD-02 acceptance.
"""
import math

LANES = ("BD", "SD", "HH", "TOM", "BASS")
STRATA = ("isolated", "sparse", "full_mix")
COUNTS = ("onset_tp", "onset_fp", "onset_fn", "cell_tp", "cell_fp", "cell_fn",
          "negative_control_painted_events", "negative_control_clips")


def evaluate(measurements):
    errors, domains, scores = [], set(), []
    lane_velocity = {lane: [] for lane in LANES}
    lane_negatives = {lane: 0 for lane in LANES}
    for index, row in enumerate(measurements):
        if not isinstance(row, dict):
            errors.append("invalid measurement %d" % index)
            continue
        domain = (row.get("lane"), row.get("stratum"))
        if domain[0] not in LANES or domain[1] not in STRATA or domain in domains:
            errors.append("unknown or repeated lane/stratum %r" % (domain,))
            continue
        domains.add(domain)
        if any(type(row.get(field)) is not int or row[field] < 0 for field in COUNTS):
            errors.append("invalid counts for %r" % (domain,))
            continue
        velocity = row.get("velocity_absolute_errors")
        if not isinstance(velocity, list) or any(type(v) not in (int, float) or not math.isfinite(v) or not 0 <= v <= 126 for v in velocity):
            errors.append("invalid independent velocity measurements for %r" % (domain,))
            continue
        lane_velocity[domain[0]].extend(velocity)
        lane_negatives[domain[0]] += row["negative_control_clips"]
        if row.get("velocity_monotonic") is not True:
            errors.append("gain ladder missing or nonmonotonic for %r" % (domain,))
        if row["negative_control_painted_events"]:
            errors.append("negative control painted events for %r" % (domain,))
        score = {"lane": domain[0], "stratum": domain[1]}
        for prefix, gate in (("onset", .80), ("cell", .85)):
            tp, fp, fn = (row[prefix + suffix] for suffix in ("_tp", "_fp", "_fn"))
            if tp + fn == 0:
                errors.append("missing positive %s reference events for %r" % (prefix, domain))
            denominator = 2 * tp + fp + fn
            f1 = 2 * tp / denominator if denominator else 0
            score[prefix + "_f1"] = f1
            if f1 < gate:
                errors.append("%s F1 below %.2f for %r" % (prefix, gate, domain))
        scores.append(score)
    for lane in LANES:
        for stratum in STRATA:
            if (lane, stratum) not in domains:
                errors.append("missing domain %s/%s" % (lane, stratum))
        if lane_negatives[lane] < 5:
            errors.append("missing absent-lane controls for " + lane)
        values = lane_velocity[lane]
        if not values or sum(values) / len(values) > 16:
            errors.append("missing or failing per-lane velocity MAE for " + lane)
    return {"passed": not errors, "errors": errors, "scores": scores,
            "complete_rd02_acceptance": False,
            "scope": "quality metrics only; corpus and provenance gates remain separate"}
