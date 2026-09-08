// Workspace-only changes never overwrite source files; Export persists edits.
let speakerUndo = null;
let renamedSpeakers = [];
let startedAt = 0;
let elapsedTimer = null;

function speakerRow(name = '') {
    const row = document.createElement('div');
    row.className = 'speaker-row';
    const previous = document.createElement('input');
    previous.placeholder = 'Current name or label';
    previous.setAttribute('aria-label', 'Current speaker name');
    previous.value = name;
    const next = document.createElement('input');
    next.placeholder = 'New name';
    next.setAttribute('aria-label', 'New speaker name');
    previous.maxLength = next.maxLength = 100;
    row.append(previous, next);
    $('speaker-rows').append(row);
}

function detectedSpeakers() {
    const text = Object.values(state.outputs).join('\n');
    const names = new Set(renamedSpeakers.filter(name => text.includes(name)));
    for (const match of text.matchAll(/\b(?:Speaker|SPEAKER|Kõneleja|KÕNELEJA|Esineja)[ _-]*(?:\d+|[A-Z])\b/gu)) names.add(match[0]);
    // Named turns such as [00:01:20] **Anna:** are common in saved transcripts.
    for (const match of state.outputs.transcript.matchAll(/^\s*\[\d{1,2}:\d{2}(?::\d{2})?\]\s*\*{0,2}([^:\n*]{1,80})\*{0,2}:/gm)) names.add(match[1].trim());
    return [...names].slice(0, 100);
}

function updateSpeakerControls() {
    $('speakers-toggle').disabled = state.busy || !Object.values(state.outputs).some(Boolean);
    $('speakers-undo').hidden = !speakerUndo;
    $('speakers-undo').disabled = state.busy;
}

const renderDocument = render;
render = function () { renderDocument(); updateSpeakerControls(); };
const saveDocumentEdit = saveEdit;
saveEdit = function () {
    const changed = state.editing && state.outputs[state.output] !== $('output-editor').value;
    saveDocumentEdit();
    if (changed) { speakerUndo = null; updateSpeakerControls(); }
};

$('speakers-toggle').onclick = () => {
    saveEdit(); render();
    $('speaker-rows').replaceChildren();
    const labels = detectedSpeakers();
    (labels.length ? labels : ['']).forEach(speakerRow);
    $('speaker-status').textContent = '';
    $('speakers-panel').hidden = false;
    $('speaker-rows').querySelector('input').focus();
};
$('speakers-close').onclick = () => $('speakers-panel').hidden = true;
$('speaker-add').onclick = () => speakerRow();

