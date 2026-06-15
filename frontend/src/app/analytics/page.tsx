"use client";

import { useState, useEffect } from "react";
import { apiFetch } from "@/lib/api";

interface Summary {
  total_documents: number;
  total_chunks: number;
  total_queries: number;
}

interface QueryVolume {
  date: string;
  count: number;
}

interface Keyword {
  keyword: string;
  count: number;
}

interface ResponseTimes {
  average_ms: number;
  min_ms: number | null;
  max_ms: number | null;
  count: number;
}

export default function AnalyticsPage() {
  const [summary, setSummary] = useState<Summary>({ total_documents: 0, total_chunks: 0, total_queries: 0 });
  const [volume, setVolume] = useState<QueryVolume[]>([]);
  const [keywords, setKeywords] = useState<Keyword[]>([]);
  const [responseTimes, setResponseTimes] = useState<ResponseTimes>({ average_ms: 0, min_ms: null, max_ms: null, count: 0 });
  const [granularity, setGranularity] = useState("daily");

  useEffect(() => {
    loadData();
  }, [granularity]);

  async function loadData() {
    try {
      const [summaryRes, volumeRes, keywordsRes, timesRes] = await Promise.all([
        apiFetch("/analytics/summary"),
        apiFetch(`/analytics/query-volume?granularity=${granularity}`),
        apiFetch("/analytics/top-keywords"),
        apiFetch("/analytics/response-times"),
      ]);
      setSummary(summaryRes.data);
      setVolume(volumeRes.data);
      setKeywords(keywordsRes.data);
      setResponseTimes(timesRes.data);
    } catch {}
  }

  return (
    <div className="p-8">
      <h1 className="text-2xl font-bold mb-6">Analytics</h1>

      {/* Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-8">
        <div className="bg-white rounded-xl shadow p-6">
          <p className="text-sm text-gray-500">Total Documents</p>
          <p className="text-3xl font-bold mt-1">{summary.total_documents}</p>
        </div>
        <div className="bg-white rounded-xl shadow p-6">
          <p className="text-sm text-gray-500">Total Chunks</p>
          <p className="text-3xl font-bold mt-1">{summary.total_chunks}</p>
        </div>
        <div className="bg-white rounded-xl shadow p-6">
          <p className="text-sm text-gray-500">Total Queries</p>
          <p className="text-3xl font-bold mt-1">{summary.total_queries}</p>
        </div>
      </div>

      {/* Response Times */}
      <div className="bg-white rounded-xl shadow p-6 mb-8">
        <h2 className="text-lg font-semibold mb-4">Response Times</h2>
        <div className="grid grid-cols-3 gap-4">
          <div>
            <p className="text-sm text-gray-500">Average</p>
            <p className="text-2xl font-bold">{Math.round(responseTimes.average_ms)} ms</p>
          </div>
          <div>
            <p className="text-sm text-gray-500">Min</p>
            <p className="text-2xl font-bold">{responseTimes.min_ms ?? "-"} ms</p>
          </div>
          <div>
            <p className="text-sm text-gray-500">Max</p>
            <p className="text-2xl font-bold">{responseTimes.max_ms ?? "-"} ms</p>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        {/* Query Volume */}
        <div className="bg-white rounded-xl shadow p-6">
          <div className="flex justify-between items-center mb-4">
            <h2 className="text-lg font-semibold">Query Volume</h2>
            <select
              value={granularity}
              onChange={(e) => setGranularity(e.target.value)}
              className="border rounded px-2 py-1 text-sm"
            >
              <option value="daily">Daily</option>
              <option value="weekly">Weekly</option>
              <option value="monthly">Monthly</option>
            </select>
          </div>
          {volume.length > 0 ? (
            <div className="space-y-2">
              {volume.slice(-10).map((v) => (
                <div key={v.date} className="flex items-center gap-2">
                  <span className="text-xs text-gray-500 w-24">{new Date(v.date).toLocaleDateString()}</span>
                  <div className="flex-1 bg-gray-100 rounded-full h-4">
                    <div
                      className="bg-blue-500 rounded-full h-4"
                      style={{ width: `${Math.min(100, (v.count / Math.max(...volume.map(x => x.count))) * 100)}%` }}
                    />
                  </div>
                  <span className="text-xs font-medium w-8">{v.count}</span>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-gray-400 text-center py-8">No query data yet</p>
          )}
        </div>

        {/* Top Keywords */}
        <div className="bg-white rounded-xl shadow p-6">
          <h2 className="text-lg font-semibold mb-4">Top Keywords</h2>
          {keywords.length > 0 ? (
            <div className="space-y-2">
              {keywords.map((kw, i) => (
                <div key={kw.keyword} className="flex items-center justify-between">
                  <span className="text-sm">
                    <span className="text-gray-400 mr-2">{i + 1}.</span>
                    {kw.keyword}
                  </span>
                  <span className="text-sm font-medium text-gray-600">{kw.count}</span>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-gray-400 text-center py-8">No keywords yet</p>
          )}
        </div>
      </div>
    </div>
  );
}
