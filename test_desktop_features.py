import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

from desktop_view import DesktopAPI, clipboard_html
from test_prompt_loading import load_memomaker_module


class DesktopFeaturesTests(unittest.TestCase):
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


if __name__ == "__main__":
    unittest.main()
