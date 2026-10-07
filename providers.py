"""Explicit model providers; no automatic network calls or downloads."""
import json
import re
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError


class ProviderError(ValueError):
    pass


def post_json(url, payload, headers=None):
    request = Request(url, data=json.dumps(payload).encode("utf-8"),
                      headers={"Content-Type": "application/json", **(headers or {})}, method="POST")
    try:
        with urlopen(request, timeout=90) as response:
            return json.load(response)
    except HTTPError as error:
        raise ProviderError(f"Model request failed (HTTP {error.code}); no retry was made.") from None
    except (URLError, TimeoutError, OSError, ValueError):
        raise ProviderError("Model unavailable or returned unreadable data; no retry was made.") from None


class Gemini:
    def __init__(self, key, model):
        from evidence_answers import normalize_api_key
        self.key = normalize_api_key(key)
        if not re.fullmatch(r"gemini-[A-Za-z0-9._-]+", model):
            raise ValueError("Specify a valid Gemini model ID available to your account.")
        self.model = model

    def decide(self, system, context, schema):
        result = post_json("https://generativelanguage.googleapis.com/v1beta/interactions", {
            "model": self.model, "system_instruction": system,
            "input": json.dumps(context, ensure_ascii=False), "store": False,
            "generation_config": {"max_output_tokens": 4096},
            "response_format": {"type": "text", "mime_type": "application/json", "schema": schema}},
            {"x-goog-api-key": self.key})
        try:
            if result.get("status") != "completed":
                raise ValueError()
            output = "".join(part["text"] for step in result["steps"]
                             if step.get("type") == "model_output"
                             for part in step.get("content", []) if part.get("type") == "text")
            return json.loads(output)
        except (KeyError, TypeError, ValueError):
            raise ProviderError("Gemini did not return a complete JSON decision.") from None


class Ollama:
    def __init__(self, model):
        if not isinstance(model, str) or not model.strip():
            raise ValueError("Specify an already installed local Ollama model.")
        self.model = model

    def decide(self, system, context, schema):
        result = post_json("http://127.0.0.1:11434/api/chat", {
            "model": self.model, "stream": False, "format": schema,
            "messages": [{"role": "system", "content": system},
                         {"role": "user", "content": json.dumps(context, ensure_ascii=False)}],
            "options": {"temperature": 0, "num_predict": 4096}})
        try:
            return json.loads(result["message"]["content"])
        except (KeyError, TypeError, ValueError):
            raise ProviderError("Ollama did not return a JSON decision.") from None
