"""Visual and interaction checks using installed Microsoft Edge."""
from pathlib import Path
from playwright.sync_api import sync_playwright

SIZES = [(1536, 1024), (1200, 800), (960, 720), (390, 844)]


def check_controls(page, container, selectors):
    """Check geometry inside a control group, even below the mobile fold."""
    parent = page.locator(container).bounding_box()
    boxes = []
    for selector in selectors:
        for control in page.locator(selector).all():
            assert control.is_visible(), (selector, "hidden", page.viewport_size)
            box = control.bounding_box()
            assert box and box["width"] > 0 and box["height"] > 0, selector
            assert box["x"] >= parent["x"] - 1 and box["y"] >= parent["y"] - 1, (selector, "outside", container)
            assert box["x"] + box["width"] <= parent["x"] + parent["width"] + 1, (selector, "clipped horizontally", container)
            assert box["y"] + box["height"] <= parent["y"] + parent["height"] + 1, (selector, "clipped vertically", container)
            for other_selector, other in boxes:
                overlap_x = min(box["x"] + box["width"], other["x"] + other["width"]) - max(box["x"], other["x"])
                overlap_y = min(box["y"] + box["height"], other["y"] + other["height"]) - max(box["y"], other["y"])
                assert overlap_x <= 1 or overlap_y <= 1, (selector, "overlaps", other_selector, page.viewport_size)
            boxes.append((selector, box))


def check_layout(page, speakers=False, progress=False):
    for width, height in SIZES:
        page.set_viewport_size({"width": width, "height": height})
        assert page.evaluate("document.body.scrollWidth <= innerWidth"), (width, "horizontal overflow")
        check_controls(page, "header", [".brand", "#settings-open"])
        check_controls(page, ".workspace-toolbar", [".output-tabs button", ".output-actions button:not([hidden])"])
        check_controls(page, ".setup", [".setup-scroll", "#generate"])
        if width > 750:
            box = page.locator("#generate").bounding_box()
            assert box["y"] + box["height"] <= height, (width, "Generate below viewport")
        if speakers:
            check_controls(page, "#speakers-panel", ["#speakers-panel h2", "#speakers-close", ".speaker-row input", "#speaker-add", "#speakers-form button[type=submit]"])
            check_controls(page, ".workspace", ["#speakers-panel", "#document"])
        if progress:
            check_controls(page, "footer", [".status-dot", "#status", "#job-progress", "#activity-toggle"])
            check_controls(page, "#job-progress", ["#progress", "#progress-label", "#elapsed"])
    page.set_viewport_size({"width": 1536, "height": 1024})


