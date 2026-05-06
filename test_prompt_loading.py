import importlib.util
import pathlib
import sys
import types
import unittest


def load_memomaker_module():
    root = pathlib.Path(__file__).resolve().parent
    module_path = root / "memomaker-ui.pyw"

    sys.modules.setdefault("customtkinter", types.SimpleNamespace(CTk=object))
    sys.modules.setdefault("google", types.ModuleType("google"))
    sys.modules.setdefault(
        "google.generativeai",
        types.SimpleNamespace(configure=lambda **kwargs: None),
    )
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

    def test_recording_functionality_is_not_present(self):
        source = pathlib.Path(__file__).resolve().with_name("memomaker-ui.pyw").read_text(encoding="utf-8")

        removed_recording_hooks = [
            "AudioRecorder",
            "Start Recording",
            "Stop Recording",
            "Ready to record",
            "toggle_recording",
            "on_recording_complete",
            "sounddevice",
            "lameenc",
            "wavfile",
            "RECORDINGS_FOLDER",
            '"recordings"',
        ]

        for hook in removed_recording_hooks:
            with self.subTest(hook=hook):
                self.assertNotIn(hook, source)


if __name__ == "__main__":
    unittest.main()
