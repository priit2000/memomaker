# MemoMaker

MemoMaker turns an existing audio file or saved transcript into a structured written output using Google Gemini, OpenRouter, or a compatible custom API.

The light desktop workspace supports Google Gemini, OpenRouter, and custom OpenAI-compatible APIs. Select providers and models independently for transcription and writing. For example, transcribe through Google and write the article with an OpenRouter text model.

## Providers and API Settings

Open **API settings** to configure provider keys. Google reads `GEMINI_API_KEY`, OpenRouter reads `OPENROUTER_API_KEY`, and custom endpoints read `CUSTOM_API_KEY`. Keys entered in the dialog apply for the session; the optional Windows checkbox stores them in your user environment. Custom endpoint settings are saved under `%APPDATA%/MemoMaker/settings.json` without keys.

Provider and model selection are in **API settings**, with separate transcription and writing controls. Use the refresh icon beside a model field to fetch models, then type to filter the list or enter an exact model ID. OpenRouter transcription lists include audio-capable chat models and dedicated speech-to-text models such as `microsoft/mai-transcribe-2`. Writing lists exclude transcription-only models. Custom model catalogs do not consistently publish capabilities; choose a model supporting the selected endpoint. Google lists generation-capable models, so choose one supporting audio for transcription.

Google retains Auto, Inline, and Upload processing, with **Inline as the GUI and CLI default**. OpenRouter routes audio-capable chat models to chat completions and dedicated transcription models to `/audio/transcriptions` using base64 JSON. MAI-Transcribe 2 requests structured timestamps and speaker labels; returned segments become timestamped transcript paragraphs. Dedicated transcription models do not apply the Markdown transcription prompt; memo instructions still apply to the writing model. Other specialists use their default JSON response, retaining segments when returned. Custom APIs support either chat audio messages or multipart `/audio/transcriptions`; writing uses `/chat/completions`. Set the custom base URL including `/v1` when required. Provider/model file-format, size, and context limits still apply. Unsupported requests report an error; the app does not silently switch providers or split long audio.

## Saved Work and Prompts

Select the **Transcript** or **Memo** tab, then the folder icon to load a previous `.txt` or `.md` file. Files must be UTF-8 (a BOM is supported). Loading does not modify the original file. Edit, Copy, and Export work on loaded content too.

Loading a transcript selects **Workspace transcript** as the processing source. Generate memo then uses the current transcript and writing model only, without reading audio or requiring transcription credentials. Select **Audio file** to transcribe again. Loading a memo opens it for viewing and editing; it does not generate anything.

The save icon below the prompt editor saves **both prompt tabs** to the selected `transcription-prompt-*.md` profile after an overwrite confirmation. Cancel leaves the file unchanged. Existing section headings, including Article headings, are preserved. Reset restores the last loaded or saved prompts. Prompt edits otherwise remain session-only.

Results appear in Memo and Transcript tabs with Copy, Export, and an edit icon. Memo Markdown is rendered as a formatted document. The bottom Activity log opens a drawer with progress and token usage. A completed transcript is saved even if writing fails. The Generate button remains visible while the setup area scrolls. The initial document is explicitly labeled EXAMPLE MEMO and is replaced by generated output.

**Speakers** in the right panel opens name replacements. Detected speaker labels and timestamped names are prefilled; the plus button adds a manual replacement. Apply names updates exact matching names in both the transcript and memo in one pass, without another API call. Undo reverses the latest rename. This does not rewrite inferred identities or unrelated wording. Export each changed document to save it; source files are not overwritten automatically.

**Copy** places rendered text and HTML formatting on the Windows clipboard. Headings, emphasis, lists, links, and tables are available to rich-text paste destinations; plain-text apps receive readable text without Markdown markers. Selecting text in the preview and pressing Ctrl+C also preserves formatting. Copying from the raw editor retains the source text. Paste appearance depends on the destination application.

The footer shows actual completed stages and elapsed time: validation, transcription, memo writing, and saving. Loading a transcript skips transcription, leaving three stages. The bar advances on completed work, not on a guessed time percentage, and stops at the last completed stage on failure. Provider requests do not expose within-stage completion percentages or a reliable remaining-time estimate.

The desktop UI uses pywebview with Microsoft Edge WebView2 on Windows. Fonts, Lucide icons, Markdown parsing, and sanitization are bundled locally under `ui/`; the UI does not load these assets from a CDN at runtime.

Example mixed-provider command:

