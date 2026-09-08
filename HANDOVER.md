# MemoMaker Handover

State recorded on 2026-09-08. This is a working-tree handover, not a release note. Read AGENTS.md and README.md before making changes, then inspect the current Git diff: the working tree is the source of truth.

## Start Here

The repository is at `C:\Users\priit\OneDrive\projektid\amperly\ai-tools-coding-chatgpt\memomaker`. Use PowerShell 5.1-compatible commands and run the app from this directory because prompt discovery and output paths depend on the current working directory.

The current branch is `master`. HEAD is `04a8a28` (`Remove recording UI and support prompt profiles`). The provider expansion, desktop UI rebuild, and subsequent features described below are uncommitted. No commit or push was performed for those changes.

The latest user request was to add this handover. There is no authorized new application feature pending. Previously mentioned improvement ideas are proposals only.

## User Expectations

The user expects close visual fidelity to the supplied light MemoMaker reference, not a loose restyling. Preserve the white workspace, restrained teal accents, two-panel composition, underline tabs, document preview, and slim status footer. Functional controls may differ from the reference.

The user requested subagents for all tasks. No subagent tools were available during this work; this was disclosed, and implementation continued directly. Use real subagents when available. Do not substitute unrelated user-visible tasks or claim delegation that did not happen.

The user explicitly requested that CLAUDE.md be an exact copy of AGENTS.md. That copy was made and verified with matching SHA-256 hashes. Keep them synchronized when changing shared guidance. CLAUDE.md is currently gitignored.

Do not revert existing user edits to prompt files or generated content. Do not implement code for explanation-only requests. Preserve the shared repository instruction requiring an explicit request before implementation.

## Implemented State

The application no longer uses the previous CustomTkinter workspace. The desktop entry point is `memomaker-ui.pyw`, which hosts local HTML through pywebview and Edge WebView2. No development server is required. Close and reopen the app to load code/UI changes.

| File | Responsibility |
| --- | --- |
| `memomaker-ui.pyw` | Startup, profile discovery, validation, initial defaults |
| `providers.py` | Google, OpenRouter, and custom API transports |
| `workspace_ui.py` | Shared pipeline, CLI, settings location |
| `desktop_view.py` | Desktop bridge, dialogs, clipboard, loading, prompt saving |
| `ui/index.html`, `ui/style.css`, `ui/app.js` | Main interface and state |
| `ui/workspace-tools.js` | Speaker editing, Undo, stage progress, rich copying |
| `requirements.txt` | Runtime Python dependencies |

Local fonts, Lucide icons, Marked, DOMPurify, and their licenses are bundled under `ui/`. Ship these assets with the app. The initial sample document is explicitly marked EXAMPLE MEMO; Copy and Export are disabled until actual output is loaded or generated. The `?example` query parameter is a visual-test fixture, not the desktop startup mode.

### Providers

Transcription and writing models are selected independently in API settings. Google retains Inline, Auto, and Upload. Inline is the default in the GUI, CLI, and provider methods. Auto switches to upload at 20 MB; the active cutoff lives in `providers.py`, not the legacy entry-point constant.

OpenRouter model discovery merges the normal catalog and `models?output_modalities=transcription`. Audio-capable chat models use chat completions. Dedicated speech-to-text models use base64 JSON at `/audio/transcriptions`. Transcription-only models cannot be selected for writing.

`microsoft/mai-transcribe-2` requests verbose segments, word timestamps, and Azure diarization. The app renders returned segments as timestamped speaker paragraphs. Other specialists use default JSON responses and retain segments when returned. Dedicated transcription models do not consume the Markdown transcription prompt; the writing prompt still applies.

Custom APIs support chat audio or multipart transcription requests and chat-completion writing. A configurable URL supports those protocols, not every arbitrary vendor API. Google file uploads are polled until ready, with remote cleanup attempted afterward.

### Saved Work and Prompts

The folder icon loads a `.txt` or `.md` file into the active Transcript or Memo tab. Loading a transcript selects Workspace transcript as the processing source. Generation then skips audio and transcription credentials and uses only the writing model. Selecting Audio file restores the audio path.

Generation saves timestamped transcript and memo files under `outputs/`. The transcript survives writing failure. Reusing a loaded transcript saves a new transcript copy alongside the memo. Loaded source files are not overwritten automatically.

All `transcription-prompt-*.md` profiles are discovered using the full filename suffix, including EN-ARTICLE. The first two top-level headings delimit the prompts; the writing section may include later headings. Saving persists both prompt tabs after confirmation, preserves section headings, checks for external changes during confirmation, and atomically replaces the file. Reset uses the latest loaded/saved defaults.

### Workspace Tools

Speakers opens a right-panel name editor with detected labels and manual replacement rows. Apply performs case-sensitive, boundary-aware replacements in both workspace documents in one pass. It supports name swaps without cascading replacements and provides Undo for the latest rename. It does not infer identities or regenerate prose. Export each changed document to persist it.

Progress events carry completed stage count, total stages, and a label. Audio processing has four stages: validation, transcription, writing, and saving. Transcript reuse has three. The footer also shows elapsed time. Progress does not advance artificially while waiting for a provider and remains incomplete on failure.

