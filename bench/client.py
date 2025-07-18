"""Streaming timings and exact application-body byte counts, excluding TLS/IP overhead."""

import json
import re
import time
from urllib.parse import urlsplit

import httpx


class CompletionFailure(Exception):
    def __init__(self, error_type, telemetry):
        super().__init__(error_type)
        self.error_type = error_type
        self.telemetry = telemetry


def validate_endpoint(endpoint):
    parsed = urlsplit(endpoint)
    if parsed.scheme not in {"https", "http"} or not parsed.hostname:
        raise ValueError("Expected an HTTP(S) endpoint")
    if parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise ValueError("Endpoint must not contain embedded credentials, query, or fragment")
    return endpoint.rstrip("/")


class Endpoint:
    def __init__(self, url, model, key=None, transport=None, timeout=180):
        self.url = validate_endpoint(url)
        self.model = model
        self.client = httpx.Client(
            timeout=timeout,
            transport=transport,
            headers={"Authorization": f"Bearer {key}"} if key else {},
        )

    def close(self):
        self.client.close()

    def complete(self, messages, max_tokens=128):
        self.telemetry = {"request_body_bytes": 0, "response_body_bytes": 0, "mb_per_question": 0.0}
        start = time.perf_counter()
        try:
            return self._complete(messages, max_tokens)
        except Exception as error:
            self.telemetry["latency_seconds"] = time.perf_counter() - start
            raise CompletionFailure(type(error).__name__, self.telemetry.copy()) from None

    def _complete(self, messages, max_tokens):
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": 0,
            "max_tokens": max_tokens,
            "stream": True,
            "stream_options": {"include_usage": True},
        }
        body = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode()
        self.telemetry.update(request_body_bytes=len(body), mb_per_question=len(body) / 1_000_000)
        start = time.perf_counter()
        text, buffer = "", b""
        received, first_text, first_word, usage, finish = 0, None, None, None, None
        with self.client.stream(
            "POST",
            self.url + "/chat/completions",
            content=body,
            headers={"Content-Type": "application/json", "Accept-Encoding": "identity"},
        ) as response:
            self.telemetry["http_status"] = response.status_code
            if response.status_code != 200:
                for chunk in response.iter_raw():
                    received += len(chunk)
                self.telemetry.update(
                    response_body_bytes=received, mb_per_question=(len(body) + received) / 1_000_000
                )
                response.raise_for_status()
                raise ValueError("Unexpected non-200 completion response")
            for chunk in response.iter_raw():
                received += len(chunk)
                self.telemetry.update(
                    response_body_bytes=received, mb_per_question=(len(body) + received) / 1_000_000
                )
                buffer += chunk
                while b"\n" in buffer:
                    line, buffer = buffer.split(b"\n", 1)
                    line = line.strip()
                    if not line.startswith(b"data:"):
                        continue
                    raw = line[5:].strip()
                    if raw == b"[DONE]":
                        continue
                    event = json.loads(raw)
                    if event.get("usage"):
                        usage = event["usage"]
                    choices = event.get("choices", [])
                    if choices:
                        finish = choices[0].get("finish_reason") or finish
                        delta = choices[0].get("delta", {}).get("content") or ""
                        if delta:
                            now = time.perf_counter() - start
                            if first_text is None:
                                first_text = now
                            text += delta
                            if first_word is None and re.search(r"\S+\s", text):
                                first_word = now
        duration = time.perf_counter() - start
        if buffer.strip() and buffer.strip() != b"data: [DONE]":
            raise ValueError("Truncated SSE response without a final newline")
        if not text or finish is None:
            raise ValueError("Empty or incomplete streamed completion")
        words = len(text.split())
        return {
            "text": text,
            "latency_seconds": duration,
            "time_to_first_text_seconds": first_text,
            "time_to_first_word_seconds": first_word if first_word is not None else duration,
            "words": words,
            "words_per_second": words / duration,
            "decode_words_per_second": (
                (words - 1) / (duration - first_text)
                if words > 1 and duration > first_text
                else None
            ),
            "request_body_bytes": len(body),
            "response_body_bytes": received,
            "mb_per_question": (len(body) + received) / 1_000_000,
            "byte_scope": "HTTP application bodies including SSE framing; excludes headers/TLS/IP",
            "usage": usage,
            "finish_reason": finish,
        }
