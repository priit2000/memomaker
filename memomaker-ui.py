#!/usr/bin/env python3

import os
import argparse
import threading
import tkinter as tk
from tkinter import ttk, filedialog, scrolledtext
import customtkinter as ctk
from PIL import Image, ImageTk
import google.generativeai as genai
import webbrowser
import math
import time

# ============================================================================
# USER SETTINGS & CONFIGURATION
# ============================================================================

# API Configuration
API_KEY = os.environ.get("GOOGLE_API_KEY")

# Model Settings
MODEL_NAME = 'gemini-flash-latest'

# Prompt Settings
PROMPT_FILE = "transcription-prompt.md"

# File Processing Settings
INLINE_THRESHOLD = 20 * 1024 * 1024  # 20 MB in bytes

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

# Output File Settings
TRANSCRIPT_FILENAME = "transcript.txt"
MEMO_FILENAME = "memo.html"

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
        self.create_widgets()

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
                                       placeholder_text="Select an audio file to process...",
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


    def browse_file(self):
        file_path = filedialog.askopenfilename(
            title="Select Audio File",
            filetypes=SUPPORTED_AUDIO_TYPES
        )
        if file_path:
            self.audio_file_path = file_path
            self.file_entry.delete(0, tk.END)
            self.file_entry.insert(0, file_path)
            file_size = os.path.getsize(file_path)
            size_mb = file_size / (1024 * 1024)
            self.log_message(f"✅ Selected: {os.path.basename(file_path)} ({size_mb:.2f} MB)")
            self.file_entry.configure(border_color=["#4CAF50", "#66BB6A"])
            self.after(2000, lambda: self.file_entry.configure(border_color=["#4A90E2", "#5BA3F5"]))

    def log_message(self, message):
        timestamp = time.strftime("%H:%M:%S")
        formatted_message = f"[{timestamp}] {message}"
        self.results_text.insert(tk.END, formatted_message + "\n")
        self.results_text.see(tk.END)
        self.after(100, lambda: self.results_text.see(tk.END))

    def update_status(self, message, color=None):
        if color:
            self.status_label.configure(text_color=color)
        self.status_var.set(message)
        self.update_idletasks()

    def process_audio(self):
        if self.processing:
            return
        if not self.audio_file_path or not os.path.exists(self.audio_file_path):
            self.log_message("❌ Error: Please select a valid audio file first.")
            self.update_status("❌ No file selected", ["#FF5252", "#FF6B6B"])
            return

        transcript_prompt = self.transcript_text.get("1.0", tk.END).strip() or DEFAULT_TRANS_PROMPT
        memo_prompt = self.memo_text.get("1.0", tk.END).strip() or DEFAULT_MEMO_PROMPT
        method = self.method_var.get()

        self.processing = True
        self.progress_bar.set(0.5)
        self.process_btn.configure(state="disabled", text="⏳ Processing...")
        self.update_status("🔄 Processing audio file...", ["#FF9800", "#FFB74D"])

        thread = threading.Thread(
            target=self.process_thread,
            args=(self.audio_file_path, transcript_prompt, memo_prompt, method)
        )
        thread.daemon = True
        thread.start()

    def process_thread(self, audio_file_path, transcript_prompt, memo_prompt, method):
        try:
            file_size = os.path.getsize(audio_file_path)
            genai.configure(api_key=API_KEY)
            model = genai.GenerativeModel(MODEL_NAME)

            self.update_status("🎯 Generating transcript...")
            self.log_message(f"🔧 Using {method} method (File size: {file_size:,} bytes)")

            if method == "upload" or (method == "auto" and file_size >= INLINE_THRESHOLD):
                self.log_message("☁️ Using cloud upload method")
                uploaded_file = genai.upload_file(path=audio_file_path)
                transcript_response = model.generate_content([transcript_prompt, uploaded_file])
            else:
                self.log_message("⚡ Using inline processing method")
                with open(audio_file_path, 'rb') as f:
                    audio_data = f.read()
                transcript_response = model.generate_content([
                    transcript_prompt,
                    {"mime_type": "audio/mp3", "data": audio_data}
                ])

            transcript = transcript_response.text
            self.log_message("✅ Transcript generated successfully!")

            with open(TRANSCRIPT_FILENAME, "w", encoding="utf-8") as f:
                f.write(transcript)
            self.log_message(f"💾 Transcript saved to {TRANSCRIPT_FILENAME}")
            self.transcript = transcript

            self.update_status("📋 Generating intelligent memo...")
            memo_response = model.generate_content([memo_prompt, transcript])
            memo_content = memo_response.text.replace("```html", "").replace("```", "").strip()

            if not memo_content.strip().startswith('<!DOCTYPE html>'):
                memo_content = f"{memo_content}"

            with open(MEMO_FILENAME, "w", encoding="utf-8") as f:
                f.write(memo_content)
            self.log_message(f"📋 Memo saved to {MEMO_FILENAME}")

            self.update_status("🎉 Processing completed successfully!", ["#4CAF50", "#66BB6A"])
            self.log_message("🌐 Opening memo in browser...")
            webbrowser.open(MEMO_FILENAME)

        except Exception as e:
            self.log_message(f"💥 Error occurred: {str(e)}")
            self.update_status("❌ Processing failed", ["#FF5252", "#FF6B6B"])
        finally:
            self.processing = False
            self.progress_bar.set(0)
            self.process_btn.configure(state="normal", text="🚀 Process Audio")

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

    if not os.path.exists(args.audio_file):
        print("❌ Error: The file does not exist.")
        return

    file_size = os.path.getsize(args.audio_file)
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
        memo_content = memo_response.text.replace("```html", "").replace("```", "").strip()
        if not memo_content.strip().startswith('<!DOCTYPE html>'):
            memo_content = f"{memo_content}"
        with open(MEMO_FILENAME, "w", encoding="utf-8") as f:
            f.write(memo_content)
        print(f"📋 Memo saved to {MEMO_FILENAME}")

    except Exception as e:
        print("💥 An error occurred:", e)

if __name__ == "__main__":
    main()
