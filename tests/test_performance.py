import json

import pytest

from bench.performance import percentile, summarize


def timing_inputs(tmp_path):
    items = [
        {"id": str(i), "language": str(i // 30), "task": str(i % 30 // 10)} for i in range(120)
    ]
    paths = []
    for repetition in range(1, 4):
        path = tmp_path / f"repeat-{repetition}.jsonl"
        records = [
            {
                **item,
                "run_id": str(repetition),
                "replicate": repetition,
                "status": "ok",
                "translate": False,
                "model": "qwen",
                "model_revision": "hash",
                "items_sha256": "sample",
                "prompt_version": "fixed",
                "max_tokens": 128,
                "end_to_end_seconds": repetition,
                "latency_seconds": 1,
                "time_to_first_word_seconds": 0.2,
                "peak_server_rss_bytes_sampled": 100,
                "peak_client_rss_bytes_sampled": 10,
                "decode_words_per_second": None,
                "text": "same" if int(item["id"]) else str(repetition),
            }
            for item in items
        ]
        path.write_text("".join(json.dumps(r) + "\n" for r in records))
        paths.append(path)
    return items, paths


def test_repeats_do_not_inflate_distinct_items_and_report_text_changes(tmp_path):
    items, paths = timing_inputs(tmp_path)
    overall = summarize(paths, items)["groups"][0]
    assert overall["requests"] == 360
    assert overall["distinct_items"] == 120
    assert overall["median_end_to_end_seconds"] == 2
    assert overall["items_with_different_text_across_repeats"] == 1
    assert overall["median_decode_words_per_second"] is None
    assert percentile([0, 10], 0.95) == 9.5


def test_missing_items_or_changed_identity_cannot_be_reported_as_complete(tmp_path):
    items, paths = timing_inputs(tmp_path)
    raw = paths[1].read_text()
    paths[1].write_text(raw.replace('"max_tokens": 128', '"max_tokens": 256', 1))
    with pytest.raises(ValueError, match="changed"):
        summarize(paths, items)
    paths[1].write_text("\n".join(raw.splitlines()[:-1]) + "\n")
    with pytest.raises(ValueError, match="120 items"):
        summarize(paths, items)