function renameSpeakers(text, mapping) {
    const escaped = [...mapping.keys()].sort((a, b) => b.length - a.length)
        .map(name => name.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'));
    if (!escaped.length) return text;
    // One pass prevents swaps and overlapping names from cascading.
    const pattern = new RegExp('(?<![\\p{L}\\p{N}_])(?:' + escaped.join('|') + ')(?![\\p{L}\\p{N}_])', 'gu');
    return text.replace(pattern, name => mapping.get(name));
}

$('speakers-form').onsubmit = event => {
    event.preventDefault();
    if (state.busy) return;
    saveEdit();
    const mapping = new Map();
    for (const row of $('speaker-rows').children) {
        const [previous, next] = [...row.querySelectorAll('input')].map(input => input.value.trim());
        if (!next) continue;
        if (!previous || mapping.has(previous)) {
            $('speaker-status').textContent = 'Enter a unique current name for each replacement.';
            return;
        }
        if (/[\n\r<>*`\[\]#|]/.test(next)) {
            $('speaker-status').textContent = 'Use plain names without Markdown or HTML markup.';
            return;
        }
        mapping.set(previous, next);
    }
    const updated = Object.fromEntries(Object.entries(state.outputs).map(([kind, text]) => [kind, renameSpeakers(text, mapping)]));
    if (Object.keys(updated).every(kind => updated[kind] === state.outputs[kind])) {
        $('speaker-status').textContent = 'No matching names changed.';
        return;
    }
    speakerUndo = {outputs: {...state.outputs}, names: [...renamedSpeakers]};
    state.outputs = updated;
    renamedSpeakers = [...mapping.values()];
    $('speakers-panel').hidden = true;
    render();
    status('Names updated in transcript and memo. Export to save.');
};
$('speakers-undo').onclick = () => {
    if (!speakerUndo || state.busy) return;
    state.outputs = speakerUndo.outputs;
    renamedSpeakers = speakerUndo.names;
    speakerUndo = null;
    state.editing = false;
    render();
    status('Speaker name changes undone');
};

function tickElapsed() {
    const seconds = Math.floor((performance.now() - startedAt) / 1000);
    $('elapsed').textContent = Math.floor(seconds / 60) + ':' + String(seconds % 60).padStart(2, '0') + ' elapsed';
}
function showProgress(value) {
    $('job-progress').hidden = false;
    $('progress').hidden = false;
    $('progress').max = value.total;
    $('progress').value = value.completed;
    const label = value.completed + '/' + value.total + ' stages complete';
    $('progress-label').textContent = label;
    $('progress').setAttribute('aria-valuetext', label + ': ' + value.label);
    status(value.label);
}
const setBusy = busy;
busy = function (value) {
    setBusy(value);
    if (value) {
        $('speakers-panel').hidden = true;
        startedAt = performance.now();
        clearInterval(elapsedTimer);
        tickElapsed();
        elapsedTimer = setInterval(tickElapsed, 1000);
        $('job-progress').classList.remove('failed');
        showProgress({completed: 0, total: $('source').value === 'transcript' ? 3 : 4, label: 'Validating inputs and models'});
    } else {
        clearInterval(elapsedTimer);
        $('progress').hidden = false;
        $('job-progress').classList.toggle('failed', $('progress').value < $('progress').max);
    }
    updateSpeakerControls();
};
const receiveResult = window.receive;
window.receive = (kind, value) => {
    if (kind === 'progress') { showProgress(value); return; }
    if (kind === 'memo' || kind === 'transcript') {
        speakerUndo = null;
        renamedSpeakers = [];
        $('speakers-panel').hidden = true;
    }
    receiveResult(kind, value);
};

function richFragment(html) {
    const container = document.createElement('div');
    container.innerHTML = DOMPurify.sanitize(html);
    container.style.cssText = 'font-family:Arial,sans-serif;font-size:11pt;color:#101727;line-height:1.5;';
    const styles = {
        h1: 'font-size:22pt;font-weight:bold;margin:16pt 0 10pt;',
        h2: 'font-size:16pt;font-weight:bold;margin:14pt 0 8pt;',
        h3: 'font-size:13pt;font-weight:bold;margin:12pt 0 6pt;',
        p: 'margin:0 0 10pt;', ul: 'list-style-type:disc;padding-left:24pt;',
        ol: 'list-style-type:decimal;padding-left:24pt;', li: 'margin:4pt 0;',
        table: 'border-collapse:collapse;', th: 'border:1px solid #999;padding:6pt;font-weight:bold;',
        td: 'border:1px solid #999;padding:6pt;', pre: 'white-space:pre-wrap;font-family:Consolas,monospace;',
        blockquote: 'border-left:3px solid #999;padding-left:12pt;'
    };
    Object.entries(styles).forEach(([tag, style]) => container.querySelectorAll(tag).forEach(node => node.style.cssText = style));
    return container.outerHTML;
}

$('copy').title = 'Copy with formatting';
$('copy').onclick = async () => {
    saveEdit(); render();
    const preview = $('preview');
    let html = preview.innerHTML;
    if (state.output === 'transcript') {
        const pre = document.createElement('pre');
        pre.textContent = state.outputs.transcript;
        html = pre.outerHTML;
    }
    if (await api('copy', preview.innerText, richFragment(html))) status('Copied with formatting');
};
// Ctrl+C retains rich text for a selection, while editor copying stays raw text.
$('preview').addEventListener('copy', event => {
    const selection = window.getSelection();
    if (!selection.rangeCount || selection.isCollapsed || !event.clipboardData) return;
    const range = selection.getRangeAt(0);
    if (!$('preview').contains(range.commonAncestorContainer)) return;
    const fragment = document.createElement(state.output === 'transcript' ? 'pre' : 'div');
    let content = range.cloneContents();
    let ancestor = range.commonAncestorContainer.nodeType === Node.ELEMENT_NODE ? range.commonAncestorContainer : range.commonAncestorContainer.parentElement;
    while (ancestor && ancestor !== $('preview')) {
        const wrapper = ancestor.cloneNode(false);
        wrapper.removeAttribute('id');
        wrapper.append(content);
        content = wrapper;
        ancestor = ancestor.parentElement;
    }
    fragment.append(content);
    event.clipboardData.setData('text/html', richFragment(fragment.outerHTML));
    event.clipboardData.setData('text/plain', selection.toString());
    event.preventDefault();
});
updateSpeakerControls();
