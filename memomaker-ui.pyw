#!/usr/bin/env python3

import os
import argparse
import threading
import tkinter as tk
from tkinter import filedialog
import webbrowser
import time
import mimetypes
import pathlib
import glob
import re

# ============================================================================
# USER SETTINGS & CONFIGURATION
# ============================================================================

# API Configuration
API_KEY = os.environ.get("GEMINI_API_KEY")

# Model Settings
MODEL_NAME = 'gemini-3-flash-preview'


# File Processing Settings
INLINE_THRESHOLD = 20 * 1024 * 1024  # 20 MB in bytes
MAX_FILE_SIZE = 100 * 1024 * 1024  # 100 MB max file size
MIN_FILE_SIZE = 1024  # 1 KB minimum file size

# File Validation Settings
VALID_AUDIO_EXTENSIONS = {'.mp3', '.wav', '.m4a', '.ogg', '.flac', '.aac'}
VALID_MIME_TYPES = {
    'audio/mpeg', 'audio/wav', 'audio/x-wav', 'audio/mp4', 'audio/m4a',
    'audio/ogg', 'audio/flac', 'audio/aac', 'audio/x-m4a'
}


# Create output folder
OUTPUT_FOLDER = os.path.join(os.getcwd(), "outputs")
if not os.path.exists(OUTPUT_FOLDER):
    os.makedirs(OUTPUT_FOLDER)

# File naming will be handled dynamically with session timestamp

# Language detection and prompt file handling
def detect_available_languages():
    """Detect available prompt files and return language options."""
    languages = {}
    prompt_pattern = "transcription-prompt-*.md"
    
    prompt_files = glob.glob(os.path.join(os.getcwd(), prompt_pattern))
    
    for file_path in prompt_files:
        filename = os.path.basename(file_path)
        # Extract language code from filename like 'transcription-prompt-et.md' -> 'et'
        if filename.startswith('transcription-prompt-') and filename.endswith('.md'):
            lang_code = filename[len('transcription-prompt-'):-3]
            if lang_code:
                languages[lang_code.upper()] = file_path
    
    return languages

# Detect available languages
AVAILABLE_LANGUAGES = detect_available_languages()
DEFAULT_LANGUAGE = list(AVAILABLE_LANGUAGES.keys())[0] if AVAILABLE_LANGUAGES else None

# File validation functions
def validate_audio_file(file_path):
    """Validate audio file format, size, and basic integrity."""
    if not file_path or not os.path.exists(file_path):
        return False, "File does not exist"
    
    # Check file extension
    file_ext = pathlib.Path(file_path).suffix.lower()
    if file_ext not in VALID_AUDIO_EXTENSIONS:
        return False, f"Unsupported file format: {file_ext}. Supported: {', '.join(VALID_AUDIO_EXTENSIONS)}"
    
    # Check file size
    try:
        file_size = os.path.getsize(file_path)
        if file_size < MIN_FILE_SIZE:
            return False, f"File too small ({file_size} bytes). Minimum: {MIN_FILE_SIZE} bytes"
        if file_size > MAX_FILE_SIZE:
            return False, f"File too large ({file_size:,} bytes). Maximum: {MAX_FILE_SIZE:,} bytes"
    except OSError as e:
        return False, f"Cannot read file size: {str(e)}"
    
    # Check MIME type
    mime_type, _ = mimetypes.guess_type(file_path)
    if mime_type and mime_type not in VALID_MIME_TYPES:
        return False, f"Invalid MIME type: {mime_type}"
    
    # Basic file integrity check
    try:
        with open(file_path, 'rb') as f:
            # Read first few bytes to ensure file is readable
            f.read(1024)
    except (OSError, IOError) as e:
        return False, f"File appears corrupted or unreadable: {str(e)}"
    
    return True, "File validation passed"

def validate_prompt_input(prompt_text):
    """Validate prompt input text."""
    if not prompt_text or not prompt_text.strip():
        return False, "Prompt cannot be empty"
    
    # Check for reasonable length limits
    if len(prompt_text.strip()) < 10:
        return False, "Prompt too short (minimum 10 characters)"
    
    if len(prompt_text) > 5000:
        return False, "Prompt too long (maximum 5000 characters)"
    
    return True, "Prompt validation passed"

