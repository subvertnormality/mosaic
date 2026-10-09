"""Durable pure Doctor fixture guards: characterization outside README.

These test receipt/parser/phrase boundaries, not application audio acceptance.
No emulator startup or fabricated bank is passed to Mosaic.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools'))
import doctor_ready_fixture


def load_tests(loader, tests, pattern):
    return doctor_ready_fixture.guard_test_suite()
