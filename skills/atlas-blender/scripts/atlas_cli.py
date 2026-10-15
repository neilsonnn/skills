"""Command line client for the file based Blender Atlas transport."""

from __future__ import annotations

import argparse
import contextlib
import json
import math
import os
import re
import tempfile
import time
import uuid
from pathlib import Path
from typing import Any

SCHEMA_VERSION = 1
DEFAULT_TIMEOUT = 30.0
DEFAULT_WAIT_TIMEOUT = 300.0
MAX_TIMEOUT = 300.0
HEARTBEAT_MAX_AGE = 120.0
_SESSION_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,127}\Z")


class CliError(Exception):
    """An expected command line or transport error."""

    def __init__(
        self,
        code: str,
        message: str,
        *,
        request_id: str | None = None,
        details: dict[str, Any] | None = None,
    ):
        super().__init__(message)
        self.code = code
        self.message = message
        self.request_id = request_id
        self.details = details or {}


def session_root() -> Path:
    """Return the configured directory containing live Atlas sessions."""

    return Path(
        os.environ.get(
            "ATLAS_SESSION_ROOT",
            os.path.join(tempfile.gettempdir(), "worldlabs-atlas-sessions"),
        )
    )


def _valid_session_id(session_id: str) -> str:
    if not _SESSION_ID.fullmatch(session_id):
        raise CliError("invalid_session", "session ID contains unsafe characters")
    return session_id


