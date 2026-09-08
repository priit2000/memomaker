"""Embedded desktop view; provider calls remain in Python."""
import json
import os
import re
import tempfile
import threading
from pathlib import Path
from providers import KEY_NAMES, create_provider
from workspace_ui import CONFIG, run_pipeline


def clipboard_html(fragment):
    """Windows CF_HTML offsets count UTF-8 bytes, not Unicode characters."""
    header = "Version:1.0\r\nStartHTML:%010d\r\nEndHTML:%010d\r\nStartFragment:%010d\r\nEndFragment:%010d\r\n"
    prefix = '<html><head><meta charset="utf-8"></head><body><!--StartFragment-->'
    suffix = '<!--EndFragment--></body></html>'
    start_html = len((header % (0, 0, 0, 0)).encode("utf-8"))
    start_fragment = start_html + len(prefix.encode("utf-8"))
    end_fragment = start_fragment + len(fragment.encode("utf-8"))
    end_html = end_fragment + len(suffix.encode("utf-8"))
    return header % (start_html, end_html, start_fragment, end_fragment) + prefix + fragment + suffix


class DesktopAPI:
    def __init__(self, core):
        self._core = core
        self._path = None
        self._window = None
        self._lock = threading.Lock()
        try:
            self._settings = json.loads(CONFIG.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            self._settings = {}

    def initialize(self):
        settings = dict(self._settings)
        for key in KEY_NAMES.values():
            settings[key] = os.environ.get(key, "")
            if not settings[key] and os.name == "nt":
                import winreg
                try:
                    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment") as registry:
                        settings[key] = winreg.QueryValueEx(registry, key)[0]
                except OSError:
                    pass
        self._settings.update(settings)
        profile = self._core.DEFAULT_LANGUAGE
        return {"settings": settings, "profiles": list(self._core.AVAILABLE_LANGUAGES),
                "profile": profile, "prompts": list(self._core.read_prompts_from_file(profile)),
                "stages": settings.get("stages", [["Google Gemini", self._core.MODEL_NAME]] * 2)}

    def profile(self, name):
        prompts = self._core.read_prompts_from_file(name)
        return list(prompts) if all(prompts) else {"error": "Could not load prompt profile."}

    def save_prompts(self, name, prompts):
        if name not in self._core.AVAILABLE_LANGUAGES or len(prompts) != 2:
            return {"error": "Select an existing prompt profile."}
        for prompt in prompts:
            valid, reason = self._core.validate_prompt_input(prompt)
            if not valid:
                return {"error": reason}
        if re.search(r"(?m)^#\s+", prompts[0]):
            return {"error": "Use ## for headings inside the transcription prompt."}
        temporary = None
        try:
            path = Path(self._core.AVAILABLE_LANGUAGES[name]).resolve()
            original = path.read_bytes()
            content = original.decode("utf-8-sig")
            headings = list(re.finditer(r"(?m)^#\s+[^\r\n]+", content))
            if len(headings) < 2:
                return {"error": "The profile must contain two top-level headings."}
            if not self._window.create_confirmation_dialog("Save prompts", "Replace both prompt sections in %s?" % path.name):
                return False
            if path.read_bytes() != original:
                return {"error": "The profile changed on disk. Reload it before saving."}
            updated = (content[:headings[0].end()] + "\n" + prompts[0].strip() + "\n\n" +
                       headings[1].group() + "\n" + prompts[1].strip() + "\n")
            with tempfile.NamedTemporaryFile(dir=path.parent, delete=False, suffix=".tmp") as handle:
                temporary = Path(handle.name)
                handle.write(updated.encode("utf-8-sig" if original.startswith(b"\xef\xbb\xbf") else "utf-8"))
            os.replace(temporary, path)
            return list(self._core.read_prompts_from_file(name))
        except (OSError, UnicodeError) as exc:
            return {"error": str(exc)}
        finally:
            if temporary and temporary.exists():
                temporary.unlink()

    def load_output(self, kind):
        if kind not in ("memo", "transcript"):
            return {"error": "Choose Memo or Transcript."}
        import webview
        paths = self._window.create_file_dialog(
            webview.FileDialog.OPEN, directory=str(Path(self._core.OUTPUT_FOLDER).resolve()),
            file_types=("Text and Markdown (*.txt;*.md)",))
        if not paths:
            return None
        try:
            path = Path(paths[0])
            if path.stat().st_size > 10 * 1024 * 1024:
                return {"error": "Select a text file smaller than 10 MB."}
            text = path.read_text(encoding="utf-8-sig")
            if not text.strip():
                return {"error": "The selected file is empty."}
            return {"text": text, "name": path.name}
        except (OSError, UnicodeError) as exc:
            return {"error": str(exc)}

    def select_file(self, path):
        valid, reason = self._core.validate_audio_file(path)
        if not valid:
            return {"error": reason}
        self._path = path
        return {"name": Path(path).name, "size": "%.1f MB" % (Path(path).stat().st_size / 1048576)}

    def browse(self):
        import webview
        paths = self._window.create_file_dialog(webview.FileDialog.OPEN, file_types=("Audio files (*.mp3;*.wav;*.m4a;*.ogg;*.flac;*.aac)",))
        return self.select_file(paths[0]) if paths else None

    def clear_file(self):
        self._path = None
        return True

    def models(self, name, audio, settings):
        try:
            return create_provider(name, settings).models(audio)
        except Exception as exc:
            return {"error": str(exc)}

    def save_settings(self, settings, remember, stages):
        try:
            settings["stages"] = stages
            CONFIG.parent.mkdir(parents=True, exist_ok=True)
            CONFIG.write_text(json.dumps({k: v for k, v in settings.items() if k not in KEY_NAMES.values()}), encoding="utf-8")
            if remember and os.name == "nt":
                import winreg
                with winreg.CreateKey(winreg.HKEY_CURRENT_USER, "Environment") as registry:
                    for key in KEY_NAMES.values():
                        winreg.SetValueEx(registry, key, 0, winreg.REG_SZ, settings.get(key, ""))
                        os.environ[key] = settings.get(key, "")
            self._settings = settings
            return True
        except OSError as exc:
            return {"error": str(exc)}

    def emit(self, kind, value):
        self._window.evaluate_js("window.receive(%s,%s)" % (json.dumps(kind), json.dumps(value)))

    def generate(self, stages, prompts, method, transcript=None):
        if transcript is None and not self._path:
            return {"error": "Select an audio file first."}
        if not self._lock.acquire(blocking=False):
            return {"error": "Processing is already running."}
        path, settings = self._path, dict(self._settings)
        def work():
            try:
                run_pipeline(self._core, path, stages, settings, prompts, method, self.emit, transcript)
                self.emit("done", "Completed")
            except Exception as exc:
                self.emit("done", "Failed: " + str(exc))
            finally:
                self._lock.release()
        threading.Thread(target=work, daemon=True).start()
        return True

    def copy(self, text, html=None):
        # Clipboard calls are marshalled to the WinForms UI thread by pywebview.
        from System import Action
        from System.Windows.Forms import Clipboard, DataObject, DataFormats
        def set_clipboard():
            data = DataObject()
            data.SetData(DataFormats.UnicodeText, True, text)
            if html:
                data.SetData(DataFormats.Html, clipboard_html(html))
            Clipboard.SetDataObject(data, True)
        self._window.native.Invoke(Action(set_clipboard))
        return True

    def open_link(self, url):
        from urllib.parse import urlparse
        import webbrowser
        if urlparse(url).scheme in ("https", "http"):
            webbrowser.open(url)
        return True

    def export(self, kind, text):
        import webview
        path = self._window.create_file_dialog(webview.FileDialog.SAVE, save_filename=kind + (".md" if kind == "memo" else ".txt"))
        if not path:
            return False
        if isinstance(path, (tuple, list)):
            path = path[0]
        try:
            Path(path).write_text(text, encoding="utf-8")
            return True
        except OSError as exc:
            return {"error": str(exc)}


class WebWorkspace:
    def __init__(self, core):
        self._core = core

    def mainloop(self):
        import webview
        api = DesktopAPI(self._core)
        api._window = webview.create_window("MemoMaker", str(Path(__file__).parent / "ui" / "index.html"),
                                           js_api=api, width=1536, height=1060, min_size=(960, 720),
                                           background_color="#fafbfa")
        def dropped(event):
            files = event.get("dataTransfer", {}).get("files", [])
            if files:
                result = api.select_file(files[0].get("pywebviewFullPath", ""))
                if "error" in result:
                    api.emit("status", result["error"])
                else:
                    api._window.evaluate_js("fileChosen(%s)" % json.dumps(result))
        def loaded():
            api._window.dom.get_element("#drop-zone").events.drop += dropped
        api._window.events.loaded += loaded
        webview.start(gui="edgechromium")
