# 🎵 MemoMaker - Audio to Intelligent Memos

Transform audio recordings into professional transcripts and actionable memos using Google's Gemini AI.

![Python](https://img.shields.io/badge/python-3.8+-blue.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)
![AI](https://img.shields.io/badge/AI-Google%20Gemini-orange.svg)

## ✨ Features

- 🎯 **Smart Audio Processing** - Automatic detection of optimal processing method
- 🎨 **Modern UI** - Beautiful dark-themed interface with animations
- 🌍 **Estonian Language** - Native support for Estonian transcription and memos
- ⚡ **Multiple Processing Methods** - Inline, cloud upload, or auto-detection
- 📝 **Configurable Prompts** - Customize transcription and memo generation
- 🔊 **Wide Audio Support** - MP3, WAV, M4A, OGG, FLAC, AAC formats
- 📋 **Structured Output** - Professional memo format with timestamps and action items

## 🚀 Quick Start

### Prerequisites

1. **Python 3.8+**
2. **Google API Key** - Get one from [Google AI Studio](https://aistudio.google.com/app/apikey)
3. **Required packages**:
   ```bash
   pip install customtkinter google-generativeai pillow
   ```

### Setup

1. **Clone the repository**:
   ```bash
   git clone https://github.com/priit2000/memomaker.git
   cd memomaker
   ```

2. **Set your Google API key**:
   ```bash
   export GOOGLE_API_KEY="your-api-key-here"
   ```
   
   Or on Windows:
   ```cmd
   set GOOGLE_API_KEY=your-api-key-here
   ```

3. **Run the application**:
   ```bash
   python memomaker-ui.py
   ```

## 🎯 How to Use

### GUI Mode (Recommended)

1. **Launch the app** - Run `python memomaker-ui.py`
2. **Select audio file** - Click "Browse" and choose your audio file
3. **Choose processing method**:
   - 🎯 **Auto** - Smart detection based on file size
   - ⚡ **Inline** - Fast processing for smaller files (<20MB)
   - ☁️ **Cloud Upload** - Better for larger files (>20MB)
4. **Customize prompts** (optional) - Edit transcription and memo prompts
5. **Process** - Click "Process Audio" and wait for results
6. **View results** - Transcript saves to `transcript.txt`, memo opens in browser

### CLI Mode

```bash
python memomaker-ui.py audio_file.mp3 [--method auto|inline|upload] [--prompt "custom prompt"]
```

## ⚙️ Configuration

### Settings (Top of `memomaker-ui.py`)

```python
# API Configuration
API_KEY = os.environ.get("GOOGLE_API_KEY")

# Model Settings
MODEL_NAME = 'gemini-flash-latest'

# Prompt Settings
PROMPT_FILE = "transcription-prompt.md"

# File Processing Settings
INLINE_THRESHOLD = 20 * 1024 * 1024  # 20 MB

# Output File Settings
TRANSCRIPT_FILENAME = "transcript.txt"
MEMO_FILENAME = "memo.html"

# UI Settings
WINDOW_WIDTH = 1000
WINDOW_HEIGHT = 800
```

### Custom Prompts

Edit `transcription-prompt.md` to customize:
- **Transcription rules** - Under `# Transkriptsioon` section
- **Memo format** - Under `# Memo` section

## 📁 File Structure

```
memomaker/
├── memomaker-ui.py          # Main application
├── transcription-prompt.md  # Estonian prompts configuration
├── .gitignore              # Git ignore rules
├── README.md               # This file
├── transcript.txt          # Generated transcript (after processing)
└── memo.html              # Generated memo (after processing)
```

## 🎨 Processing Methods

| Method | Best For | File Size | Speed | Quality |
|--------|----------|-----------|-------|---------|
| **Auto** | Most cases | Any | Smart | Optimal |
| **Inline** | Quick processing | < 20MB | Fastest | Good |
| **Upload** | Large files | > 20MB | Slower | Best |

## 📝 Output Examples

### Transcript Format
```
[00h:02m:15s] Priit Kallas: Alustame tänase koosoleku. Päevakorras on kolm punkti.
[00h:02m:28s] Henrik Aavik: Tänan. Kas võiksime alustada eelmise nädala tulemustega?
[00h:02m:45s] Priit Kallas: Kindlasti. Numbrid on väga head...
```

### Memo Format
- **Structured sections**: Participants, summary, decisions, actions
- **Timestamps**: References to specific moments in audio
- **Action items**: Clear responsibilities and deadlines
- **Estonian language**: Professional business Estonian

## 🔧 Troubleshooting

### Common Issues

**"No module named 'customtkinter'"**
```bash
pip install customtkinter
```

**"Invalid API key"**
- Verify your Google API key is correct
- Check environment variable is set: `echo $GOOGLE_API_KEY`

**"File too large" errors**
- Use "Upload" method for files > 20MB
- Consider compressing audio file

**UI not appearing**
- Ensure you're running GUI mode: `python memomaker-ui.py`
- Check if running with command line arguments (switches to CLI mode)

### Performance Tips

- **Use MP3 format** for best compatibility
- **Compress large files** before processing
- **Close other applications** during processing for better performance

## 🛠️ Development

### Requirements
- Python 3.8+
- tkinter (usually included with Python)
- customtkinter
- google-generativeai
- Pillow

### Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## 📋 Roadmap

- [ ] **Batch processing** - Process multiple files
- [ ] **Export formats** - PDF, Word, plain text
- [ ] **Audio player** - Built-in playback with waveform
- [ ] **Cloud storage** - Direct integration with Google Drive/OneDrive
- [ ] **Multi-language** - Support for other languages
- [ ] **Templates** - Custom memo templates

## ⚠️ Security & Privacy

- **API keys** are stored locally as environment variables
- **Audio files** are processed according to Google's privacy policy
- **No data retention** - Files are not stored after processing
- **Local processing** - Transcripts and memos saved locally

## 📄 License

MIT License - see [LICENSE](LICENSE) file for details.

## 🤝 Support

- **Issues**: [GitHub Issues](https://github.com/priit2000/memomaker/issues)
- **Discussions**: [GitHub Discussions](https://github.com/priit2000/memomaker/discussions)

## 🙏 Acknowledgments

- **Google Gemini AI** - For powerful audio processing capabilities
- **CustomTkinter** - For modern UI components
- **Estonian language community** - For feedback and testing

---

Made with ❤️ for efficient meeting documentation