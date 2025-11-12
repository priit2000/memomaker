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

# File Processing Settings
INLINE_THRESHOLD = 20 * 1024 * 1024  # 20 MB in bytes

# Function to read prompts from transcription-prompt.md
def read_prompts_from_file():
    try:
        with open("transcription-prompt.md", "r", encoding="utf-8") as f:
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

# Animation Settings
ANIMATION_SPEED = 0.15
PULSE_SPEED = 50
FLOAT_SPEED = 100
PARTICLE_COUNT = 15

# Audio File Types
SUPPORTED_AUDIO_TYPES = [
    ("Audio Files", "*.mp3 *.wav *.m4a *.ogg *.flac *.aac"),
    ("All Files", "*.*")
]

# ============================================================================
# END USER SETTINGS
# ============================================================================

class AnimatedFrame(ctk.CTkFrame):
    def __init__(self, parent, **kwargs):
        super().__init__(parent, **kwargs)
        self.original_y = 0
        self.target_y = 0
        self.animation_speed = ANIMATION_SPEED
        
    def animate_in(self, delay=0):
        self.after(int(delay * 1000), self._start_animation)
        
    def _start_animation(self):
        self.original_y = self.winfo_y()
        self.place(y=self.original_y + 50)
        self._animate_step()
        
    def _animate_step(self):
        current_y = self.winfo_y()
        if abs(current_y - self.original_y) > 1:
            new_y = current_y + (self.original_y - current_y) * self.animation_speed
            self.place(y=new_y)
            self.after(16, self._animate_step)

class GlowButton(ctk.CTkButton):
    def __init__(self, parent, **kwargs):
        self.glow_color = kwargs.pop('glow_color', '#4A90E2')
        super().__init__(parent, **kwargs)
        self.bind("<Enter>", self.on_enter)
        self.bind("<Leave>", self.on_leave)
        
    def on_enter(self, event):
        self.configure(fg_color=self.glow_color, hover_color=self.glow_color)
        
    def on_leave(self, event):
        self.configure(fg_color=["#3B8ED0", "#1F6AA5"], hover_color=["#36719F", "#144870"])

class PulsingProgressBar(ctk.CTkProgressBar):
    def __init__(self, parent, **kwargs):
        super().__init__(parent, **kwargs)
        self.is_pulsing = False
        self.pulse_direction = 1
        self.pulse_value = 0.0
        
    def start_pulse(self):
        self.is_pulsing = True
        self._pulse_step()
        
    def stop_pulse(self):
        self.is_pulsing = False
        self.set(0)
        
    def _pulse_step(self):
        if not self.is_pulsing:
            return
            
        self.pulse_value += 0.02 * self.pulse_direction
        if self.pulse_value >= 1.0:
            self.pulse_direction = -1
        elif self.pulse_value <= 0.0:
            self.pulse_direction = 1
            
        self.set(self.pulse_value)
        self.after(PULSE_SPEED, self._pulse_step)

class FloatingLabel(ctk.CTkLabel):
    def __init__(self, parent, **kwargs):
        super().__init__(parent, **kwargs)
        self.float_offset = 0
        self.float_direction = 1
        self.is_floating = False
        
    def start_float(self):
        self.is_floating = True
        self._float_step()
        
    def stop_float(self):
        self.is_floating = False
        
    def _float_step(self):
        if not self.is_floating:
            return
            
        self.float_offset += 0.5 * self.float_direction
        if self.float_offset >= 5:
            self.float_direction = -1
        elif self.float_offset <= -5:
            self.float_direction = 1
            
        # Create subtle floating effect with padding
        self.configure(pady=(10 + int(self.float_offset), 10 - int(self.float_offset)))
        self.after(FLOAT_SPEED, self._float_step)

