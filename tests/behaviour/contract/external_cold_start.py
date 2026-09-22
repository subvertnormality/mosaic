"""Cold 20 BPM timing contract with a known failing wall-clock baseline."""

from external_cold_start import external_cold_start


def external_cold_start_20(c):
    return external_cold_start(c, bpm=20)
