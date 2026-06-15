"use client";

import { useState, useRef, useEffect } from "react";
import { apiFetch } from "@/lib/api";
import { streamChat, SSEEvent } from "@/lib/sse";
import type { Message, SourceReference, Conversation } from "@/types";

export default function ChatPage() {
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [activeSession, setActiveSession] = useState<string | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [isStreaming, setIsStreaming] = useState(false);
  const [streamingContent, setStreamingContent] = useState("");
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    loadConversations();
  }, []);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, streamingContent]);

  async function loadConversations() {
    try {
      const res = await apiFetch("/conversations");
      setConversations(res.data || []);
    } catch {}
  }

  async function createSession() {
    const res = await apiFetch("/conversations", {
      method: "POST",
      body: JSON.stringify({ title: null }),
    });
    const newId = res.data.id;
    setActiveSession(newId);
    setMessages([]);
    loadConversations();
    return newId;
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!input.trim() || isStreaming) return;

    let sessionId = activeSession;
    if (!sessionId) {
      sessionId = await createSession();
    }

    const question = input.trim();
    setInput("");
    setMessages((prev) => [
      ...prev,
      { id: crypto.randomUUID(), role: "user", content: question, source_references: null, created_at: new Date().toISOString() },
    ]);

    setIsStreaming(true);
    setStreamingContent("");
    let fullContent = "";
    let sources: SourceReference[] = [];

    try {
      for await (const event of streamChat(sessionId!, question)) {
        if (event.event === "token") {
          fullContent += event.data.content;
          setStreamingContent(fullContent);
        } else if (event.event === "sources") {
          sources = event.data.references;
        } else if (event.event === "done") {
          setMessages((prev) => [
            ...prev,
            { id: event.data.message_id, role: "assistant", content: fullContent, source_references: sources, created_at: new Date().toISOString() },
          ]);
          setStreamingContent("");
        } else if (event.event === "error") {
          setMessages((prev) => [
            ...prev,
            { id: crypto.randomUUID(), role: "assistant", content: `⚠️ ${event.data.message}`, source_references: null, created_at: new Date().toISOString() },
          ]);
          setStreamingContent("");
        }
      }
    } catch (err: any) {
      setMessages((prev) => [
        ...prev,
        { id: crypto.randomUUID(), role: "assistant", content: `⚠️ Error: ${err.message}`, source_references: null, created_at: new Date().toISOString() },
      ]);
      setStreamingContent("");
    }
    setIsStreaming(false);
  }

  async function selectConversation(id: string) {
    setActiveSession(id);
    try {
      const res = await apiFetch(`/conversations/${id}/messages`);
      setMessages(res.data || []);
    } catch {}
  }

  return (
    <div className="flex h-screen">
      {/* Conversation sidebar */}
      <div className="w-64 bg-gray-100 border-r overflow-y-auto p-4">
        <button
          onClick={createSession}
          className="w-full bg-blue-600 text-white rounded-lg py-2 px-4 mb-4 hover:bg-blue-700"
        >
          + New Chat
        </button>
        {conversations.map((c) => (
          <div key={c.id} className="flex items-center group">
            <button
              onClick={() => selectConversation(c.id)}
              className={`flex-1 text-left px-3 py-2 rounded-l mb-1 text-sm truncate ${
                activeSession === c.id ? "bg-blue-100 text-blue-800" : "hover:bg-gray-200"
              }`}
            >
              {c.title || "Untitled chat"}
            </button>
            <button
              onClick={async (e) => {
                e.stopPropagation();
                if (!confirm("Delete this conversation?")) return;
                try {
                  await apiFetch(`/conversations/${c.id}`, { method: "DELETE" });
                  if (activeSession === c.id) {
                    setActiveSession(null);
                    setMessages([]);
                  }
                  loadConversations();
                } catch {}
              }}
              className="px-2 py-2 text-gray-400 hover:text-red-600 opacity-0 group-hover:opacity-100 transition-opacity text-xs"
              title="Delete"
            >
              ✕
            </button>
          </div>
        ))}
      </div>

      {/* Chat area */}
      <div className="flex-1 flex flex-col">
        <div className="flex-1 overflow-y-auto p-6 space-y-4">
          {messages.map((msg) => (
            <div key={msg.id} className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}>
              <div className={`max-w-2xl rounded-lg p-4 ${
                msg.role === "user" ? "bg-blue-600 text-white" : "bg-white border shadow-sm"
              }`}>
                <p className="whitespace-pre-wrap">{msg.content}</p>
                {msg.source_references && msg.source_references.length > 0 && (
                  <div className="mt-3 pt-3 border-t border-gray-200 space-y-2">
                    <p className="text-xs font-semibold text-gray-500">Sources:</p>
                    {msg.source_references.map((ref, i) => (
                      <div key={i} className="text-xs bg-gray-50 rounded p-2">
                        <span className="font-medium">{ref.document_name}</span>
                        {ref.page_number && <span className="text-gray-400"> • p.{ref.page_number}</span>}
                        <span className="text-gray-400"> • {Math.round(ref.confidence_score * 100)}%</span>
                        <p className="text-gray-600 mt-1 line-clamp-2">{ref.excerpt}</p>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          ))}
          {streamingContent && (
            <div className="flex justify-start">
              <div className="max-w-2xl rounded-lg p-4 bg-white border shadow-sm">
                <p className="whitespace-pre-wrap">{streamingContent}<span className="animate-pulse">▊</span></p>
              </div>
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>

        {/* Input */}
        <form onSubmit={handleSubmit} className="p-4 border-t bg-white">
          <div className="flex gap-2 max-w-4xl mx-auto">
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Ask a question about your documents..."
              className="flex-1 border rounded-lg px-4 py-3 focus:outline-none focus:ring-2 focus:ring-blue-500"
              disabled={isStreaming}
              maxLength={2000}
            />
            <button
              type="submit"
              disabled={isStreaming || !input.trim()}
              className="bg-blue-600 text-white px-6 py-3 rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              Send
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
