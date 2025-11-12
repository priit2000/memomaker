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

# ============================================================================
# USER SETTINGS & CONFIGURATION
# ============================================================================

# API Configuration
API_KEY = os.environ.get("GOOGLE_API_KEY")

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


# File paths (cross-platform compatible)
PROMPT_FILE = os.path.join(os.getcwd(), "transcription-prompt.md")
TRANSCRIPT_FILENAME = os.path.join(os.getcwd(), "transcript.txt")
MEMO_FILENAME = os.path.join(os.getcwd(), "memo.md")

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

# Function to read prompts from prompt file
def read_prompts_from_file():
    try:
        with open(PROMPT_FILE, "r", encoding="utf-8") as f:
            content = f.read()
        # Split by # Memo section
        parts = content.split("# Memo")
        if len(parts) >= 2:
            transcript_section = parts[0].replace("# Transkriptsioon", "").strip()
            memo_section = parts[1].strip()
            return transcript_section, memo_section
        else:
            return None, None
    except FileNotFoundError:
        return None, None

# Read prompts from file
_transcript_prompt, _memo_prompt = read_prompts_from_file()

DEFAULT_TRANS_PROMPT = _transcript_prompt
DEFAULT_MEMO_PROMPT = _memo_prompt


# UI Settings
APP_TITLE = "✨ Gemini Audio Processor Pro"
APP_SUBTITLE = "Transform audio into intelligent transcripts and memos"
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
        self.create_widgets()
        self.setup_drag_drop()

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

        # File selection
        file_section = ctk.CTkFrame(main_container,
                                    fg_color=["#1A1A2E", "#252540"],
                                    corner_radius=20,
                                    border_width=1,
                                    border_color=["#333355", "#444466"])
        file_section.pack(fill=tk.X, pady=(0, 20))

        file_header = ctk.CTkLabel(file_section,
                                   text="📁 Audio File Selection",
                                   font=ctk.CTkFont(size=18, weight="bold"),
                                   text_color=["#E0E0E0", "#F0F0F0"])
        file_header.pack(anchor="w", padx=20, pady=(15, 10))

        file_input_frame = ctk.CTkFrame(file_section, fg_color="transparent")
        file_input_frame.pack(fill=tk.X, padx=20, pady=(0, 15))

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

        # Prompts
        self.prompts_tabview = ctk.CTkTabview(main_container,
                                              height=200,
                                              corner_radius=20,
                                              border_width=1,
                                              border_color=["#4A90E2", "#5BA3F5"])
        self.prompts_tabview.pack(fill=tk.BOTH, expand=True, pady=(0, 20))

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

        self.process_btn = ctk.CTkButton(control_inner,
                                         text="🚀 Process Audio",
                                         command=self.process_audio,
                                         width=180,
                                         height=50,
                                         font=ctk.CTkFont(size=16, weight="bold"),
                                         corner_radius=25)
        self.process_btn.pack(side=tk.RIGHT, padx=(20, 0))
    def setup_drag_drop(self):
        """Setup file entry click handler."""
        self.file_entry.bind("<Button-1>", self.on_entry_click)
        
    def on_entry_click(self, event):
        """Handle click on file entry to open file dialog."""
        self.browse_file()
    
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

            with open(TRANSCRIPT_FILENAME, "w", encoding="utf-8") as f:
                f.write(transcript)
            self.log_message(f"💾 Transcript saved to {TRANSCRIPT_FILENAME}")
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

            with open(MEMO_FILENAME, "w", encoding="utf-8") as f:
                f.write(memo_content)
            self.log_message(f"📋 Memo saved to {MEMO_FILENAME}")

            # Calculate total processing time
            processing_time = time.time() - self.api_start_time
            self.progress_bar.set(1.0)
            
            # Display total usage statistics
            total_usage = format_api_usage("Total Processing", file_size, processing_time, success=True)
            self.log_message(total_usage)
            self.log_message(f"⏱️ Total processing completed in {processing_time:.2f} seconds")
            
            self.update_status("🎉 Processing completed successfully!", ["#4CAF50", "#66BB6A"])
            self.log_message(f"📄 Opening memo file: {MEMO_FILENAME}")
            
            # Use absolute path for cross-platform compatibility
            memo_path = os.path.abspath(MEMO_FILENAME)
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
        with open(TRANSCRIPT_FILENAME, "w", encoding="utf-8") as f:
            f.write(transcript)
        print(f"💾 Transcript saved to {TRANSCRIPT_FILENAME}")

        memo_response = model.generate_content([DEFAULT_MEMO_PROMPT, transcript])
        memo_content = memo_response.text.replace("```markdown", "").replace("```md", "").replace("```", "").strip()
        with open(MEMO_FILENAME, "w", encoding="utf-8") as f:
            f.write(memo_content)
        print(f"📋 Memo saved to {MEMO_FILENAME}")
        
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
