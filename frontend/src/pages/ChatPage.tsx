import { useEffect, useRef, useState, useCallback } from 'react';
import { useAuthStore } from '../store/authStore';
import { useChatStore } from '../store/chatStore';
import { chatApi, createChatWebSocket } from '../services/api';
import { Sidebar } from '../components/Sidebar';
import { MessageList } from '../components/MessageList';
import { ChatInput } from '../components/ChatInput';

export function ChatPage() {
  const accessToken = useAuthStore((s) => s.accessToken);
  const logout = useAuthStore((s) => s.logout);

  const {
    conversations,
    currentConversationId,
    messages,
    isStreaming,
    streamingContent,
    setConversations,
    setCurrentConversation,
    setMessages,
    addMessage,
    appendStreamToken,
    startStreaming,
    stopStreaming,
  } = useChatStore();

  const wsRef = useRef<WebSocket | null>(null);
  const [error, setError] = useState('');

  // Load conversations
  useEffect(() => {
    chatApi
      .listConversations()
      .then(setConversations)
      .catch((err) => {
        if (err.message.includes('401')) logout();
      });
  }, [setConversations, logout]);

  // Load messages when conversation changes
  useEffect(() => {
    if (!currentConversationId) {
      setMessages([]);
      return;
    }

    chatApi
      .getConversation(currentConversationId)
      .then((conv) => setMessages(conv.messages || []))
      .catch(() => setMessages([]));
  }, [currentConversationId, setMessages]);

  // Connect WebSocket — runs ONCE when accessToken is available
  useEffect(() => {
    if (!accessToken) return;

    const ws = createChatWebSocket(accessToken);
    wsRef.current = ws;

    ws.onopen = () => {
      console.log('WebSocket connected');
      setError('');
    };

    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);

      switch (data.type) {
        case 'token':
          appendStreamToken(data.content);
          break;

        case 'done': {
          // Read latest streamingContent from store (not stale closure)
          const fullContent = useChatStore.getState().streamingContent;
          const assistantMsg = {
            id: data.message_id,
            conversation_id: data.conversation_id,
            role: 'assistant' as const,
            content: fullContent,
            token_count: data.tokens_used || 0,
            created_at: new Date().toISOString(),
          };

          // Update conversation ID if new
          if (!useChatStore.getState().currentConversationId) {
            useChatStore.setState({
              currentConversationId: data.conversation_id,
            });

            // Refresh conversation list
            chatApi.listConversations().then(setConversations);
          }

          stopStreaming(assistantMsg);
          break;
        }

        case 'error':
          setError(data.message);
          stopStreaming();
          break;
      }
    };

    ws.onerror = () => {
      setError('Connection error. Please try again.');
      stopStreaming();
    };

    ws.onclose = () => {
      console.log('WebSocket disconnected');
    };

    return () => {
      ws.close();
      wsRef.current = null;
    };
  }, [accessToken]); // only reconnect when token changes

  // Send message via WebSocket
  const sendMessage = useCallback(
    (text: string) => {
      if (!text.trim() || !wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) {
        setError('Not connected. Please refresh.');
        return;
      }

      setError('');

      const convId = useChatStore.getState().currentConversationId;

      // Add user message to local state
      const userMsg = {
        id: crypto.randomUUID(),
        conversation_id: convId || 'pending',
        role: 'user' as const,
        content: text,
        token_count: 0,
        created_at: new Date().toISOString(),
      };
      addMessage(userMsg);

      startStreaming();

      wsRef.current.send(
        JSON.stringify({
          type: 'message',
          conversation_id: convId,
          message: text,
          use_memory: true,
        })
      );
    },
    [addMessage, startStreaming]
  );

  const selectConversation = useCallback(
    (id: string) => {
      setCurrentConversation(id);
    },
    [setCurrentConversation]
  );

  const newConversation = useCallback(() => {
    setCurrentConversation(null);
    setMessages([]);
  }, [setCurrentConversation, setMessages]);

  const deleteConversation = useCallback(
    async (id: string) => {
      try {
        await chatApi.deleteConversation(id);
        useChatStore.getState().removeConversation(id);
        if (useChatStore.getState().currentConversationId === id) {
          setCurrentConversation(null);
          setMessages([]);
        }
      } catch {
        setError('Failed to delete conversation');
      }
    },
    [setCurrentConversation, setMessages]
  );

  return (
    <div className="h-screen flex bg-jarvis-bg">
      {/* Sidebar */}
      <Sidebar
        conversations={conversations}
        currentId={currentConversationId}
        onSelect={selectConversation}
        onNew={newConversation}
        onDelete={deleteConversation}
        onLogout={logout}
      />

      {/* Main Chat Area */}
      <div className="flex-1 flex flex-col min-w-0">
        {/* Header */}
        <header className="h-14 border-b border-jarvis-border flex items-center px-6 flex-shrink-0">
          <div className="flex items-center gap-3">
            <div className="w-3 h-3 rounded-full bg-jarvis-accent jarvis-orb" />
            <h2 className="font-medium text-jarvis-text">
              {currentConversationId
                ? conversations.find((c) => c.id === currentConversationId)?.title ||
                  'Jarvis'
                : 'New Conversation'}
            </h2>
          </div>
        </header>

        {/* Messages */}
        <MessageList
          messages={messages}
          streamingContent={streamingContent}
          isStreaming={isStreaming}
        />

        {/* Error */}
        {error && (
          <div className="mx-6 mb-2 p-2 bg-red-500/10 border border-red-500/30 rounded-lg text-red-400 text-sm text-center">
            {error}
            <button
              onClick={() => setError('')}
              className="ml-2 underline hover:text-red-300"
            >
              Dismiss
            </button>
          </div>
        )}

        {/* Input */}
        <ChatInput onSend={sendMessage} disabled={isStreaming} />
      </div>
    </div>
  );
}
