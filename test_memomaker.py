"""Unit tests for provider routing, saved work, prompts, and clipboard encoding.

Run: python -B -m unittest discover -v
Browser and native integration checks remain in verify_ui.py and verify_desktop.py.
"""
import importlib.util
import pathlib
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

from desktop_view import DesktopAPI, clipboard_html
from providers import ChatProvider, OpenRouterProvider, ProviderError, create_provider


def load_memomaker_module():
    root = pathlib.Path(__file__).resolve().parent
    module_path = root / "memomaker-ui.pyw"

    spec = importlib.util.spec_from_file_location("memomaker_ui", module_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class PromptLoadingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.memomaker = load_memomaker_module()

    def test_loads_every_detected_prompt_file(self):
        self.assertIn("EN-ARTICLE", self.memomaker.AVAILABLE_LANGUAGES)

        for language_code in self.memomaker.AVAILABLE_LANGUAGES:
            with self.subTest(language_code=language_code):
                transcript_prompt, output_prompt = self.memomaker.read_prompts_from_file(language_code)

                self.assertIsInstance(transcript_prompt, str)
                self.assertIsInstance(output_prompt, str)
                self.assertTrue(transcript_prompt.strip())
                self.assertTrue(output_prompt.strip())

    def test_second_prompt_section_can_use_article_heading(self):
        transcript_prompt, output_prompt = self.memomaker.read_prompts_from_file("EN-ARTICLE")

        self.assertIn("Please create an article", output_prompt)
        self.assertIn("# Title: <title>", output_prompt)
        self.assertNotIn("# Transcription", transcript_prompt)


class DesktopFeaturesTests(unittest.TestCase):
    def test_transcript_only_skips_writing_configuration_and_request(self):
        from workspace_ui import run_pipeline
        with tempfile.TemporaryDirectory() as directory:
            core = SimpleNamespace(OUTPUT_FOLDER=directory,
                                   validate_audio_file=Mock(return_value=(True, "")),
                                   validate_prompt_input=Mock(return_value=(True, "")))
            provider = Mock()
            provider.transcribe.return_value = ("Audio transcript", {})
            events = []
            with patch("workspace_ui.create_provider", return_value=provider) as factory:
                run_pipeline(core, "audio.mp3", [("Custom API", "transcriber"), ("Google Gemini", "")],
                             {}, ["Transcribe", ""], "inline", lambda k, v: events.append((k, v)),
                             transcript_only=True)
            factory.assert_called_once_with("Custom API", {})
            core.validate_prompt_input.assert_called_once_with("Transcribe")
            provider.generate.assert_not_called()
            self.assertEqual(next(Path(directory).glob("*-transcript.txt")).read_text(), "Audio transcript")
            self.assertEqual(list(Path(directory).glob("*-memo.md")), [])
            self.assertFalse(any(k == "memo" for k, v in events))
            self.assertEqual(events[-1], ("progress", {"completed": 3, "total": 3, "label": "Completed"}))

    def test_rich_clipboard_offsets_count_utf8_bytes(self):
        fragment = '<div><h1>Memo</h1><p><b>J\u00fcri</b> &amp; Liis</p></div>'
        payload = clipboard_html(fragment).encode('utf-8')
        import re
        offsets = {name.decode(): int(value) for name, value in re.findall(rb'(StartHTML|EndHTML|StartFragment|EndFragment):(\d+)', payload)}
        self.assertEqual(payload[offsets['StartFragment']:offsets['EndFragment']].decode('utf-8'), fragment)
        self.assertTrue(payload[offsets['StartHTML']:offsets['EndHTML']].startswith(b'<html>'))
        self.assertEqual(offsets['EndHTML'], len(payload))

    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.path = Path(self.directory.name) / "transcription-prompt-en-article.md"
        self.original = "# Transcription\nOld transcription.\n\n# Article\nOld article.\n"
        self.path.write_text(self.original, encoding="utf-8")
        core = load_memomaker_module()
        core.AVAILABLE_LANGUAGES = {"EN-ARTICLE": str(self.path)}
        core.OUTPUT_FOLDER = self.directory.name
        with patch("desktop_view.CONFIG", Path(self.directory.name) / "settings.json"):
            self.api = DesktopAPI(core)
        self.api._window = Mock()

    def test_prompt_save_requires_confirmation_and_preserves_headings(self):
        self.api._window.create_confirmation_dialog.return_value = False
        prompts = ["New transcription rules.", "New article rules.\n# Title: <title>"]
        self.assertFalse(self.api.save_prompts("EN-ARTICLE", prompts))
        self.assertEqual(self.path.read_text(encoding="utf-8"), self.original)
        self.api._window.create_confirmation_dialog.return_value = True
        self.assertEqual(self.api.save_prompts("EN-ARTICLE", prompts), prompts)
        self.assertIn("# Article\n", self.path.read_text(encoding="utf-8"))
        self.assertEqual(list(Path(self.directory.name).glob("*.tmp")), [])

    def test_concurrent_prompt_change_not_overwritten(self):
        def change(*args):
            self.path.write_text("External edit", encoding="utf-8")
            return True
        self.api._window.create_confirmation_dialog.side_effect = change
        result = self.api.save_prompts("EN-ARTICLE", ["Transcribe accurately.", "Write a concise memo."])
        self.assertIn("changed on disk", result["error"])
        self.assertEqual(self.path.read_text(), "External edit")

    def test_invalid_profile_and_transcript_heading_are_rejected(self):
        self.assertIn("error", self.api.save_prompts("../elsewhere", ["Transcribe accurately.", "Write a memo."]))
        self.assertIn("error", self.api.save_prompts("EN-ARTICLE", ["# Wrong heading\nRules here.", "Write a memo."]))
        self.api._window.create_confirmation_dialog.assert_not_called()

    def test_load_bom_transcript_and_memo_without_overwriting_files(self):
        with patch.dict("sys.modules", {"webview": SimpleNamespace(FileDialog=SimpleNamespace(OPEN=1))}):
            for kind, extension in [("transcript", ".txt"), ("memo", ".md")]:
                path = Path(self.directory.name) / (kind + extension)
                path.write_text("Saved content", encoding="utf-8-sig")
                self.api._window.create_file_dialog.return_value = [str(path)]
                self.assertEqual(self.api.load_output(kind), {"text": "Saved content", "name": path.name})
                self.assertTrue(path.read_bytes().startswith(b"\xef\xbb\xbf"))
            self.api._window.create_file_dialog.return_value = None
            self.assertIsNone(self.api.load_output("memo"))

    def test_empty_and_non_utf8_load_errors(self):
        with patch.dict("sys.modules", {"webview": SimpleNamespace(FileDialog=SimpleNamespace(OPEN=1))}):
            path = Path(self.directory.name) / "memo.md"
            self.api._window.create_file_dialog.return_value = [str(path)]
            for content in (b"", b"\xff"):
                path.write_bytes(content)
                self.assertIn("error", self.api.load_output("memo"))


class ProviderTests(unittest.TestCase):
    def router(self):
        provider = OpenRouterProvider("key")
        provider._catalog = {
            "microsoft/mai-transcribe-2": {"architecture": {"input_modalities": ["audio"], "output_modalities": ["transcription"]}},
            "audio-chat": {"architecture": {"input_modalities": ["audio", "text"], "output_modalities": ["text"]}},
            "writer": {"architecture": {"input_modalities": ["text"], "output_modalities": ["text"]}},
        }
        return provider


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
                audio = request.call_args.args[1]["messages"][0]["content"][1]["input_audio"]
                self.assertEqual(audio, {"data": "YXVkaW8=", "format": "wav"})

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
        with patch.object(provider, "request", side_effect=[{"data": rows}, {"data": specialists}]) as request:
            self.assertEqual(provider.models(True), ["audio", "stt"])
            self.assertEqual(provider.models(False), ["audio", "text"])
            self.assertEqual(request.call_args.args[0], "/models?output_modalities=transcription")
            self.assertEqual(request.call_count, 2)

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
