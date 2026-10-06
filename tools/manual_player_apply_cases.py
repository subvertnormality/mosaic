"""Controlled software-player selection, apply, and reopen acceptance.

All assertions use the public norns page and pixel matchers. No app internals,
MIDI playback, or n.b. audio state are used as an oracle.
"""
from frame_oracle import footer_matches

TARGETS = (
    (1, "Oilcan 1"),
    (2, "Polyperc 1"),
    (3, "Doubledecker"),
)


def _last_public_state(c):
    observations = getattr(c, "observations", None)
    if not observations:
        raise AssertionError("native observation is missing after public screen assertion")
    state = observations[-1].get("state")
    frame = state.get("frame") if isinstance(state, dict) else None
    if not isinstance(frame, dict) or not frame.get("sha256"):
        raise AssertionError("latest public observation has no native frame hash")
    return state


def _require_same_frame_device_receipt(c, device):
    state = _last_public_state(c)
    observations = c.observations
    latest_index = len(observations) - 1
    receipt = next((row for row in reversed(c.results)
                    if row.get("kind") == "selected-field"), None)
    if (not receipt or receipt.get("matched") is not True
            or receipt.get("layout") != "detail"
            or receipt.get("label") != "Device"
            or receipt.get("value") != device
            or receipt.get("observation_index") != latest_index
            or receipt.get("frame_sha256") != state["frame"]["sha256"]):
        raise AssertionError("Device field pixel receipt is not bound to the latest native frame")
    return state


def _choose_pending_player(c, channel, device):
    # Device is a public selected field; every change is made through E3.
    for _ in range(40):
        if c.ui.shown_device([device]) == device:
            return
        c.ui.turn(3, 1)
    raise AssertionError("supported Device row did not reach the requested player")


def _pending(c, channel, device):
    state = _require_same_frame_device_receipt(c, device)
    if not footer_matches(state, "Press K3 to confirm"):
        raise AssertionError("selected player is not visibly waiting for K3 confirmation")
    c.results.append(dict(kind="manual-player-apply-pending", citation="manual:mods-and-software-devices",
                          channel=channel, field="Device", value=device,
                          confirmation_prompt="Press K3 to confirm", passed=True))


def _no_pending_prompt(c, channel, device, kind):
    # Value and prompt are checked against the same latest native observation.
    state = _require_same_frame_device_receipt(c, device)
    if footer_matches(state, "Press K3 to confirm"):
        raise AssertionError("Device page still shows pending confirmation")
    c.results.append(dict(kind=kind, citation="manual:mods-and-software-devices",
                          channel=channel, page="midi_config", field="Device",
                          value=device, confirmation_prompt_absent=True, passed=True))


def apply_and_reopen_players(c):
    for index, (channel, device) in enumerate(TARGETS, start=1):
        c.ui.select_channel(channel)
        c.ui.channel_page("midi_config", channel=channel)
        c.ui.expect_header("midi_config", channel=channel)
        # The initial value is intentionally observed from the current Device
        # row; the case makes no assumption about a pre-existing assignment.
        c.ui.expect_selected_field("detail", label="Device")
        c.results.append(dict(kind="manual-player-apply-start", citation="manual:mods-and-software-devices",
                              channel=channel, page="midi_config", field="Device", passed=True))

        _choose_pending_player(c, channel, device)
        c.ui.expect_header("midi_config", channel=channel)
        c.ui.expect_selected_field("detail", label="Device", value=device)
        _pending(c, channel, device)

        c.ui.press_key(3)
        # Observe application on the current public Device page before leaving.
        c.ui.expect_header("midi_config", channel=channel)
        c.ui.expect_selected_field("detail", label="Device", value=device)
        _no_pending_prompt(c, channel, device, "manual-player-apply-applied")

        # Leave the page through the public Channel Tasks path and reopen it.
        c.ui.channel_page("midi_config", channel=channel)
        c.ui.expect_header("midi_config", channel=channel)
        c.ui.expect_selected_field("detail", label="Device", value=device)
        _no_pending_prompt(c, channel, device, "manual-player-apply-reopened")


CASES = {
    "M-MANUAL-PLAYER-APPLY-001": dict(
        run=apply_and_reopen_players,
        citation="manual:mods-and-software-devices",
        requirements=["CH-DEVICE"],
        description="Choose three supported players, apply with K3, then reopen Device and verify the persisted public value without a pending-confirmation prompt",
    )
}
