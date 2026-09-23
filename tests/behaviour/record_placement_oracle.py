_WITNESS_PITCH_BY_STEP = {1: 60, 2: 62, 3: 64, 4: 65}


def derive_boundary_recorded_step(prior_pitch, following_pitch, candidate_steps):
    """Derive a boundary placement from witnesses under README.md's Arm live record rule."""
    candidates = tuple(candidate_steps)
    step = next((candidate for candidate in candidates
                 if _WITNESS_PITCH_BY_STEP.get(candidate) == prior_pitch), None)
    assert step is not None, dict(prior_pitch=prior_pitch, candidates=candidates,
                                  reason='prior witness is not an allowed candidate')
    expected_following = _WITNESS_PITCH_BY_STEP[step % 4 + 1]
    assert following_pitch == expected_following, dict(prior_pitch=prior_pitch,
        following_pitch=following_pitch, expected_following=expected_following,
        reason='witnesses are not adjacent')
    return step
