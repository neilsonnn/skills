"""Tests for Atlas CLI transport and argument translation."""

from __future__ import annotations

import contextlib
import io
import json
import os
import tempfile
import threading
import time
import unittest
import uuid
from pathlib import Path

import atlas_cli


class CliTransportTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)
        self.previous_root = os.environ.get("ATLAS_SESSION_ROOT")
        os.environ["ATLAS_SESSION_ROOT"] = str(self.root)
        self.session_id = "test-session"
        session = self.root / self.session_id
        (session / "inbox").mkdir(mode=0o700, parents=True)
        (session / "outbox").mkdir(mode=0o700)
        (session / "session.json").write_text(
            json.dumps(
                {
                    "sessionId": self.session_id,
                    "pid": os.getpid(),
                    "sceneId": "scene",
                    "blendFile": "scene.blend",
                    "createdAt": time.time(),
                    "heartbeat": time.time(),
                }
            )
        )
        os.chmod(session, 0o700)

    def tearDown(self) -> None:
        if self.previous_root is None:
            os.environ.pop("ATLAS_SESSION_ROOT", None)
        else:
            os.environ["ATLAS_SESSION_ROOT"] = self.previous_root
        self.temp_dir.cleanup()

    def test_duplicate_request_id_keeps_original_request(self) -> None:
        request_id = str(uuid.uuid4())
        request = atlas_cli.make_request(
            "frames.list", request_id=request_id, timeout=2
        )
        response = {
            "schemaVersion": 1,
            "requestId": request_id,
            "ok": True,
            "result": {"revision": 4},
        }

        def respond() -> None:
            while not (
                self.root / self.session_id / "inbox" / f"{request_id}.json"
            ).exists():
                time.sleep(0.001)
            (self.root / self.session_id / "outbox" / f"{request_id}.json").write_text(
                json.dumps(response)
            )

        thread = threading.Thread(target=respond)
        thread.start()
        self.assertEqual(
            atlas_cli.send_request(self.session_id, request, timeout=1), response
        )
        thread.join()
        original = json.loads(
            (self.root / self.session_id / "inbox" / f"{request_id}.json").read_text()
        )
        self.assertEqual(original, request)
        retry = dict(request)
        retry["command"] = "frames.inspect"
        retry["args"] = {"frameId": "different"}
        self.assertEqual(
            atlas_cli.send_request(self.session_id, retry, timeout=1), response
        )

    def test_traversal_and_malformed_sessions_are_rejected(self) -> None:
        with self.assertRaises(atlas_cli.CliError) as traversal:
            atlas_cli.send_request(
                "../other", atlas_cli.make_request("frames.list"), timeout=1
            )
        self.assertEqual(traversal.exception.code, "invalid_session")

        malformed = self.root / "malformed"
        malformed.mkdir(mode=0o700)
        (malformed / "session.json").write_text("[]")
        with self.assertRaises(atlas_cli.CliError) as invalid:
            atlas_cli.send_request(
                "malformed", atlas_cli.make_request("frames.list"), timeout=1
            )
        self.assertEqual(invalid.exception.code, "invalid_session")

    def test_timeout_leaves_request_for_later_inspection(self) -> None:
        request = atlas_cli.make_request("frames.list", timeout=1)
        with self.assertRaises(atlas_cli.CliError) as timed_out:
            atlas_cli.send_request(self.session_id, request, timeout=0.05)
        self.assertEqual(timed_out.exception.code, "timeout")
        self.assertIn("unknown", timed_out.exception.message)
        self.assertTrue(
            (
                self.root / self.session_id / "inbox" / f"{request['requestId']}.json"
            ).exists()
        )
        self.assertFalse(
            (
                self.root / self.session_id / "outbox" / f"{request['requestId']}.json"
            ).exists()
        )

    def test_command_arguments_use_wire_names(self) -> None:
        parser = atlas_cli._build_parser()
        namespace = parser.parse_args(
            [
                "--session",
                self.session_id,
                "filters",
                "set",
                "frame-1",
                "confidence_min=0.2",
                "preview_stride=4",
            ]
        )
        request = atlas_cli.request_from_namespace(namespace)
        self.assertEqual(request["command"], "filters.set")
        self.assertEqual(
            request["args"],
            {
                "frameId": "frame-1",
                "filters": {"confidence_min": 0.2, "preview_stride": 4},
            },
        )

    def test_raw_inline_json_can_exceed_filename_length(self) -> None:
        command = {
            "command": "generate",
            "args": {"prompt": "Concrete walls with bronze doors. " * 20},
        }
        request = atlas_cli._raw_request(json.dumps(command), 30, None)
        self.assertEqual(request["args"], command["args"])

    def test_generate_inherits_scene_settings_unless_explicitly_overridden(
        self,
    ) -> None:
        parser = atlas_cli._build_parser()
        request = atlas_cli.request_from_namespace(parser.parse_args(["generate"]))
        self.assertEqual(request["args"], {"targetNames": [], "wait": False})
        request = atlas_cli.request_from_namespace(
            parser.parse_args(
                ["generate", "--prompt", "", "--no-enhance-prompt", "--return-depth"]
            )
        )
        self.assertEqual(
            request["args"],
            {
                "targetNames": [],
                "wait": False,
                "prompt": "",
                "enhancePrompt": False,
                "returnDepth": True,
            },
        )

    def test_chisel_preserves_camera_order_and_sampling_overrides(self) -> None:
        parser = atlas_cli._build_parser()
        request = atlas_cli.request_from_namespace(
            parser.parse_args(
                [
                    "chisel",
                    "--target-names",
                    "B",
                    "A",
                    "--prompt",
                    "Stone room",
                    "--return-depth",
                    "--no-enhance-prompt",
                    "--voxel-size",
                    "0.1",
                    "--seed",
                    "3",
                    "--num-steps",
                    "25",
                    "--cfg",
                    "2",
                ]
            )
        )
        self.assertEqual(request["command"], "chisel")
        self.assertEqual(
            request["args"],
            {
                "targetNames": ["B", "A"],
                "promptOnly": False,
                "prompt": "Stone room",
                "returnDepth": True,
                "enhancePrompt": False,
                "voxelSize": 0.1,
                "modelParameters": {"seed": 3, "numSteps": 25, "cfg": 2.0},
            },
        )
        inherited = atlas_cli.request_from_namespace(
            parser.parse_args(
                [
                    "chisel",
                    "--target-names",
                    "Camera",
                    "--prompt-only",
                ]
            )
        )
        self.assertEqual(
            inherited["args"], {"targetNames": ["Camera"], "promptOnly": True}
        )

    def test_live_wait_polls_jobs_through_same_session(self) -> None:
        inbox = self.root / self.session_id / "inbox"
        outbox = self.root / self.session_id / "outbox"
        initial = atlas_cli.make_request("generate", {"wait": True}, timeout=2)
        initial_response = {
            "schemaVersion": 1,
            "requestId": initial["requestId"],
            "ok": True,
            "result": {"jobs": [{"id": "job-1", "state": "submitted"}]},
        }

        def respond() -> None:
            while True:
                for request_path in inbox.glob("*.json"):
                    request = json.loads(request_path.read_text())
                    response_path = outbox / request_path.name
                    if response_path.exists():
                        continue
                    if request["command"] == "generate":
                        response_path.write_text(json.dumps(initial_response))
                    elif request["command"] == "jobs.status":
                        response_path.write_text(
                            json.dumps(
                                {
                                    "schemaVersion": 1,
                                    "requestId": request["requestId"],
                                    "ok": True,
                                    "result": {
                                        "jobs": [{"id": "job-1", "state": "ready"}]
                                    },
                                }
                            )
                        )
                        return
                time.sleep(0.001)

        thread = threading.Thread(target=respond)
        thread.start()
        submitted = atlas_cli.send_request(self.session_id, initial, timeout=1)
        completed = atlas_cli._wait_for_live_jobs(self.session_id, submitted, timeout=1)
        thread.join(timeout=1)
        self.assertEqual(completed["result"]["jobs"][0]["state"], "ready")
        self.assertFalse(thread.is_alive())

    def test_cli_job_wait_outlasts_transport_timeout(self) -> None:
        inbox = self.root / self.session_id / "inbox"
        outbox = self.root / self.session_id / "outbox"
        stop = threading.Event()
        requests = []

        def respond() -> None:
            submitted_at = None
            while not stop.wait(0.005):
                for path in inbox.glob("*.json"):
                    if (outbox / path.name).exists():
                        continue
                    request = json.loads(path.read_text())
                    requests.append(request)
                    if request["command"] in {"pose", "generate"}:
                        submitted_at = time.monotonic()
                    ready = time.monotonic() - submitted_at >= 0.4
                    atlas_cli._atomic_json_write(
                        outbox / path.name,
                        {
                            "requestId": request["requestId"],
                            "ok": True,
                            "result": {
                                "jobs": [
                                    {
                                        "id": "job-1",
                                        "state": "ready" if ready else "running",
                                    }
                                ]
                            },
                        },
                    )

        thread = threading.Thread(target=respond)
        thread.start()
        try:
            for command, timeout in (("generate", "2"), ("pose", "600")):
                with self.subTest(command=command):
                    output = io.StringIO()
                    with contextlib.redirect_stdout(output):
                        code = atlas_cli.main(
                            [
                                "--session",
                                self.session_id,
                                "--timeout",
                                "0.2",
                                command,
                                "--wait",
                                "--timeout-secs",
                                timeout,
                            ]
                        )
                    self.assertEqual(code, 0, output.getvalue())
                    self.assertEqual(
                        json.loads(output.getvalue())["result"]["jobs"][0]["state"],
                        "ready",
                    )
            self.assertEqual(
                [r["command"] for r in requests if r["command"] != "jobs.status"],
                ["generate", "pose"],
            )
        finally:
            stop.set()
            thread.join(timeout=2)

    def test_invalid_job_wait_is_rejected_before_submission(self) -> None:
        for timeout in ("0", "-1", "nan", "inf"):
            with self.subTest(timeout=timeout):
                output = io.StringIO()
                with contextlib.redirect_stdout(output):
                    code = atlas_cli.main(
                        [
                            "--session",
                            self.session_id,
                            "generate",
                            "--wait",
                            "--timeout-secs",
                            timeout,
                        ]
                    )
                self.assertEqual(code, 1)
                self.assertEqual(
                    json.loads(output.getvalue())["error"]["code"], "invalid_timeout"
                )
        self.assertEqual(
            list((self.root / self.session_id / "inbox").glob("*.json")), []
        )


if __name__ == "__main__":
    unittest.main()
