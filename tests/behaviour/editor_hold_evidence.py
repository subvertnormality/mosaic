"""Keep timing diagnostics while making controlled hold results deterministic."""


def record_hold_input_bounds(driver, sample):
    if not isinstance(sample, dict) or sample.get("kind") != "hold-input-bounds":
        raise ValueError("expected a hold-input-bounds sample")

    observation = dict(sample)
    observation["kind"] = "hold-input-bounds-sample"
    driver.observations.append(observation)

    if driver.clock_mode == "controlled-experimental":
        result = {key: sample[key] for key in (
            "kind", "x", "interrupted", "expected_long", "logical_seconds")}
    else:
        result = dict(sample)
    driver.results.append(result)
    return result


def raw_editor_range_hold(c, x, y):
    """Replay the pre-abstraction range hold as the same primitive grid edges."""
    c.action(type="grid", x=x, y=y, state=1)
    try:
        c.elapse(1.1)
    finally:
        c.action(type="grid", x=x, y=y, state=0)