```powershell
python .\memomaker-ui.pyw .\audio.mp3 --provider "Google Gemini" --model gemini-3-flash-preview --writing-provider OpenRouter --writing-model "your-provider/model-id"
```

Custom endpoint example:

```powershell
python .\memomaker-ui.pyw .\audio.mp3 --provider "Custom API" --base-url http://localhost:8000/v1 --audio-mode transcriptions --model whisper --writing-provider OpenRouter --writing-model "your-provider/model-id"
```

Use `--profile EN-ARTICLE` to select a prompt profile in CLI mode. New providers can implement `models`, `transcribe`, and `generate` in `providers.py` and be registered in `create_provider`. A custom URL supports compatible protocols, not arbitrary vendor APIs.

The app supports GUI and CLI modes from `memomaker-ui.pyw`. It does not record audio. Select an existing audio file, choose a prompt profile, process it, and the app writes timestamped results to `outputs/`.

## Features

- File-based audio processing for MP3, WAV, M4A, OGG, FLAC, and AAC files
- Independent transcription and writing models, including specialist speech-to-text models
- Prompt profiles loaded from every `transcription-prompt-*.md` file in the app folder
- Google processing modes: inline (default), auto, and upload
- File validation for extension, MIME type, size, and readability
- Stage-based progress, elapsed time, and available API usage summaries
- Load saved transcripts and memos; generate new memos from existing transcripts
- Confirmed prompt saving, speaker renaming with Undo, and formatted copying
- Built-in API key setup dialog
- CLI mode for direct file processing

## Requirements

- Python 3.10+
- Microsoft Edge WebView2 Runtime (Windows)
- Credentials for the selected provider(s); a Google key is unnecessary when Google is not selected
- Python packages:

```powershell
python -m pip install -r requirements.txt
```

## API Keys

Set credentials only for the providers you use. These PowerShell assignments apply to the current terminal session:

```powershell
$env:GEMINI_API_KEY = "your-api-key-here"
$env:OPENROUTER_API_KEY = "your-openrouter-key-here"
$env:CUSTOM_API_KEY = "your-custom-key-here"
```

Use **API settings** in the GUI to enter the keys for your selected providers.

Remembered Windows environment keys are not encrypted credential storage. Do not put real keys in tracked files or screenshots.

## Run

Run commands from the MemoMaker folder. Prompt discovery and the `outputs/` directory currently use the working directory. Restart the app after adding a prompt profile or updating the application.

GUI mode:

```powershell
python .\memomaker-ui.pyw
```

CLI mode:

```powershell
python .\memomaker-ui.pyw .\audio_file.mp3 --method inline
```

Google processing methods (other providers use their own transport):

- `auto`: uses inline processing below 20 MB and upload processing at or above 20 MB
- `inline`: sends the audio bytes directly in the request; default
- `upload`: uploads the file through Gemini's file API before processing

## GUI Workflow

1. Launch `memomaker-ui.pyw`.
2. Open **API settings**, configure keys, and select separate transcription and writing models. Apply settings.
3. Drop an audio file into the upload area or click **browse files**. For saved transcripts, use the folder icon in the Transcript tab instead.
4. Choose a profile in **Prompts** and edit the Transcript or Memo prompt. The save icon persists both prompts after confirmation.
5. Check the **Processing** source. For Google audio, leave **Inline** selected or choose Auto or Upload.
6. Click **Generate memo** and follow the stage counter and elapsed time in the footer.
7. Review the Memo and Transcript tabs. Use **Speakers** to rename participants or the pencil icon for raw text edits.
8. Use **Copy** for formatted text or **Export** to save the active document. Export both tabs after changing names in both documents.

## Prompt Files

Prompt profiles are detected from files named:

```text
transcription-prompt-*.md
```

The profile name comes from the filename. Examples:

- `transcription-prompt-et.md` -> `ET`
- `transcription-prompt-en.md` -> `EN`
- `transcription-prompt-en-article.md` -> `EN-ARTICLE`

Each prompt file must contain at least two top-level Markdown headings:

```markdown
# Transcription
[transcription prompt]

# Memo
[memo/output prompt]
```

The first top-level section becomes the transcription prompt. The second top-level section, including any later headings, becomes the output prompt. The second heading can be `# Memo`, `# Article`, `# Summary`, or another profile-specific output type.

Use `##` or deeper headings inside the transcription prompt so they are not mistaken for the second section. Saving validates each prompt against the app's 10-to-5,000-character limits and refuses to overwrite a file changed externally while the confirmation was open. Dedicated OpenRouter transcription models do not consume this Markdown transcription prompt.

