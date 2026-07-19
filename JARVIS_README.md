# Jarvis AI OS — Single-File Voice Assistant

A self-contained, professional-grade AI voice assistant inspired by Iron Man's Jarvis. Built with Python, featuring wake word detection, long-term memory, voice I/O, and an animated tkinter HUD.

## Features

✨ **Voice Interaction**
- Wake word detection ("Hey Jarvis") via OpenWakeWord
- Persian/Farsi speech recognition (Google Speech Recognition)
- Text-to-speech output (pyttsx3)

🧠 **Smart Memory System**
- Automatically extracts facts, preferences, and events from conversations
- Stores memories locally (JSON) for persistent learning
- Injects relevant memories into chat prompts
- Memory relevance scoring based on keyword overlap, importance, and recency

🤖 **AI Brain**
- Groq API integration (llama-3.3-70b-versatile model)
- Multi-turn conversation with context awareness
- Efficient token usage with conversation history management

🎨 **Animated HUD**
- Iron Man-style tkinter interface
- Real-time animated rings and pulsing core
- Listening/processing state indicators
- Scrollable chat log with timestamps

💾 **Data Persistence**
- Conversation history saved to `~/.jarvis/chat_history.json`
- Long-term memory stored in `~/.jarvis/memory.json`
- Auto-recovery of conversation context on restart

## Requirements

- Python 3.8+
- Microphone & speakers
- Internet connection (for Groq API & speech recognition)
- GROQ_API_KEY environment variable set

## Installation

### 1. Clone or download `jarvis.py`

```bash
# From the repo
git clone https://github.com/joyboyn794/jarvis-ai-os.git
cd jarvis-ai-os
python jarvis.py
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

On some systems, you may need system dependencies for audio:

**Ubuntu/Debian:**
```bash
sudo apt-get install python3-pyaudio portaudio19-dev
```

**macOS (with Homebrew):**
```bash
brew install portaudio
pip install pyaudio
```

**Windows:**
- pyaudio is usually installed with `pip install SpeechRecognition`
- If issues, use: `pip install pipwin` then `pipwin install pyaudio`

### 3. Set Groq API Key

```bash
export GROQ_API_KEY="gsk_your_key_here"
```

Get a free API key: https://console.groq.com/keys

## Usage

### Basic Launch

```bash
python jarvis.py
```

### How to Interact

1. **Wake up Jarvis** — Say "Hey Jarvis" followed by your command
   - Examples: "Hey Jarvis, what's the weather?" or "Hey Jarvis, نام‌ت چیه؟" (Persian)

2. **Chat normally** — Once awake, Jarvis will respond and continue listening

3. **Multiple languages** — Persian and English supported in speech recognition

4. **Memory learns over time** — Jarvis extracts and remembers:
   - Your preferences ("I like science fiction")
   - Personal facts ("My name is Tony")
   - Events ("We had a meeting yesterday")
   - Skills ("I'm a programmer")

### File Structure

```
~/.jarvis/
├── memory.json           # Long-term user memories
└── chat_history.json     # Conversation history
```

## Architecture

### Threading Model

- **Listening Thread**: Continuously captures audio and detects wake word
- **Processing Thread**: Handles LLM requests and memory extraction
- **Main Thread**: Runs tkinter HUD and coordinates threads via queues

### Memory Flow

```
User Input → Wake Word Detection
           → Speech Recognition (fa-IR/en)
           → LLM Processing (Groq)
           → Memory Extraction (every 3 exchanges)
           ↓
           → Memory Storage (JSON)
           ↓
           → Memory Retrieval for next query
           → System Prompt Injection
           → Response
```

### Components

| Component | Purpose |
|-----------|---------|
| `AudioManager` | Speech recognition & TTS |
| `WakeWordDetector` | "Hey Jarvis" detection |
| `MemoryManager` | Long-term memory with semantic scoring |
| `JarvisAI` | LLM orchestration with Groq |
| `JarvisHUD` | tkinter animated interface |
| `JarvisApp` | Main orchestrator & threading |

## Advanced Configuration

### Adjust wake word sensitivity

Edit `WakeWordDetector.is_wake_word()` to add custom phrases:

```python
wake_phrases = ["hey jarvis", "jarvis", "جارویس", "your_custom_phrase"]
```

### Control TTS output

Comment out `self.audio.speak(response)` in `_processing_loop()` for faster feedback:

```python
# self.audio.speak(response)  # Disable TTS if needed
```

### Adjust LLM parameters

In `JarvisAI.process()`:

```python
response = self.client.chat.completions.create(
    # ... other params
    temperature=0.7,      # Lower = more focused, Higher = more creative
    max_tokens=800,       # Max response length
)
```

### Memory extraction frequency

In `JarvisAI.process()`, change the modulo:

```python
if len(self.conversation_history) % 6 == 0:  # Every 3 exchanges
    self.memory_manager.extract_from_conversation(self.conversation_history)
```

## Troubleshooting

### ❌ "openwakeword not installed"

```bash
pip install openwakeword --upgrade
```

### ❌ Microphone not detected

```bash
python -m speech_recognition
```

This will test your microphone setup.

### ❌ "GROQ_API_KEY not set"

```bash
# Linux/macOS
export GROQ_API_KEY="your_key"

# Windows (PowerShell)
$env:GROQ_API_KEY="your_key"
```

### ❌ "Could not understand audio"

- Speak clearly and loudly
- Reduce background noise
- Check microphone volume

### ❌ Memory extraction returning empty

Increase conversation length or check `MEMORY_FILE` permissions.

## Performance Notes

- First run downloads OpenWakeWord model (~100MB)
- Memory extraction adds ~1-2 seconds to every 3rd exchange
- Groq API response typically: 1-3 seconds
- Animated HUD updates at 20 FPS

## Future Enhancements

- [ ] Embeddings-based memory retrieval (semantic search)
- [ ] Multi-user support with separate memory profiles
- [ ] Custom command execution (e.g., "open browser")
- [ ] Web interface alongside HUD
- [ ] Plugin system for extensibility
- [ ] Vision capabilities (webcam)
- [ ] Local LLM fallback (ollama)

## License

MIT — Feel free to fork and customize!

## Support

- 📝 Issues: https://github.com/joyboyn794/jarvis-ai-os/issues
- 🔑 Groq API Docs: https://console.groq.com/docs
- 🎙️ Speech Recognition: https://github.com/Uberi/speech_recognition

---

**Built with ❤️ for Persian-speaking developers and AI enthusiasts.**
