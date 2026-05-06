# MemoMaker

MemoMaker turns an existing audio file into a transcript and a structured written output using Google's Gemini API.

The app supports GUI and CLI modes from `memomaker-ui.pyw`. It does not record audio. Select an existing audio file, choose a prompt profile, process it, and the app writes timestamped results to `outputs/`.

## Features

- File-based audio processing for MP3, WAV, M4A, OGG, FLAC, and AAC files
- Gemini transcript generation plus a second configurable output step
- Prompt profiles loaded from every `transcription-prompt-*.md` file in the app folder
- Processing modes: auto, inline, and upload
- File validation for extension, MIME type, size, and readability
- GUI progress/status updates and API usage summaries
- Built-in API key setup dialog
- CLI mode for direct file processing

## Requirements

- Python 3.8+
- Google Gemini API key
- Python packages:

```powershell
pip install customtkinter google-generativeai
```

## API Key

MemoMaker reads the API key from `GEMINI_API_KEY`.

PowerShell:

```powershell
$env:GEMINI_API_KEY = "your-api-key-here"
```

Command Prompt:

```cmd
set GEMINI_API_KEY=your-api-key-here
```

The GUI also opens an API key dialog when no key is configured.

## Run

GUI mode:

```powershell
python .\memomaker-ui.pyw
```

CLI mode:

```powershell
python .\memomaker-ui.pyw .\audio_file.mp3 --method auto
```

Available CLI methods:

- `auto`: uses inline processing below the configured threshold and upload processing for larger files
- `inline`: sends the audio bytes directly in the request
- `upload`: uploads the file through Gemini's file API before processing

## GUI Workflow

1. Launch `memomaker-ui.pyw`.
2. Click `Browse` or the file path field.
3. Select an audio file.
4. Choose a prompt profile from the language/profile dropdown.
5. Choose `Auto`, `Inline Processing`, or `Cloud Upload`.
6. Edit the transcript/output prompts when needed.
7. Click `Process Audio`.
8. Open the generated files from `outputs/`.

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

## Output Files

Generated files are written to `outputs/`:

```text
outputs/
  260506-143022-transcript.txt
  260506-143022-memo.md
```

The timestamp format is `yymmdd-hhmmss`.

## Configuration

Main settings are near the top of `memomaker-ui.pyw`:

```python
API_KEY = os.environ.get("GEMINI_API_KEY")
MODEL_NAME = 'gemini-3-flash-preview'

INLINE_THRESHOLD = 20 * 1024 * 1024
MAX_FILE_SIZE = 100 * 1024 * 1024
MIN_FILE_SIZE = 1024

OUTPUT_FOLDER = os.path.join(os.getcwd(), "outputs")
```

## Project Files

```text
memomaker/
  memomaker-ui.pyw
  transcription-prompt-et.md
  transcription-prompt-en.md
  transcription-prompt-en-article.md
  test_prompt_loading.py
  outputs/
```

## Testing

Run the regression tests:

```powershell
python -m unittest .\test_prompt_loading.py
```

Check Python syntax:

```powershell
python -m py_compile .\memomaker-ui.pyw
```

## Troubleshooting

### `No module named 'customtkinter'`

Install dependencies:

```powershell
pip install customtkinter google-generativeai
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
