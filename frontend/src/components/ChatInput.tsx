import { useState, useRef, KeyboardEvent } from 'react';
import { Send, Mic, MicOff } from 'lucide-react';

interface ChatInputProps {
  onSend: (message: string) => void;
  disabled?: boolean;
}

export function ChatInput({ onSend, disabled }: ChatInputProps) {
  const [input, setInput] = useState('');
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const handleSend = () => {
    const trimmed = input.trim();
    if (!trimmed || disabled) return;

    onSend(trimmed);
    setInput('');

    // Reset textarea height
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
    }
  };

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    // Enter to send (without Shift)
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  // Auto-resize textarea
  const handleInput = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setInput(e.target.value);

    const textarea = e.target;
    textarea.style.height = 'auto';
    textarea.style.height = Math.min(textarea.scrollHeight, 200) + 'px';
  };

  return (
    <div className="border-t border-jarvis-border p-4">
      <div className="max-w-3xl mx-auto">
        <div className="flex items-end gap-2 bg-jarvis-surface border border-jarvis-border rounded-xl px-4 py-2 focus-within:border-jarvis-accent/50 transition-colors">
          {/* Voice button placeholder */}
          <button
            type="button"
            className="p-2 text-jarvis-text-muted hover:text-jarvis-text rounded-lg hover:bg-jarvis-border/50 transition-colors flex-shrink-0"
            title="Voice input (coming soon)"
          >
            <Mic size={18} />
          </button>

          {/* Text input */}
          <textarea
            ref={textareaRef}
            value={input}
            onChange={handleInput}
            onKeyDown={handleKeyDown}
            placeholder="Message Jarvis..."
            disabled={disabled}
            rows={1}
            className="flex-1 bg-transparent text-jarvis-text placeholder:text-jarvis-text-muted resize-none outline-none py-1.5 text-sm max-h-[200px]"
          />

          {/* Send button */}
          <button
            onClick={handleSend}
            disabled={disabled || !input.trim()}
            className="p-2 text-jarvis-accent hover:bg-jarvis-accent/10 rounded-lg transition-colors disabled:opacity-30 disabled:cursor-not-allowed flex-shrink-0"
          >
            <Send size={18} />
          </button>
        </div>

        <p className="text-xs text-jarvis-text-muted text-center mt-2">
          Jarvis can make mistakes. Verify important information.
        </p>
      </div>
    </div>
  );
}
