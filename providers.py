"""Provider-specific transport behind a small common interface."""
import base64
import json
import mimetypes
import os
import re
import time
import urllib.error
import urllib.request
from pathlib import Path


class ProviderError(RuntimeError):
    pass


class ChatProvider:
    def __init__(self, key, base_url, audio_mode="chat"):
        self.key = key
        self.base_url = base_url.rstrip("/")
        self.audio_mode = audio_mode

    def error_detail(self, result):
        error = result.get("error", {}) if isinstance(result, dict) else {}
        message = error.get("message", "") if isinstance(error, dict) else error
        metadata = error.get("metadata", {}) if isinstance(error, dict) else {}
        raw = metadata.get("raw", "") if isinstance(metadata, dict) else ""
        if isinstance(raw, str):
            try:
                raw = json.loads(raw)
            except ValueError:
                raw = {}
        if isinstance(raw, dict):
            nested = raw.get("error", raw)
            detail = nested.get("message", "") if isinstance(nested, dict) else ""
            if detail and detail != message:
                message = str(message) + ": " + str(detail)
        message = str(message)
        if self.key:
            message = message.replace(self.key, "[REDACTED]")
        message = re.sub(r"(?i)Bearer\s+\S+|sk-[A-Za-z0-9_-]+", "[REDACTED]", message)
        return " ".join(message.split())[:1000]

    def request(self, route, payload=None, raw=None, content_type=None):
        headers = {"Accept": "application/json"}
        if self.key:
            headers["Authorization"] = "Bearer " + self.key
        body = raw
        if payload is not None:
            body = json.dumps(payload).encode()
            content_type = "application/json"
        if content_type:
            headers["Content-Type"] = content_type
        request = urllib.request.Request(self.base_url + route, data=body, headers=headers)
        try:
            with urllib.request.urlopen(request, timeout=180) as response:
                result = json.load(response)
        except urllib.error.HTTPError as exc:
            try:
                detail = self.error_detail(json.loads(exc.read(65536)))
            except (OSError, ValueError):
                detail = ""
            raise ProviderError("API request failed (HTTP %s) at %s: %s" %
                                (exc.code, route, detail or "Provider returned no readable error message.")) from exc
        except (OSError, ValueError) as exc:
            raise ProviderError("API connection failed or returned invalid JSON.") from exc
        if "error" in result:
            raise ProviderError("Provider returned an error: " + (self.error_detail(result) or "No explanation provided."))
        return result

    def models(self, audio=False):
        rows = self.request("/models").get("data", [])
        if "openrouter.ai" in self.base_url:
            rows = [r for r in rows if "text" in r.get("architecture", {}).get("output_modalities", [])
                    and (not audio or "audio" in r.get("architecture", {}).get("input_modalities", []))]
        return sorted(r["id"] for r in rows if r.get("id"))

    def completion(self, model, content):
        result = self.request("/chat/completions", {"model": model, "messages": [{"role": "user", "content": content}]})
        try:
            text = result["choices"][0]["message"]["content"]
            if isinstance(text, list):
                text = "\n".join(p.get("text", "") for p in text)
            if not text or not text.strip():
                raise ValueError()
        except (KeyError, IndexError, TypeError, ValueError) as exc:
            raise ProviderError("Model returned no text.") from exc
        return text, result.get("usage", {})

    def transcribe(self, model, path, prompt, method="inline"):
        audio = Path(path).read_bytes()
        if self.audio_mode == "transcriptions":
            import uuid
            boundary = uuid.uuid4().hex
            chunks = []
            for name, value in [("model", model), ("prompt", prompt)]:
                chunks.append(("--%s\r\nContent-Disposition: form-data; name=\"%s\"\r\n\r\n%s\r\n" % (boundary, name, value)).encode())
            chunks.append(("--%s\r\nContent-Disposition: form-data; name=\"file\"; filename=\"audio%s\"\r\nContent-Type: %s\r\n\r\n" % (boundary, Path(path).suffix.lower(), mimetypes.guess_type(path)[0] or "application/octet-stream")).encode())
            chunks.extend([audio, ("\r\n--%s--\r\n" % boundary).encode()])
            result = self.request("/audio/transcriptions", raw=b"".join(chunks), content_type="multipart/form-data; boundary=" + boundary)
            if not result.get("text", "").strip():
                raise ProviderError("Transcription endpoint returned no text.")
            return result["text"], result.get("usage", {})
        return self.completion(model, [{"type": "text", "text": prompt}, {"type": "input_audio", "input_audio": {"data": base64.b64encode(audio).decode(), "format": Path(path).suffix[1:].lower()}}])

    def generate(self, model, transcript, prompt):
        return self.completion(model, prompt + "\n\n" + transcript)


