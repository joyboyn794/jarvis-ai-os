# Jarvis Simple — CLI Version

🚀 **Quick-start text-only version** of Jarvis AI without voice/GUI complexity.

Perfect for:
- ✅ Testing memory system
- ✅ Quick chat interactions
- ✅ Lightweight servers
- ✅ SSH/remote sessions
- ✅ Learning/debugging

## 📋 Requirements

- Python 3.8+
- Internet connection (Groq API)
- GROQ_API_KEY set

## 🚀 Installation & Usage

### 1. Get API Key
https://console.groq.com/keys

### 2. Install dependencies
```bash
pip install groq
```

### 3. Set API key
**Linux/macOS:**
```bash
export GROQ_API_KEY="gsk_your_key_here"
python jarvis_simple.py
```

**Windows CMD:**
```cmd
set GROQ_API_KEY=gsk_your_key_here
python jarvis_simple.py
```

**Windows PowerShell:**
```powershell
$env:GROQ_API_KEY="gsk_your_key_here"
python jarvis_simple.py
```

## 💬 How to Use

```
You: Hey Jarvis, what's your name?
🤖 Jarvis: I'm Jarvis, an advanced AI assistant inspired by Iron Man's Jarvis...

You: I like Python programming
🤖 Jarvis: That's great! Python is...

You: status
📊 Status:
   • Memories: 2
   • Conversation turns: 3

You: quit
👋 Goodbye!
```

## 🧠 Features

| Feature | Details |
|---------|---------|
| **Memory** | Automatically extracts facts/preferences every 3 exchanges |
| **Context** | Injects relevant memories into chat prompts |
| **History** | Saved to `~/.jarvis/chat_history.json` |
| **Persistence** | Memories saved to `~/.jarvis/memory.json` |
| **Language** | Persian & English supported in text |

## 🔧 Commands

| Command | Action |
|---------|--------|
| `quit` / `exit` | Close Jarvis |
| `status` | Show memory & conversation stats |
| Regular text | Chat normally |

## 📁 Data Storage

```
~/.jarvis/
├── chat_history.json    # All conversations
└── memory.json          # Long-term memories
```

## 🆚 vs Full Version

| Feature | Simple | Full (jarvis.py) |
|---------|--------|------------------|
| Text Chat | ✅ | ✅ |
| Memory System | ✅ | ✅ |
| Voice Input/Output | ❌ | ✅ |
| Wake Word Detection | ❌ | ✅ |
| Animated HUD | ❌ | ✅ |
| tkinter GUI | ❌ | ✅ |

## 🚨 Troubleshooting

### ❌ "GROQ_API_KEY not set"
```bash
export GROQ_API_KEY="your_key_here"
```

### ❌ "groq not installed"
```bash
pip install groq
```

### ❌ Memory extraction returning empty
- Make sure you have a few exchanges (memory extracts every 3 turns)
- Check `~/.jarvis/memory.json` file

### ❌ Connection errors
- Check internet connection
- Verify API key is valid
- Check Groq service status

## 💡 Tips

1. **First run** downloads Groq client (~10MB)
2. **Memory extracts** every 3 exchanges (can be customized in code)
3. **Context window** keeps last 20 messages for efficiency
4. **Type `status`** to see how many memories Jarvis has learned

## 📖 Example Session

```
============================================================
  JARVIS AI OS — Simplified CLI
  Memory-Enabled Conversational AI
============================================================

📁 Data: /home/user/.jarvis
💾 Memories: /home/user/.jarvis/memory.json

Type 'quit' or 'exit' to close. Type 'status' for memory info.

✓ Initialized with 0 memories

You: My name is Alice and I'm a data scientist
🤖 Jarvis: Nice to meet you, Alice! Data science is a fascinating field...

You: I work mostly with Python and machine learning
🤖 Jarvis: Python and ML are powerful tools for data science...

You: status
📊 Status:
   • Memories: 2
   • Conversation turns: 2

You: What do I do for work?
🤖 Jarvis: Based on our conversation, you're a data scientist working...

You: quit
👋 Goodbye!
```

## 🔐 Security Notes

- Never commit `.env` files with API keys
- Use environment variables for sensitive data
- Local memory files stored in `~/.jarvis/` (readable by your user only)

---

**Ready to chat? Run: `python jarvis_simple.py`** 🚀
