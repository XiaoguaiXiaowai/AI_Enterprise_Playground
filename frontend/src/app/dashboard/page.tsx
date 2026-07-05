"use client";

import { useCallback, useEffect, useMemo, useState } from "react";

import { loadToken, saveToken } from "@/lib/auth";
import { apiGet } from "@/lib/api";

type Overview = {
  health: Record<string, unknown>;
  server_time: string;
  counts: Record<string, number>;
  recents: Record<string, Array<Record<string, unknown>>>;
  token_usage_24h: Record<string, unknown>;
  range?: { since: string; until: string; hours: number };
  failure_rates?: {
    agent_runs_total: number;
    agent_runs_failed: number;
    agent_runs_failure_rate: number;
    mcp_tool_calls_total: number;
    mcp_tool_calls_failed: number;
    mcp_tool_calls_failure_rate: number;
  };
  hitl_pending_queue?: {
    total: number;
    limit: number;
    offset: number;
    items: Array<Record<string, unknown>>;
  };
};

function Card({
  title,
  value,
}: {
  title: string;
  value: string | number;
}) {
  return (
    <div className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
      <div className="text-xs text-slate-500">{title}</div>
      <div className="mt-2 text-2xl font-semibold">{value}</div>
    </div>
  );
}

function Table({
  title,
  rows,
}: {
  title: string;
  rows: Array<Record<string, unknown>>;
}) {
  const keys = useMemo(() => {
    const first = rows[0] || {};
    return Object.keys(first).slice(0, 6);
  }, [rows]);

  return (
    <div className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
      <div className="text-sm font-medium">{title}</div>
      <div className="mt-3 overflow-x-auto">
        <table className="min-w-full text-sm">
          <thead>
            <tr className="border-b border-slate-200 text-left text-xs text-slate-500">
              {keys.map((k) => (
                <th key={k} className="py-2 pr-4 font-medium">
                  {k}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.slice(0, 5).map((r, i) => (
              <tr key={i} className="border-b border-slate-100 last:border-0">
                {keys.map((k) => (
                  <td key={k} className="py-2 pr-4 text-slate-700">
                    {String(r[k] ?? "")}
                  </td>
                ))}
              </tr>
            ))}
            {rows.length === 0 ? (
              <tr>
                <td colSpan={keys.length || 1} className="py-3 text-slate-500">
                  No data
                </td>
              </tr>
            ) : null}
          </tbody>
        </table>
      </div>
    </div>
  );
}

export default function DashboardPage() {
  const [token, setToken] = useState("");
  const [overview, setOverview] = useState<Overview | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [hours, setHours] = useState(24);
  const [hitlOffset, setHitlOffset] = useState(0);
  const hitlLimit = 20;

  useEffect(() => {
    setToken(loadToken());
  }, []);

  const refresh = useCallback(async () => {
    setLoading(true);
    setError("");
    const r = await apiGet<Overview>(
      `/api/v1/dashboard/overview?hours=${encodeURIComponent(String(hours))}&hitl_pending_limit=${encodeURIComponent(
        String(hitlLimit),
      )}&hitl_pending_offset=${encodeURIComponent(String(hitlOffset))}`,
      token,
    );
    if (r.ok) setOverview(r.data);
    else setError(r.error);
    setLoading(false);
  }, [hours, hitlLimit, hitlOffset, token]);

  useEffect(() => {
    if (!token) return;
    if (!overview) return;
    refresh();
  }, [hitlOffset, overview, refresh, token]);

  const counts = overview?.counts || {};
  const recents = overview?.recents || {};
  const failure = overview?.failure_rates;
  const pendingQueue = overview?.hitl_pending_queue;
  const pendingRows = (pendingQueue?.items || []) as Array<Record<string, unknown>>;
  const totalPending = pendingQueue?.total || 0;
  const from = hitlOffset + 1;
  const to = Math.min(hitlOffset + hitlLimit, totalPending);

  return (
    <main className="mx-auto max-w-6xl px-6 py-10">
      <div className="flex items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold">Dashboard</h1>
          <div className="mt-1 text-sm text-slate-500">
            {overview ? `Server time: ${overview.server_time}` : "Connect to backend and load overview"}
          </div>
        </div>
        <a className="text-sm text-slate-600 underline" href="/">
          Home
        </a>
      </div>

      <div className="mt-6 rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
        <div className="flex flex-col gap-3 md:flex-row md:items-end">
          <div className="flex-1">
            <div className="text-xs text-slate-500">Access token</div>
            <input
              value={token}
              onChange={(e) => setToken(e.target.value)}
              className="mt-1 w-full rounded-md border border-slate-200 px-3 py-2 text-sm outline-none focus:border-slate-400"
              placeholder="Paste JWT access token"
            />
          </div>
          <div>
            <div className="text-xs text-slate-500">Time range</div>
            <select
              value={hours}
              onChange={(e) => {
                setHours(Number(e.target.value));
                setHitlOffset(0);
              }}
              className="mt-1 rounded-md border border-slate-200 bg-white px-3 py-2 text-sm outline-none focus:border-slate-400"
            >
              <option value={1}>Last 1h</option>
              <option value={6}>Last 6h</option>
              <option value={24}>Last 24h</option>
              <option value={72}>Last 3d</option>
              <option value={168}>Last 7d</option>
            </select>
          </div>
          <button
            onClick={() => saveToken(token)}
            className="rounded-md border border-slate-200 bg-white px-4 py-2 text-sm hover:bg-slate-50"
          >
            Save
          </button>
          <button
            onClick={refresh}
            className="rounded-md bg-slate-900 px-4 py-2 text-sm text-white hover:bg-slate-800 disabled:opacity-50"
            disabled={!token || loading}
          >
            {loading ? "Loading..." : "Load"}
          </button>
        </div>
        {error ? <div className="mt-3 text-sm text-red-600">{error}</div> : null}
      </div>

      <div className="mt-6 grid grid-cols-1 gap-4 md:grid-cols-2">
        <div className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
          <div className="text-sm font-medium">Failure rates (range)</div>
          <div className="mt-3 grid grid-cols-2 gap-4">
            <Card
              title="Agent failures"
              value={
                failure
                  ? `${Math.round(failure.agent_runs_failure_rate * 100)}% (${failure.agent_runs_failed}/${failure.agent_runs_total})`
                  : "-"
              }
            />
            <Card
              title="MCP failures"
              value={
                failure
                  ? `${Math.round(failure.mcp_tool_calls_failure_rate * 100)}% (${failure.mcp_tool_calls_failed}/${failure.mcp_tool_calls_total})`
                  : "-"
              }
            />
          </div>
          <div className="mt-3 text-xs text-slate-500">
            {overview?.range ? `Range: ${overview.range.since} → ${overview.range.until}` : ""}
          </div>
        </div>

        <div className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
          <div className="flex items-center justify-between gap-3">
            <div>
              <div className="text-sm font-medium">HITL pending queue</div>
              <div className="mt-1 text-xs text-slate-500">
                {totalPending > 0 ? `Showing ${from}-${to} of ${totalPending}` : "No pending items"}
              </div>
            </div>
            <div className="flex gap-2">
              <button
                className="rounded-md border border-slate-200 bg-white px-3 py-2 text-sm disabled:opacity-50"
                onClick={() => setHitlOffset((v) => Math.max(0, v - hitlLimit))}
                disabled={hitlOffset === 0 || loading}
              >
                Prev
              </button>
              <button
                className="rounded-md border border-slate-200 bg-white px-3 py-2 text-sm disabled:opacity-50"
                onClick={() => setHitlOffset((v) => v + hitlLimit)}
                disabled={hitlOffset + hitlLimit >= totalPending || loading}
              >
                Next
              </button>
            </div>
          </div>
          <div className="mt-3">
            <Table title="Pending HITL" rows={pendingRows} />
          </div>
          <div className="mt-3">
            <button
              onClick={refresh}
              className="rounded-md bg-slate-900 px-4 py-2 text-sm text-white hover:bg-slate-800 disabled:opacity-50"
              disabled={!token || loading}
            >
              Refresh queue
            </button>
          </div>
        </div>
      </div>

      <div className="mt-6 grid grid-cols-2 gap-4 md:grid-cols-4">
        <Card title="Chat Sessions" value={counts["chat_sessions"] ?? 0} />
        <Card title="Chat Messages" value={counts["chat_messages"] ?? 0} />
        <Card title="Agent Runs" value={counts["agent_runs"] ?? 0} />
        <Card title="HITL Pending" value={counts["hitl_pending"] ?? 0} />
      </div>

      <div className="mt-4 grid grid-cols-2 gap-4 md:grid-cols-4">
        <Card title="MCP Servers" value={counts["mcp_servers"] ?? 0} />
        <Card title="MCP Tool Calls" value={counts["mcp_tool_calls"] ?? 0} />
        <Card title="RAG Documents" value={counts["rag_documents"] ?? 0} />
        <Card title="Memories" value={counts["memories"] ?? 0} />
      </div>

      <div className="mt-6 grid grid-cols-1 gap-4 lg:grid-cols-2">
        <Table title="Recent Agent Runs" rows={recents["agent_runs"] || []} />
        <Table title="Recent HITL Requests" rows={recents["hitl_requests"] || []} />
        <Table title="Recent MCP Tool Calls" rows={recents["mcp_tool_calls"] || []} />
        <Table title="Recent RAG Documents" rows={recents["rag_documents"] || []} />
        <Table title="Recent Chat Sessions" rows={recents["chat_sessions"] || []} />
        <Table title="Recent Audit Logs" rows={recents["audit_logs"] || []} />
      </div>
    </main>
  );
}
