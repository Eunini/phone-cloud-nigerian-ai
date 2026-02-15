import json

import httpx
import pytest

from bench.client import CompletionFailure, Endpoint
from bench.cost import cheapest_eligible, cost_per_1000
from bench.scoring import correct, extract, prompt


ITEM = {
    "id": "toy-yor",
    "language": "yor",
    "task": "afrimmlu",
    "question": "Choose A.",
    "choices": ["one", "two", "three", "four"],
    "answer": "A",
}


def test_answer_extraction_rejects_ambiguous_reasoning():
    assert extract("afrimmlu", "A or B") is None
    assert extract("afrimmlu", "FINAL: A\nFINAL: B") is None
    assert extract("afrimgsm", "I tried 10, then 20") is None
    assert extract("afrimgsm", "FINAL: 70,000") == "7E+4"
    assert extract("afrimgsm", "FINAL: 70,00") is None
    assert correct({"task": "afrimgsm", "answer": "18"}, "thinking\nFINAL: 18.0")
    assert extract("afrixnli", "FINAL: contradiction") == "contradiction"
    assert "gold" not in prompt(
        {"task": "afrimmlu", "question": "test", "choices": ["a", "b", "c", "d"], "answer": "gold"}
    )


def test_streaming_bytes_and_unicode_are_measured():
    chunks = [
        b'data: {"choices":[{"delta":{"content":"FINAL: "},"finish_reason":null}]}\n\n',
        b'data: {"choices":[{"delta":{"content":"A"},"finish_reason":null}]}\n\n',
        b'data: {"choices":[{"delta":{},"finish_reason":"stop"}],"usage":{"prompt_tokens":4,"completion_tokens":2}}\n\n',
        b"data: [DONE]\n\n",
    ]
    seen = []

    def handler(request):
        seen.append(request.content)
        return httpx.Response(200, stream=httpx.ByteStream(b"".join(chunks)))

    endpoint = Endpoint("http://localhost:8080/v1", "test", transport=httpx.MockTransport(handler))
    result = endpoint.complete([{"role": "user", "content": "ẹ́"}])
    endpoint.close()
    assert result["text"] == "FINAL: A"
    assert result["request_body_bytes"] == len(seen[0])
    assert result["response_body_bytes"] == sum(map(len, chunks))
    assert json.loads(seen[0])["messages"][0]["content"] == "ẹ́"


def test_cost_units_and_missing_prices():
    assert cost_per_1000(placement="cloud", mb_per_question=0.01, ngn_per_mb=3.07, free_tier=True)[
        "total_ngn"
    ] == pytest.approx(30.7)
    assert cost_per_1000(placement="local", mb_per_question=1, ngn_per_mb=3.07)["total_ngn"] == 0
    with pytest.raises(ValueError):
        cost_per_1000(placement="cloud", mb_per_question=1, ngn_per_mb=1)
    assert cheapest_eligible([{"accuracy": 0.5, "cost_ngn": 0}], 0.6) is None
    with pytest.raises(ValueError):
        Endpoint("https://secret@example.com/v1", "test")


def test_failed_stream_preserves_bytes_without_response_content():
    content = b"data: invalid-json\n\n"
    endpoint = Endpoint(
        "http://localhost:8080/v1",
        "test",
        transport=httpx.MockTransport(
            lambda request: httpx.Response(200, stream=httpx.ByteStream(content))
        ),
    )
    with pytest.raises(CompletionFailure) as caught:
        endpoint.complete([{"role": "user", "content": "hello"}])
    assert caught.value.telemetry["request_body_bytes"] > 0
    assert caught.value.telemetry["response_body_bytes"] == len(content)
    assert "invalid-json" not in str(caught.value)


def test_device_metadata_survives_android_memory_permission_restrictions(monkeypatch):
    from bench import device

    def denied():
        raise PermissionError("restricted /proc")

    monkeypatch.setattr(device.psutil, "virtual_memory", denied)
    monkeypatch.setattr(device.shutil, "which", lambda _: None)
    result = device.metadata()
    assert result["memory_total_bytes"] is None
    assert result["memory_available_bytes_at_setup"] is None
    assert result["memory_metadata_error"] == "PermissionError"


@pytest.mark.parametrize("when", ["before", "after"])
def test_translation_failure_keeps_only_actual_target_bytes(when):
    from bench.run import measure_question

    class Target:
        calls = 0

        def complete(self, *args):
            self.calls += 1
            return {
                "text": "FINAL: A",
                "request_body_bytes": 120,
                "response_body_bytes": 80,
                "mb_per_question": 0.0002,
                "http_status": 200,
            }

    class Translation:
        def fail(self):
            raise CompletionFailure(
                "HTTPStatusError", {"http_status": 429, "request_body_bytes": 999}
            )

        def item_to_english(self, item):
            return self.fail() if when == "before" else item

        def text(self, *args):
            self.fail()

    target = Target()
    result = measure_question(target, ITEM, translator=Translation())
    assert result["status"] == "error" and not result["correct"]
    assert result["translation_http_status"] == 429
    if when == "before":
        assert target.calls == 0 and result["mb_per_question"] == 0
        assert result["request_body_bytes"] == 0 and "http_status" not in result
    else:
        assert target.calls == 1 and result["answer_correct"]
        assert result["request_body_bytes"] == 120 and result["response_body_bytes"] == 80
        assert result["http_status"] == 200 and result["mb_per_question"] == 0.0002


@pytest.mark.parametrize("request_fails,expected_attempts", [(False, 1), (True, 2)])
def test_resume_never_resamples_wrong_answers_and_bounds_request_failures(
    tmp_path, monkeypatch, request_fails, expected_attempts
):
    import sys

    from bench import run

    items, out = tmp_path / "items.jsonl", tmp_path / "run.jsonl"
    items.write_text(json.dumps(ITEM) + "\n")

    class FakeEndpoint:
        def __init__(self, url, *args):
            self.url = url

        def complete(self, messages, *args):
            if request_fails and messages[0]["content"] != "Return the word ready.":
                raise CompletionFailure(
                    "HTTPStatusError",
                    {"http_status": 503, "request_body_bytes": 120, "response_body_bytes": 80},
                )
            return {"text": "FINAL: B", "http_status": 200, "mb_per_question": 0.0002}

        def close(self):
            pass

    monkeypatch.setattr(run, "Endpoint", FakeEndpoint)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "bench.run", "--items", str(items), "--endpoint", "http://localhost:8080/v1",
            "--model", "toy", "--model-revision", "fixture-v1", "--placement", "cloud",
            "--device", "fixture", "--max-attempts-per-item", "2", "--out", str(out),
        ],
    )
    for _ in range(4):
        run.main()
    rows = [json.loads(line) for line in out.read_text().splitlines()]
    assert len(rows) == expected_attempts
    assert all(not row["correct"] for row in rows)
    assert len({row["run_id"] for row in rows}) == 1
