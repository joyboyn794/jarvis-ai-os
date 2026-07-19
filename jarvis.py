#!/usr/bin/env python3
"""
Jarvis AI OS — Single-file voice assistant with memory system
Features: Wake word detection, voice I/O, Groq API, animated HUD, long-term memory
"""

import os
import sys
import json
import threading
import queue
import time
import math
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any
import tkinter as tk
from tkinter import Canvas, Label, scrolledtext
import logging

# ============================================================================
# DEPENDENCIES
# ============================================================================
try:
    from openwakeword.model import Model as WakeWordModel
except ImportError:
    print("❌ openwakeword not installed. Install: pip install openwakeword")
    sys.exit(1)

try:
    from groq import Groq
except ImportError:
    print("❌ groq not installed. Install: pip install groq")
    sys.exit(1)

try:
    import speech_recognition as sr
except ImportError:
    print("❌ speech_recognition not installed. Install: pip install SpeechRecognition pydub")
    sys.exit(1)

try:
    import pyttsx3
except ImportError:
    print("❌ pyttsx3 not installed. Install: pip install pyttsx3")
    sys.exit(1)

# ============================================================================
# CONFIGURATION
# ============================================================================
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
if not GROQ_API_KEY:
    print("❌ GROQ_API_KEY environment variable not set")
    sys.exit(1)

DATA_DIR = Path.home() / ".jarvis"
MEMORY_FILE = DATA_DIR / "memory.json"
CHAT_HISTORY_FILE = DATA_DIR / "chat_history.json"

DATA_DIR.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s'
)
logger = logging.getLogger("Jarvis")

