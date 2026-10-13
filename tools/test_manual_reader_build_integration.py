"""Reader projection is a required build stage in both build completion lanes."""
from __future__ import annotations

import importlib.util
import os
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch


TOOLS = Path(os.environ.get("MOSAIC_RESUME_TEST_TOOLS", Path(__file__).parent)).resolve()
ROOT = Path(os.environ.get("MOSAIC_REPO_ROOT", Path(__file__).resolve().parents[1])).resolve()


def load_builder():
    spec = importlib.util.spec_from_file_location("manual_build_reader_test", TOOLS / "manual_build.py")
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    module.ROOT = ROOT
    return module


def test_build_plan_runs_projection_after_book_compile_and_before_audit():
    builder = load_builder()
    options = SimpleNamespace(
        real_install="/qualified-real", emulator="/emu", audio_emulator="/audio-emu",
        audio_install="/audio-install", mod_code_root="/mods", ffmpeg="ffmpeg",
        controlled_install="/controlled", modulation_code_root="/mod-code",
        modulation_emulator="/mod-emu", modulation_controlled_install="/mod-controlled",
        readability_real_install="/readability-real", browser_tests=False, python="python3",
        node="node", quick_output="manual/generated/quick-reference.html",
    )
    plans = [path.name for path in sorted((ROOT / "manual").glob("scene-plans*.yaml"))]
    stages = builder.plan(options, plans, controlled_local=True)
    names = [stage["name"] for stage in stages]
    assert names.count("reader-projection") == 1
    assert names.index("compile-book") < names.index("reader-projection") < names.index("quick-reference")
    command = stages[names.index("reader-projection")]["command"]
    assert any(Path(value).name == "manual_reader_projection.py" for value in command)


def test_completion_requires_one_successful_projection_receipt():
    builder = load_builder()
    book = {"complete_manual": True}
    with patch.object(builder, "verify_doctor_completion"):
        assert not builder.complete_build(True, ["all"], ["all"], book, [])
        assert not builder.complete_build(True, ["all"], ["all"], book, [
            {"name": "reader-projection", "passed": False, "reader_projection": {"passed": True}},
        ])
        assert not builder.complete_build(True, ["all"], ["all"], book, [
            {"name": "reader-projection", "passed": True, "reader_projection": {"passed": True}},
            {"name": "reader-projection", "passed": True, "reader_projection": {"passed": True}},
        ])
        assert builder.complete_build(True, ["all"], ["all"], book, [
            {"name": "reader-projection", "passed": True, "reader_projection": {"passed": True}},
        ])