def _atomic_json_write(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        if hasattr(os, "fchmod"):
            os.fchmod(fd, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump(value, stream, separators=(",", ":"), sort_keys=True)
            stream.write("\n")
        os.replace(temporary, path)
    except Exception:
        with contextlib.suppress(OSError):
            os.close(fd)
        with contextlib.suppress(OSError):
            os.unlink(temporary)
        raise


def _read_json(path: Path) -> Any:
    try:
        with path.open(encoding="utf-8") as stream:
            return json.load(stream)
    except FileNotFoundError as exc:
        raise CliError("missing_session", f"file does not exist: {path.name}") from exc
    except (OSError, json.JSONDecodeError) as exc:
        raise CliError("invalid_json", f"cannot read {path.name}: {exc}") from exc


def _pid_is_alive(pid: int) -> bool:
    if pid <= 0:
        return False
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    except OSError:
        return False
    return True


def _session_dir(session_id: str, *, require_live: bool = True) -> Path:
    session_id = _valid_session_id(session_id)
    root = session_root()
    root.mkdir(mode=0o700, parents=True, exist_ok=True)
    os.chmod(root, 0o700)
    directory = root / session_id
    try:
        resolved_root = root.resolve()
        resolved_directory = directory.resolve(strict=False)
    except OSError as exc:
        raise CliError(
            "invalid_session", f"cannot resolve session path: {exc}"
        ) from exc
    if resolved_directory.parent != resolved_root:
        raise CliError("invalid_session", "session path escapes the session root")
    try:
        stat = directory.stat()
    except FileNotFoundError as exc:
        raise CliError("missing_session", f"session not found: {session_id}") from exc
    except OSError as exc:
        raise CliError(
            "invalid_session", f"cannot inspect session directory: {exc}"
        ) from exc
    current_uid = getattr(os, "getuid", lambda: stat.st_uid)()
    if stat.st_uid != current_uid or stat.st_mode & 0o077:
        raise CliError("invalid_session", "session directory must be owner-only")
    metadata = _read_json(directory / "session.json")
    if not isinstance(metadata, dict) or metadata.get("sessionId") != session_id:
        raise CliError(
            "invalid_session", "session metadata does not match its directory"
        )
    if require_live:
        try:
            pid = int(metadata["pid"])
            heartbeat = float(metadata["heartbeat"])
        except (KeyError, TypeError, ValueError) as exc:
            raise CliError(
                "invalid_session", "session metadata lacks pid or heartbeat"
            ) from exc
        if not _pid_is_alive(pid):
            raise CliError(
                "stale_session", "Blender session process is no longer running"
            )
        if time.time() - heartbeat > HEARTBEAT_MAX_AGE:
            raise CliError("stale_session", "Blender session heartbeat is stale")
    return directory


def list_sessions() -> list[dict[str, Any]]:
    """Return registry entries, including liveness information."""

    root = session_root()
    if not root.exists():
        return []
    entries: list[dict[str, Any]] = []
    for directory in sorted(root.iterdir(), key=lambda item: item.name):
        if not directory.is_dir() or not _SESSION_ID.fullmatch(directory.name):
            continue
        try:
            metadata = _read_json(directory / "session.json")
            pid = int(metadata.get("pid", 0))
            heartbeat = float(metadata.get("heartbeat", 0))
            metadata = dict(metadata)
            metadata["live"] = (
                _pid_is_alive(pid) and time.time() - heartbeat <= HEARTBEAT_MAX_AGE
            )
            entries.append(metadata)
        except CliError:
            entries.append({"sessionId": directory.name, "live": False})
    return entries


def _request_id(value: str | None) -> str:
    if value is None:
        return str(uuid.uuid4())
    try:
        return str(uuid.UUID(value))
    except ValueError as exc:
        raise CliError("invalid_request_id", "request ID must be a UUID") from exc


def make_request(
    command: str,
    args: dict[str, Any] | None = None,
    *,
    request_id: str | None = None,
    expected_revision: int | None = None,
    timeout: float = DEFAULT_TIMEOUT,
) -> dict[str, Any]:
    """Build a versioned dispatcher request."""

    if not command or not isinstance(command, str):
        raise CliError("invalid_command", "command must be a non-empty string")
    if timeout <= 0 or timeout > MAX_TIMEOUT:
        raise CliError(
            "invalid_timeout", f"timeout must be in (0, {MAX_TIMEOUT:g}] seconds"
        )
    request: dict[str, Any] = {
        "schemaVersion": SCHEMA_VERSION,
        "requestId": _request_id(request_id),
        "command": command,
        "args": args or {},
        "deadline": time.time() + timeout,
    }
    if expected_revision is not None:
        request["expectedRevision"] = expected_revision
    return request


def send_request(
    session_id: str,
    request: dict[str, Any],
    *,
    timeout: float = DEFAULT_TIMEOUT,
) -> dict[str, Any]:
    """Write one request and wait for its matching response."""

    if timeout <= 0 or timeout > MAX_TIMEOUT:
        raise CliError(
            "invalid_timeout", f"timeout must be in (0, {MAX_TIMEOUT:g}] seconds"
        )
    request_id = request.get("requestId")
    if not isinstance(request_id, str):
        raise CliError("invalid_request", "requestId is required")
    request_id = _request_id(request_id)
    if request.get("requestId") != request_id:
        raise CliError("invalid_request", "requestId must use canonical UUID spelling")
    if request.get("schemaVersion") != SCHEMA_VERSION or not isinstance(
        request.get("command"), str
    ):
        raise CliError(
            "invalid_request",
            "request must use schemaVersion 1 and contain command",
            request_id=request_id,
        )
    if not isinstance(request.get("args"), dict) or not isinstance(
        request.get("deadline"), int | float
    ):
        raise CliError(
            "invalid_request",
            "request must contain object args and numeric deadline",
            request_id=request_id,
        )
    directory = _session_dir(session_id)
    inbox = directory / "inbox"
    outbox = directory / "outbox"
    inbox.mkdir(mode=0o700, exist_ok=True)
    outbox.mkdir(mode=0o700, exist_ok=True)
    os.chmod(inbox, 0o700)
    os.chmod(outbox, 0o700)
    request_path = inbox / f"{request_id}.json"
    response_path = outbox / f"{request_id}.json"
    if request_path.exists():
        # A retry may have a new local deadline. The first body remains the
        # authority so a retry cannot submit the same paid operation twice.
        pass
    else:
        _atomic_json_write(request_path, request)

    deadline = min(time.monotonic() + timeout, float("inf"))
    while time.monotonic() < deadline:
        if response_path.exists():
            response = _read_json(response_path)
            if (
                not isinstance(response, dict)
                or response.get("requestId") != request_id
            ):
                raise CliError(
                    "invalid_response",
                    "response has an unexpected request ID",
                    request_id=request_id,
                )
            return response
        time.sleep(min(0.05, max(0.0, deadline - time.monotonic())))
    raise CliError(
        "timeout",
        "request timed out; the Blender command may still be running (status unknown)",
        request_id=request_id,
    )


_JOB_TERMINAL_STATES = {"ready", "failed", "cancelled", "paused"}


def _jobs_from_result(result: Any) -> list[dict[str, Any]]:
    if not isinstance(result, dict):
        return []
    if isinstance(result.get("job"), dict):
        return [result["job"]]
    if isinstance(result.get("jobs"), list):
        return [job for job in result["jobs"] if isinstance(job, dict)]
    return []


def _job_failure(jobs: list[dict[str, Any]], request_id: str) -> CliError | None:
    failed = [job for job in jobs if str(job.get("state", "")).lower() != "ready"]
    if not failed:
        return None
    paused = [job for job in failed if str(job.get("state", "")).lower() == "paused"]
    cancelled = [
        job for job in failed if str(job.get("state", "")).lower() == "cancelled"
    ]
    if paused:
        code, message = "job_paused", "job paused and can be resumed"
    elif cancelled:
        code, message = "job_cancelled", "job was cancelled"
    else:
        code, message = "job_failed", "job failed"
    details: dict[str, Any] = {"jobs": jobs}
    for job in failed:
        if job.get("error"):
            details["jobError"] = job["error"]
            break
    return CliError(code, message, request_id=request_id, details=details)


def _wait_for_live_jobs(
    session_id: str,
    initial: dict[str, Any],
    timeout: float,
    *,
    command_timeout: float = DEFAULT_TIMEOUT,
) -> dict[str, Any]:
    """Poll jobs through the same Blender session used for submission."""

    if not initial.get("ok"):
        return initial
    jobs = _jobs_from_result(initial.get("result"))
    if not jobs:
        return initial
    request_id = initial.get("requestId")
    deadline = time.monotonic() + timeout
    latest = jobs
    while time.monotonic() < deadline:
        statuses: list[dict[str, Any]] = []
        for job in latest:
            job_id = job.get("id", job.get("jobId"))
            if not job_id:
                continue
            remaining = min(command_timeout, max(0.05, deadline - time.monotonic()))
            status_request = make_request(
                "jobs.status",
                {"jobId": job_id},
                timeout=min(MAX_TIMEOUT, remaining),
            )
            status = send_request(
                session_id, status_request, timeout=min(MAX_TIMEOUT, remaining)
            )
            if not status.get("ok"):
                error = status.get("error", {})
                raise CliError(
                    error.get("code", "job_status_failed"),
                    error.get("message", "jobs.status failed"),
                    request_id=request_id,
                    details={"jobs": latest},
                )
            statuses.extend(_jobs_from_result(status.get("result")))
        if statuses:
            latest = statuses
        if latest and all(
            str(job.get("state", "")).lower() in _JOB_TERMINAL_STATES for job in latest
        ):
            failure = _job_failure(latest, request_id)
            if failure:
                raise failure
            return {
                "schemaVersion": SCHEMA_VERSION,
                "requestId": request_id,
                "ok": True,
                "result": {"jobs": latest},
            }
        time.sleep(min(0.1, max(0.0, deadline - time.monotonic())))
    raise CliError(
        "timeout",
        "job wait timed out; the Blender command may still be running (status unknown)",
        request_id=request_id,
    )


def _add_revision(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--expected-revision", type=int)


def _parse_filters(values: list[str]) -> dict[str, float | int]:
    result: dict[str, float | int] = {}
    allowed = {
        "confidence_min",
        "confidence_max",
        "z_min",
        "z_max",
        "x_min",
        "x_max",
        "y_min",
        "y_max",
        "point_size",
        "preview_stride",
    }
    for value in values:
        if "=" not in value:
            raise CliError("invalid_filters", f"filter must be NAME=VALUE: {value}")
        name, raw = value.split("=", 1)
        if name not in allowed:
            raise CliError("invalid_filters", f"unknown filter: {name}")
        try:
            result[name] = int(raw) if name == "preview_stride" else float(raw)
        except ValueError as exc:
            raise CliError("invalid_filters", f"invalid filter value: {value}") from exc
    return result


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="atlas_cli")
    parser.add_argument("--session")
    parser.add_argument("--timeout", type=float, default=DEFAULT_TIMEOUT)
    parser.add_argument("--request-id")
    subparsers = parser.add_subparsers(dest="group", required=True)

    sessions = subparsers.add_parser("sessions")
    sessions.add_subparsers(dest="action").add_parser("list")

    frames = subparsers.add_parser("frames")
    frame_actions = frames.add_subparsers(dest="action", required=True)
    frame_actions.add_parser("list")
    inspect = frame_actions.add_parser("inspect")
    inspect.add_argument("frame_id")
    hide = frame_actions.add_parser("hide")
    hide.add_argument("frame_id")
    hide.add_argument("--show", action="store_true")
    delete = frame_actions.add_parser("delete")
    delete.add_argument("frame_id")
    reorder = frame_actions.add_parser("reorder")
    reorder.add_argument("frame_id")
    reorder.add_argument("--index", type=int, required=True)
    for action in (inspect, hide, delete, reorder):
        _add_revision(action)

    buffers = subparsers.add_parser("buffers")
    buffer_actions = buffers.add_subparsers(dest="action", required=True)
    export = buffer_actions.add_parser("export")
    export.add_argument("frame_id")
    export.add_argument("--output", required=True)
    sample = buffer_actions.add_parser("sample")
    sample.add_argument("frame_id")
    sample.add_argument("--pixel", nargs=2, type=int, metavar=("X", "Y"), required=True)

    pose = subparsers.add_parser("pose")
    pose.add_argument("files", nargs="*")
    pose.add_argument("--files", dest="file_options", nargs="+")
    pose.add_argument("--mode", choices=("separate", "reconstruct"), default="separate")
    pose.add_argument("--preserve-framing", action="store_true")
    pose.add_argument("--return-depth", action="store_true")
    pose.add_argument("--wait", action="store_true")
    pose.add_argument(
        "--timeout-secs",
        type=float,
        default=DEFAULT_WAIT_TIMEOUT,
        help="Job wait limit in seconds (default: 300); does not cancel remote work",
    )

    generate = subparsers.add_parser("generate")
    generate.add_argument("--prompt", help="Override the scene's saved prompt")
    generate.add_argument("--target-names", nargs="*", default=[])
    generate.add_argument("--context-ids", nargs="*")
    generate.add_argument(
        "--return-depth",
        action=argparse.BooleanOptionalAction,
        default=None,
        help="Override the scene's depth setting",
    )
    generate.add_argument(
        "--enhance-prompt",
        action=argparse.BooleanOptionalAction,
        default=None,
        help="Override the scene's prompt enhancement setting",
    )
    generate.add_argument("--wait", action="store_true")
    generate.add_argument(
        "--timeout-secs",
        type=float,
        default=DEFAULT_WAIT_TIMEOUT,
        help="Job wait limit in seconds (default: 300); does not cancel remote work",
    )

    chisel = subparsers.add_parser("chisel")
    chisel.add_argument("--target-names", nargs="+", required=True)
    chisel.add_argument("--prompt", help="Override the scene's saved prompt")
    chisel.add_argument("--prompt-only", action="store_true")
    chisel.add_argument(
        "--return-depth", action=argparse.BooleanOptionalAction, default=None
    )
    chisel.add_argument(
        "--enhance-prompt", action=argparse.BooleanOptionalAction, default=None
    )
    chisel.add_argument("--voxel-size", type=float)
    chisel.add_argument("--voxel-grid-orientation", choices=("world", "gauge"))
    chisel.add_argument("--seed", type=int)
    chisel.add_argument("--cfg", type=float)
    chisel.add_argument("--num-steps", type=int)
    chisel.add_argument("--wait", action="store_true")
    chisel.add_argument(
        "--timeout-secs",
        type=float,
        default=DEFAULT_WAIT_TIMEOUT,
        help="Job wait limit; does not cancel remote work",
    )

    jobs = subparsers.add_parser("jobs")
    job_actions = jobs.add_subparsers(dest="action", required=True)
    status = job_actions.add_parser("status")
    status.add_argument("job_id", nargs="?")
    cancel = job_actions.add_parser("cancel")
    cancel.add_argument("job_id")

    camera = subparsers.add_parser("camera")
    camera_action = camera.add_subparsers(dest="action", required=True).add_parser(
        "set"
    )
    camera_action.add_argument("frame_id")
    camera_action.add_argument("--matrix-world", required=True)
    camera_action.add_argument(
        "--coordinate-system", choices=("blender", "api"), default="blender"
    )
    _add_revision(camera_action)

    filters = subparsers.add_parser("filters")
    filters_action = filters.add_subparsers(dest="action", required=True).add_parser(
        "set"
    )
    filters_action.add_argument("frame_id")
    filters_action.add_argument("filters", nargs="+", metavar="NAME=VALUE")
    _add_revision(filters_action)

    raw = subparsers.add_parser("raw")
    raw.add_argument(
        "request", nargs="?", help="JSON request text or a path to a JSON request file"
    )
    raw.add_argument("--request", dest="request_option")
    return parser


def _raw_request(value: str, timeout: float, request_id: str | None) -> dict[str, Any]:
    try:
        candidate = Path(value)
        if value.lstrip().startswith("{"):
            request = json.loads(value)
        elif candidate.is_file():
            request = _read_json(candidate)
        else:
            request = json.loads(value)
    except (OSError, json.JSONDecodeError) as exc:
        raise CliError(
            "invalid_request", f"raw request is not valid JSON: {exc}"
        ) from exc
    if not isinstance(request, dict) or not isinstance(request.get("command"), str):
        raise CliError("invalid_request", "raw request must contain a command")
    request = dict(request)
    request["schemaVersion"] = SCHEMA_VERSION
    request["requestId"] = _request_id(request_id or request.get("requestId"))
    request.setdefault("args", {})
    request["deadline"] = time.time() + timeout
    return request


def request_from_namespace(namespace: argparse.Namespace) -> dict[str, Any]:
    """Translate parsed CLI arguments into the public dispatcher request."""

    group, action = namespace.group, getattr(namespace, "action", None)
    command: str
    args: dict[str, Any]
    if group == "frames":
        command = f"frames.{action}"
        args = {} if action == "list" else {"frameId": namespace.frame_id}
        if action == "hide":
            args["hidden"] = not namespace.show
        elif action == "reorder":
            args["index"] = namespace.index
    elif group == "buffers":
        command = f"buffers.{action}"
        args = {"frameId": namespace.frame_id}
        if action == "export":
            args["output"] = namespace.output
        else:
            args["pixel"] = namespace.pixel
    elif group == "pose":
        command = "pose"
        args = {
            "files": namespace.file_options or namespace.files,
            "mode": namespace.mode,
            "preserveFraming": namespace.preserve_framing,
            "returnDepth": namespace.return_depth,
            "wait": namespace.wait,
        }
    elif group == "chisel":
        command = "chisel"
        args = {
            "targetNames": namespace.target_names,
            "promptOnly": namespace.prompt_only,
        }
        for key, value in (
            ("prompt", namespace.prompt),
            ("returnDepth", namespace.return_depth),
            ("enhancePrompt", namespace.enhance_prompt),
            ("voxelSize", namespace.voxel_size),
            ("voxelGridOrientation", namespace.voxel_grid_orientation),
        ):
            if value is not None:
                args[key] = value
        parameters = {
            key: value
            for key, value in (
                ("seed", namespace.seed),
                ("cfg", namespace.cfg),
                ("numSteps", namespace.num_steps),
            )
            if value is not None
        }
        if parameters:
            args["modelParameters"] = parameters
    elif group == "generate":
        command = "generate"
        args = {
            "targetNames": namespace.target_names,
            "wait": namespace.wait,
        }
        for key, value in (
            ("prompt", namespace.prompt),
            ("contextIds", namespace.context_ids),
            ("returnDepth", namespace.return_depth),
            ("enhancePrompt", namespace.enhance_prompt),
        ):
            if value is not None:
                args[key] = value
    elif group == "jobs":
        command = f"jobs.{action}"
        args = {} if namespace.job_id is None else {"jobId": namespace.job_id}
    elif group == "camera":
        command = "camera.set"
        try:
            matrix = json.loads(namespace.matrix_world)
        except json.JSONDecodeError as exc:
            raise CliError("invalid_camera", "matrix-world must be JSON") from exc
        args = {
            "frameId": namespace.frame_id,
            "matrixWorld": matrix,
            "coordinateSystem": namespace.coordinate_system,
        }
    elif group == "filters":
        command = "filters.set"
        args = {
            "frameId": namespace.frame_id,
            "filters": _parse_filters(namespace.filters),
        }
    else:
        raise CliError(
            "invalid_command", f"unsupported command: {group} {action or ''}".strip()
        )
    request = make_request(
        command,
        args,
        request_id=namespace.request_id,
        expected_revision=getattr(namespace, "expected_revision", None),
        timeout=namespace.timeout,
    )
    return request


def _error_response(error: CliError) -> dict[str, Any]:
    response: dict[str, Any] = {
        "schemaVersion": SCHEMA_VERSION,
        "requestId": error.request_id,
        "ok": False,
        "error": {"code": error.code, "message": error.message, **error.details},
    }
    if error.code == "timeout":
        response["status"] = "unknown"
    return response


def main(argv: list[str] | None = None) -> int:
    """Run the CLI and print exactly one JSON response."""

    try:
        namespace = _build_parser().parse_args(argv)
        if namespace.group == "sessions":
            if namespace.action not in (None, "list"):
                raise CliError("invalid_command", "only sessions list is supported")
            response = {
                "schemaVersion": SCHEMA_VERSION,
                "requestId": None,
                "ok": True,
                "result": {"sessions": list_sessions()},
            }
        elif namespace.group == "raw":
            if not namespace.session:
                raise CliError("missing_session", "--session is required")
            raw_value = namespace.request_option or namespace.request
            if raw_value is None:
                raise CliError(
                    "invalid_request", "raw requires JSON text or a JSON request file"
                )
            request = _raw_request(raw_value, namespace.timeout, namespace.request_id)
            response = send_request(
                namespace.session, request, timeout=namespace.timeout
            )
        else:
            if not namespace.session:
                raise CliError("missing_session", "--session is required")
            wait_timeout = getattr(namespace, "timeout_secs", DEFAULT_WAIT_TIMEOUT)
            if not math.isfinite(wait_timeout) or wait_timeout <= 0:
                raise CliError(
                    "invalid_timeout", "--timeout-secs must be finite and positive"
                )
            request = request_from_namespace(namespace)
            response = send_request(
                namespace.session, request, timeout=namespace.timeout
            )
            if getattr(namespace, "wait", False):
                response = _wait_for_live_jobs(
                    namespace.session,
                    response,
                    wait_timeout,
                    command_timeout=namespace.timeout,
                )
    except SystemExit as exc:
        return int(exc.code)
    except CliError as exc:
        response = _error_response(exc)
    print(json.dumps(response, sort_keys=True))
    return 0 if response.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
