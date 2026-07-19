#!/usr/bin/env python3
"""
Jarvis AI OS — Simplified CLI Version
Text-based chat with memory system (no voice/GUI)
For quick testing and lightweight usage
"""

import os
import sys
import json
import time
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any
import logging

try:
    from groq import Groq
except ImportError:
    print("❌ groq not installed. Install: pip install groq")
    sys.exit(1)

# ============================================================================
# CONFIGURATION
# ============================================================================
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
if not GROQ_API_KEY:
    print("❌ GROQ_API_KEY environment variable not set")
    print("   Run: export GROQ_API_KEY='your_key_here'")
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

# Initialize Groq client once
try:
    GROQ_CLIENT = Groq(api_key=GROQ_API_KEY)
    logger.info("✓ Groq client initialized")
except Exception as e:
    print(f"❌ Failed to initialize Groq: {e}")
    sys.exit(1)


# ============================================================================
# MEMORY SYSTEM
# ============================================================================
class MemoryManager:
    """Manages long-term user memory with semantic extraction."""
    
    def __init__(self, memory_file: Path):
        self.memory_file = memory_file
        self.groq = GROQ_CLIENT
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
- "content": the fact or preference (keep concise)
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
        Simple keyword matching.
        """
        if not self.memories:
            return ""
        
        # Simple relevance scoring
        scored = []
        query_words = set(query.lower().split())
        
        for mem in self.memories:
            content_words = set(mem["content"].lower().split())
            overlap = len(query_words & content_words) / max(len(query_words), 1)
            
            # Recency boost
            try:
                last_accessed = datetime.fromisoformat(mem.get("last_accessed", "2000-01-01"))
                days_old = (datetime.now() - last_accessed).days
                recency_score = max(0, 1 - (days_old / 30))
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
# AI ENGINE
# ============================================================================
class JarvisAI:
    """Main AI logic with Groq integration and memory."""
    
    SYSTEM_PROMPT_TEMPLATE = """You are Jarvis, an advanced AI assistant inspired by Iron Man's Jarvis.
Characteristics:
- Intelligent, efficient, and helpful
- Professional yet warm in tone
- Brief and direct (avoid unnecessary preamble)
- Always honest about limitations

You have access to long-term memory of past conversations.

{memory_context}

Respond concisely and naturally. Reference memories when relevant."""
    
    def __init__(self, memory_manager: MemoryManager):
        self.client = GROQ_CLIENT
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
        
        # Prepare messages for LLM
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
# MAIN CLI
# ============================================================================
def main():
    """Main CLI loop."""
    print("\n" + "="*60)
    print("  JARVIS AI OS — Simplified CLI")
    print("  Memory-Enabled Conversational AI")
    print("="*60)
    print(f"\n📁 Data: {DATA_DIR}")
    print(f"💾 Memories: {MEMORY_FILE}")
    print(f"\nType 'quit' or 'exit' to close. Type 'status' for memory info.\n")
    
    # Initialize
    memory = MemoryManager(MEMORY_FILE)
    ai = JarvisAI(memory)
    
    print(f"✓ Initialized with {len(memory.memories)} memories\n")
    
    # Main loop
    while True:
        try:
            # Get user input
            user_input = input("You: ").strip()
            
            if not user_input:
                continue
            
            if user_input.lower() in ['quit', 'exit']:
                print("\n👋 Goodbye!\n")
                break
            
            if user_input.lower() == 'status':
                print(f"\n📊 Status:")
                print(f"   • Memories: {len(memory.memories)}")
                print(f"   • Conversation turns: {len(ai.conversation_history) // 2}")
                print()
                continue
            
            # Process and respond
            print("\n🤖 Jarvis: ", end="", flush=True)
            response = ai.process(user_input)
            print(response)
            print()
        
        except KeyboardInterrupt:
            print("\n\n👋 Interrupted. Goodbye!\n")
            break
        except Exception as e:
            print(f"\n❌ Error: {e}\n")
            logger.error(f"Main loop error: {e}")


if __name__ == "__main__":
    main()
