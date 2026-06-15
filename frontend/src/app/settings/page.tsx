"use client";

import { useState, useEffect } from "react";
import { apiFetch } from "@/lib/api";

const PROVIDERS = ["openai", "anthropic", "gemini", "groq", "ollama"];

interface ConfigState {
  provider: string;
  model: string;
  api_key: string;
  endpoint_url: string;
}

export default function SettingsPage() {
  const [llmConfig, setLlmConfig] = useState<ConfigState>({ provider: "ollama", model: "llama3", api_key: "", endpoint_url: "" });
  const [embeddingConfig, setEmbeddingConfig] = useState<ConfigState>({ provider: "ollama", model: "nomic-embed-text", api_key: "", endpoint_url: "" });
  const [currentConfig, setCurrentConfig] = useState<any>(null);
  const [llmLoading, setLlmLoading] = useState(false);
  const [embeddingLoading, setEmbeddingLoading] = useState(false);
  const [llmError, setLlmError] = useState<string | null>(null);
  const [embeddingError, setEmbeddingError] = useState<string | null>(null);
  const [llmSuccess, setLlmSuccess] = useState(false);
  const [embeddingSuccess, setEmbeddingSuccess] = useState(false);

  useEffect(() => {
    loadConfig();
  }, []);

  async function loadConfig() {
    try {
      const res = await apiFetch("/providers/config");
      setCurrentConfig(res.data);
    } catch {}
  }

  async function saveLLM(e: React.FormEvent) {
    e.preventDefault();
    setLlmLoading(true);
    setLlmError(null);
    setLlmSuccess(false);
    try {
      await apiFetch("/providers/llm", {
        method: "PUT",
        body: JSON.stringify(llmConfig),
      });
      setLlmSuccess(true);
      loadConfig();
    } catch (err: any) {
      setLlmError(err.message);
    }
    setLlmLoading(false);
  }

  async function saveEmbedding(e: React.FormEvent) {
    e.preventDefault();
    setEmbeddingLoading(true);
    setEmbeddingError(null);
    setEmbeddingSuccess(false);
    try {
      await apiFetch("/providers/embedding", {
        method: "PUT",
        body: JSON.stringify(embeddingConfig),
      });
      setEmbeddingSuccess(true);
      loadConfig();
    } catch (err: any) {
      setEmbeddingError(err.message);
    }
    setEmbeddingLoading(false);
  }

  return (
    <div className="p-8 max-w-3xl">
      <h1 className="text-2xl font-bold mb-6">Provider Settings</h1>

      {/* Current Config */}
      {currentConfig && (
        <div className="bg-white rounded-xl shadow p-6 mb-8">
          <h2 className="text-lg font-semibold mb-3">Current Configuration</h2>
          <div className="grid grid-cols-2 gap-4 text-sm">
            <div>
              <p className="text-gray-500">LLM Provider</p>
              <p className="font-medium">{currentConfig.llm ? `${currentConfig.llm.provider_name}/${currentConfig.llm.model_identifier}` : "Not configured"}</p>
            </div>
            <div>
              <p className="text-gray-500">Embedding Provider</p>
              <p className="font-medium">{currentConfig.embedding ? `${currentConfig.embedding.provider_name}/${currentConfig.embedding.model_identifier}` : "Not configured"}</p>
            </div>
          </div>
        </div>
      )}

      {/* LLM Config */}
      <form onSubmit={saveLLM} className="bg-white rounded-xl shadow p-6 mb-8">
        <h2 className="text-lg font-semibold mb-4">LLM Provider</h2>
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Provider</label>
            <select
              value={llmConfig.provider}
              onChange={(e) => setLlmConfig({ ...llmConfig, provider: e.target.value })}
              className="w-full border rounded-lg px-3 py-2"
            >
              {PROVIDERS.map((p) => <option key={p} value={p}>{p}</option>)}
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Model</label>
            <input
              type="text"
              value={llmConfig.model}
              onChange={(e) => setLlmConfig({ ...llmConfig, model: e.target.value })}
              className="w-full border rounded-lg px-3 py-2"
              placeholder="e.g. gpt-4o, claude-3-sonnet, llama3"
            />
          </div>
          {llmConfig.provider !== "ollama" && (
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">API Key</label>
              <input
                type="password"
                value={llmConfig.api_key}
                onChange={(e) => setLlmConfig({ ...llmConfig, api_key: e.target.value })}
                className="w-full border rounded-lg px-3 py-2"
                placeholder="sk-..."
              />
            </div>
          )}
          {llmConfig.provider === "ollama" && (
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Endpoint URL</label>
              <input
                type="text"
                value={llmConfig.endpoint_url}
                onChange={(e) => setLlmConfig({ ...llmConfig, endpoint_url: e.target.value })}
                className="w-full border rounded-lg px-3 py-2"
                placeholder="http://host.docker.internal:11434"
              />
            </div>
          )}
          {llmError && <p className="text-red-600 text-sm">{llmError}</p>}
          {llmSuccess && <p className="text-green-600 text-sm">✓ LLM provider configured successfully</p>}
          <button
            type="submit"
            disabled={llmLoading}
            className="bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700 disabled:opacity-50"
          >
            {llmLoading ? "Validating..." : "Save LLM Config"}
          </button>
        </div>
      </form>

      {/* Embedding Config */}
      <form onSubmit={saveEmbedding} className="bg-white rounded-xl shadow p-6">
        <h2 className="text-lg font-semibold mb-4">Embedding Provider</h2>
        <div className="bg-yellow-50 border border-yellow-200 rounded p-3 mb-4 text-sm text-yellow-800">
          ⚠️ Changing the embedding model will require re-processing all existing documents.
        </div>
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Provider</label>
            <select
              value={embeddingConfig.provider}
              onChange={(e) => setEmbeddingConfig({ ...embeddingConfig, provider: e.target.value })}
              className="w-full border rounded-lg px-3 py-2"
            >
              {PROVIDERS.map((p) => <option key={p} value={p}>{p}</option>)}
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Model</label>
            <input
              type="text"
              value={embeddingConfig.model}
              onChange={(e) => setEmbeddingConfig({ ...embeddingConfig, model: e.target.value })}
              className="w-full border rounded-lg px-3 py-2"
              placeholder="e.g. text-embedding-3-small, nomic-embed-text"
            />
          </div>
          {embeddingConfig.provider !== "ollama" && (
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">API Key</label>
              <input
                type="password"
                value={embeddingConfig.api_key}
                onChange={(e) => setEmbeddingConfig({ ...embeddingConfig, api_key: e.target.value })}
                className="w-full border rounded-lg px-3 py-2"
                placeholder="sk-..."
              />
            </div>
          )}
          {embeddingConfig.provider === "ollama" && (
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Endpoint URL</label>
              <input
                type="text"
                value={embeddingConfig.endpoint_url}
                onChange={(e) => setEmbeddingConfig({ ...embeddingConfig, endpoint_url: e.target.value })}
                className="w-full border rounded-lg px-3 py-2"
                placeholder="http://host.docker.internal:11434"
              />
            </div>
          )}
          {embeddingError && <p className="text-red-600 text-sm">{embeddingError}</p>}
          {embeddingSuccess && <p className="text-green-600 text-sm">✓ Embedding provider configured successfully</p>}
          <button
            type="submit"
            disabled={embeddingLoading}
            className="bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700 disabled:opacity-50"
          >
            {embeddingLoading ? "Validating..." : "Save Embedding Config"}
          </button>
        </div>
      </form>
    </div>
  );
}