Copy writes Windows CF_HTML and Unicode plain text. UTF-8 byte offsets are generated by `clipboard_html()` in `desktop_view.py`. Rich preview selections also retain HTML on Ctrl+C, including ancestor formatting. Raw-editor copying remains source text. Destination applications determine final paste appearance.

## Verification Already Performed

The following checks passed after the latest application changes. Subsequent changes were documentation-only. These results are historical; rerun after implementation changes.

- `python -m unittest discover -v`: 21 tests passed.
- `python verify_ui.py`: responsive layouts, saved-file loading, transcript reuse, prompt saving, speaker replacement/Undo, rich copy and selection, progress/failure, and existing workspace controls passed.
- `python verify_desktop.py`: native desktop bridge, HTML/Unicode clipboard content, and Markdown rendering passed. The test restores prior clipboard content when available.
- Python compilation passed for the entry point and backend modules.
- A read-only query against the live OpenRouter catalog confirmed MAI-Transcribe 2 appears in transcription models and not writing models.

No paid transcription or memo-generation request was made to verify the new specialist path. Mock tests and catalog checks do not prove end-to-end behavior for all models. Rich clipboard formats were inspected natively; pasting into every third-party editor was not tested.

The local environment has pywebview and Python Playwright installed. Browser QA uses installed Microsoft Edge via `channel="msedge"`; bundled Playwright Chromium was not required.

```powershell
python -m pip install -r requirements.txt
python -m unittest discover -v
python -m py_compile .\memomaker-ui.pyw .\providers.py .\workspace_ui.py .\desktop_view.py
python -m pip install playwright
python .\verify_ui.py
python .\verify_desktop.py
python .\memomaker-ui.pyw
```

The desktop smoke test opens and closes a temporary window. It does not call paid APIs. The browser test writes `ui-reference-check.png`, `ui-speakers-check.png`, and `ui-workspace-check.png`; those screenshots contain test fixtures, not actual user results.

## Git and Data Safety

At handover, tracked modifications include `.gitignore`, README.md, `memomaker-ui.pyw`, and the English and Estonian prompt files. New backend modules, UI assets, requirements, tests, agent guidance, and QA scripts are untracked. `transcription-prompt-et-article.md` is also untracked. Review individual diffs and ownership before staging anything.

The prompt edits predate or occurred during the work and include user changes. Documentation updates did not edit prompt content. Preserve those changes rather than replacing them with older versions.

`outputs/` contains many existing generated memos and other user documents and is currently not ignored. The three QA screenshots are also untracked and not ignored. Do not run `git add .` blindly.

The user asked which files should be ignored; the answer recommended ignoring `/outputs/`, generated QA screenshots, and `.env.*` while retaining `.env.example`. Those ignore additions have not been implemented. Existing broad `*.txt` and `*.html` rules have exceptions for `requirements.txt` and `ui/index.html`. CLAUDE.md remains ignored. Do not assume ignore policy has already been fixed.

Keep application source, tests, prompt profiles, runtime assets, and third-party licenses versioned. Generated documents, private audio, credentials, and QA screenshots are not application source. This handover contains no API keys.

## Known Limitations

There is no autosaved workspace or crash recovery. Manual edits and speaker changes require Export. Speaker Undo is invalidated by subsequent document editing or replacement. Loading independently chosen transcript and memo files does not establish that they belong to the same session.

Long audio is not chunked automatically. Provider-specific file-size, format, context, and timeout limits may be stricter than the app's 100 MB validation limit. Specialist timestamps and speaker metadata vary by model/provider. There is no automatic provider fallback, reliable remaining-time estimate, or cancellation workflow.

Google discovery lists generation-capable models rather than independently verifying audio support. Custom catalogs lack consistent capability metadata. The configurable API layer is not universal compatibility. Avoid promising all models work without checking their actual protocol and capabilities.

Remembered API keys live in the Windows user environment, not an encrypted vault. Non-key configuration is stored in `%APPDATA%/MemoMaker/settings.json`. Do not expose credentials in logs, tests, or screenshots.

Prompt discovery happens at startup in the current working directory. Loaded text must be UTF-8, optionally with a BOM, nonempty, and no larger than 10 MB. Prompt validation limits each section to 10-5,000 characters. The CLI still requires an audio-file argument; saved-transcript reuse is currently a GUI feature.

`ui/workspace-tools.js` currently extends the global functions/state established by `ui/app.js`, so script order matters. Keep this in mind when changing event handling. The entry point still has legacy imports/constants; do not assume all old definitions control the new architecture.

## Possible Follow-Ups

The user asked for improvement ideas. Automatic workspace recovery, audio playback linked to timestamps, and one-click retry of a failed writing stage were suggested but not implemented or separately authorized. Repository ignore cleanup was discussed but not requested for implementation. Confirm the next task's scope instead of treating this list as a backlog to execute automatically.

## Visual References

The source design task is `codex://threads/01a08107-6798-78d0-8197-b9e5818d01a9`. It contains a generated visual reference, not an HTML implementation.

The reference image used locally was `C:\Users\priit\AppData\Local\Temp\codex-clipboard-c550bd1e-b495-44b1-81c7-a7d5bd83152d.png`. Temporary attachments may disappear. The current QA screenshots show the implemented layout and controls; they do not establish literal pixel equality with the reference.