with sync_playwright() as p:
    browser = p.chromium.launch(channel="msedge")
    page = browser.new_page(viewport={"width": 1536, "height": 1024})
    errors = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    page.goto(Path("ui/index.html").resolve().as_uri() + "?example")
    page.evaluate("document.fonts.ready")
    page.screenshot(path="ui-reference-check.png")
    check_layout(page)
    page.locator("#settings-open").click()
    assert page.locator("#settings").is_visible()
    page.locator(".stage select").first.select_option("OpenRouter")
    assert page.locator(".stage input").first.input_value() == ""
    page.locator('.stage input').first.fill('microsoft/mai-transcribe-2')
    assert '15 minutes' in page.locator('.stage .audio-limits').inner_text()
    page.locator('.stage input').first.fill('openai/whisper-1')
    assert '25 MB audio-file limit' in page.locator('.stage .audio-limits').inner_text()
    page.locator('.stage input').first.fill('unlisted-model')
    assert 'not in the checked audio catalog' in page.locator('.stage .audio-limits').inner_text()
    assert page.evaluate("Object.keys(audioModelCatalog).every(m => audioLimits('OpenRouter',m).notes.length >= 2)")
    page.locator("#settings-close").click()
    assert page.locator("[data-method='inline']").get_attribute("class") == "active"
    page.evaluate("""window.calls=[];window.pywebview={api:{
        load_output:async kind=>({text:kind==='memo'?'# Loaded memo':'Loaded transcript',name:kind+'.txt'}),
        save_prompts:async (...args)=>{calls.push(['save',...args]);return args[1];},
        copy:async (...args)=>{calls.push(['copy',...args]);return true;},
        generate:async (...args)=>{calls.push(['generate',...args]);return true;}
    }}""")
    page.locator("[data-output='transcript']").click()
    assert page.locator("#load-output").get_attribute("title") == "Load transcript"
    page.locator("#load-output").click()
    assert page.locator("#preview").inner_text() == "Loaded transcript"
    assert page.locator("#source").input_value() == "transcript"
    assert page.locator("#methods").is_hidden()
    page.locator("#generate").click()
    assert page.evaluate("calls.at(-1).slice(-3)") == ["inline", "Loaded transcript", False]
    assert page.locator("#load-output").is_disabled()
    page.evaluate("receive('done','Completed')")
    page.locator("#source").select_option("transcript-only")
    assert page.locator("#generate").inner_text() == "Generate transcript"
    page.locator("#generate").click()
    assert page.evaluate("calls.at(-1).slice(-3)") == ["inline", None, True]
    page.evaluate("receive('done','Completed')")
    page.locator("[data-output='memo']").click()
    page.locator("#load-output").click()
    assert page.locator("#preview h1").inner_text() == "Loaded memo"
    page.locator("#source").select_option("audio")
    assert page.locator("#methods").is_visible()
    page.locator("[data-prompt='1']").click()
    page.locator("#prompt-editor").fill("Write a concise article.")
    page.locator("[data-prompt='0']").click()
    page.locator("[data-prompt='1']").click()
    assert page.locator("#prompt-editor").input_value() == "Write a concise article."
    page.locator("#save-prompts").click()
    assert page.evaluate("calls.at(-1)[0]") == "save"
    assert page.evaluate("calls.at(-1)[2][1]") == "Write a concise article."
    page.evaluate("receive('memo', '# Real output\\n\\n**Bold text** <img src=x onerror=alert(1)>')")
    assert page.locator("#preview h1").inner_text() == "Real output"
    assert page.locator("#preview [onerror]").count() == 0
    page.locator("#edit").click()
    page.locator("#output-editor").fill("# Edited output")
    page.locator("#edit").click()
    assert page.locator("#preview h1").inner_text() == "Edited output"
    page.evaluate("receive('transcript', '[00:00:01] Speaker 1: Hello\\n[00:00:04] Speaker 10: Welcome')")
    page.evaluate("receive('memo', '# Meeting\\n\\n**Speaker 1** met Speaker 10.\\n\\n- A decision')")
    page.locator('#speakers-toggle').click()
    assert page.locator('#speakers-panel').is_visible()
    page.locator('.speaker-row').first.locator('input').nth(1).fill('Anna')
    check_layout(page, speakers=True)
    page.screenshot(path='ui-speakers-check.png')
    page.locator('#speakers-form button[type=submit]').click()
    assert 'Anna met Speaker 10.' in page.locator('#preview').inner_text()
    assert page.evaluate('state.outputs.transcript') == '[00:00:01] Anna: Hello\n[00:00:04] Speaker 10: Welcome'
    page.locator('#speakers-undo').click()
    assert 'Speaker 1 met Speaker 10.' in page.locator('#preview').inner_text()
    assert page.evaluate("renameSpeakers('Ann Anna Speaker 1 Speaker 10',new Map([['Ann','Liis'],['Speaker 1','Speaker 10'],['Speaker 10','Speaker 1']]))") == 'Liis Anna Speaker 10 Speaker 1'
    page.locator('#copy').click()
    copied = page.evaluate('calls.at(-1)')
    assert copied[0] == 'copy' and '# Meeting' not in copied[1]
    assert '<h1' in copied[2] and '<strong>Speaker 1</strong>' in copied[2] and '<ul' in copied[2]
    selected = page.evaluate("""() => {
        const node=document.querySelector('#preview strong').firstChild;
        const range=document.createRange();range.selectNodeContents(node);
        const selection=getSelection();selection.removeAllRanges();selection.addRange(range);
        const clipboard=new DataTransfer();
        document.querySelector('#preview').dispatchEvent(new ClipboardEvent('copy',{clipboardData:clipboard,bubbles:true,cancelable:true}));
        return [clipboard.getData('text/plain'),clipboard.getData('text/html')];
    }""")
    assert selected[0] == 'Speaker 1' and '<strong>Speaker 1</strong>' in selected[1]
    page.locator("#speakers-toggle").click()
    page.evaluate("busy(true); receive('progress',{completed:2,total:4,label:'Writing memo'})")
    assert page.locator('#progress').get_attribute('value') == '2'
    assert page.locator('#progress-label').inner_text() == '2/4 stages complete'
    assert page.locator('#elapsed').inner_text().endswith('elapsed')
    assert page.locator('#speakers-toggle').is_disabled()
    assert page.locator("#speakers-panel").is_hidden()
    check_layout(page, progress=True)
    page.screenshot(path='ui-workspace-check.png')
    page.evaluate("receive('done','Failed: Writing failed')")
    assert page.locator('#progress').get_attribute('value') == '2'
    assert 'failed' in page.locator('#job-progress').get_attribute('class')
    check_layout(page, progress=True)
    page.evaluate("busy(true);receive('progress',{completed:4,total:4,label:'Completed'});receive('done','Completed')")
    assert page.locator('#progress').get_attribute('value') == '4'
    page.locator("#activity-toggle").click()
    assert page.locator("#activity").is_visible()
    assert not errors, errors
    browser.close()
    print("Viewport, loading, prompt, speaker rename/undo, rich copy/selection, progress/failure, and workspace checks passed.")