## Output Files

Generated files are written to `outputs/`:

```text
outputs/
  260908-143022-123-transcript.txt
  260908-143022-123-memo.md
```

The filename prefix is `yymmdd-hhmmss-mmm`, including milliseconds. A transcript is saved before memo writing, so it remains available after a writing failure. Generating from a loaded transcript saves a new transcript copy alongside the new memo.

Manual edits and speaker changes are workspace-only until exported. There is no automatic workspace recovery after closing the app. The folder picker loads nonempty UTF-8 text files up to 10 MB.

## Configuration

File validation and initial model defaults are near the top of `memomaker-ui.pyw`:

```python
API_KEY = os.environ.get("GEMINI_API_KEY")
MODEL_NAME = 'gemini-3-flash-preview'

MAX_FILE_SIZE = 100 * 1024 * 1024
MIN_FILE_SIZE = 1024

OUTPUT_FOLDER = os.path.join(os.getcwd(), "outputs")
```

Provider/model choices and custom endpoint settings are stored in `%APPDATA%/MemoMaker/settings.json`, excluding API keys. Google Auto's 20 MB cutoff is implemented in `providers.py`; editing the legacy `INLINE_THRESHOLD` constant in the entry point alone does not change provider routing. Model-specific limits may be lower than the app's 100 MB validation limit.

## Project Files

```text
memomaker/
  memomaker-ui.pyw
  providers.py
  workspace_ui.py
  desktop_view.py
  ui/
  requirements.txt
  transcription-prompt-et.md
  transcription-prompt-en.md
  transcription-prompt-en-article.md
  test_memomaker.py
  verify_ui.py
  verify_desktop.py
  outputs/
```

`memomaker-ui.pyw` handles startup, profile discovery, and validation. `workspace_ui.py` owns the CLI and shared pipeline; `providers.py` owns API transports. `desktop_view.py` hosts pywebview and native dialogs/clipboard operations. `ui/app.js` handles the main interface, and `ui/workspace-tools.js` handles speaker changes, stage progress, and rich copying. HTML, CSS, fonts, third-party scripts, and their licenses are bundled under `ui/`.

## Testing

Run the regression tests:

```powershell
python -m unittest discover -v
```

Check Python syntax:

```powershell
python -m py_compile .\memomaker-ui.pyw .\providers.py .\workspace_ui.py .\desktop_view.py
```

UI checks require the optional Playwright Python package and installed Microsoft Edge:

```powershell
python -m pip install playwright
python .\verify_ui.py
python .\verify_desktop.py
```

The browser checks cover layout, loading, prompts, speaker replacement/Undo, progress, and rich copying. The desktop smoke check opens a temporary window and checks native clipboard formats, restoring prior clipboard content when present. Tests use mocks and local fixtures, not paid transcription requests; passing them does not establish live compatibility with every model.

## Troubleshooting

Use the status footer and **Activity log** for processing errors. The checks below address common setup and workflow issues.

### Missing Python dependency

Install dependencies:

```powershell
python -m pip install -r requirements.txt
```

### `Google API key not found`

Set `GEMINI_API_KEY` or use the GUI API key dialog.

### `File validation failed`

Check that the file:

- uses a supported extension: MP3, WAV, M4A, OGG, FLAC, or AAC
- is between 1 KB and 100 MB
- can be read from disk

### Prompt profile fails to load

Check that the file:

- matches `transcription-prompt-*.md`
- has at least two top-level headings beginning with `# `
- is saved as UTF-8
- is in the working directory used to start MemoMaker

### OpenRouter transcription model is missing

Select OpenRouter for the transcription stage in **API settings** and refresh its model list. Dedicated speech-to-text models belong in that stage, not the writing selector. Enter an exact model ID only if it appears in the current OpenRouter catalog; the app validates its capabilities before processing.

### Progress stays on one stage

The bar measures completed stages, not bytes uploaded or audio seconds transcribed. During a provider request, the stage count can stay unchanged while elapsed time increases. Errors stop progress short of completion; no remaining-time estimate is available.

### Names or formatting did not change

Speaker replacement is case-sensitive and matches names as written. Add a manual current-name/new-name row for labels that were not detected. It does not infer that two different labels refer to the same person. Export changed documents to persist them.

Use Copy from the rendered preview for rich formatting. Copying the raw editor gives source text, and plain-text destinations cannot preserve formatting. Rich-text destinations control how they render the clipboard HTML.
