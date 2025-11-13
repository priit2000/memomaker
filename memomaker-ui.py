#!/usr/bin/env python3

import os
import argparse
import threading
import tkinter as tk
from tkinter import filedialog
import customtkinter as ctk
import google.generativeai as genai
import webbrowser
import time
import mimetypes
import pathlib
import glob
import numpy as np
import sounddevice as sd
import scipy.io.wavfile as wavfile
try:
    import lameenc
    LAMEENC_AVAILABLE = True
except ImportError:
    LAMEENC_AVAILABLE = False

# ============================================================================
# USER SETTINGS & CONFIGURATION
# ============================================================================

# API Configuration
API_KEY = os.environ.get("GEMINI_API_KEY")

# Model Settings
MODEL_NAME = 'gemini-flash-latest'


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


# Create recordings folder
RECORDINGS_FOLDER = os.path.join(os.getcwd(), "recordings")
if not os.path.exists(RECORDINGS_FOLDER):
    os.makedirs(RECORDINGS_FOLDER)

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
        # Split by # Memo section
        parts = content.split("# Memo")
        if len(parts) >= 2:
            # Remove first heading (could be "# Transkriptsioon" or "# Transcription")
            first_line_end = parts[0].find('\n')
            if first_line_end != -1:
                transcript_section = parts[0][first_line_end+1:].strip()
            else:
                transcript_section = parts[0].strip()
            memo_section = parts[1].strip()
            return transcript_section, memo_section
        else:
            return None, None
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
APP_SUBTITLE = "Record, transcribe and create intelligent memos"
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

class AudioRecorder:
    def __init__(self, callback=None):
        self.is_recording = False
        self.audio_data = []
        self.sample_rate = 22050  # Optimized for speech
        self.channels = 1  # Mono for speech
        self.output_folder = RECORDINGS_FOLDER
        self.audio_path = None
        self.temp_wav_path = None
        self.session_timestamp = None
        self.callback = callback  # Callback to notify when recording is complete
        
    def start_recording(self):
        """Start audio recording."""
        if self.is_recording:
            return False
            
        self.is_recording = True
        # Use session timestamp format: yymmdd-hhmmss
        self.session_timestamp = time.strftime("%y%m%d-%H%M%S")
        self.temp_wav_path = os.path.join(self.output_folder, f"temp_{self.session_timestamp}.wav")
        self.audio_path = os.path.join(self.output_folder, f"{self.session_timestamp}-recording.mp3")
        self.audio_data = []
        
        self.audio_thread = threading.Thread(target=self.record_audio)
        self.audio_thread.daemon = True
        self.audio_thread.start()
        
        return True
    
    def stop_recording(self):
        """Stop audio recording and save file."""
        if not self.is_recording:
            return None
            
        self.is_recording = False
        
        if hasattr(self, 'audio_thread'):
            self.audio_thread.join()
        
        saved_path = self.save_recording()
        
        if self.callback and saved_path:
            self.callback(saved_path)
            
        return saved_path
    
    def record_audio(self):
        """Record audio in chunks."""
        try:
            duration = 1.0
            
            while self.is_recording:
                try:
                    audio = sd.rec(int(duration * self.sample_rate), 
                                 samplerate=self.sample_rate, 
                                 channels=self.channels, 
                                 dtype=np.int16)
                    sd.wait()
                    self.audio_data.append(audio)
                    
                except Exception as e:
                    print(f"Audio error: {e}")
                    break
                    
        except Exception as e:
            print(f"Audio setup error: {e}")
    
    def save_recording(self):
        """Save recorded audio to MP3 file using lameenc."""
        try:
            if self.audio_data:
                audio_array = np.concatenate(self.audio_data, axis=0)
                
                if LAMEENC_AVAILABLE:
                    # Convert directly to MP3 using lameenc
                    success = self.encode_to_mp3(audio_array, self.audio_path)
                    if success:
                        return self.audio_path
                
                # Fallback to WAV if MP3 encoding failed
                wav_path = os.path.join(self.output_folder, f"{self.session_timestamp}-recording.wav")
                wavfile.write(wav_path, self.sample_rate, audio_array)
                return wav_path
            else:
                return None
                
        except Exception as e:
            print(f"Save error: {e}")
            return None
    
    def encode_to_mp3(self, audio_data, mp3_path):
        """Encode audio data to MP3 using lameenc."""
        try:
            # Ensure audio is in the right format for lameenc (int16)
            if audio_data.dtype != np.int16:
                audio_data = audio_data.astype(np.int16)
            
            # Flatten to 1D array if mono
            if len(audio_data.shape) > 1 and audio_data.shape[1] == 1:
                audio_data = audio_data.flatten()
            
            # Create MP3 encoder
            encoder = lameenc.Encoder()
            encoder.set_bit_rate(128)  # 128 kbps
            encoder.set_in_sample_rate(self.sample_rate)
            encoder.set_channels(self.channels)
            encoder.set_quality(2)  # Good quality
            
            # Encode to MP3
            mp3_data = encoder.encode(audio_data.tobytes())
            mp3_data += encoder.flush()
            
            # Write MP3 file
            with open(mp3_path, 'wb') as f:
                f.write(mp3_data)
            
            return True
            
        except Exception as e:
            print(f"MP3 encoding error: {e}")
            return False

class GeminiAudioApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        # Theme / window
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")
        self.title(APP_TITLE)
        self.geometry(f"{WINDOW_WIDTH}x{WINDOW_HEIGHT}")
        self.minsize(MIN_WIDTH, MIN_HEIGHT)
        self.configure(fg_color=["#0F0F0F", "#0F0F0F"])
        # State
        self.audio_file_path = None
        self.transcript = None
        self.processing = False
        self.api_start_time = None
        self.current_language = DEFAULT_LANGUAGE
        # Audio recording
        self.audio_recorder = AudioRecorder(callback=self.on_recording_complete)
        self.recording = False
        self.current_session_timestamp = None
        self.create_widgets()
        self.setup_drag_drop()
        self.check_mp3_support()
        self.check_api_key()
    
    def check_mp3_support(self):
        """Check if MP3 encoding is available."""
        if LAMEENC_AVAILABLE:
            self.log_message("✅ MP3 encoding available - optimized for meetings")
        else:
            self.log_message("⚠️ MP3 encoding not available - recordings will be WAV")
            self.log_message("💡 For smaller files, install: pip install lameenc")

    def create_widgets(self):
        # Main container
        main_container = ctk.CTkFrame(self, fg_color="transparent")
        main_container.pack(fill=tk.BOTH, expand=True, padx=30, pady=30)

        # Header
        header_frame = ctk.CTkFrame(main_container,
                                    fg_color=["#1E1E2E", "#2A2A40"],
                                    corner_radius=20,
                                    border_width=2,
                                    border_color=["#4A90E2", "#357ABD"])
        header_frame.pack(fill=tk.X, pady=(0, 25))

        title_container = ctk.CTkFrame(header_frame, fg_color="transparent")
        title_container.pack(fill=tk.X, padx=20, pady=20)

        self.title_label = ctk.CTkLabel(title_container,
                                        text=APP_TITLE,
                                        font=ctk.CTkFont(size=32, weight="bold"),
                                        text_color=["#4A90E2", "#5BA3F5"])
        self.title_label.pack(side=tk.LEFT)

        subtitle = ctk.CTkLabel(title_container,
                                text=APP_SUBTITLE,
                                font=ctk.CTkFont(size=14),
                                text_color=["#888888", "#AAAAAA"])
        subtitle.pack(side=tk.LEFT, padx=(20, 0))

        # File selection and recording
        file_section = ctk.CTkFrame(main_container,
                                    fg_color=["#1A1A2E", "#252540"],
                                    corner_radius=20,
                                    border_width=1,
                                    border_color=["#333355", "#444466"])
        file_section.pack(fill=tk.X, pady=(0, 20))

        file_header = ctk.CTkLabel(file_section,
                                   text="📁 Audio Input",
                                   font=ctk.CTkFont(size=18, weight="bold"),
                                   text_color=["#E0E0E0", "#F0F0F0"])
        file_header.pack(anchor="w", padx=20, pady=(15, 10))

        # Recording section
        record_frame = ctk.CTkFrame(file_section, fg_color="transparent")
        record_frame.pack(fill=tk.X, padx=20, pady=(0, 15))

        self.record_btn = ctk.CTkButton(record_frame,
                                       text="🎤 Start Recording",
                                       command=self.toggle_recording,
                                       width=150,
                                       height=45,
                                       font=ctk.CTkFont(size=14, weight="bold"),
                                       corner_radius=15,
                                       fg_color=["#4CAF50", "#66BB6A"])
        self.record_btn.pack(side=tk.LEFT, padx=(0, 15))

        # Recording status
        self.record_status_var = tk.StringVar(value="Ready to record")
        self.record_status_label = ctk.CTkLabel(record_frame,
                                               textvariable=self.record_status_var,
                                               font=ctk.CTkFont(size=12),
                                               text_color=["#AAAAAA", "#CCCCCC"])
        self.record_status_label.pack(side=tk.LEFT, padx=(0, 20))

        # Separator
        separator = ctk.CTkLabel(record_frame,
                                text="OR",
                                font=ctk.CTkFont(size=12, weight="bold"),
                                text_color=["#666666", "#888888"])
        separator.pack(side=tk.LEFT, padx=(20, 20))

        # File input
        file_input_frame = ctk.CTkFrame(record_frame, fg_color="transparent")
        file_input_frame.pack(side=tk.LEFT, fill=tk.X, expand=True)

        self.file_entry = ctk.CTkEntry(file_input_frame,
                                       height=45,
                                       font=ctk.CTkFont(size=14),
                                       placeholder_text="Click Browse to select an audio file...",
                                       corner_radius=15,
                                       border_width=2,
                                       border_color=["#4A90E2", "#5BA3F5"])
        self.file_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 15))

        self.browse_btn = ctk.CTkButton(file_input_frame,
                                        text="🔍 Browse",
                                        command=self.browse_file,
                                        width=120,
                                        height=45,
                                        font=ctk.CTkFont(size=14, weight="bold"),
                                        corner_radius=15)
        self.browse_btn.pack(side=tk.RIGHT)

        # Method selection
        method_section = ctk.CTkFrame(main_container,
                                      fg_color=["#1A1A2E", "#252540"],
                                      corner_radius=20,
                                      border_width=1,
                                      border_color=["#333355", "#444466"])
        method_section.pack(fill=tk.X, pady=(0, 20))

        method_header = ctk.CTkLabel(method_section,
                                     text="⚙️ Processing Method",
                                     font=ctk.CTkFont(size=18, weight="bold"),
                                     text_color=["#E0E0E0", "#F0F0F0"])
        method_header.pack(anchor="w", padx=20, pady=(15, 10))

        method_frame = ctk.CTkFrame(method_section, fg_color="transparent")
        method_frame.pack(fill=tk.X, padx=20, pady=(0, 15))

        self.method_var = tk.StringVar(value="auto")
        methods = [("🎯 Auto (Smart Detection)", "auto"),
                   ("⚡ Inline Processing", "inline"),
                   ("☁️ Cloud Upload", "upload")]
        for i, (text, value) in enumerate(methods):
            radio = ctk.CTkRadioButton(method_frame,
                                       text=text,
                                       variable=self.method_var,
                                       value=value,
                                       font=ctk.CTkFont(size=14),
                                       radiobutton_width=20,
                                       radiobutton_height=20)
            radio.pack(side=tk.LEFT, padx=(0, 30), pady=5)

        # Prompts section
        prompts_container = ctk.CTkFrame(main_container,
                                        fg_color=["#1A1A2E", "#252540"],
                                        corner_radius=20,
                                        border_width=1,
                                        border_color=["#333355", "#444466"])
        prompts_container.pack(fill=tk.BOTH, expand=True, pady=(0, 20))
        
        # Prompts header with language selection
        prompts_header_frame = ctk.CTkFrame(prompts_container, fg_color="transparent")
        prompts_header_frame.pack(fill=tk.X, padx=20, pady=(15, 10))
        
        prompts_header = ctk.CTkLabel(prompts_header_frame,
                                     text="📝 Prompts",
                                     font=ctk.CTkFont(size=18, weight="bold"),
                                     text_color=["#E0E0E0", "#F0F0F0"])
        prompts_header.pack(side=tk.LEFT)
        
        # Language selection (only show if multiple languages available)
        if len(AVAILABLE_LANGUAGES) > 1:
            lang_frame = ctk.CTkFrame(prompts_header_frame, fg_color="transparent")
            lang_frame.pack(side=tk.RIGHT)
            
            lang_label = ctk.CTkLabel(lang_frame,
                                     text="Language:",
                                     font=ctk.CTkFont(size=12),
                                     text_color=["#AAAAAA", "#CCCCCC"])
            lang_label.pack(side=tk.LEFT, padx=(0, 8))
            
            self.language_var = tk.StringVar(value=self.current_language or "")
            self.language_combo = ctk.CTkOptionMenu(lang_frame,
                                                   variable=self.language_var,
                                                   values=list(AVAILABLE_LANGUAGES.keys()),
                                                   command=self.on_language_change,
                                                   width=80,
                                                   height=28,
                                                   font=ctk.CTkFont(size=12))
            self.language_combo.pack(side=tk.RIGHT)
        elif len(AVAILABLE_LANGUAGES) == 1:
            # Show current language as label
            current_lang = list(AVAILABLE_LANGUAGES.keys())[0]
            lang_label = ctk.CTkLabel(prompts_header_frame,
                                     text=f"Language: {current_lang}",
                                     font=ctk.CTkFont(size=12),
                                     text_color=["#AAAAAA", "#CCCCCC"])
            lang_label.pack(side=tk.RIGHT)
        else:
            # Show error indicator
            error_label = ctk.CTkLabel(prompts_header_frame,
                                      text="⚠️ No prompt files",
                                      font=ctk.CTkFont(size=12),
                                      text_color=["#FF6B6B", "#FF5252"])
            error_label.pack(side=tk.RIGHT)
        
        # Prompts tabview
        self.prompts_tabview = ctk.CTkTabview(prompts_container,
                                              height=180,
                                              corner_radius=15,
                                              border_width=1,
                                              border_color=["#4A90E2", "#5BA3F5"])
        self.prompts_tabview.pack(fill=tk.BOTH, expand=True, padx=20, pady=(0, 15))

        transcript_tab = self.prompts_tabview.add("📝 Transcript Prompt")
        self.transcript_text = ctk.CTkTextbox(transcript_tab,
                                              font=ctk.CTkFont(size=13),
                                              corner_radius=15,
                                              border_width=2,
                                              border_color=["#333355", "#444466"])
        self.transcript_text.pack(fill=tk.BOTH, expand=True, padx=15, pady=15)
        self.transcript_text.insert("1.0", DEFAULT_TRANS_PROMPT)

        memo_tab = self.prompts_tabview.add("📋 Memo Prompt")
        self.memo_text = ctk.CTkTextbox(memo_tab,
                                        font=ctk.CTkFont(size=13),
                                        corner_radius=15,
                                        border_width=2,
                                        border_color=["#333355", "#444466"])
        self.memo_text.pack(fill=tk.BOTH, expand=True, padx=15, pady=15)
        self.memo_text.insert("1.0", DEFAULT_MEMO_PROMPT)

        # Results
        results_section = ctk.CTkFrame(main_container,
                                       fg_color=["#1A1A2E", "#252540"],
                                       corner_radius=20,
                                       border_width=1,
                                       border_color=["#333355", "#444466"])
        results_section.pack(fill=tk.BOTH, expand=True, pady=(0, 20))

        results_header = ctk.CTkLabel(results_section,
                                      text="📊 Processing Results",
                                      font=ctk.CTkFont(size=18, weight="bold"),
                                      text_color=["#E0E0E0", "#F0F0F0"])
        results_header.pack(anchor="w", padx=20, pady=(15, 10))


        self.results_text = ctk.CTkTextbox(results_section,
                                           height=120,
                                           font=ctk.CTkFont(size=12),
                                           corner_radius=15,
                                           border_width=2,
                                           border_color=["#333355", "#444466"])
        self.results_text.pack(fill=tk.BOTH, expand=True, padx=20, pady=(0, 15))

        # Control panel
        control_panel = ctk.CTkFrame(main_container,
                                     fg_color=["#1E1E2E", "#2A2A40"],
                                     corner_radius=20,
                                     border_width=2,
                                     border_color=["#4A90E2", "#357ABD"])
        control_panel.pack(fill=tk.X)

        control_inner = ctk.CTkFrame(control_panel, fg_color="transparent")
        control_inner.pack(fill=tk.X, padx=20, pady=15)

        status_frame = ctk.CTkFrame(control_inner, fg_color="transparent")
        status_frame.pack(side=tk.LEFT, fill=tk.X, expand=True)

        self.status_var = tk.StringVar(value="🟢 Ready to process audio")
        self.status_label = ctk.CTkLabel(status_frame,
                                         textvariable=self.status_var,
                                         font=ctk.CTkFont(size=14, weight="bold"),
                                         text_color=["#4A90E2", "#5BA3F5"])
        self.status_label.pack(anchor="w", pady=(0, 8))

        self.progress_bar = ctk.CTkProgressBar(status_frame,
                                               height=8,
                                               corner_radius=4,
                                               progress_color=["#4A90E2", "#5BA3F5"])
        self.progress_bar.pack(fill=tk.X, pady=(0, 5))
        self.progress_bar.set(0)

        # API Key button
        api_key_btn = ctk.CTkButton(control_inner,
                                   text="🔑 API Key",
                                   command=self.show_api_key_dialog,
                                   width=90,
                                   height=35,
                                   font=ctk.CTkFont(size=12),
                                   fg_color=["#6C5CE7", "#5A4FCF"])
        api_key_btn.pack(side=tk.RIGHT, padx=(10, 0))
        
        self.process_btn = ctk.CTkButton(control_inner,
                                         text="🚀 Process Audio",
                                         command=self.process_audio,
                                         width=180,
                                         height=50,
                                         font=ctk.CTkFont(size=16, weight="bold"),
                                         corner_radius=25)
        self.process_btn.pack(side=tk.RIGHT, padx=(20, 0))
        
    def toggle_recording(self):
        """Toggle audio recording."""
        if not self.recording:
            self.start_recording()
        else:
            self.stop_recording()
    
    def start_recording(self):
        """Start audio recording."""
        if self.audio_recorder.start_recording():
            self.recording = True
            self.record_btn.configure(text="🛑 Stop Recording", fg_color=["#F44336", "#FF5252"])
            self.record_status_var.set("Recording... 🔴")
            self.log_message("🎤 Recording started...")
            self.update_status("🔴 Recording in progress...", ["#FF9800", "#FFB74D"])
        else:
            self.log_message("❌ Failed to start recording")
    
    def stop_recording(self):
        """Stop audio recording."""
        self.recording = False
        self.record_btn.configure(text="🎤 Start Recording", fg_color=["#4CAF50", "#66BB6A"])
        self.record_status_var.set("Stopping recording...")
        self.log_message("⏹️ Stopping recording...")
        
        # Stop recording in a separate thread to avoid blocking UI
        threading.Thread(target=self.audio_recorder.stop_recording, daemon=True).start()
    
    def on_recording_complete(self, audio_path):
        """Callback when recording is complete."""
        if audio_path and os.path.exists(audio_path):
            self.record_status_var.set("Recording complete")
            file_size = os.path.getsize(audio_path) / (1024 * 1024)  # MB
            self.log_message(f"✅ Recording saved: {os.path.basename(audio_path)} ({file_size:.1f} MB)")
            
            # Store session timestamp from the audio recorder
            self.current_session_timestamp = self.audio_recorder.session_timestamp
            
            # Set the recorded file as the audio file and start processing
            if self.set_audio_file(audio_path):
                self.log_message("🚀 Auto-processing recorded audio...")
                # Auto-process the recorded file after a short delay
                self.after(1000, self.process_audio)
        else:
            self.record_status_var.set("Recording failed")
            self.log_message("❌ Recording failed to save")
            self.update_status("❌ Recording failed", ["#FF5252", "#FF6B6B"])
            
    def setup_drag_drop(self):
        """Setup file entry click handler."""
        self.file_entry.bind("<Button-1>", self.on_entry_click)
        
    def on_entry_click(self, event):
        """Handle click on file entry to open file dialog."""
        self.browse_file()
    
    def check_api_key(self):
        """Check if API key exists, prompt user to enter if missing."""
        if not API_KEY:
            self.log_message("⚠️ Google API key not found!")
            self.show_api_key_dialog()
    
    def show_api_key_dialog(self):
        """Show dialog to enter and save API key."""
        dialog = ctk.CTkToplevel(self)
        dialog.title("API Key Required")
        dialog.geometry("500x300")
        dialog.transient(self)
        dialog.grab_set()
        
        # Center the dialog
        dialog.update_idletasks()
        x = (dialog.winfo_screenwidth() // 2) - (500 // 2)
        y = (dialog.winfo_screenheight() // 2) - (300 // 2)
        dialog.geometry(f"500x300+{x}+{y}")
        
        # Content frame
        content_frame = ctk.CTkFrame(dialog, fg_color="transparent")
        content_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        # Title
        title_label = ctk.CTkLabel(content_frame,
                                  text="🔑 Google API Key Required",
                                  font=ctk.CTkFont(size=18, weight="bold"),
                                  text_color=["#4A90E2", "#5BA3F5"])
        title_label.pack(pady=(0, 10))
        
        # Instructions
        instructions = ctk.CTkLabel(content_frame,
                                   text="Get API key from Google AI Studio:\nhttps://aistudio.google.com/app/apikey\n\nPaste your API key below:",
                                   font=ctk.CTkFont(size=12),
                                   justify="center")
        instructions.pack(pady=(0, 15))
        
        # API key entry
        self.api_key_entry = ctk.CTkEntry(content_frame,
                                         placeholder_text="Enter your Google API key here...",
                                         width=400,
                                         height=40,
                                         font=ctk.CTkFont(size=12))  # Show key in plain text
        
        # Show existing key if available
        if API_KEY:
            self.api_key_entry.insert(0, API_KEY)
        
        self.api_key_entry.pack(pady=(0, 20))
        
        # Buttons
        button_frame = ctk.CTkFrame(content_frame, fg_color="transparent")
        button_frame.pack(fill=tk.X)
        
        save_btn = ctk.CTkButton(button_frame,
                                text="Save API Key",
                                command=lambda: self.save_api_key(dialog),
                                width=150,
                                height=35,
                                font=ctk.CTkFont(size=12, weight="bold"))
        save_btn.pack(side=tk.LEFT, padx=(50, 10))
        
        cancel_btn = ctk.CTkButton(button_frame,
                                  text="Cancel",
                                  command=dialog.destroy,
                                  width=100,
                                  height=35,
                                  font=ctk.CTkFont(size=12),
                                  fg_color=["#FF6B6B", "#FF5252"])
        cancel_btn.pack(side=tk.LEFT)
        
        # Open browser button
        browser_btn = ctk.CTkButton(button_frame,
                                   text="Get API key",
                                   command=lambda: webbrowser.open("https://aistudio.google.com/app/apikey"),
                                   width=130,
                                   height=35,
                                   font=ctk.CTkFont(size=12),
                                   fg_color=["#4CAF50", "#66BB6A"])
        browser_btn.pack(side=tk.RIGHT, padx=(10, 50))
        
        # Focus on entry
        self.api_key_entry.focus()
    
    def save_api_key(self, dialog):
        """Save the API key to environment and user profile."""
        api_key = self.api_key_entry.get().strip()
        
        if not api_key:
            self.show_error_message("Please enter a valid API key")
            return
            
        if len(api_key) < 30:  # Basic validation
            self.show_error_message("API key seems too short. Please check and try again.")
            return
        
        try:
            # Set for current session
            os.environ['GEMINI_API_KEY'] = api_key
            
            # Save to user profile for persistence
            self.save_api_key_to_profile(api_key)
            
            # Update global variable
            global API_KEY
            API_KEY = api_key
            
            self.log_message("✅ API key saved successfully!")
            self.log_message("🔄 Please restart the application for changes to take effect.")
            dialog.destroy()
            
        except Exception as e:
            self.show_error_message(f"Error saving API key: {str(e)}")
    
    def save_api_key_to_profile(self, api_key):
        """Save API key to user environment permanently."""
        import platform
        import subprocess
        
        system = platform.system()
        
        if system == "Windows":
            # Add to user environment variables
            try:
                subprocess.run([
                    'setx', 'GEMINI_API_KEY', api_key
                ], check=True, capture_output=True)
                self.log_message("💾 API key saved to Windows user environment")
            except subprocess.CalledProcessError:
                self.log_message("⚠️ Could not save to Windows environment. Set manually.")
        
        elif system in ["Linux", "Darwin"]:
            # Add to shell profile
            home_dir = os.path.expanduser("~")
            shell_profiles = ['.bashrc', '.zshrc', '.bash_profile', '.profile']
            
            for profile in shell_profiles:
                profile_path = os.path.join(home_dir, profile)
                if os.path.exists(profile_path):
                    try:
                        with open(profile_path, 'a') as f:
                            f.write(f"\n# Gemini API Key for MemoMaker\nexport GEMINI_API_KEY='{api_key}'\n")
                        self.log_message(f"💾 API key saved to {profile}")
                        break
                    except Exception:
                        continue
            else:
                self.log_message("⚠️ Could not save to shell profile. Set manually.")
    
    def show_error_message(self, message):
        """Show error message in a popup."""
        error_dialog = ctk.CTkToplevel(self)
        error_dialog.title("Error")
        error_dialog.geometry("350x150")
        error_dialog.transient(self)
        error_dialog.grab_set()
        
        # Center the dialog
        error_dialog.update_idletasks()
        x = (error_dialog.winfo_screenwidth() // 2) - (350 // 2)
        y = (error_dialog.winfo_screenheight() // 2) - (150 // 2)
        error_dialog.geometry(f"350x150+{x}+{y}")
        
        content = ctk.CTkFrame(error_dialog, fg_color="transparent")
        content.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        error_label = ctk.CTkLabel(content,
                                  text=f"❌ {message}",
                                  font=ctk.CTkFont(size=12),
                                  wraplength=300)
        error_label.pack(expand=True)
        
        ok_btn = ctk.CTkButton(content,
                              text="OK",
                              command=error_dialog.destroy,
                              width=80,
                              height=30)
        ok_btn.pack(pady=(10, 0))
    
    def on_language_change(self, selected_language):
        """Handle language selection change."""
        if selected_language in AVAILABLE_LANGUAGES:
            self.current_language = selected_language
            self.load_prompts_for_language(selected_language)
            self.log_message(f"🌍 Language changed to: {selected_language}")
    
    def load_prompts_for_language(self, language_code):
        """Load prompts for the selected language."""
        transcript_prompt, memo_prompt = read_prompts_from_file(language_code)
        
        if transcript_prompt and memo_prompt:
            # Clear and update transcript prompt
            self.transcript_text.delete("1.0", tk.END)
            self.transcript_text.insert("1.0", transcript_prompt)
            
            # Clear and update memo prompt 
            self.memo_text.delete("1.0", tk.END)
            self.memo_text.insert("1.0", memo_prompt)
            
            self.log_message(f"✅ Prompts loaded for language: {language_code}")
        else:
            error_msg = f"❌ ERROR: Could not load prompts for language: {language_code}"
            self.transcript_text.delete("1.0", tk.END)
            self.transcript_text.insert("1.0", error_msg)
            self.memo_text.delete("1.0", tk.END)
            self.memo_text.insert("1.0", error_msg)
            self.log_message(error_msg)
    
    def set_audio_file(self, file_path):
        """Set and validate audio file path."""
        # Validate the file
        is_valid, message = validate_audio_file(file_path)
        
        if not is_valid:
            self.log_message(f"❌ File validation failed: {message}")
            self.update_status("❌ Invalid file", ["#FF5252", "#FF6B6B"])
            return False
        
        # File is valid
        self.audio_file_path = os.path.abspath(file_path)  # Use absolute path
        self.file_entry.delete(0, tk.END)
        self.file_entry.insert(0, self.audio_file_path)
        
        file_size = os.path.getsize(file_path)
        size_mb = file_size / (1024 * 1024)
        self.log_message(f"✅ Selected: {os.path.basename(file_path)} ({size_mb:.2f} MB)")
        self.log_message(f"📍 Validation: {message}")
        
        return True
    
    def browse_file(self):
        file_path = filedialog.askopenfilename(
            title="Select Audio File",
            filetypes=SUPPORTED_AUDIO_TYPES,
            initialdir=os.getcwd()
        )
        if file_path:
            self.set_audio_file(file_path)

    def log_message(self, message):
        timestamp = time.strftime("%H:%M:%S")
        formatted_message = f"[{timestamp}] {message}"
        self.results_text.insert(tk.END, formatted_message + "\n")
        self.results_text.see(tk.END)

    def update_status(self, message, color=None):
        if color:
            self.status_label.configure(text_color=color)
        self.status_var.set(message)
        self.update_idletasks()

    def process_audio(self):
        if self.processing:
            return
        
        # Validate file selection
        if not self.audio_file_path:
            self.log_message("❌ Error: Please select a valid audio file first.")
            self.update_status("❌ No file selected", ["#FF5252", "#FF6B6B"])
            return
        
        # Re-validate file in case it was moved/deleted
        is_valid, message = validate_audio_file(self.audio_file_path)
        if not is_valid:
            self.log_message(f"❌ File validation failed: {message}")
            self.update_status("❌ File validation failed", ["#FF5252", "#FF6B6B"])
            return

        # Validate prompts
        transcript_prompt = self.transcript_text.get("1.0", tk.END).strip() or DEFAULT_TRANS_PROMPT
        memo_prompt = self.memo_text.get("1.0", tk.END).strip() or DEFAULT_MEMO_PROMPT
        
        trans_valid, trans_msg = validate_prompt_input(transcript_prompt)
        if not trans_valid:
            self.log_message(f"❌ Transcript prompt validation failed: {trans_msg}")
            self.update_status("❌ Invalid transcript prompt", ["#FF5252", "#FF6B6B"])
            return
            
        memo_valid, memo_msg = validate_prompt_input(memo_prompt)
        if not memo_valid:
            self.log_message(f"❌ Memo prompt validation failed: {memo_msg}")
            self.update_status("❌ Invalid memo prompt", ["#FF5252", "#FF6B6B"])
            return
        
        method = self.method_var.get()

        self.processing = True
        self.api_start_time = time.time()
        self.progress_bar.set(0.1)
        self.process_btn.configure(state="disabled", text="⏳ Processing...")
        self.update_status("🔄 Processing audio file...", ["#FF9800", "#FFB74D"])
        self.log_message("🚀 Starting audio processing...")

        thread = threading.Thread(
            target=self.process_thread,
            args=(self.audio_file_path, transcript_prompt, memo_prompt, method)
        )
        thread.daemon = True
        thread.start()

    def process_thread(self, audio_file_path, transcript_prompt, memo_prompt, method):
        file_size = os.path.getsize(audio_file_path)
        processing_error = None
        
        try:
            genai.configure(api_key=API_KEY)
            model = genai.GenerativeModel(MODEL_NAME)

            self.update_status("🎯 Generating transcript...")
            self.progress_bar.set(0.2)
            self.log_message(f"🔧 Using {method} method (File size: {file_size:,} bytes)")

            if method == "upload" or (method == "auto" and file_size >= INLINE_THRESHOLD):
                self.log_message("☁️ Using cloud upload method")
                self.progress_bar.set(0.3)
                uploaded_file = genai.upload_file(path=audio_file_path)
                self.progress_bar.set(0.4)
                transcript_response = model.generate_content([transcript_prompt, uploaded_file])
                self.progress_bar.set(0.6)
            else:
                self.log_message("⚡ Using inline processing method")
                self.progress_bar.set(0.3)
                with open(audio_file_path, 'rb') as f:
                    audio_data = f.read()
                self.progress_bar.set(0.4)
                transcript_response = model.generate_content([
                    transcript_prompt,
                    {"mime_type": "audio/mp3", "data": audio_data}
                ])
                self.progress_bar.set(0.6)

            transcript = transcript_response.text
            self.progress_bar.set(0.7)
            self.log_message("✅ Transcript generated successfully!")
            
            # Display transcript API usage
            transcript_usage = format_api_usage("Transcript Generation", file_size, 
                                              time.time() - self.api_start_time, True, None, transcript_response)
            self.log_message(transcript_usage)

            # Generate transcript filename using session timestamp
            if hasattr(self, 'current_session_timestamp') and self.current_session_timestamp:
                transcript_filename = os.path.join(RECORDINGS_FOLDER, f"{self.current_session_timestamp}-transcript.txt")
            else:
                # Fallback for file-based processing
                timestamp = time.strftime("%y%m%d-%H%M%S")
                transcript_filename = os.path.join(RECORDINGS_FOLDER, f"{timestamp}-transcript.txt")
            
            with open(transcript_filename, "w", encoding="utf-8") as f:
                f.write(transcript)
            self.log_message(f"💾 Transcript saved to {os.path.basename(transcript_filename)}")
            self.transcript = transcript

            self.update_status("📋 Generating intelligent memo...")
            self.progress_bar.set(0.8)
            memo_start_time = time.time()
            memo_response = model.generate_content([memo_prompt, transcript])
            self.progress_bar.set(0.9)
            memo_content = memo_response.text.replace("```markdown", "").replace("```md", "").replace("```", "").strip()
            
            # Display memo API usage
            memo_usage = format_api_usage("Memo Generation", len(transcript.encode('utf-8')), 
                                        time.time() - memo_start_time, True, None, memo_response)
            self.log_message(memo_usage)

            # Generate memo filename using session timestamp
            if hasattr(self, 'current_session_timestamp') and self.current_session_timestamp:
                memo_filename = os.path.join(RECORDINGS_FOLDER, f"{self.current_session_timestamp}-memo.md")
            else:
                # Fallback for file-based processing
                timestamp = time.strftime("%y%m%d-%H%M%S")
                memo_filename = os.path.join(RECORDINGS_FOLDER, f"{timestamp}-memo.md")
            
            with open(memo_filename, "w", encoding="utf-8") as f:
                f.write(memo_content)
            self.log_message(f"📋 Memo saved to {os.path.basename(memo_filename)}")

            # Calculate total processing time
            processing_time = time.time() - self.api_start_time
            self.progress_bar.set(1.0)
            
            # Display total usage statistics
            total_usage = format_api_usage("Total Processing", file_size, processing_time, success=True)
            self.log_message(total_usage)
            self.log_message(f"⏱️ Total processing completed in {processing_time:.2f} seconds")
            
            self.update_status("🎉 Processing completed successfully!", ["#4CAF50", "#66BB6A"])
            self.log_message(f"📄 Opening memo file: {os.path.basename(memo_filename)}")
            
            # Use absolute path for cross-platform compatibility
            memo_path = os.path.abspath(memo_filename)
            webbrowser.open(f"file://{memo_path}")

        except Exception as e:
            processing_error = str(e)
            self.log_message(f"💥 Error occurred: {processing_error}")
            self.update_status("❌ Processing failed", ["#FF5252", "#FF6B6B"])
            
            # Display failed usage info
            if self.api_start_time:
                processing_time = time.time() - self.api_start_time
                failed_usage = format_api_usage("Failed Processing", file_size, processing_time, success=False, error=processing_error)
                self.log_message(failed_usage)
        finally:
            self.processing = False
            # Keep progress bar at current level for a moment, then reset
            self.after(2000, lambda: self.progress_bar.set(0))
            self.process_btn.configure(state="normal", text="🚀 Process Audio")
            self.api_start_time = None

def main():
    if len(os.sys.argv) > 1:
        cli_main()
    else:
        app = GeminiAudioApp()
        app.mainloop()

def cli_main():
    parser = argparse.ArgumentParser(
        description="Interact with audio using the Gemini API to generate transcripts and memos."
    )
    parser.add_argument("audio_file", help="Path to the audio file (e.g., MP3) to send")
    parser.add_argument("--prompt", default=DEFAULT_TRANS_PROMPT, help="Prompt for the Gemini API")
    parser.add_argument("--method", choices=["auto", "inline", "upload"], default="auto",
                        help="Audio upload method")
    args = parser.parse_args()

    # Validate audio file
    is_valid, message = validate_audio_file(args.audio_file)
    if not is_valid:
        print(f"❌ File validation failed: {message}")
        return
    
    # Validate prompt
    prompt_valid, prompt_msg = validate_prompt_input(args.prompt)
    if not prompt_valid:
        print(f"❌ Prompt validation failed: {prompt_msg}")
        return

    file_size = os.path.getsize(args.audio_file)
    start_time = time.time()
    genai.configure(api_key=API_KEY)
    model = genai.GenerativeModel(MODEL_NAME)

    try:
        if args.method == "upload" or (args.method == "auto" and file_size >= INLINE_THRESHOLD):
            print(f"☁️ Using file upload method (File size: {file_size:,} bytes)")
            uploaded_file = genai.upload_file(path=args.audio_file)
            transcript_response = model.generate_content([args.prompt, uploaded_file])
        else:
            print(f"⚡ Using inline audio data method (File size: {file_size:,} bytes)")
            with open(args.audio_file, 'rb') as f:
                audio_data = f.read()
            transcript_response = model.generate_content(
                [args.prompt, {"mime_type": "audio/mp3", "data": audio_data}]
            )

        transcript = transcript_response.text
        print("📝 Transcript:")
        print(transcript)
        # Generate filenames for CLI mode
        timestamp = time.strftime("%y%m%d-%H%M%S")
        transcript_filename = os.path.join(RECORDINGS_FOLDER, f"{timestamp}-transcript.txt")
        memo_filename = os.path.join(RECORDINGS_FOLDER, f"{timestamp}-memo.md")
        
        with open(transcript_filename, "w", encoding="utf-8") as f:
            f.write(transcript)
        print(f"💾 Transcript saved to {os.path.basename(transcript_filename)}")

        memo_response = model.generate_content([DEFAULT_MEMO_PROMPT, transcript])
        memo_content = memo_response.text.replace("```markdown", "").replace("```md", "").replace("```", "").strip()
        with open(memo_filename, "w", encoding="utf-8") as f:
            f.write(memo_content)
        print(f"📋 Memo saved to {os.path.basename(memo_filename)}")
        
        # Display API usage statistics
        processing_time = time.time() - start_time
        
        # Try to get token usage from responses
        transcript_usage = format_api_usage("CLI Transcript", file_size, processing_time/2, True, None, transcript_response)
        memo_usage = format_api_usage("CLI Memo", len(transcript.encode('utf-8')), processing_time/2, True, None, memo_response)
        total_usage = format_api_usage("CLI Total", file_size, processing_time, success=True)
        
        print("\n" + transcript_usage)
        print("\n" + memo_usage) 
        print("\n" + total_usage)
        print(f"\n⏱️ Processing completed in {processing_time:.2f} seconds")

    except Exception as e:
        processing_time = time.time() - start_time
        failed_usage = format_api_usage("CLI Failed Processing", file_size, processing_time, success=False, error=str(e))
        print("\n" + failed_usage)
        print("💥 An error occurred:", e)

if __name__ == "__main__":
    main()