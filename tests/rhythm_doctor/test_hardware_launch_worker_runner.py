"""Local contract checks for the deliberately opt-in Norns launch-worker runner."""
import importlib.util
import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[2]
RUNNER = ROOT / "tests/rhythm_doctor/run_hardware_launch_worker.py"


def load_runner():
    spec = importlib.util.spec_from_file_location("hardware_launch_worker", RUNNER)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader
    spec.loader.exec_module(module)
    return module


class HardwareLaunchWorkerRunnerContract(unittest.TestCase):
    def setUp(self):
        self.runner = load_runner()

    def test_runner_is_explicitly_opt_in_and_has_a_narrow_deployment_manifest(self):
        self.assertIn("--execute", RUNNER.read_text(encoding="utf-8"))
        self.assertEqual(self.runner.FILES, (
            "tools/rhythm_doctor/launch_worker.py",
            "tools/rhythm_doctor/rd_capture_worker.c",
            "tools/rhythm_doctor/rd_capture.c",
            "lib/rhythm_doctor/native_transport.lua",
            "lib/rhythm_doctor/file_mailbox.lua",
            "tests/rhythm_doctor/test_launch_worker_transport.lua",
        ))
        self.assertTrue(all(not name.startswith(("mosaic.lua", "data/", "projects/"))
                            for name in self.runner.FILES))

    def test_launcher_command_uses_system_capture_ports_and_the_disposable_runtime(self):
        remote = "/tmp/mosaic-rd-launch-worker-abc"
        command = self.runner.launch_command(remote)
        self.assertIn("python3", command)
        self.assertIn(remote + "/tools/rhythm_doctor/launch_worker.py", command)
        self.assertIn("--source " + remote + "/tools/rhythm_doctor", command)
        self.assertIn("--runtime " + remote + "/runtime", command)
        self.assertIn("--left system:capture_1", command)
        self.assertIn("--right system:capture_2", command)
        self.assertNotIn("/home/we/dust", command)

    def test_only_the_worker_private_tmp_root_is_accepted_for_cleanup(self):
        self.assertEqual(self.runner.private_worker_root("/tmp/mosaic-rd-1000-abcdef", 1000),
                         "/tmp/mosaic-rd-1000-abcdef")
        for value in ("/tmp/other", "/tmp/mosaic-rd-1001-abcdef",
                      "/tmp/mosaic-rd-1000-abcdef/c2w", "mosaic-rd-1000-abcdef"):
            self.assertIsNone(self.runner.private_worker_root(value, 1000))

    def test_report_output_is_created_once(self):
        self.assertIn('open("x", encoding="utf-8")', RUNNER.read_text(encoding="utf-8"))

    def test_worker_build_identity_matches_the_production_helper_inputs(self):
        import hashlib

        expected = hashlib.sha256()
        source = ROOT / "tools/rhythm_doctor"
        for name in ("rd_capture_worker.c", "rd_capture.c"):
            expected.update(name.encode("utf-8") + b"\0")
            expected.update((source / name).read_bytes())
        self.assertEqual(self.runner.worker_build_identity(ROOT), expected.hexdigest())


if __name__ == "__main__":
    unittest.main()
