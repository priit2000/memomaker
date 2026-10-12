"""Light desktop workspace and shared command-line pipeline."""
import argparse
import json
import os
import time
from pathlib import Path
from providers import PROVIDERS, KEY_NAMES, ProviderError, TruncatedOutput, create_provider

CONFIG = Path(os.environ.get("APPDATA", str(Path.home()))) / "MemoMaker" / "settings.json"


def run_pipeline(core, path, selections, settings, prompts, method, emit, transcript=None, transcript_only=False):
    if transcript_only and transcript is not None:
        raise ValueError("Transcript-only processing requires an audio file.")
    first_stage = 1 if transcript is not None else 0
    last_stage = 1 if transcript_only else 2
    total = 3 if transcript_only else 4 - first_stage
    def progress(completed, label):
        emit("progress", {"completed": completed, "total": total, "label": label})
    progress(0, "Validating inputs and models")
    if first_stage == 0:
        valid, reason = core.validate_audio_file(path)
        if not valid:
            raise ValueError(reason)
    elif not transcript.strip():
        raise ValueError("Load a nonempty transcript first.")
    for prompt in prompts[first_stage:last_stage]:
        valid, reason = core.validate_prompt_input(prompt)
        if not valid:
            raise ValueError(reason)
    # Validate both configurations before making a billable request.
    providers = {}
    for index in range(first_stage, last_stage):
        name, model = selections[index]
        if not model.strip():
            raise ValueError("Select a model for each required stage.")
        provider = create_provider(name, settings)
        if name == "OpenRouter":
            provider.validate_model(model, index == 0)
            if index == 0 and provider.is_specialist(model):
                emit("log", "Specialist transcription: Markdown transcription instructions are not applied; memo instructions remain active.")
        providers[index] = provider
    progress(1, "Writing memo" if first_stage else "Transcribing audio")
    stamp = time.strftime("%y%m%d-%H%M%S") + "-%03d" % (time.time_ns() // 1000000 % 1000)
    folder = Path(core.OUTPUT_FOLDER)
    folder.mkdir(exist_ok=True)
    if first_stage == 1:
        (folder / (stamp + "-transcript.txt")).write_text(transcript, encoding="utf-8")
        emit("transcript", transcript)
    for index, (name, model) in enumerate(selections):
        if index < first_stage or index >= last_stage:
            continue
        emit("status", "Transcribing audio..." if index == 0 else "Writing output...")
        provider = providers[index]
        truncated = False
        try:
            if index == 0:
                text, usage = provider.transcribe(model, path, prompts[0], method)
            else:
                text, usage = provider.generate(model, transcript, prompts[1])
        except TruncatedOutput as exc:
            text, usage, truncated = exc.text, exc.usage, True
        if index == 0:
            transcript = text
            if transcript_only:
                progress(2, "Saving transcript")
        else:
            progress(total - 1, "Saving memo")
        target = folder / (stamp + ("-transcript.txt" if index == 0 else "-memo.md"))
        target.write_text(text, encoding="utf-8")
        emit("transcript" if index == 0 else "memo", text)
        emit("log", "%s / %s | %s | Saved %s" % (name, model, json.dumps(usage), target.name))
        if truncated:
            raise ProviderError("The %s was cut off at the model's output limit. The partial text is saved as %s."
                                % ("transcript" if index == 0 else "memo", target.name))
        if index == 0 and not transcript_only:
            progress(2, "Writing memo")
    progress(total, "Completed")




# Command-line defaults per provider. A provider without an entry needs an explicit model.
CLI_TRANSCRIPTION = ("OpenRouter", {"OpenRouter": "microsoft/mai-transcribe-2", "Google Gemini": "gemini-3.8-flash"})
CLI_WRITING = ("Google Gemini", {"Google Gemini": "gemini-3.8-flash"})


def read_text_file(parser, path, label):
    try:
        return Path(path).read_text(encoding="utf-8-sig")
    except (OSError, UnicodeError) as exc:
        parser.error("Cannot read %s %s: %s" % (label, path, exc))


def cli(core):
    parser = argparse.ArgumentParser(
        prog="memomaker-ui.pyw", description="MemoMaker: transcribe audio and write a memo without opening the window.")
    parser.add_argument("audio_file", nargs="?", help="audio file to process (MP3, WAV, M4A, OGG, FLAC, AAC); omit with --transcript or --list-models")
    parser.add_argument("--provider", choices=PROVIDERS, default=CLI_TRANSCRIPTION[0], help="transcription provider (default: %(default)s)")
    parser.add_argument("--model", help="transcription model ID; default %s" % ", ".join("%s for %s" % (m, p) for p, m in CLI_TRANSCRIPTION[1].items()))
    parser.add_argument("--writing-provider", choices=PROVIDERS, default=CLI_WRITING[0], help="memo writing provider (default: %(default)s)")
    parser.add_argument("--writing-model", help="memo writing model ID; default %s" % ", ".join("%s for %s" % (m, p) for p, m in CLI_WRITING[1].items()))
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--transcript-only", action="store_true", help="transcribe the audio and skip memo writing")
    mode.add_argument("--transcript", metavar="FILE", help="write a memo from an existing UTF-8 transcript file instead of audio")
    parser.add_argument("--method", choices=["auto", "inline", "upload"], default="inline", help="how Gemini receives audio: inline in the request, upload through the Files API, or auto (upload at 20 MB and above) (default: %(default)s)")
    parser.add_argument("--profile", choices=list(core.AVAILABLE_LANGUAGES), default=core.DEFAULT_LANGUAGE, help="prompt profile from transcription-prompt-*.md (default: %(default)s)")
    transcription_prompt = parser.add_mutually_exclusive_group()
    transcription_prompt.add_argument("--transcription-prompt", "--prompt", metavar="TEXT", help="replace the profile's transcription prompt; dedicated speech-to-text models ignore it")
    transcription_prompt.add_argument("--transcription-prompt-file", metavar="FILE", help="read the transcription prompt from a UTF-8 file")
    memo_prompt = parser.add_mutually_exclusive_group()
    memo_prompt.add_argument("--memo-prompt", metavar="TEXT", help="replace the profile's memo prompt")
    memo_prompt.add_argument("--memo-prompt-file", metavar="FILE", help="read the memo prompt from a UTF-8 file")
    parser.add_argument("--base-url", default=os.environ.get("CUSTOM_API_BASE_URL", ""), help="Custom API base URL, including /v1 when required (default: CUSTOM_API_BASE_URL environment variable)")
    parser.add_argument("--audio-mode", choices=["chat", "transcriptions"], default="chat", help="Custom API audio endpoint: chat messages or multipart /audio/transcriptions (default: %(default)s)")
    parser.add_argument("--list-models", action="store_true", help="list the transcription models of --provider and the writing models of --writing-provider, then exit")
    args = parser.parse_args()
    settings = {"base_url": args.base_url, "audio_mode": args.audio_mode}

    if args.list_models:
        try:
            for title, name, audio in [("Transcription", args.provider, True), ("Writing", args.writing_provider, False)]:
                print("%s models (%s):" % (title, name))
                for model in create_provider(name, settings).models(audio):
                    print("  " + model)
        except Exception as exc:
            parser.exit(1, "Error: %s\n" % exc)
        return

    if args.transcript and args.audio_file:
        parser.error("Use either audio_file or --transcript, not both.")
    if not args.transcript and not args.audio_file:
        parser.error("audio_file is required unless --transcript or --list-models is used.")
    model = args.model or CLI_TRANSCRIPTION[1].get(args.provider)
    writing_model = args.writing_model or CLI_WRITING[1].get(args.writing_provider)
    if not model and not args.transcript:
        parser.error("Set --model for %s." % args.provider)
    if not writing_model and not args.transcript_only:
        parser.error("Set --writing-model for %s." % args.writing_provider)

    prompts = list(core.read_prompts_from_file(args.profile))
    if args.transcription_prompt_file:
        prompts[0] = read_text_file(parser, args.transcription_prompt_file, "transcription prompt")
    elif args.transcription_prompt:
        prompts[0] = args.transcription_prompt
    if args.memo_prompt_file:
        prompts[1] = read_text_file(parser, args.memo_prompt_file, "memo prompt")
    elif args.memo_prompt:
        prompts[1] = args.memo_prompt
    transcript = read_text_file(parser, args.transcript, "transcript") if args.transcript else None

    selections = [(args.provider, model or ""), (args.writing_provider, writing_model or "")]
    try:
        run_pipeline(core, args.audio_file, selections, settings, prompts, args.method,
                     lambda kind, value: print(value) if kind in ("status", "log") else None,
                     transcript, args.transcript_only)
    except Exception as exc:
        parser.exit(1, "Error: %s\n" % exc)
    print("Saved in " + str(Path(core.OUTPUT_FOLDER).resolve()))
