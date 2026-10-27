import subprocess

import pytest

from bench.continue_workspace import command_identity, query, restartable


def test_transient_systemd_transport_error_retries_without_stopping_worker(monkeypatch):
    calls = []

    def check(command, **kwargs):
        calls.append(command)
        if len(calls) == 1:
            raise subprocess.CalledProcessError(1, command)
        return "active\n"

    monkeypatch.setattr(subprocess, "check_output", check)
    assert query(["systemctl", "show", "our-unit"], pause=lambda _: None) == "active"
    assert len(calls) == 2
    assert all("stop" not in command for command in calls)


@pytest.mark.parametrize("kind", ["TimeoutError", "TimeoutExpired"])
def test_both_controller_and_child_timeouts_can_resume_once(kind):
    progress = {"error_type": kind, "updated_at": "new"}
    assert restartable(progress, "old", 0, 2)
    assert not restartable(progress, "new", 0, 2)
    assert not restartable(progress, "old", 2, 2)


@pytest.mark.parametrize("kind", ["OSError", "CalledProcessError", "SystemExit", None])
def test_storage_model_or_operator_failures_require_diagnosis(kind):
    assert not restartable({"error_type": kind, "updated_at": "new"}, "old", 0, 2)


def test_worker_identity_ignores_runtime_metadata_but_detects_changed_arguments():
    a = "{ path=/python ; argv[]=/python -m bench.workspace --threads 2 ; ignore_errors=no ; pid=1 ; status=0 }"
    b = a.replace("pid=1", "pid=2").replace("status=0", "status=15")
    assert command_identity(a) == command_identity(b)
    assert command_identity(a) != command_identity(a.replace("--threads 2", "--threads 4"))