class ParticleCanvas(tk.Canvas):
    def __init__(self, parent, **kwargs):
        super().__init__(parent, bg='#1a1a1a', highlightthickness=0, **kwargs)
        self.particles = []
        self.running = False
        
    def start_particles(self):
        self.running = True
        for _ in range(PARTICLE_COUNT):
            self.particles.append({
                'x': self.winfo_reqwidth() * 0.5,
                'y': self.winfo_reqheight() * 0.5,
                'vx': (tk._default_root.tk.call('expr', 'rand()') - 0.5) * 2,
                'vy': (tk._default_root.tk.call('expr', 'rand()') - 0.5) * 2,
                'size': 2 + tk._default_root.tk.call('expr', 'rand()') * 3,
                'color': '#4A90E2'
            })
        self._animate_particles()
        
    def stop_particles(self):
        self.running = False
        self.delete("all")
        self.particles = []
        
    def _animate_particles(self):
        if not self.running:
            return
            
        self.delete("all")
        width = self.winfo_width()
        height = self.winfo_height()
        
        for particle in self.particles:
            particle['x'] += particle['vx']
            particle['y'] += particle['vy']
            
            # Bounce off edges
            if particle['x'] <= 0 or particle['x'] >= width:
                particle['vx'] *= -1
            if particle['y'] <= 0 or particle['y'] >= height:
                particle['vy'] *= -1
                
            # Draw particle with glow effect
            x, y = int(particle['x']), int(particle['y'])
            size = int(particle['size'])
            
            # Outer glow
            self.create_oval(x-size-2, y-size-2, x+size+2, y+size+2, 
                           fill='#2A5A9A', outline='', stipple='gray50')
            # Main particle
            self.create_oval(x-size, y-size, x+size, y+size, 
                           fill=particle['color'], outline='')
                           
        self.after(PULSE_SPEED, self._animate_particles)

class GeminiAudioApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        
        # Configure theme and appearance
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")
        
        # Window configuration
        self.title(APP_TITLE)
        self.geometry(f"{WINDOW_WIDTH}x{WINDOW_HEIGHT}")
        self.minsize(MIN_WIDTH, MIN_HEIGHT)
        
        # Configure window icon and styling
        self.configure(fg_color=["#0F0F0F", "#0F0F0F"])
        
        # Application state
        self.audio_file_path = None
        self.transcript = None
        self.processing = False
        
        # Animation properties
        self.pulse_animation_running = False
        
        self.create_widgets()
        self.setup_animations()

    def create_widgets(self):
        # Main container with gradient-like effect
        main_container = ctk.CTkFrame(self, fg_color="transparent")
        main_container.pack(fill=tk.BOTH, expand=True, padx=30, pady=30)
        
        # Header section with floating effect
        header_frame = AnimatedFrame(main_container, 
                                   fg_color=["#1E1E2E", "#2A2A40"],
                                   corner_radius=20,
                                   border_width=2,
                                   border_color=["#4A90E2", "#357ABD"])
        header_frame.pack(fill=tk.X, pady=(0, 25))
        
        # Title with glow effect
        title_container = ctk.CTkFrame(header_frame, fg_color="transparent")
        title_container.pack(fill=tk.X, padx=20, pady=20)
        
        self.title_label = FloatingLabel(title_container, 
                                       text=APP_TITLE, 
                                       font=ctk.CTkFont(size=32, weight="bold"),
                                       text_color=["#4A90E2", "#5BA3F5"])
        self.title_label.pack(side=tk.LEFT)
        
        subtitle = ctk.CTkLabel(title_container,
                              text=APP_SUBTITLE,
                              font=ctk.CTkFont(size=14),
                              text_color=["#888888", "#AAAAAA"])
        subtitle.pack(side=tk.LEFT, padx=(20, 0))

        # File selection section with enhanced styling
        file_section = AnimatedFrame(main_container,
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
        
        self.browse_btn = GlowButton(file_input_frame, 
                                   text="🔍 Browse",
                                   command=self.browse_file,
                                   width=120,
                                   height=45,
                                   font=ctk.CTkFont(size=14, weight="bold"),
                                   corner_radius=15,
                                   glow_color="#5BA3F5")
        self.browse_btn.pack(side=tk.RIGHT)

        # Upload method selection with modern radio buttons
        method_section = AnimatedFrame(main_container,
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
        methods = [
            ("🎯 Auto (Smart Detection)", "auto"),
            ("⚡ Inline Processing", "inline"), 
            ("☁️ Cloud Upload", "upload")
        ]
        
        for i, (text, value) in enumerate(methods):
            radio = ctk.CTkRadioButton(method_frame,
                                     text=text,
                                     variable=self.method_var,
                                     value=value,
                                     font=ctk.CTkFont(size=14),
                                     radiobutton_width=20,
                                     radiobutton_height=20)
            radio.pack(side=tk.LEFT, padx=(0, 30), pady=5)

        # Enhanced tabview for prompts
        self.prompts_tabview = ctk.CTkTabview(main_container,
                                            height=200,
                                            corner_radius=20,
                                            border_width=1,
                                            border_color=["#4A90E2", "#5BA3F5"])
        self.prompts_tabview.pack(fill=tk.BOTH, expand=True, pady=(0, 20))
        
        # Transcript tab with enhanced styling
        transcript_tab = self.prompts_tabview.add("📝 Transcript Prompt")
        self.transcript_text = ctk.CTkTextbox(transcript_tab,
                                            font=ctk.CTkFont(size=13),
                                            corner_radius=15,
                                            border_width=2,
                                            border_color=["#333355", "#444466"])
        self.transcript_text.pack(fill=tk.BOTH, expand=True, padx=15, pady=15)
        self.transcript_text.insert("1.0", DEFAULT_TRANS_PROMPT)
        
        # Memo tab with enhanced styling
        memo_tab = self.prompts_tabview.add("📋 Memo Prompt")
        self.memo_text = ctk.CTkTextbox(memo_tab,
                                      font=ctk.CTkFont(size=13),
                                      corner_radius=15,
                                      border_width=2,
                                      border_color=["#333355", "#444466"])
        self.memo_text.pack(fill=tk.BOTH, expand=True, padx=15, pady=15)
        self.memo_text.insert("1.0", DEFAULT_MEMO_PROMPT)

        # Results section with particle background
        results_section = AnimatedFrame(main_container,
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
        
        # Create particle canvas background
        self.particle_canvas = ParticleCanvas(results_section, height=100)
        self.particle_canvas.pack(fill=tk.X, padx=20, pady=(0, 10))
        
        self.results_text = ctk.CTkTextbox(results_section,
                                         height=120,
                                         font=ctk.CTkFont(size=12),
                                         corner_radius=15,
                                         border_width=2,
                                         border_color=["#333355", "#444466"])
        self.results_text.pack(fill=tk.BOTH, expand=True, padx=20, pady=(0, 15))

        # Control panel with advanced styling
        control_panel = AnimatedFrame(main_container,
                                    fg_color=["#1E1E2E", "#2A2A40"],
                                    corner_radius=20,
                                    border_width=2,
                                    border_color=["#4A90E2", "#357ABD"])
        control_panel.pack(fill=tk.X)
        
        control_inner = ctk.CTkFrame(control_panel, fg_color="transparent")
        control_inner.pack(fill=tk.X, padx=20, pady=15)
        
        # Status and progress section
        status_frame = ctk.CTkFrame(control_inner, fg_color="transparent")
        status_frame.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        self.status_var = tk.StringVar(value="🟢 Ready to process audio")
        self.status_label = ctk.CTkLabel(status_frame,
                                       textvariable=self.status_var,
                                       font=ctk.CTkFont(size=14, weight="bold"),
                                       text_color=["#4A90E2", "#5BA3F5"])
        self.status_label.pack(anchor="w", pady=(0, 8))
        
        self.progress_bar = PulsingProgressBar(status_frame,
                                             height=8,
                                             corner_radius=4,
                                             progress_color=["#4A90E2", "#5BA3F5"])
        self.progress_bar.pack(fill=tk.X, pady=(0, 5))
        
        # Main process button with enhanced styling
        self.process_btn = GlowButton(control_inner,
                                    text="🚀 Process Audio",
                                    command=self.process_audio,
                                    width=180,
                                    height=50,
                                    font=ctk.CTkFont(size=16, weight="bold"),
                                    corner_radius=25,
                                    glow_color="#5BA3F5")
        self.process_btn.pack(side=tk.RIGHT, padx=(20, 0))

    def setup_animations(self):
        """Initialize entrance animations"""
        def start_animations():
            self.title_label.start_float()
            # Stagger the entrance animations
            frames = self.winfo_children()[0].winfo_children()
            for i, frame in enumerate(frames):
                if isinstance(frame, AnimatedFrame):
                    frame.animate_in(delay=i * 0.1)
        
        self.after(100, start_animations)

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
            
            # Add visual feedback
            self.file_entry.configure(border_color=["#4CAF50", "#66BB6A"])
            self.after(2000, lambda: self.file_entry.configure(border_color=["#4A90E2", "#5BA3F5"]))

    def log_message(self, message):
        """Enhanced logging with timestamps and styling"""
        timestamp = time.strftime("%H:%M:%S")
        formatted_message = f"[{timestamp}] {message}"
        
        self.results_text.insert(tk.END, formatted_message + "\n")
        self.results_text.see(tk.END)
        
        # Auto-scroll with smooth effect
        self.after(100, lambda: self.results_text.see(tk.END))

    def update_status(self, message, color=None):
        """Update status with color coding"""
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

        # Get prompts
        transcript_prompt = self.transcript_text.get("1.0", tk.END).strip() or DEFAULT_TRANS_PROMPT
        memo_prompt = self.memo_text.get("1.0", tk.END).strip() or DEFAULT_MEMO_PROMPT
        method = self.method_var.get()

        # Start processing state
        self.processing = True
        self.progress_bar.start_pulse()
        self.particle_canvas.start_particles()
        
        self.process_btn.configure(state="disabled", text="⏳ Processing...")
        self.update_status("🔄 Processing audio file...", ["#FF9800", "#FFB74D"])
        
        # Start processing thread
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

            # Process based on method
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
            
            # Save transcript
            with open(TRANSCRIPT_FILENAME, "w", encoding="utf-8") as f:
                f.write(transcript)
            self.log_message(f"💾 Transcript saved to {TRANSCRIPT_FILENAME}")
            self.transcript = transcript

            # Generate memo
            self.update_status("📋 Generating intelligent memo...")
            memo_response = model.generate_content([memo_prompt, transcript])
            memo_content = memo_response.text.replace("```html", "").replace("```", "").strip()

            if not memo_content.strip().startswith('<!DOCTYPE html>'):
                memo_content = f"{memo_content}"

            # Save memo
            with open(MEMO_FILENAME, "w", encoding="utf-8") as f:
                f.write(memo_content)
            self.log_message(f"📋 Memo saved to {MEMO_FILENAME}")
            
            # Success state
            self.update_status("🎉 Processing completed successfully!", ["#4CAF50", "#66BB6A"])
            self.log_message("🌐 Opening memo in browser...")
            webbrowser.open(MEMO_FILENAME)

        except Exception as e:
            self.log_message(f"💥 Error occurred: {str(e)}")
            self.update_status("❌ Processing failed", ["#FF5252", "#FF6B6B"])
        finally:
            # Reset processing state
            self.processing = False
            self.progress_bar.stop_pulse()
            self.particle_canvas.stop_particles()
            self.process_btn.configure(state="normal", text="🚀 Process Audio")

def main():
    if len(os.sys.argv) > 1:
        cli_main()
    else:
        app = GeminiAudioApp()
        app.mainloop()

def cli_main():
    parser = argparse.ArgumentParser(description="Interact with audio using the Gemini API to generate transcripts and memos.")
    parser.add_argument("audio_file", help="Path to the audio file (e.g., MP3) to send")
    parser.add_argument("--prompt", default=DEFAULT_TRANS_PROMPT, help="Prompt for the Gemini API")
    parser.add_argument("--method", choices=["auto", "inline", "upload"], default="auto", help="Audio upload method")
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
            transcript_response = model.generate_content([args.prompt, {"mime_type": "audio/mp3", "data": audio_data}])

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