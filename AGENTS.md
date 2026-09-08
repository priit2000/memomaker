# AGENTS.md

never write core before the user asks for it

This file describes the current repository for coding agents. See README.md for user workflows and setup.

## Application Overview

MemoMaker is a Windows desktop application with a Python backend and a local HTML interface hosted by pywebview/Edge WebView2. The entry point is `memomaker-ui.pyw`, not `memomaker-ui.py`. It supports GUI and CLI operation. There is no audio-recording functionality.

## Architecture

Keep provider transport separate from the desktop interface.

- `memomaker-ui.pyw`: startup, audio/prompt validation, profile discovery, initial model defaults.
- `providers.py`: Google Gemini, OpenRouter, and custom OpenAI-compatible transports and model discovery.
- `workspace_ui.py`: shared processing pipeline, CLI arguments, settings file location.
- `desktop_view.py`: pywebview window, Python/JavaScript bridge, native file dialogs, prompt persistence, and Windows rich clipboard.
- `ui/index.html`, `ui/style.css`, `ui/app.js`: main workspace and controls.
- `ui/workspace-tools.js`: speaker renaming, Undo, stage progress, and rich-text copy.
- `ui/` also contains local fonts, third-party scripts, and their license files. These are required runtime assets.

## Providers and Processing

Transcription and memo writing select providers and models independently. Validate required stages before billable requests.

Google supports Inline (default), Auto, and Upload. Auto uses inline below 20 MB and upload at or above that threshold. Upload handling polls processing state and attempts remote-file deletion afterward. The cutoff is implemented in `providers.py`; the entry point's legacy `INLINE_THRESHOLD` constant is not the routing authority.

OpenRouter discovery merges the normal model catalog with `/models?output_modalities=transcription`. Audio-capable chat models use `/chat/completions`; dedicated speech-to-text models use base64 JSON at `/audio/transcriptions`. MAI-Transcribe 2 requests structured timestamps and diarization. Dedicated transcription models do not apply the Markdown transcription prompt. Keep transcription-only models out of the writing stage.

Custom APIs support chat audio or multipart transcription endpoints. A configurable URL supports compatible protocols, not arbitrary vendor APIs. Custom catalogs do not reliably expose capabilities.

The pipeline emits `status`, `log`, `transcript`, `memo`, and structured `progress` events. The desktop worker emits `done`. Progress counts completed stages and shows elapsed time; do not invent within-request percentages.

## Saved Work

Generated files use `outputs/yymmdd-hhmmss-mmm-transcript.txt` and matching `-memo.md` names. Save the transcript before memo writing so writing failures do not discard it.

The GUI loads nonempty UTF-8/BOM text or Markdown files up to 10 MB. Loading a transcript selects the workspace-transcript source, skips audio validation and transcription credentials, and runs only the writing model. The CLI currently still requires an audio-file argument.

Speaker changes replace matching names in both workspace documents in one pass, with Undo for the latest rename. They do not run AI generation or rewrite inferred identities. Manual edits and renames need Export to persist; source documents are not automatically overwritten.

Copy provides Windows CF_HTML plus Unicode plain text. CF_HTML offsets count UTF-8 bytes. Sanitize rendered Markdown and copied HTML. Preview selection copying preserves rich content; editor copying remains source text.

## Prompts and Configuration

Profile discovery scans the current working directory for `transcription-prompt-*.md`. Preserve the complete filename suffix: `en-article` becomes `EN-ARTICLE`. Start the app from the repository folder and restart after adding profiles.

The first two top-level Markdown headings delimit transcription and writing prompts. The second heading may be Memo, Article, Summary, or another title; later headings belong to the writing prompt. Use `##` inside the transcription section. Do not split only on a literal `# Memo`.

Saving prompts updates both sections of an existing profile after native confirmation. Preserve section headings, validate content, reject external changes during confirmation, and replace the file atomically. Reset restores the last loaded/saved prompts.

Keys: `GEMINI_API_KEY`, `OPENROUTER_API_KEY`, `CUSTOM_API_KEY`. Optional remembered keys go into the Windows user environment, not encrypted credential storage. Non-key settings are in `%APPDATA%/MemoMaker/settings.json`. Never log or commit credentials.

Audio validation currently allows MP3, WAV, M4A, OGG, FLAC, and AAC, from 1 KB to 100 MB. Provider limits can be stricter. There is no automatic long-audio splitting or provider fallback.

## Development Commands

Use PowerShell 5.1-compatible commands from the repository directory.

```powershell
python -m pip install -r requirements.txt
python .\memomaker-ui.pyw
python .\memomaker-ui.pyw .\audio.mp3 --method inline
python -m unittest discover -v
python -m py_compile .\memomaker-ui.pyw .\providers.py .\workspace_ui.py .\desktop_view.py
```

Optional browser QA requires Playwright and installed Microsoft Edge. The desktop smoke check opens a temporary native window.

```powershell
python -m pip install playwright
python .\verify_ui.py
python .\verify_desktop.py
```

Tests cover prompt profiles, provider routing, transcript reuse, prompt-save confirmation, and clipboard offsets. UI checks cover responsive layout, editing, speaker rename/Undo, rich copy, and progress states. Mocked tests and desktop checks do not prove live paid model compatibility.

## Repository Hygiene

Keep source modules, tests, prompt profiles, runtime assets, and third-party licenses versioned. Generated memos/transcripts, local audio, QA screenshots, caches, and credentials are not source artifacts. Check the actual ignore rules rather than assuming outputs are ignored. Do not alter user prompt content while updating documentation.
