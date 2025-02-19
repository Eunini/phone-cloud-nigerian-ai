import json

import httpx
import pytest

from bench.client import CompletionFailure, Endpoint
from bench.cost import cheapest_eligible, cost_per_1000
from bench.scoring import correct, extract, prompt


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
