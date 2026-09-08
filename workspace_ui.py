"""Light desktop workspace and shared command-line pipeline."""
import argparse
import json
import os
import time
from pathlib import Path
from providers import PROVIDERS, KEY_NAMES, create_provider

CONFIG = Path(os.environ.get("APPDATA", str(Path.home()))) / "MemoMaker" / "settings.json"


def run_pipeline(core, path, selections, settings, prompts, method, emit, transcript=None):
    first_stage = 1 if transcript is not None else 0
    total = 4 - first_stage
    def progress(completed, label):
        emit("progress", {"completed": completed, "total": total, "label": label})
    progress(0, "Validating inputs and models")
    if first_stage == 0:
        valid, reason = core.validate_audio_file(path)
        if not valid:
            raise ValueError(reason)
    elif not transcript.strip():
        raise ValueError("Load a nonempty transcript first.")
    for prompt in prompts[first_stage:]:
        valid, reason = core.validate_prompt_input(prompt)
        if not valid:
            raise ValueError(reason)
    # Validate both configurations before making a billable request.
    providers = {}
    for index in range(first_stage, 2):
        name, model = selections[index]
        if not model.strip():
            raise ValueError("Select a model for both stages.")
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
        if index < first_stage:
            continue
        emit("status", "Transcribing audio..." if index == 0 else "Writing output...")
        provider = providers[index]
        if index == 0:
            text, usage = provider.transcribe(model, path, prompts[0], method)
            transcript = text
        else:
            text, usage = provider.generate(model, transcript, prompts[1])
            progress(total - 1, "Saving memo")
        target = folder / (stamp + ("-transcript.txt" if index == 0 else "-memo.md"))
        target.write_text(text, encoding="utf-8")
        emit("transcript" if index == 0 else "memo", text)
        emit("log", "%s / %s | %s | Saved %s" % (name, model, json.dumps(usage), target.name))
        if index == 0:
            progress(2, "Writing memo")
    progress(total, "Completed")




def cli(core):
    parser = argparse.ArgumentParser(description="MemoMaker")
    parser.add_argument("audio_file")
    parser.add_argument("--provider", choices=PROVIDERS, default=PROVIDERS[0])
    parser.add_argument("--model", default=core.MODEL_NAME)
    parser.add_argument("--writing-provider", choices=PROVIDERS)
    parser.add_argument("--writing-model")
    parser.add_argument("--base-url", default=os.environ.get("CUSTOM_API_BASE_URL", ""))
    parser.add_argument("--audio-mode", choices=["chat", "transcriptions"], default="chat")
    parser.add_argument("--profile", choices=list(core.AVAILABLE_LANGUAGES), default=core.DEFAULT_LANGUAGE)
    parser.add_argument("--prompt")
    parser.add_argument("--method", choices=["auto", "inline", "upload"], default="inline")
    args = parser.parse_args()
    prompts = list(core.read_prompts_from_file(args.profile))
    if args.prompt:
        prompts[0] = args.prompt
    selections = [(args.provider, args.model), (args.writing_provider or args.provider, args.writing_model or args.model)]
    try:
        run_pipeline(core, args.audio_file, selections, {"base_url": args.base_url, "audio_mode": args.audio_mode}, prompts, args.method,
                     lambda kind, value: print(value) if kind in ("status", "log") else None)
    except Exception as exc:
        parser.exit(1, "Error: %s\n" % exc)
