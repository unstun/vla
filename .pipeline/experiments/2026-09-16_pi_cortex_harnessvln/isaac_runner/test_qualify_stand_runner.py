import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import qualify_stand_runner as qualify


class StandRunnerPackageTests(unittest.TestCase):
    def test_prepare_dry_run_package_uses_exact_parser_configuration(self):
        run_id = "stand_unit_package"
        with tempfile.TemporaryDirectory() as tmp:
            args = qualify.build_parser().parse_args([
                "--run-id", run_id,
                "--local-runs-root", str(Path(tmp) / "runs"),
                "--remote-root", "/remote/root",
                "--remote-v12-runtime", "/remote/v12",
                "--remote-checkpoint", "/remote/checkpoint/model.pt",
            ])
            local_run, commands = qualify.prepare(args)
            self.assertTrue((local_run / "bridge/lite3_sim_bridge/run_pct_scan_building.py").exists())
            self.assertTrue((local_run / "inputs/stand_scope.json").exists())
            self.assertTrue((local_run / "inputs/execution_manifest.json").exists())
            self.assertTrue((local_run / "remote_worker.py").exists())
            scope = json.loads((local_run / "inputs/stand_scope.json").read_text())
            runner = qualify.import_runner(local_run / "bridge/lite3_sim_bridge/run_pct_scan_building.py")
            parsed = runner.build_parser().parse_args(qualify.build_runner_argv(
                args, "/remote/root/" + run_id, run_id
            ))
            self.assertEqual(scope["execution_configuration"], runner.execution_configuration(parsed))
            self.assertEqual(scope["execution_configuration"]["case"], "stand_probe")
            self.assertTrue(scope["execution_configuration"]["external_goal_mode"])
            self.assertTrue(scope["execution_configuration"]["complete_body_state"])
            self.assertEqual(commands["remote_run"], "/remote/root/" + run_id)
            self.assertIn("--include=/bridge/***", commands["sync"])
            self.assertNotIn("full_route", scope)
            source_hashes = json.loads((local_run / "source_env_hashes.json").read_text())
            self.assertGreater(source_hashes["v12_runtime_expected_file_count"], 10)
            self.assertIn("resources/lite3/urdf/lite3.urdf", source_hashes["v12_runtime_expected"])
            manifest = json.loads((local_run / "inputs/package_manifest.json").read_text())
            self.assertIn("source_env_hashes.json", [entry["path"] for entry in manifest["files"]])
            worker_source = (local_run / "remote_worker.py").read_text()
            self.assertIn("verify_v12_runtime(args.remote_v12_runtime", worker_source)
            self.assertIn('str(runtime_source / "rsl_rl")', worker_source)
            self.assertIn('str(runtime_source / "robot_lab")', worker_source)
            self.assertIn("conda activate isaaclab", worker_source)
            self.assertIn("importlib.util.find_spec", worker_source)
            self.assertIn("find_spec_no_module_execution", worker_source)
            self.assertIn("robot_lab spec from unexpected path", worker_source)
            self.assertIn("ensure_container_absent(container_name)", worker_source)
            self.assertIn("ensure_tcp_port_free", worker_source)
            self.assertIn("if owned_container_started", worker_source)

    def test_prepare_refuses_existing_run(self):
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = Path(tmp) / "runs/existing"
            run_dir.mkdir(parents=True)
            args = qualify.build_parser().parse_args([
                "--run-id", "existing",
                "--local-runs-root", str(Path(tmp) / "runs"),
            ])
            with self.assertRaises(FileExistsError):
                qualify.prepare(args)

    def test_execute_can_load_existing_prepared_package_without_rewriting(self):
        run_id = "stand_existing_execute"
        with tempfile.TemporaryDirectory() as tmp:
            args = qualify.build_parser().parse_args([
                "--run-id", run_id,
                "--local-runs-root", str(Path(tmp) / "runs"),
                "--remote-root", "/remote/root",
            ])
            local_run, commands = qualify.prepare(args)
            source_env_before = (local_run / "source_env_hashes.json").read_text()
            exec_args = qualify.build_parser().parse_args([
                "--run-id", run_id,
                "--local-runs-root", str(Path(tmp) / "runs"),
                "--execute",
            ])
            loaded_run, loaded_commands = qualify.load_prepared_run(exec_args)
            self.assertEqual(loaded_run, local_run)
            self.assertEqual(loaded_commands, commands)
            self.assertEqual((local_run / "source_env_hashes.json").read_text(), source_env_before)

    def test_execute_collects_and_hash_verifies_after_remote_run_failure(self):
        with tempfile.TemporaryDirectory() as tmp:
            local_run = Path(tmp) / "run"
            local_run.mkdir()
            calls = []

            def fake_run_command(label, command, log_path, timeout=1800):
                calls.append(label)
                log_path.parent.mkdir(parents=True, exist_ok=True)
                log_path.write_text(label, encoding="utf-8")
                if label == "run":
                    raise RuntimeError("remote worker failed")
                if label == "collect":
                    returned = local_run / "returned_artifacts"
                    returned.mkdir()
                    (returned / "result.json").write_text("{}", encoding="utf-8")
                    qualify.write_json(returned / "artifact_hashes.json", {
                        "result.json": qualify.sha256(returned / "result.json")
                    })

            commands = {
                "mkdir": ["mkdir"],
                "sync": ["sync"],
                "run": ["run"],
                "collect": ["collect"],
            }
            with mock.patch.object(qualify, "run_command", side_effect=fake_run_command):
                with self.assertRaisesRegex(RuntimeError, "remote worker failed"):
                    qualify.execute(local_run, commands)

            self.assertEqual(calls, ["mkdir", "sync", "run", "collect"])
            verdict = json.loads((local_run / "return_verdict.json").read_text())
            self.assertTrue(verdict["remote_worker_started"])
            self.assertIn("remote worker failed", verdict["run_error"])
            self.assertTrue(verdict["returned_hashes_match"])


