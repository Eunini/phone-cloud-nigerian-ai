"""Finite supervision of the pinned CPU runner; transient bus errors never kill it."""

import argparse
import fcntl
import json
import signal
import subprocess
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

UNIT = "afri-research-workspace-cpu.service"


def query(command, attempts=5, pause=time.sleep):
    for attempt in range(attempts):
        try:
            return subprocess.check_output(
                command, text=True, stderr=subprocess.PIPE, timeout=15
            ).strip()
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
            if attempt + 1 == attempts:
                raise
            pause(10)


def restartable(progress, last_stamp, restarts, maximum):
    return (
        progress.get("error_type") in {"TimeoutError", "TimeoutExpired"}
        and bool(progress.get("updated_at"))
        and progress["updated_at"] != last_stamp
        and restarts < maximum
    )


def command_identity(raw):
    if "argv[]=" not in raw or "; ignore_errors=" not in raw:
        raise ValueError("Cannot identify the worker command")
    # systemd also returns the last PID/start/exit timestamps in ExecStart.
    # Those change after a valid restart and must not change command identity.
    return raw.split("; ignore_errors=", 1)[0].strip()


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--source", type=Path, required=True)
    p.add_argument("--progress", type=Path, required=True)
    p.add_argument("--receipt", type=Path, required=True)
    p.add_argument("--max-hours", type=float, default=168)
    p.add_argument("--max-restarts", type=int, default=32)
    a = p.parse_args()
    if not 0 < a.max_hours <= 168 or not 0 < a.max_restarts <= 32:
        p.error("Use at most seven days and 32 recorded timeout resumptions")
    a.source = a.source.resolve(strict=True)
    a.receipt.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    lock = a.receipt.with_suffix(".lock").open("a")
    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    revision = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=a.source, text=True
    ).strip()
    if revision != "c75b734e48defc6f19cc0c2d32bd8a944f6b0595":
        raise ValueError("This continuation is for the already-started pinned CPU study")
    working_dir = query(["systemctl", "show", UNIT, "-p", "WorkingDirectory", "--value"])
    if Path(working_dir).resolve() != a.source:
        raise ValueError("Worker unit points at another source checkout")
    service_command = command_identity(
        query(["systemctl", "show", UNIT, "-p", "ExecStart", "--value"])
    )
    now = datetime.now(timezone.utc)
    if a.receipt.exists():
        state = json.loads(a.receipt.read_text())
        if state["source_commit"] != revision or state["worker_command"] != service_command:
            raise ValueError("Continuation identity changed")
    else:
        state = {
            "started_at": now.isoformat(),
            "expires_at": (now + timedelta(hours=a.max_hours)).isoformat(),
            "max_restarts": a.max_restarts,
            "source_commit": revision,
            "worker_command": service_command,
            "restarts": 0,
            "last_resumed_timestamp": None,
        }
    stop_requested = False

    def interrupted(*_):
        nonlocal stop_requested
        stop_requested = True

    signal.signal(signal.SIGTERM, interrupted)
    signal.signal(signal.SIGINT, interrupted)

    def save():
        state["updated_at"] = datetime.now(timezone.utc).isoformat()
        temp = a.receipt.with_suffix(".tmp")
        temp.write_text(json.dumps(state, indent=2) + "\n")
        temp.chmod(0o600)
        temp.replace(a.receipt)

    state["status"] = "watching"
    save()
    try:
        while not stop_requested and datetime.now(timezone.utc) < datetime.fromisoformat(
            state["expires_at"]
        ):
            active = query(["systemctl", "show", UNIT, "-p", "ActiveState", "--value"])
            if active in {"active", "activating", "deactivating"}:
                time.sleep(15)
                continue
            progress = json.loads(a.progress.read_text())
            if progress.get("status") == "complete":
                state["status"] = "complete"
                break
            if not restartable(
                progress, state["last_resumed_timestamp"], state["restarts"], state["max_restarts"]
            ):
                state.update(
                    status="stopped_for_diagnosis", worker_error_type=progress.get("error_type")
                )
                break
            if (
                command_identity(query(["systemctl", "show", UNIT, "-p", "ExecStart", "--value"]))
                != state["worker_command"]
            ):
                raise ValueError("Worker command changed; refusing to resume")
            subprocess.run(
                ["sudo", "-n", "systemctl", "restart", "--no-block", UNIT], check=True, timeout=30
            )
            state["restarts"] += 1
            state["last_resumed_timestamp"] = progress["updated_at"]
            save()
            time.sleep(15)
        else:
            state["status"] = "operator_stopped" if stop_requested else "overall_deadline_reached"
            subprocess.run(
                ["sudo", "-n", "systemctl", "stop", "--no-block", UNIT], check=True, timeout=30
            )
    except (subprocess.SubprocessError, OSError, ValueError) as error:
        # An unavailable monitor is not evidence that the independently bounded
        # worker failed. Preserve its running process and its 24-hour limit.
        state.update(status="monitor_stopped_for_diagnosis", error_type=type(error).__name__)
        raise
    finally:
        save()


if __name__ == "__main__":
    main()
