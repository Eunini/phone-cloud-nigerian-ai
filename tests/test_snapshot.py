import json

import pytest

from bench.snapshot import snapshot


def test_snapshot_excludes_live_partial_tail_without_repairing_source(tmp_path):
    source, target = tmp_path / "live.jsonl", tmp_path / "snapshot.jsonl"
    complete = (json.dumps({"run_id": "study", "id": "one", "status": "ok"}) + "\n").encode()
    raw = complete + b'{"run_id":'
    source.write_bytes(raw)
    receipt = snapshot(source, target)
    assert source.read_bytes() == raw
    assert target.read_bytes() == complete
    assert receipt["unflushed_tail_bytes_excluded"] == len(raw) - len(complete)
    with pytest.raises(FileExistsError):
        snapshot(source, target)


def test_internal_corruption_or_mixed_identity_never_produces_a_snapshot(tmp_path):
    source, target = tmp_path / "live.jsonl", tmp_path / "snapshot.jsonl"
    source.write_text("{broken}\n")
    with pytest.raises(ValueError):
        snapshot(source, target)
    assert not target.exists()
