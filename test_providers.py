import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from providers import ChatProvider, OpenRouterProvider, ProviderError, create_provider


class ProviderTests(unittest.TestCase):
    def router(self):
        provider = OpenRouterProvider("key")
        provider._catalog = {
            "microsoft/mai-transcribe-2": {"architecture": {"input_modalities": ["audio"], "output_modalities": ["transcription"]}},
            "audio-chat": {"architecture": {"input_modalities": ["audio", "text"], "output_modalities": ["text"]}},
            "writer": {"architecture": {"input_modalities": ["text"], "output_modalities": ["text"]}},
        }
        return provider

    def test_specialists_discovered_separately(self):
        provider = OpenRouterProvider("key")
        with patch.object(provider, "request", side_effect=[{"data": []}, {"data": [
                {"id": "stt", "architecture": {"input_modalities": ["audio"], "output_modalities": ["transcription"]}}]}]) as request:
            self.assertEqual(provider.models(True), ["stt"])
            self.assertEqual(provider.models(False), [])
            self.assertEqual(request.call_args.args[0], "/models?output_modalities=transcription")
            self.assertEqual(request.call_count, 2)

    def test_specialist_routes_json_and_preserves_speakers_and_timestamps(self):
        provider = self.router()
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "sample.mp3"
            path.write_bytes(b"audio")
            response = {"text": "Hello", "segments": [{"start": 3661.4, "speaker": 0, "text": "Hello"}], "usage": {"seconds": 3}}
            with patch.object(provider, "request", return_value=response) as request:
                text, usage = provider.transcribe("microsoft/mai-transcribe-2", path, "Not sent as chat")
                self.assertEqual(text, "[01:01:01] Speaker 0: Hello")
                self.assertEqual(usage, {"seconds": 3})
                route, payload = request.call_args.args
                self.assertEqual(route, "/audio/transcriptions")
                self.assertEqual(payload["input_audio"], {"data": "YXVkaW8=", "format": "mp3"})
                self.assertNotIn("prompt", payload)
                self.assertTrue(payload["provider"]["options"]["azure"]["diarization"]["enabled"])

    def test_specialist_cannot_write(self):
        provider = self.router()
        with patch.object(provider, "request") as request:
            with self.assertRaises(ProviderError):
                provider.generate("microsoft/mai-transcribe-2", "Transcript", "Write")
            request.assert_not_called()
        self.assertEqual(provider.models(False), ["audio-chat", "writer"])

    def test_router_chat_audio_still_uses_chat_endpoint(self):
        provider = self.router()
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "sample.wav"
            path.write_bytes(b"audio")
            with patch.object(provider, "request", return_value={"choices": [{"message": {"content": "Transcript"}}]}) as request:
                provider.transcribe("audio-chat", path, "Transcribe")
                self.assertEqual(request.call_args.args[0], "/chat/completions")

    def test_loaded_transcript_skips_audio_and_transcription_provider(self):
        from types import SimpleNamespace
        from unittest.mock import Mock
        from workspace_ui import run_pipeline
        with tempfile.TemporaryDirectory() as directory:
            core = SimpleNamespace(OUTPUT_FOLDER=directory, validate_audio_file=Mock(side_effect=AssertionError("Audio must not be read")), validate_prompt_input=lambda p: (True, ""))
            provider = Mock()
            provider.generate.return_value = ("New memo", {})
            events = []
            with patch("workspace_ui.create_provider", return_value=provider) as create:
                run_pipeline(core, None, [("Google Gemini", ""), ("Custom API", "writer")], {}, ["", "Write a memo"], "inline", lambda k, v: events.append((k, v)), transcript="Loaded transcript")
                create.assert_called_once_with("Custom API", {})
            provider.transcribe.assert_not_called()
            provider.generate.assert_called_once_with("writer", "Loaded transcript", "Write a memo")
            self.assertEqual(next(Path(directory).glob("*-transcript.txt")).read_text(), "Loaded transcript")
            self.assertIn(("memo", "New memo"), events)
            progress = [value for kind, value in events if kind == 'progress']
            self.assertEqual([value['completed'] for value in progress], [0, 1, 2, 3])
            self.assertTrue(all(value['total'] == 3 for value in progress))

    def test_audio_chat_encodes_file_and_format(self):
        provider = ChatProvider("key", "https://example.test/v1")
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "sample.wav"
            path.write_bytes(b"audio")
            with patch.object(provider, "request", return_value={"choices": [{"message": {"content": "Transcript"}}]}) as request:
                self.assertEqual(provider.transcribe("model", path, "Transcribe")[0], "Transcript")
                audio = request.call_args.args[1]["messages"][0]["content"][1]["input_audio"]
                self.assertEqual(audio, {"data": "YXVkaW8=", "format": "wav"})

    def test_custom_multipart_endpoint(self):
        provider = ChatProvider("", "http://localhost:8000/v1", "transcriptions")
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "sample.mp3"
            path.write_bytes(b"sample-audio")
            with patch.object(provider, "request", return_value={"text": "Transcript"}) as request:
                provider.transcribe("whisper", path, "Transcribe")
                self.assertEqual(request.call_args.args[0], "/audio/transcriptions")
                self.assertIn(b"sample-audio", request.call_args.kwargs["raw"])
                self.assertIn("multipart/form-data", request.call_args.kwargs["content_type"])

    def test_openrouter_factory_filters_merged_catalog_by_stage(self):
        provider = create_provider("OpenRouter", {"OPENROUTER_API_KEY": "key"})
        self.assertIsInstance(provider, OpenRouterProvider)
        rows = [
            {"id": "audio", "architecture": {"input_modalities": ["audio", "text"], "output_modalities": ["text"]}},
            {"id": "text", "architecture": {"input_modalities": ["text"], "output_modalities": ["text"]}},
        ]
        specialists = [{"id": "stt", "architecture": {"input_modalities": ["audio"], "output_modalities": ["transcription"]}}]
        with patch.object(provider, "request", side_effect=[{"data": rows}, {"data": specialists}]):
            self.assertEqual(provider.models(True), ["audio", "stt"])
            self.assertEqual(provider.models(False), ["audio", "text"])

    def test_empty_response_rejected(self):
        provider = ChatProvider("key", "https://example.test/v1")
        with patch.object(provider, "request", return_value={"choices": []}):
            with self.assertRaises(ProviderError):
                provider.generate("model", "transcript", "write")

    def test_missing_key_rejected(self):
        with self.assertRaises(ProviderError):
            create_provider("OpenRouter", {"OPENROUTER_API_KEY": ""})

    def test_google_inline_uses_actual_mime_and_upload_is_cleaned(self):
        from unittest.mock import Mock
        from types import SimpleNamespace
        from providers import GoogleProvider
        provider = GoogleProvider.__new__(GoogleProvider)
        provider.api = Mock()
        provider.api.GenerativeModel.return_value.generate_content.return_value = SimpleNamespace(text="Transcript")
        uploaded = SimpleNamespace(name="files/test", state=SimpleNamespace(name="ACTIVE"))
        provider.api.upload_file.return_value = uploaded
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "audio.wav"
            path.write_bytes(b"audio")
            provider.transcribe("gemini", str(path), "Transcribe", "inline")
            content = provider.api.GenerativeModel.return_value.generate_content.call_args.args[0][1]
            self.assertIn(content["mime_type"], ("audio/wav", "audio/x-wav"))
            provider.transcribe("gemini", str(path), "Transcribe", "upload")
            provider.api.delete_file.assert_called_once_with("files/test")

    def test_mixed_provider_pipeline_preserves_transcript_on_writing_failure(self):
        from types import SimpleNamespace
        from unittest.mock import Mock
        from workspace_ui import run_pipeline
        with tempfile.TemporaryDirectory() as directory:
            core = SimpleNamespace(OUTPUT_FOLDER=directory, validate_audio_file=lambda p: (True, ""), validate_prompt_input=lambda p: (True, ""))
            google = Mock()
            google.transcribe.return_value = ("Saved transcript", {})
            router = Mock()
            router.generate.side_effect = ProviderError("Writing failed")
            events = []
            with patch("workspace_ui.create_provider", side_effect=lambda name, settings: google if name == "Google Gemini" else router):
                with self.assertRaises(ProviderError):
                    run_pipeline(core, "audio.mp3", [("Google Gemini", "gemini"), ("OpenRouter", "writer")], {}, ["Transcribe", "Write"], "upload", lambda k, v: events.append((k, v)))
            self.assertEqual(next(Path(directory).glob("*-transcript.txt")).read_text(), "Saved transcript")
            router.generate.assert_called_once_with("writer", "Saved transcript", "Write")
            self.assertIn(("transcript", "Saved transcript"), events)
            progress = [value for kind, value in events if kind == 'progress']
            self.assertEqual([value['completed'] for value in progress], [0, 1, 2])
            self.assertTrue(all(value['completed'] < value['total'] for value in progress))


if __name__ == "__main__":
    unittest.main()
