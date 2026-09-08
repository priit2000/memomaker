"""Local desktop smoke check without API calls or stored credentials."""
import runpy
from pathlib import Path
from types import SimpleNamespace
import webview
from desktop_view import DesktopAPI

core = SimpleNamespace(**runpy.run_path("memomaker-ui.pyw", run_name="smoke"))
api = DesktopAPI(core)
api.initialize = lambda: {"settings": {}, "profiles": ["EN"], "profile": "EN",
                          "prompts": ["Transcribe the audio.", "Write the memo."],
                          "stages": [["Google Gemini", core.MODEL_NAME]] * 2}
api._window = webview.create_window("MemoMaker QA", str(Path("ui/index.html").resolve()), js_api=api, width=1200, height=850)


failures = []
completed = False

def check():
    global completed
    try:
        import time
        time.sleep(1)
        assert api._window.evaluate_js("document.getElementById('profile').value") == "EN"
        from System import Action
        from System.Windows.Forms import Clipboard, DataFormats
        previous = []
        api._window.native.Invoke(Action(lambda: previous.append(Clipboard.GetDataObject())))
        try:
            assert api.copy("MemoMaker J\u00fcri", '<div><b>MemoMaker J\u00fcri</b></div>')
            copied = []
            api._window.native.Invoke(Action(lambda: copied.extend([Clipboard.GetText(), str(Clipboard.GetData(DataFormats.Html))])))
            assert copied[0] == 'MemoMaker J\u00fcri'
            assert '<b>MemoMaker J\u00fcri</b>' in copied[1]
            assert 'StartFragment:' in copied[1]
        finally:
            if previous[0] is not None:
                api._window.native.Invoke(Action(lambda: Clipboard.SetDataObject(previous[0], True)))
        api.emit("memo", "# Smoke test\n\nRendered output.")
        assert "Smoke test" in api._window.evaluate_js("document.getElementById('preview').textContent")
        completed = True
    except BaseException as error:
        failures.append(error)
    finally:
        api._window.destroy()


api._window.events.loaded += check
webview.start(gui="edgechromium")

if failures:
    raise failures[0]
if not completed:
    raise RuntimeError("Desktop smoke check closed before completing")
print("Desktop bridge, clipboard, and Markdown rendering passed.")