def format_api_usage(operation, file_size, processing_time, success=True, error=None, response_data=None):
    """Format API usage information for display."""
    usage_info = []
    usage_info.append(f"📊 API Usage Summary:")
    usage_info.append(f"   Operation: {operation}")
    usage_info.append(f"   File Size: {file_size:,} bytes ({file_size/(1024*1024):.2f} MB)")
    usage_info.append(f"   Processing Time: {processing_time:.2f} seconds")
    
    if response_data:
        if hasattr(response_data, 'usage_metadata'):
            metadata = response_data.usage_metadata
            usage_info.append(f"   Input Tokens: {getattr(metadata, 'prompt_token_count', 'N/A')}")
            usage_info.append(f"   Output Tokens: {getattr(metadata, 'candidates_token_count', 'N/A')}")
            usage_info.append(f"   Total Tokens: {getattr(metadata, 'total_token_count', 'N/A')}")
    
    usage_info.append(f"   Success: {'✅ Yes' if success else '❌ No'}")
    if error:
        usage_info.append(f"   Error: {error}")
    
    return "\n".join(usage_info)

def read_prompts_from_file(language_code=None):
    """Read prompts from language-specific prompt file."""
    if language_code is None:
        language_code = DEFAULT_LANGUAGE
    
    if not language_code or language_code not in AVAILABLE_LANGUAGES:
        return None, None
        
    prompt_file = AVAILABLE_LANGUAGES[language_code]
    
    try:
        with open(prompt_file, "r", encoding="utf-8") as f:
            content = f.read()

        headings = list(re.finditer(r"(?m)^#\s+.+$", content))
        if len(headings) < 2:
            return None, None

        first_heading, second_heading = headings[0], headings[1]
        first_body_start = content.find("\n", first_heading.end())
        second_body_start = content.find("\n", second_heading.end())

        if first_body_start == -1 or second_body_start == -1:
            return None, None

        transcript_section = content[first_body_start + 1:second_heading.start()].strip()
        memo_section = content[second_body_start + 1:].strip()
        return transcript_section, memo_section
    except FileNotFoundError:
        return None, None

# Initialize default prompts
if AVAILABLE_LANGUAGES:
    _transcript_prompt, _memo_prompt = read_prompts_from_file(DEFAULT_LANGUAGE)
    DEFAULT_TRANS_PROMPT = _transcript_prompt if _transcript_prompt else "❌ ERROR: Could not load transcript prompt from file!"
    DEFAULT_MEMO_PROMPT = _memo_prompt if _memo_prompt else "❌ ERROR: Could not load memo prompt from file!"
else:
    DEFAULT_TRANS_PROMPT = "❌ ERROR: No prompt files found!\n\nPlease create prompt files like 'transcription-prompt-en.md' or 'transcription-prompt-et.md'"
    DEFAULT_MEMO_PROMPT = "❌ ERROR: No prompt files found!\n\nPlease create prompt files like 'transcription-prompt-en.md' or 'transcription-prompt-et.md'"


# UI Settings
APP_TITLE = "✨ Gemini Audio Processor Pro"
APP_SUBTITLE = "Transcribe audio files and create intelligent memos"
WINDOW_WIDTH = 1000
WINDOW_HEIGHT = 800
MIN_WIDTH = 900
MIN_HEIGHT = 1200


# Audio File Types
SUPPORTED_AUDIO_TYPES = [
    ("Audio Files", "*.mp3 *.wav *.m4a *.ogg *.flac *.aac"),
    ("All Files", "*.*")
]


# ============================================================================
# END USER SETTINGS
# ============================================================================

from workspace_ui import cli
from desktop_view import WebWorkspace


def main():
    import sys
    core = sys.modules[__name__]
    if len(sys.argv) > 1:
        cli(core)
    else:
        WebWorkspace(core).mainloop()


if __name__ == "__main__":
    main()