class OpenRouterProvider(ChatProvider):
    def __init__(self, key):
        super().__init__(key, "https://openrouter.ai/api/v1")
        self._catalog = None

    def catalog(self):
        if self._catalog is None:
            rows = self.request("/models").get("data", [])
            specialists = self.request("/models?output_modalities=transcription").get("data", [])
            self._catalog = {row["id"]: row for row in rows + specialists if row.get("id")}
        return self._catalog

    def is_specialist(self, model):
        row = self.catalog().get(model)
        if not row:
            raise ProviderError("Model is not in the OpenRouter catalog. Refresh the model list.")
        return "transcription" in row.get("architecture", {}).get("output_modalities", [])

    def models(self, audio=False):
        result = []
        for model, row in self.catalog().items():
            architecture = row.get("architecture", {})
            inputs = architecture.get("input_modalities", [])
            outputs = architecture.get("output_modalities", [])
            if audio and "audio" in inputs and ("text" in outputs or "transcription" in outputs):
                result.append(model)
            elif not audio and "text" in inputs and "text" in outputs and "transcription" not in outputs:
                result.append(model)
        return sorted(result)

    def validate_model(self, model, audio=False):
        if model not in self.models(audio):
            raise ProviderError("Select an OpenRouter %s model." % ("audio transcription" if audio else "text-generation"))

    def transcribe(self, model, path, prompt, method="inline"):
        if not self.is_specialist(model):
            return super().transcribe(model, path, prompt, method)
        audio_format = Path(path).suffix[1:].lower()
        if audio_format not in ("wav", "mp3", "flac", "m4a", "ogg", "webm", "aac", "opus"):
            raise ProviderError("Unsupported OpenRouter transcription audio format: " + audio_format)
        payload = {"model": model, "input_audio": {
            "data": base64.b64encode(Path(path).read_bytes()).decode(), "format": audio_format}}
        if model == "microsoft/mai-transcribe-2":
            payload.update(response_format="verbose_json", timestamp_granularities=["segment", "word"],
                           provider={"options": {"azure": {"diarization": {"enabled": True}}}})
        result = self.request("/audio/transcriptions", payload)
        lines = []
        for segment in result.get("segments", []):
            text = segment.get("text", "").strip()
            if not text:
                continue
            seconds = max(0, int(float(segment.get("start", 0))))
            timestamp = "[%02d:%02d:%02d]" % (seconds // 3600, seconds // 60 % 60, seconds % 60)
            speaker = " Speaker %s:" % segment["speaker"] if segment.get("speaker") is not None else ""
            lines.append(timestamp + speaker + " " + text)
        text = "\n\n".join(lines) or result.get("text", "")
        if not text.strip():
            raise ProviderError("Transcription endpoint returned no text.")
        return text, result.get("usage", {})

    def generate(self, model, transcript, prompt):
        self.validate_model(model, False)
        return super().generate(model, transcript, prompt)


class GoogleProvider:
    def __init__(self, key):
        import google.generativeai as genai
        self.api = genai
        self.api.configure(api_key=key)

    def models(self, audio=False):
        return sorted(m.name.split("/", 1)[-1] for m in self.api.list_models()
                      if "generateContent" in m.supported_generation_methods)

    def result(self, response):
        text = response.text
        if not text.strip():
            raise ProviderError("Google returned no text.")
        usage = getattr(response, "usage_metadata", None)
        return text, {"prompt_tokens": getattr(usage, "prompt_token_count", None), "completion_tokens": getattr(usage, "candidates_token_count", None)}

    def transcribe(self, model, path, prompt, method="inline"):
        uploaded = None
        try:
            if method == "upload" or (method == "auto" and os.path.getsize(path) >= 20 * 1024 * 1024):
                uploaded = self.api.upload_file(path=path)
                deadline = time.monotonic() + 180
                while uploaded.state.name == "PROCESSING":
                    if time.monotonic() > deadline:
                        raise ProviderError("Google file processing timed out.")
                    time.sleep(1)
                    uploaded = self.api.get_file(uploaded.name)
                if uploaded.state.name == "FAILED":
                    raise ProviderError("Google could not process this file.")
                content = uploaded
            else:
                content = {"mime_type": mimetypes.guess_type(path)[0] or "application/octet-stream", "data": Path(path).read_bytes()}
            return self.result(self.api.GenerativeModel(model).generate_content([prompt, content]))
        finally:
            if uploaded:
                try:
                    self.api.delete_file(uploaded.name)
                except Exception:
                    pass

    def generate(self, model, transcript, prompt):
        return self.result(self.api.GenerativeModel(model).generate_content([prompt, transcript]))


PROVIDERS = ("Google Gemini", "OpenRouter", "Custom API")
KEY_NAMES = {"Google Gemini": "GEMINI_API_KEY", "OpenRouter": "OPENROUTER_API_KEY", "Custom API": "CUSTOM_API_KEY"}


def create_provider(name, settings):
    key = settings.get(KEY_NAMES[name], os.environ.get(KEY_NAMES[name], ""))
    if not key and KEY_NAMES[name] not in settings and os.name == "nt":
        import winreg
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment") as registry:
                key = winreg.QueryValueEx(registry, KEY_NAMES[name])[0]
        except OSError:
            pass
    if name != "Custom API" and not key:
        raise ProviderError("Set the API key for " + name + " in API settings.")
    if name == "Google Gemini":
        return GoogleProvider(key)
    if name == "OpenRouter":
        return OpenRouterProvider(key)
    url = "https://openrouter.ai/api/v1" if name == "OpenRouter" else settings.get("base_url", "").strip()
    if not url.startswith(("https://", "http://")):
        raise ProviderError("Set a valid custom API base URL, including /v1 when required.")
    return ChatProvider(key, url, settings.get("audio_mode", "chat") if name == "Custom API" else "chat")