# ============================================================================
# MEMORY SYSTEM
# ============================================================================
class MemoryManager:
    """Manages long-term user memory with semantic extraction."""
    
    def __init__(self, memory_file: Path, groq_client: Groq):
        self.memory_file = memory_file
        self.groq = groq_client
        self.memories: List[Dict[str, Any]] = self._load()
    
    def _load(self) -> List[Dict[str, Any]]:
        """Load memories from JSON file."""
        if self.memory_file.exists():
            try:
                with open(self.memory_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Failed to load memories: {e}")
        return []
    
    def _save(self):
        """Save memories to JSON file."""
        try:
            with open(self.memory_file, 'w', encoding='utf-8') as f:
                json.dump(self.memories, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Failed to save memories: {e}")
    
    def extract_from_conversation(self, messages: List[Dict[str, str]]) -> List[Dict[str, Any]]:
        """
        Use LLM to extract important facts/preferences from conversation.
        Returns list of new memory entries.
        """
        if len(messages) < 2:
            return []
        
        # Format recent messages for extraction
        recent = messages[-6:]  # Last 6 messages
        conv_text = "\n".join(f"{m['role'].upper()}: {m['content']}" for m in recent)
        
        extraction_prompt = f"""Extract key facts and preferences from this conversation.
Return ONLY a JSON array (no other text). Each item must have:
- "content": the fact or preference (keep concise, in Persian if applicable)
- "type": "fact", "preference", "event", or "skill"
- "importance": 0.0-1.0

Ignore trivial chat. Only extract genuinely useful information.

Conversation:
{conv_text}

Return ONLY valid JSON array:"""
        
        try:
            response = self.groq.chat.completions.create(
                messages=[{"role": "user", "content": extraction_prompt}],
                model="llama-3.3-70b-versatile",
                temperature=0.3,
                max_tokens=500
            )
            
            content = response.choices[0].message.content.strip()
            # Clean up markdown code blocks if present
            if content.startswith("```"):
                content = content.split("```")[1]
                if content.startswith("json"):
                    content = content[4:]
                content = content.strip()
            
            items = json.loads(content)
            
            new_memories = []
            for item in items:
                if isinstance(item, dict) and "content" in item:
                    memory_entry = {
                        "id": len(self.memories) + len(new_memories),
                        "content": item["content"],
                        "type": item.get("type", "fact"),
                        "importance": min(1.0, max(0.0, item.get("importance", 0.5))),
                        "created_at": datetime.now().isoformat(),
                        "last_accessed": datetime.now().isoformat()
                    }
                    new_memories.append(memory_entry)
                    self.memories.append(memory_entry)
            
            if new_memories:
                logger.info(f"✓ Extracted {len(new_memories)} memories")
                self._save()
            
            return new_memories
            
        except Exception as e:
            logger.error(f"Memory extraction failed: {e}")
            return []
    
    def retrieve_context(self, query: str, limit: int = 5) -> str:
        """
        Build formatted memory context for injection into system prompt.
        Simple keyword matching for now (can be improved with embeddings).
        """
        if not self.memories:
            return ""
        
        # Simple relevance scoring: keyword overlap + importance + recency
        scored = []
        query_words = set(query.lower().split())
        
        for mem in self.memories:
            content_words = set(mem["content"].lower().split())
            overlap = len(query_words & content_words) / max(len(query_words), 1)
            
            # Recency boost
            try:
                last_accessed = datetime.fromisoformat(mem.get("last_accessed", "2000-01-01"))
                days_old = (datetime.now() - last_accessed).days
                recency_score = max(0, 1 - (days_old / 30))  # Decay over 30 days
            except:
                recency_score = 0
            
            final_score = (overlap * 0.5) + (mem["importance"] * 0.3) + (recency_score * 0.2)
            scored.append((final_score, mem))
        
        # Get top relevant memories
        top_memories = sorted(scored, key=lambda x: x[0], reverse=True)[:limit]
        
        # Update access times
        for _, mem in top_memories:
            mem["last_accessed"] = datetime.now().isoformat()
        self._save()
        
        if not top_memories:
            return ""
        
        lines = ["\n=== RELEVANT CONTEXT FROM MEMORY ==="]
        for score, mem in top_memories:
            type_label = mem["type"].upper()
            lines.append(f"[{type_label}] {mem['content']}")
        lines.append("====================================\n")
        
        return "\n".join(lines)


# ============================================================================
# AUDIO I/O
# ============================================================================
class AudioManager:
    """Handles speech recognition and text-to-speech."""
    
    def __init__(self):
        self.recognizer = sr.Recognizer()
        self.recognizer.energy_threshold = 4000
        
        # TTS engine
        self.tts_engine = pyttsx3.init()
        self.tts_engine.setProperty('rate', 150)
        self.tts_engine.setProperty('volume', 0.9)
    
    def listen_for_speech(self, timeout: float = 10) -> Optional[str]:
        """Capture audio and convert to text (English/Persian)."""
        try:
            with sr.Microphone() as source:
                self.recognizer.adjust_for_ambient_noise(source, duration=0.5)
                logger.info("🎤 Listening...")
                audio = self.recognizer.listen(source, timeout=timeout, phrase_time_limit=15)
            
            # Try Google Speech Recognition (supports Persian: fa-IR)
            text = self.recognizer.recognize_google(audio, language='fa-IR')
            logger.info(f"📝 Heard: {text}")
            return text
        
        except sr.UnknownValueError:
            logger.warning("Could not understand audio")
            return None
        except sr.RequestError as e:
            logger.error(f"Speech recognition error: {e}")
            return None
        except Exception as e:
            logger.error(f"Audio error: {e}")
            return None
    
    def speak(self, text: str):
        """Convert text to speech."""
        try:
            logger.info(f"🔊 Speaking: {text[:50]}...")
            self.tts_engine.say(text)
            self.tts_engine.runAndWait()
        except Exception as e:
            logger.error(f"TTS error: {e}")


# ============================================================================
# WAKE WORD DETECTION
# ============================================================================
class WakeWordDetector:
    """Detects "Hey Jarvis" wake word using OpenWakeWord."""
    
    def __init__(self):
        try:
            self.model = WakeWordModel(
                wake_word_models={"jarvis": {"model_path": None}},  # Uses default/bundled model
                model_name="jarvis"
            )
            logger.info("✓ Wake word model loaded")
        except Exception as e:
            logger.warning(f"⚠ Wake word model error: {e}. Will use manual activation.")
            self.model = None
    
    def is_wake_word(self, text: str) -> bool:
        """Check if text contains wake word."""
        wake_phrases = ["hey jarvis", "jarvis", "جارویس", "hey جارویس"]
        return any(phrase in text.lower() for phrase in wake_phrases)


# ============================================================================
# LLM INTERACTION
# ============================================================================
class JarvisAI:
    """Main AI logic with Groq integration and memory."""
    
    SYSTEM_PROMPT_TEMPLATE = """You are Jarvis, an advanced AI assistant inspired by Iron Man's Jarvis.
Characteristics:
- Intelligent, efficient, and helpful
- Professional yet warm in tone
- Brief and direct (avoid unnecessary preamble)
- Always honest about limitations
- Proactive in anticipating user needs

You have access to:
- Long-term memory of past conversations and user preferences
- Ability to learn and remember user information
- Task planning and step-by-step guidance

{memory_context}

When responding:
1. Be concise but thorough
2. Use the user's name if known
3. Reference relevant memories naturally
4. For complex tasks, break into clear steps"""
    
    def __init__(self, groq_api_key: str, memory_manager: MemoryManager):
        self.client = Groq(api_key=groq_api_key)
        self.memory_manager = memory_manager
        self.conversation_history: List[Dict[str, str]] = self._load_history()
    
    def _load_history(self) -> List[Dict[str, str]]:
        """Load conversation history."""
        if CHAT_HISTORY_FILE.exists():
            try:
                with open(CHAT_HISTORY_FILE, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                return []
        return []
    
    def _save_history(self):
        """Save conversation history."""
        try:
            with open(CHAT_HISTORY_FILE, 'w', encoding='utf-8') as f:
                json.dump(self.conversation_history, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Failed to save history: {e}")
    
    def process(self, user_input: str) -> str:
        """Process user input and return AI response."""
        # Add user message to history
        self.conversation_history.append({"role": "user", "content": user_input})
        
        # Extract memories from recent conversation periodically
        if len(self.conversation_history) % 6 == 0:  # Every 3 exchanges
            self.memory_manager.extract_from_conversation(self.conversation_history)
        
        # Build context with memories
        memory_context = self.memory_manager.retrieve_context(user_input, limit=4)
        system_prompt = self.SYSTEM_PROMPT_TEMPLATE.format(
            memory_context=memory_context if memory_context else "[No relevant memories yet]"
        )
        
        # Prepare messages for LLM (keep last 10 exchanges for context)
        messages = [
            {"role": "system", "content": system_prompt},
            *self.conversation_history[-20:]
        ]
        
        try:
            response = self.client.chat.completions.create(
                messages=messages,
                model="llama-3.3-70b-versatile",
                temperature=0.7,
                max_tokens=800
            )
            
            assistant_response = response.choices[0].message.content
            
            # Add to history
            self.conversation_history.append({
                "role": "assistant",
                "content": assistant_response
            })
            self._save_history()
            
            return assistant_response
        
        except Exception as e:
            logger.error(f"LLM error: {e}")
            return f"Sorry, I encountered an error: {str(e)}"


# ============================================================================
# ANIMATED TKINTER HUD
# ============================================================================
class JarvisHUD:
    """Iron Man-style animated HUD interface."""
    
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Jarvis AI OS")
        self.root.geometry("900x700")
        self.root.configure(bg="#0a0e27")
        
        # State
        self.is_listening = False
        self.is_processing = False
        self.current_task = ""
        self.animation_frame = 0
        
        # Colors
        self.bg_color = "#0a0e27"
        self.blue = "#3aa8ff"
        self.cyan = "#8fe3ff"
        self.text_color = "#e0e8ff"
        
        self._create_widgets()
        self._schedule_animation()
    
    def _create_widgets(self):
        """Create UI elements."""
        # Main canvas for HUD
        self.canvas = Canvas(
            self.root, width=900, height=700,
            bg=self.bg_color, highlightthickness=0, cursor="arrow"
        )
        self.canvas.pack(fill=tk.BOTH, expand=True)
        
        # Title
        self.title_label = Label(
            self.root, text="JARVIS AI OS", bg=self.bg_color,
            fg=self.blue, font=("Arial", 24, "bold")
        )
        self.title_label.place(x=50, y=20)
        
        # Status indicator
        self.status_label = Label(
            self.root, text="● SYSTEMS ONLINE", bg=self.bg_color,
            fg="#4ade80", font=("Courier", 10, "bold")
        )
        self.status_label.place(x=50, y=60)
        
        # Chat/Log area
        self.log_text = scrolledtext.ScrolledText(
            self.root, width=100, height=20,
            bg="#0f1425", fg=self.text_color,
            font=("Courier", 9), insertbackground=self.cyan
        )
        self.log_text.pack(padx=20, pady=(100, 80), fill=tk.BOTH, expand=True)
        self.log_text.config(state=tk.DISABLED)
        
        # Info bar
        self.info_label = Label(
            self.root, text="Groq/Llama 3.1 | Memory: 0 entries | Ready",
            bg=self.bg_color, fg=self.text_color,
            font=("Courier", 8)
        )
        self.info_label.pack(side=tk.BOTTOM, pady=10)
    
    def _schedule_animation(self):
        """Schedule continuous HUD animation."""
        self.animation_frame += 1
        self._draw_hud()
        self.root.after(50, self._schedule_animation)
    
    def _draw_hud(self):
        """Draw animated HUD elements on canvas."""
        self.canvas.delete("all")
        
        w, h = 900, 200
        cx, cy = w // 2, h // 2
        
        # Background grid
        for i in range(0, w, 40):
            alpha = int(255 * 0.05)
            self.canvas.create_line(i, 0, i, h, fill=self.blue, width=1)
        
        for i in range(0, h, 40):
            self.canvas.create_line(0, i, w, h, fill=self.blue, width=1)
        
        # Animated rings
        t = self.animation_frame * 0.05
        
        for ring in range(3):
            radius = 60 + ring * 40
            angle_offset = t + (ring * 120)
            
            # Draw dashed circle
            points = []
            for angle in range(0, 360, 15):
                rad = math.radians(angle + angle_offset)
                x = cx + radius * math.cos(rad)
                y = cy + radius * math.sin(rad)
                points.append((x, y))
            
            for i in range(0, len(points), 2):
                self.canvas.create_line(
                    points[i][0], points[i][1],
                    points[(i+1) % len(points)][0], points[(i+1) % len(points)][1],
                    fill=self.blue if ring % 2 == 0 else self.cyan,
                    width=2
                )
        
        # Central pulsing core
        core_size = 15 + 5 * math.sin(t * 0.1)
        self.canvas.create_oval(
            cx - core_size, cy - core_size,
            cx + core_size, cy + core_size,
            fill=self.cyan, outline=self.blue, width=2
        )
        
        # Listening indicator
        if self.is_listening:
            for i in range(3):
                wave_r = 30 + (i * 15) + ((t * 100) % 60)
                opacity = max(0, 1 - (wave_r / 90))
                self.canvas.create_oval(
                    cx - wave_r, cy - wave_r,
                    cx + wave_r, cy + wave_r,
                    outline=self.blue, width=1
                )
    
    def log(self, role: str, text: str):
        """Add message to log."""
        self.log_text.config(state=tk.NORMAL)
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_text.insert(tk.END, f"[{timestamp}] {role}: {text}\n")
        self.log_text.see(tk.END)
        self.log_text.config(state=tk.DISABLED)
    
    def set_listening(self, state: bool):
        """Toggle listening indicator."""
        self.is_listening = state
        self.status_label.config(
            text="● LISTENING..." if state else "● SYSTEMS ONLINE",
            fg=self.cyan if state else "#4ade80"
        )
    
    def set_processing(self, state: bool):
        """Toggle processing indicator."""
        self.is_processing = state
        self.status_label.config(
            text="● PROCESSING..." if state else "● SYSTEMS ONLINE",
            fg="#fbbf24" if state else "#4ade80"
        )
    
    def update_info(self, memory_count: int):
        """Update info bar."""
        self.info_label.config(
            text=f"Groq/Llama 3.1 | Memory: {memory_count} entries | Running"
        )


# ============================================================================
# MAIN APPLICATION
# ============================================================================
class JarvisApp:
    """Main application orchestrator."""
    
    def __init__(self, root: tk.Tk):
        self.root = root
        
        # Initialize components
        self.audio = AudioManager()
        self.wake_detector = WakeWordDetector()
        self.memory = MemoryManager(MEMORY_FILE, Groq(api_key=GROQ_API_KEY))
        self.ai = JarvisAI(GROQ_API_KEY, self.memory)
        self.hud = JarvisHUD(root)
        
        # Queue for thread communication
        self.input_queue: queue.Queue = queue.Queue()
        
        # Start listening thread
        self.listening_thread = threading.Thread(
            target=self._listening_loop, daemon=True
        )
        self.listening_thread.start()
        
        # Start processing thread
        self.processing_thread = threading.Thread(
            target=self._processing_loop, daemon=True
        )
        self.processing_thread.start()
        
        self.hud.log("SYSTEM", "Jarvis initialized. Say 'Hey Jarvis' to start.")
        logger.info("✓ Jarvis app started")
    
    def _listening_loop(self):
        """Continuously listen for wake word and user input."""
        logger.info("🔊 Listening thread started")
        
        while True:
            try:
                # Listen for speech
                self.hud.set_listening(True)
                text = self.audio.listen_for_speech(timeout=30)
                self.hud.set_listening(False)
                
                if not text:
                    continue
                
                # Check for wake word
                if self.wake_detector.is_wake_word(text):
                    # Remove wake word
                    for phrase in ["hey jarvis", "jarvis", "جارویس", "hey جارویس"]:
                        if phrase in text.lower():
                            text = text.lower().replace(phrase, "").strip()
                            break
                    
                    if text:
                        self.hud.log("USER", text)
                        self.input_queue.put(text)
                
                time.sleep(0.5)
            
            except KeyboardInterrupt:
                logger.info("Listening thread interrupted")
                break
            except Exception as e:
                logger.error(f"Listening loop error: {e}")
                time.sleep(1)
    
    def _processing_loop(self):
        """Process user input and generate responses."""
        logger.info("💬 Processing thread started")
        
        while True:
            try:
                # Get user input from queue (blocking)
                user_input = self.input_queue.get(timeout=1)
                
                self.hud.set_processing(True)
                
                # Get AI response
                response = self.ai.process(user_input)
                
                self.hud.log("JARVIS", response)
                
                # Speak response (optional, can disable for faster feedback)
                # self.audio.speak(response)
                
                # Update memory count
                self.hud.update_info(len(self.memory.memories))
                
                self.hud.set_processing(False)
            
            except queue.Empty:
                continue
            except KeyboardInterrupt:
                logger.info("Processing thread interrupted")
                break
            except Exception as e:
                logger.error(f"Processing loop error: {e}")
                self.hud.set_processing(False)


# ============================================================================
# ENTRY POINT
# ============================================================================
if __name__ == "__main__":
    root = tk.Tk()
    app = JarvisApp(root)
    
    try:
        root.mainloop()
    except KeyboardInterrupt:
        logger.info("👋 Jarvis shutting down...")
        sys.exit(0)
