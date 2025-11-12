# 🎵 MemoMaker - Audio to Intelligent Memos

Transform audio recordings into professional transcripts and actionable memos using Google's Gemini AI.

![Python](https://img.shields.io/badge/python-3.8+-blue.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)
![AI](https://img.shields.io/badge/AI-Google%20Gemini-orange.svg)

## ✨ Features

- 🎯 **Smart Audio Processing** - Automatic detection of optimal processing method
- 🎨 **Modern UI** - Clean dark-themed interface with real-time progress tracking
- 🌍 **Multi-Language Support** - Estonian and English prompts with easy language switching
- ⚡ **Multiple Processing Methods** - Inline, cloud upload, or auto-detection
- 📝 **Configurable Prompts** - Customize transcription and memo generation
- 🔊 **Wide Audio Support** - MP3, WAV, M4A, OGG, FLAC, AAC formats
- 📋 **Markdown Output** - Professional memo format with timestamps and action items
- 🛡️ **File Validation** - Comprehensive format, size, and integrity checking
- 📊 **API Usage Tracking** - Real-time token counts and processing statistics
- 🔄 **Real Progress Bar** - Step-by-step progress indication during processing
- 🔑 **Built-in API Key Manager** - Easy setup and management of Gemini API keys

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

2. **Set your Gemini API key**:
   ```bash
   export GEMINI_API_KEY="your-api-key-here"
   ```
   
   Or on Windows:
   ```cmd
   set GEMINI_API_KEY=your-api-key-here
   ```
   
   **Or use the built-in API key manager**: The app will show a setup dialog if no API key is found.

3. **Run the application**:
   ```bash
   python memomaker-ui.py
   ```

## 🎯 How to Use

### GUI Mode (Recommended)

1. **Launch the app** - Run `python memomaker-ui.py`
2. **Select audio file** - Click "Browse" and choose your audio file (or click the file path field)
3. **Choose language** - Select Estonian (ET) or English (EN) from the language dropdown
4. **Choose processing method**:
   - 🎯 **Auto** - Smart detection based on file size
   - ⚡ **Inline** - Fast processing for smaller files (<20MB)
   - ☁️ **Cloud Upload** - Better for larger files (>20MB)
5. **Customize prompts** (optional) - Edit transcription and memo prompts in the tabs
6. **Process** - Click "Process Audio" and watch real-time progress
7. **Manage API key** (optional) - Click "🔑 API Key" button to view/edit your Gemini API key
8. **View results** - Transcript saves to `transcript.txt`, memo saves to `memo.md` and opens automatically
9. **Monitor usage** - View detailed API usage statistics including token counts in the results area

### CLI Mode

```bash
python memomaker-ui.py audio_file.mp3 [--method auto|inline|upload] [--prompt "custom prompt"]
```

## ⚙️ Configuration

### Settings (Top of `memomaker-ui.py`)

```python
# API Configuration
API_KEY = os.environ.get("GEMINI_API_KEY")

# Model Settings
MODEL_NAME = 'gemini-flash-latest'

# File Processing Settings
INLINE_THRESHOLD = 20 * 1024 * 1024  # 20 MB
MAX_FILE_SIZE = 100 * 1024 * 1024     # 100 MB max
MIN_FILE_SIZE = 1024                   # 1 KB min

# Output File Settings
TRANSCRIPT_FILENAME = "transcript.txt"
MEMO_FILENAME = "memo.md"

# UI Settings
WINDOW_WIDTH = 1000
WINDOW_HEIGHT = 800
```

### Multi-Language Prompts

The app automatically detects and uses language-specific prompt files:

- **Estonian**: `transcription-prompt-et.md`
- **English**: `transcription-prompt-en.md` 
- **Future**: `transcription-prompt-fr.md`, `transcription-prompt-de.md`, etc.

Each file contains:
- **Transcription rules** - Under `# Transkriptsioon`/`# Transcription` section
- **Memo format** - Under `# Memo` section

**Language Selection**:
- Dropdown menu appears when multiple language files are present
- Single language shows as label
- Missing files show clear error messages in prompt areas

## 📁 File Structure

```
memomaker/
├── memomaker-ui.py              # Main application
├── transcription-prompt-et.md   # Estonian prompts
├── transcription-prompt-en.md   # English prompts
├── .gitignore                  # Git ignore rules
├── README.md                   # This file
├── transcript.txt              # Generated transcript (after processing)
└── memo.md                     # Generated memo (after processing)
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

### Memo Format (Markdown)
- **Structured sections**: Participants, summary, decisions, actions
- **Timestamps**: References to specific moments in audio
- **Action items**: Clear responsibilities and deadlines
- **Multi-language**: Professional business language (Estonian or English)
- **Markdown format**: Easy to edit and convert to other formats

## 🔧 Troubleshooting

### Common Issues

**"No module named 'customtkinter'"**
```bash
pip install customtkinter
```

**"Invalid API key"**
- Verify your Google API key is correct
- Check environment variable is set: `echo $GEMINI_API_KEY` (Linux/Mac) or `echo %GEMINI_API_KEY%` (Windows)
- Use the built-in "🔑 API Key" button to set up your key

**"File validation failed" errors**
- Check file format (supported: MP3, WAV, M4A, OGG, FLAC, AAC)
- Ensure file size is between 1KB and 100MB
- Use "Upload" method for files > 20MB
- Consider compressing large audio files

**UI not appearing**
- Ensure you're running GUI mode: `python memomaker-ui.py`
- Check if running with command line arguments (switches to CLI mode)
- Verify prompt files exist: `transcription-prompt-et.md` or `transcription-prompt-en.md`

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
- [x] **Multi-language** - Estonian and English support (completed)
- [ ] **Additional languages** - French, German, etc.
- [ ] **Templates** - Custom memo templates

## ⚠️ Security & Privacy

- **API keys** are stored locally as environment variables
- **Audio files** are processed according to Google's privacy policy
- **No data retention** - Files are not stored after processing
- **Local processing** - Transcripts and memos saved locally

## 📄 License

MIT License - see [LICENSE](LICENSE) file for details.

## 📊 New Features

### API Usage Tracking
- **Real-time statistics** displayed in results area
- **Token counts**: Input, output, and total tokens
- **Processing time**: Detailed timing for each operation
- **No log files**: All data shown directly in UI

### File Validation
- **Format checking**: Validates audio file extensions and MIME types
- **Size limits**: Enforces minimum (1KB) and maximum (100MB) file sizes
- **Integrity checks**: Basic corruption detection
- **Clear error messages**: Specific validation failure details

### Real Progress Bar
- **Step-by-step progress**: Shows actual processing stages
- **Visual feedback**: Progress from 0.1 (start) to 1.0 (complete)
- **Stays visible**: Progress remains visible for 2 seconds after completion

## 🤝 Support

- **Issues**: [GitHub Issues](https://github.com/priit2000/memomaker/issues)
- **Discussions**: [GitHub Discussions](https://github.com/priit2000/memomaker/discussions)

## 🙏 Acknowledgments

- **Google Gemini AI** - For powerful audio processing capabilities
- **CustomTkinter** - For modern UI components
- **Estonian language community** - For feedback and testing

---

Made with ❤️ for efficient meeting documentation