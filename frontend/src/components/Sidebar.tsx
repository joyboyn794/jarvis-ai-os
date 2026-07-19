import { MessageSquare, Plus, Trash2, LogOut } from 'lucide-react';
import type { Conversation } from '../store/chatStore';

interface SidebarProps {
  conversations: Conversation[];
  currentId: string | null;
  onSelect: (id: string) => void;
  onNew: () => void;
  onDelete: (id: string) => void;
  onLogout: () => void;
}

export function Sidebar({
  conversations,
  currentId,
  onSelect,
  onNew,
  onDelete,
  onLogout,
}: SidebarProps) {
  return (
    <aside className="w-72 border-r border-jarvis-border bg-jarvis-surface flex flex-col flex-shrink-0">
      {/* Header */}
      <div className="p-4 border-b border-jarvis-border">
        <button
          onClick={onNew}
          className="w-full flex items-center gap-2 px-4 py-2.5 bg-jarvis-accent hover:bg-jarvis-accent/90 text-white rounded-lg font-medium transition-colors"
        >
          <Plus size={18} />
          New Conversation
        </button>
      </div>

      {/* Conversation List */}
      <div className="flex-1 overflow-y-auto p-2">
        {conversations.length === 0 ? (
          <div className="text-center text-jarvis-text-muted text-sm mt-8 px-4">
            No conversations yet. Start a new one!
          </div>
        ) : (
          conversations.map((conv) => (
            <div
              key={conv.id}
              onClick={() => onSelect(conv.id)}
              className={`
                group flex items-center gap-3 px-3 py-2.5 rounded-lg cursor-pointer
                transition-colors mb-0.5
                ${
                  conv.id === currentId
                    ? 'bg-jarvis-accent/10 text-jarvis-accent'
                    : 'hover:bg-jarvis-border/50 text-jarvis-text'
                }
              `}
            >
              <MessageSquare size={16} className="flex-shrink-0 opacity-70" />
              <span className="flex-1 truncate text-sm">{conv.title}</span>
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  onDelete(conv.id);
                }}
                className="opacity-0 group-hover:opacity-100 p-1 hover:bg-jarvis-border rounded transition-all"
              >
                <Trash2 size={14} className="text-jarvis-text-muted hover:text-jarvis-danger" />
              </button>
            </div>
          ))
        )}
      </div>

      {/* Footer */}
      <div className="p-3 border-t border-jarvis-border">
        <button
          onClick={onLogout}
          className="w-full flex items-center gap-2 px-3 py-2 text-sm text-jarvis-text-muted hover:text-jarvis-text hover:bg-jarvis-border/50 rounded-lg transition-colors"
        >
          <LogOut size={16} />
          Sign Out
        </button>
      </div>
    </aside>
  );
}
