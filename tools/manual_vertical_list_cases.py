"""Compatibility import for vertical-list acceptance now registered in CI.

The actual public-input acceptance lives under tests/behaviour/contract/vertical_list_ui.py.
No duplicate CASES are exported through --extra-cases; the canonical registry
already supplies M-UI-VERTICAL-001. Historical native helper bytes stay frozen
in their original start-source captures.
"""
from contract.vertical_list_ui import clock_list, label_row
CASES = {}