class StandHoldSettingsTests(unittest.TestCase):
    def prepare(self, tmp, run_id, *extra):
        args = qualify.build_parser().parse_args([
            "--run-id", run_id,
            "--local-runs-root", str(Path(tmp) / "runs"),
            "--remote-root", "/remote/root",
            *extra,
        ])
        return args, qualify.prepare(args)

    def test_defaults_keep_the_legacy_stand_and_pass_stance_hold_off(self):
        with tempfile.TemporaryDirectory() as tmp:
            args, (local_run, commands) = self.prepare(tmp, "stand_defaults")
            argv = qualify.build_runner_argv(args, "/remote/root/stand_defaults", "stand_defaults")
            self.assertEqual(argv[argv.index("--duration-seconds") + 1], "8.0")
            self.assertEqual(argv[argv.index("--stance-hold") + 1], "off")
            scope = json.loads((local_run / "inputs/stand_scope.json").read_text())
            self.assertEqual(scope["execution_configuration"]["stance_hold"], "off")
            self.assertEqual(scope["execution_configuration"]["duration_seconds"], 8.0)
            self.assertEqual(scope["resource_ceiling"]["simulation_seconds"], 8.0)
            request = json.loads((local_run / "run_request.json").read_text())
            self.assertEqual((request["stance_hold"], request["duration_seconds"], request["finish_after_sim_seconds"]),
                             ("off", 8.0, 2.0))
            self.assertEqual(commands["run"][-1].split()[-2:], ["--finish-after-sim-seconds", "2.0"])
            runner_text = (local_run / "bridge/lite3_sim_bridge/run_pct_scan_building.py").read_text()
            self.assertIn("def _stance_hold_setup(", runner_text)

    def test_sixty_second_auto_stand_package(self):
        with tempfile.TemporaryDirectory() as tmp:
            args, (local_run, commands) = self.prepare(
                tmp, "stand_auto", "--stance-hold", "auto", "--duration-seconds", "60", "--finish-after-sim-seconds", "58")
            scope = json.loads((local_run / "inputs/stand_scope.json").read_text())
            self.assertEqual(scope["execution_configuration"]["stance_hold"], "auto")
            self.assertEqual(scope["execution_configuration"]["duration_seconds"], 60.0)
            self.assertEqual(scope["stance_hold"], "auto")
            runner = qualify.import_runner(local_run / "bridge/lite3_sim_bridge/run_pct_scan_building.py")
            parsed = runner.build_parser().parse_args(json.loads(
                commands["run"][-1].split("--runner-argv-json ")[1].split(" --ros-domain-id")[0].strip("'")))
            runner.validate_run_duration(parsed.case, parsed.duration_seconds)
            self.assertEqual(runner.execution_configuration(parsed), scope["execution_configuration"])
            request = json.loads((local_run / "run_request.json").read_text())
            self.assertEqual((request["stance_hold"], request["duration_seconds"], request["finish_after_sim_seconds"]),
                             ("auto", 60.0, 58.0))
            self.assertIn("--finish-after-sim-seconds 58.0", commands["run"][-1])
            worker = (local_run / "remote_worker.py").read_text()
            self.assertIn('runner_arg_value(runner_argv, "--stance-hold")', worker)
            self.assertIn("runner summary stance_hold mode differs", worker)
            self.assertIn(">= args.finish_after_sim_seconds", worker)

    def test_invalid_settings_are_refused_before_creating_the_package(self):
        cases = [
            ["--duration-seconds", "60.5"],
            ["--duration-seconds", "0"],
            ["--duration-seconds", "nan"],
            ["--duration-seconds", "60", "--finish-after-sim-seconds", "58.5"],
            ["--finish-after-sim-seconds", "-1"],
        ]
        with tempfile.TemporaryDirectory() as tmp:
            for index, extra in enumerate(cases):
                with self.subTest(extra=extra):
                    with self.assertRaises(ValueError):
                        self.prepare(tmp, "stand_bad_%d" % index, *extra)
                    self.assertFalse((Path(tmp) / "runs" / ("stand_bad_%d" % index)).exists())
            with self.assertRaises(SystemExit), contextlib.redirect_stderr(io.StringIO()):
                qualify.build_parser().parse_args(["--stance-hold", "on"])

    def test_execute_refuses_settings_that_differ_from_the_package(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.prepare(tmp, "stand_prepared", "--stance-hold", "auto", "--duration-seconds", "60",
                         "--finish-after-sim-seconds", "58")
            runs = str(Path(tmp) / "runs")
            base = ["--run-id", "stand_prepared", "--local-runs-root", runs, "--execute"]
            same = base + ["--stance-hold", "auto", "--duration-seconds", "60", "--finish-after-sim-seconds", "58"]
            with mock.patch.object(qualify, "execute") as execute, contextlib.redirect_stdout(io.StringIO()):
                qualify.main(same)
                execute.assert_called_once()
            for extra, flag in (([], "stance-hold"),
                                (["--stance-hold", "auto"], "duration-seconds"),
                                (["--stance-hold", "auto", "--duration-seconds", "60"], "finish-after-sim-seconds")):
                with self.subTest(flag=flag), mock.patch.object(qualify, "execute") as execute:
                    with self.assertRaisesRegex(RuntimeError, "--%s .* differs from the prepared package" % flag):
                        qualify.main(base + extra)
                    execute.assert_not_called()

    def test_legacy_package_request_counts_as_off_eight_seconds(self):
        with tempfile.TemporaryDirectory() as tmp:
            run = Path(tmp)
            (run / "run_request.json").write_text(json.dumps({"duration_seconds": 8.0}))
            args = qualify.build_parser().parse_args([])
            self.assertEqual(qualify.check_prepared_request(args, run),
                             {"stance_hold": "off", "duration_seconds": 8.0, "finish_after_sim_seconds": 2.0,
                              "case": "stand_probe", "stance_entry_kd": "ramp", "camera_preset": "rear",
                              "command_script": None})
            args = qualify.build_parser().parse_args(["--stance-hold", "auto"])
            with self.assertRaisesRegex(RuntimeError, "stance-hold"):
                qualify.check_prepared_request(args, run)


D5_SCRIPT = Path(qualify.HERE) / "command_scripts/walk_stop_start_stop_v1.json"
# build_runner_argv before PRD D5, with {run} for the remote run root; the D5 change only adds
# --stance-entry-kd after --stance-hold for the default stand.
LEGACY_STAND_ARGV = [
    "--scene", "{run}/inputs/building.usda", "--runtime", qualify.DEFAULT_REMOTE_V12,
    "--checkpoint", qualify.DEFAULT_REMOTE_CHECKPOINT, "--route-artifact", "{run}/inputs/stand_route_artifact.json",
    "--scope", "{run}/inputs/stand_scope.json", "--execution-manifest", "{run}/inputs/execution_manifest.json",
    "--output", "{run}/artifacts/runner_output", "--case", "stand_probe", "--duration-seconds", "8.0",
    "--telemetry-host", "127.0.0.1", "--telemetry-port", "46240", "--command-host", "127.0.0.1",
    "--command-port", "46241", "--max-vx", "0.30", "--max-vy", "0.30", "--max-wz", "0.8",
    "--max-horizontal-norm", "0.30", "--speed-profile", "conservative_0p3", "--contact-policy", "native_v12",
    "--unfiltered-planner-cloud", "--goal-tolerance-m", "0.25", "--terminal-window-seconds", "2.0",
    "--terminal-command-norm", "0.01", "--terminal-speed-mps", "0.10", "--terminal-yaw-rate-radps", "0.15",
    "--connection-ready-timeout-seconds", "120.0", "--max-wall-seconds", "600.0", "--video-fps", "12.5",
    "--camera-capture-stride", "4", "--complete-body-state", "--priority-telemetry", "--async-recording",
    "--freeze-gc", "--external-goal-mode", "--external-run-id", "{id}", "--external-control-dir",
    "{run}/artifacts/external_episode", "--external-finish-stillness-seconds", "1.0",
    "--external-status-freshness-seconds", "2.0", "--stance-hold", "off", "--seed", "42", "--device", "cuda:0",
]
WALK_FLAGS = ["--case", "scripted_walk", "--command-script", str(D5_SCRIPT), "--camera-preset", "side",
              "--duration-seconds", "26", "--finish-after-sim-seconds", "20"]


def runner_argv_from(commands):
    return json.loads(commands["run"][-1].split("--runner-argv-json ")[1].split(" --ros-domain-id")[0].strip("'"))


class ScriptedWalkPackageTests(unittest.TestCase):
    def prepare(self, tmp, run_id, *extra):
        args = qualify.build_parser().parse_args([
            "--run-id", run_id, "--local-runs-root", str(Path(tmp) / "runs"), "--remote-root", "/remote/root",
            *extra,
        ])
        return args, qualify.prepare(args)

    def test_default_stand_argv_only_gains_the_entry_kd_flag(self):
        args = qualify.build_parser().parse_args([])
        argv = qualify.build_runner_argv(args, "/r/run", "run")
        legacy = [item.replace("{run}", "/r/run").replace("{id}", "run") for item in LEGACY_STAND_ARGV]
        position = legacy.index("--stance-hold") + 2
        self.assertEqual(argv, legacy[:position] + ["--stance-entry-kd", "ramp"] + legacy[position:])
        self.assertNotIn("--command-script", argv)
        self.assertNotIn("--camera-heading-mode", argv)

    def test_scripted_walk_package_binds_script_limits_camera_and_variant(self):
        with tempfile.TemporaryDirectory() as tmp:
            args, (local_run, commands) = self.prepare(
                tmp, "walk_auto_step2p5", *WALK_FLAGS, "--stance-hold", "auto", "--stance-entry-kd", "step2p5")
            sha = qualify.sha256(D5_SCRIPT)
            argv = runner_argv_from(commands)
            self.assertEqual(argv, qualify.build_runner_argv(args, "/remote/root/walk_auto_step2p5",
                                                              "walk_auto_step2p5"))
            value = lambda flag: argv[argv.index(flag) + 1]
            self.assertEqual((value("--case"), value("--duration-seconds"), value("--stance-hold"),
                              value("--stance-entry-kd")), ("scripted_walk", "26.0", "auto", "step2p5"))
            self.assertEqual(value("--command-script"), "/remote/root/walk_auto_step2p5/inputs/command_script.json")
            self.assertEqual([value(f) for f in ("--max-vx", "--max-vy", "--max-wz", "--max-horizontal-norm",
                                                 "--speed-profile")], ["1.0", "0.35", "1.0", "1.0", "speed_1p0"])
            self.assertEqual([value(f) for f in ("--camera-trail-m", "--camera-lateral-m", "--camera-height-m",
                                                 "--camera-look-ahead-m", "--camera-look-down-m",
                                                 "--camera-heading-mode", "--camera-capture-stride",
                                                 "--video-fps")],
                             ["0.0", "-1.25", "0.2", "0.0", "0.12", "initial", "2", "25.0"])
            self.assertEqual((local_run / "inputs/command_script.json").read_bytes(), D5_SCRIPT.read_bytes())
            manifest = json.loads((local_run / "inputs/package_manifest.json").read_text())
            entry = [e for e in manifest["files"] if e["path"] == "inputs/command_script.json"]
            self.assertEqual([e["sha256"] for e in entry], [sha])
            self.assertEqual(json.loads((local_run / "source_env_hashes.json").read_text())["command_script_sha256"], sha)
            route = json.loads((local_run / "inputs/stand_route_artifact.json").read_text())
            self.assertEqual(route["route_id"], "scripted_walk_spawn_metadata")
            scope = json.loads((local_run / "inputs/stand_scope.json").read_text())
            self.assertEqual((scope["case"], scope["command_script_sha256"], scope["stance_entry_kd"],
                              scope["camera_heading_mode"], scope["revision"]),
                             ("scripted_walk", sha, "step2p5", "initial", "p2b-scripted-walk-runner-qualification-r1"))
            self.assertIn("No SCAN", scope["claim"])
            request = json.loads((local_run / "run_request.json").read_text())
            self.assertEqual((request["case"], request["stance_hold"], request["stance_entry_kd"],
                              request["camera_preset"], request["duration_seconds"], request["finish_after_sim_seconds"]),
                             ("scripted_walk", "auto", "step2p5", "side", 26.0, 20.0))
            self.assertEqual(request["command_script"]["sha256"], sha)
            self.assertEqual(request["command_script"]["package_path"], "inputs/command_script.json")
            self.assertEqual(request["camera"]["camera_heading_mode"], "initial")
            self.assertEqual(request["command_limits"]["speed_profile"], "speed_1p0")
            self.assertIn("not a real-robot", request["claim_boundary"])
            self.assertIn("--finish-after-sim-seconds 20.0", commands["run"][-1])

            # The packaged runner accepts this exact configuration with the packaged script.
            runner = qualify.import_runner(local_run / "bridge/lite3_sim_bridge/run_pct_scan_building.py")
            parsed = runner.build_parser().parse_args(argv)
            self.assertEqual(runner.execution_configuration(parsed), scope["execution_configuration"])
            self.assertNotIn("command_script", scope["execution_configuration"])
            runner.validate_run_duration(parsed.case, parsed.duration_seconds)
            runner.validate_motion_profile(parsed)
            parsed.command_script = local_run / "inputs/command_script.json"
            parsed.output = Path(tmp) / "runner_output"
            parsed.output.mkdir()
            runner._scripted_walk_validate_args(parsed)
            runner._validate_external_goal_args(parsed)
            loaded = runner._scripted_walk_setup(parsed, scope)
            self.assertEqual(loaded["sha256"], sha)
            self.assertAlmostEqual(1.0 / (0.02 * parsed.camera_capture_stride), parsed.video_fps, places=9)

            worker = (local_run / "remote_worker.py").read_text()
            for text in ('runner_arg_value(runner_argv, "--stance-entry-kd")',
                         '["EXTERNAL_EPISODE_FINISHED", "DURATION_REACHED"] if case == "scripted_walk"',
                         "runner summary case differs", "runner summary stance_hold entry_kd differs",
                         "runner summary camera heading_mode differs",
                         "packaged command script SHA-256 differs from source_env_hashes.json",
                         "finish_request_snapshot_sim_time_s"):
                self.assertIn(text, worker)
            compile(worker, "remote_worker.py", "exec")

    def test_hold_off_walk_package_uses_ramp_and_stand_defaults_are_unchanged(self):
        with tempfile.TemporaryDirectory() as tmp:
            _args, (local_run, commands) = self.prepare(tmp, "walk_off", *WALK_FLAGS)
            argv = runner_argv_from(commands)
            self.assertEqual(argv[argv.index("--stance-hold") + 1], "off")
            self.assertEqual(argv[argv.index("--stance-entry-kd") + 1], "ramp")
            _args, (stand_run, _commands) = self.prepare(tmp, "stand_default")
            request = json.loads((stand_run / "run_request.json").read_text())
            self.assertEqual((request["case"], request["camera_preset"], request["stance_entry_kd"],
                              request["command_script"]), ("stand_probe", "rear", "ramp", None))
            self.assertEqual(request["camera"]["video_fps"], 12.5)
            scope = json.loads((stand_run / "inputs/stand_scope.json").read_text())
            self.assertNotIn("command_script_sha256", scope)
            self.assertEqual(scope["revision"], "p2b-stand-only-runner-qualification-r1")
            self.assertEqual(scope["execution_configuration"]["camera_heading_mode"], "body")
            self.assertFalse((stand_run / "inputs/command_script.json").exists())

    def test_invalid_walk_settings_are_refused_before_creating_the_package(self):
        with tempfile.TemporaryDirectory() as tmp:
            nonzero_last = Path(tmp) / "nonzero_last.json"
            nonzero_last.write_text(json.dumps({"schema_version": 1, "segments": [
                {"t_start_s": 0.0, "vx": 0.0, "vy": 0.0, "wz": 0.0},
                {"t_start_s": 4.0, "vx": 0.6, "vy": 0.0, "wz": 0.0}]}))
            too_fast = Path(tmp) / "too_fast.json"
            too_fast.write_text(json.dumps({"schema_version": 1, "segments": [
                {"t_start_s": 0.0, "vx": 1.2, "vy": 0.0, "wz": 0.0},
                {"t_start_s": 4.0, "vx": 0.0, "vy": 0.0, "wz": 0.0}]}))
            base = ["--duration-seconds", "26", "--finish-after-sim-seconds", "20"]
            cases = {
                "requires --command-script": ["--case", "scripted_walk"] + base,
                "only with --case scripted_walk": ["--command-script", str(D5_SCRIPT)],
                "applies only with --stance-hold auto": WALK_FLAGS + ["--stance-entry-kd", "step1"],
                "comes before the last": ["--case", "scripted_walk", "--command-script", str(D5_SCRIPT),
                                          "--duration-seconds", "26", "--finish-after-sim-seconds", "14"],
                "last segment must be a zero command": ["--case", "scripted_walk", "--command-script",
                                                        str(nonzero_last)] + base,
                "exceeds the runner limit": ["--case", "scripted_walk", "--command-script", str(too_fast)] + base,
                "within": ["--case", "scripted_walk", "--command-script", str(D5_SCRIPT),
                           "--duration-seconds", "61", "--finish-after-sim-seconds", "20"],
                "leaves less than": ["--case", "scripted_walk", "--command-script", str(D5_SCRIPT),
                                     "--duration-seconds", "21.5", "--finish-after-sim-seconds", "20"],
            }
            for index, (message, extra) in enumerate(cases.items()):
                with self.subTest(message=message):
                    with self.assertRaisesRegex(ValueError, message):
                        self.prepare(tmp, "walk_bad_%d" % index, *extra)
                    self.assertFalse((Path(tmp) / "runs" / ("walk_bad_%d" % index)).exists())
            missing = ["--case", "scripted_walk", "--command-script", str(Path(tmp) / "missing.json")] + base
            with self.assertRaises(FileNotFoundError):
                self.prepare(tmp, "walk_missing", *missing)
            for flags in (["--case", "flat_nominal"], ["--camera-preset", "top"], ["--stance-entry-kd", "step3"]):
                with self.subTest(flags=flags), self.assertRaises(SystemExit), \
                        contextlib.redirect_stderr(io.StringIO()):
                    qualify.build_parser().parse_args(flags)

    def test_execute_refuses_walk_settings_that_differ_from_the_package(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.prepare(tmp, "walk_prepared", *WALK_FLAGS, "--stance-hold", "auto", "--stance-entry-kd", "step1")
            runs = str(Path(tmp) / "runs")
            base = ["--run-id", "walk_prepared", "--local-runs-root", runs, "--execute"]
            same = base + WALK_FLAGS + ["--stance-hold", "auto", "--stance-entry-kd", "step1"]
            with mock.patch.object(qualify, "execute") as execute, contextlib.redirect_stdout(io.StringIO()):
                qualify.main(same)
                execute.assert_called_once()
            changed_script = Path(tmp) / "changed.json"
            changed_script.write_bytes(D5_SCRIPT.read_bytes() + b"\n")

            def replace(flag, value):
                result = list(same)
                result[result.index(flag) + 1] = value
                return result

            variants = {
                "stance-entry-kd": replace("--stance-entry-kd", "step2p5"),
                "camera-preset": replace("--camera-preset", "rear"),
                "command-script": replace("--command-script", str(changed_script)),
                "case": base + ["--stance-hold", "auto", "--stance-entry-kd", "step1", "--duration-seconds", "26",
                                "--finish-after-sim-seconds", "20"],
            }
            for flag, argv in variants.items():
                with self.subTest(flag=flag), mock.patch.object(qualify, "execute") as execute:
                    with self.assertRaisesRegex(RuntimeError, "--%s .* differs from the prepared package" % flag):
                        qualify.main(argv)
                    execute.assert_not_called()

    def test_legacy_request_defaults_cover_the_new_settings(self):
        with tempfile.TemporaryDirectory() as tmp:
            run = Path(tmp)
            (run / "run_request.json").write_text(json.dumps({"duration_seconds": 8.0, "stance_hold": "auto"}))
            args = qualify.build_parser().parse_args(["--stance-hold", "auto"])
            self.assertEqual(qualify.check_prepared_request(args, run), {
                "case": "stand_probe", "stance_hold": "auto", "stance_entry_kd": "ramp", "duration_seconds": 8.0,
                "finish_after_sim_seconds": 2.0, "camera_preset": "rear", "command_script": None})
            for flags, name in ((["--stance-entry-kd", "step1"], "stance-entry-kd"),
                                (["--camera-preset", "side"], "camera-preset")):
                args = qualify.build_parser().parse_args(["--stance-hold", "auto"] + flags)
                with self.subTest(flag=name), self.assertRaisesRegex(RuntimeError, name):
                    qualify.check_prepared_request(args, run)

    def test_launcher_entry_kd_choices_match_the_module(self):
        import stance_hold
        self.assertEqual(qualify.STANCE_ENTRY_KD_CHOICES, stance_hold.STANCE_ENTRY_KD_MODES)
        self.assertEqual(qualify.DEFAULT_STANCE_ENTRY_KD, stance_hold.STANCE_ENTRY_KD_DEFAULT)
        self.assertEqual(qualify.native_command_limits(), {
            "max_vx": 1.0, "max_vy": 0.35, "max_wz": 1.0, "max_horizontal_norm": 1.0, "speed_profile": "speed_1p0"})


if __name__ == "__main__":
    unittest.main()
