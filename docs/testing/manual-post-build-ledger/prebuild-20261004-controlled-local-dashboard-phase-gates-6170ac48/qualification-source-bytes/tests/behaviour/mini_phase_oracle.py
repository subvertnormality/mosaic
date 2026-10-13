"""Compatibility imports for the contract-owned native mini-phase oracle.

Native framebuffer and musical-phase acceptance lives in contract/; this
module retains the existing tools/tests import path without another oracle.
"""
from contract.mini_phase_oracle import (
    require, finite, observed_phases, native_frame, clock_receipt, phase_interval,
    check_stopped_phase, check_playing_phases,
)
