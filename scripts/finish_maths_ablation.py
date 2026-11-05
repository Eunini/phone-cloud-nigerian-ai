"""Bounded monitor: await the running pilot, verify counts, publish in an isolated worktree.

Only aggregate report files are committed. Never stages the original working
tree or edits existing benchmark responses. At most one recorded timeout resume.
"""

import argparse
import json
import os
import signal
from pathlib import Path
import subprocess
import sys
import tempfile
import time

import psutil

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from bench.maths_report import verified_report  # noqa: E402


def stop_family(pid):
    parent = psutil.Process(pid)
    children = parent.children(recursive=True)
    parent.send_signal(signal.SIGINT)
    psutil.wait_procs([parent], timeout=20)
    for process in children:
        try:
            process.terminate()
        except psutil.NoSuchProcess:
            pass
    _, remaining = psutil.wait_procs(children, timeout=10)
    for process in remaining:
        process.kill()
    if parent.is_running():
        parent.kill()


def worker_alive(pid, started):
    try:
        process = psutil.Process(pid)
        return process.create_time() == started and process.status() != psutil.STATUS_ZOMBIE
    except psutil.NoSuchProcess:
        return False


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pid", type=int, required=True)
    args = parser.parse_args()
    private = ROOT / "runs/private/maths-ablation-v1"
    receipt = private / "publication.json"
    stop_file = private / "STOP"
    if receipt.exists():
        raise ValueError("A publication receipt already exists")
    deadline = time.monotonic() + 4.5 * 3600
    started = psutil.Process(args.pid).create_time()
    while worker_alive(args.pid, started):
        if stop_file.exists():
            stop_family(args.pid)
            receipt.write_text('{"published":false,"stopped_by_owner":true}\n')
            return
        if time.monotonic() >= deadline:
            stop_family(args.pid)
            raise TimeoutError("Monitor deadline reached; no unverified publication")
        time.sleep(30)
    report = verified_report(ROOT)
    attempted = sum(g["completed"] + g["request_errors"] for g in report["groups"])
    if (attempted < 200 and time.time() - started >= 2 * 3600 and not stop_file.exists()
            and not any(g["request_errors"] for g in report["groups"])):
        # A partial time-bounded controller may resume once; completed answers
        # stay immutable and are skipped by the frozen runner.
        remaining = min(2 * 3600 + 600, deadline - time.monotonic())
        with (private / "resume.log").open("w") as log:
            process = subprocess.Popen([sys.executable, "-m", "bench.maths_ablation", "--server",
                                        str(ROOT.parent.parent / "tools/llama-workspace/build/bin/llama-server")],
                                       cwd=ROOT, stdout=log, stderr=subprocess.STDOUT,
                                       start_new_session=True)
            try:
                until = time.monotonic() + remaining
                while process.poll() is None:
                    if stop_file.exists() or time.monotonic() >= until:
                        raise subprocess.TimeoutExpired(process.args, remaining)
                    time.sleep(15)
                if process.returncode != 0:
                    raise RuntimeError("Bounded resume failed; inspect private log")
            except subprocess.TimeoutExpired:
                os.killpg(process.pid, signal.SIGTERM)
                try:
                    process.wait(timeout=20)
                except subprocess.TimeoutExpired:
                    os.killpg(process.pid, signal.SIGKILL)
                    process.wait()
                if stop_file.exists():
                    receipt.write_text('{"published":false,"stopped_by_owner":true}\n')
                    return
                raise TimeoutError("Resume and its model server stopped at monitor deadline") from None
        report = verified_report(ROOT)
    # The user authorized Eunini, never the unrelated global gh/app account.
    key = subprocess.check_output(["gh", "auth", "token", "--hostname", "github.com",
                                   "--user", "Eunini"], text=True).strip()
    env = {**os.environ, "GH_TOKEN": key}
    if subprocess.check_output(["gh", "api", "user", "--jq", ".login"], env=env, text=True).strip() != "Eunini":
        raise ValueError("Unexpected GitHub account")
    git = ["git", "-c", "credential.helper=", "-c", "credential.helper=!gh auth git-credential"]
    subprocess.run(git + ["fetch", "origin"], cwd=ROOT, env=env, check=True, capture_output=True)
    target = Path(tempfile.mkdtemp(prefix="maths-publication-", dir=private))
    subprocess.run(["git", "worktree", "add", "--detach", str(target), "origin/main"],
                   cwd=ROOT, check=True, capture_output=True)
    try:
        if (target / "report/maths-ablation/plan.json").read_bytes() != (ROOT / "report/maths-ablation/plan.json").read_bytes():
            raise ValueError("Remote experiment plan changed; publication stopped")
        names = ["results.json", "results.md", "shutdown.json"]
        for name in names:
            destination = target / "report/maths-ablation" / name
            if destination.exists():
                raise ValueError("Preserve an already published report; manual integration needed")
            destination.write_bytes((ROOT / "report/maths-ablation" / name).read_bytes())
        subprocess.run(["git", "add", *["report/maths-ablation/" + n for n in names]],
                       cwd=target, check=True)
        staged = subprocess.check_output(["git", "diff", "--cached", "--name-only"], cwd=target, text=True).splitlines()
        if set(staged) != {"report/maths-ablation/" + n for n in names}:
            raise ValueError("Unexpected publication files")
        scanner = Path.home() / ".local/state/afri-research/publication-audit-20261027/gitleaks"
        subprocess.run([str(scanner), "git", "--pre-commit", "--staged", "--redact",
                        "--no-banner", "--no-color", "."], cwd=target, check=True)
        subprocess.run(["git", "diff", "--cached", "--check"], cwd=target, check=True)
        subprocess.run(["git", "commit", "-m", "Record verified exploratory maths prompt-length pilot"],
                       cwd=target, check=True, capture_output=True)
        subprocess.run(git + ["push", "origin", "HEAD:main"], cwd=target, env=env,
                       check=True, capture_output=True)
        receipt.write_text(json.dumps({"published": True, "status": report["status"],
                                       "commit": subprocess.check_output(["git", "rev-parse", "HEAD"],
                                                                         cwd=target, text=True).strip()}) + "\n")
        receipt.chmod(0o600)
    finally:
        subprocess.run(["git", "worktree", "remove", "--force", str(target)],
                       cwd=ROOT, check=False, capture_output=True)


if __name__ == "__main__":
    main()
