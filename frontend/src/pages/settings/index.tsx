import { useEffect, useState } from "react";

import { api } from "@/api/client";
import { Card } from "@/components/layout/Card";

const PIPELINE_VERSIONS = [
  { stage: "Respiratory event detection", version: "envelope-v1" },
  { stage: "Oxygen burden (ODI)", version: "3%-dip, 1Hz decimation" },
  { stage: "Sleep staging", version: "MIT-BIH PSG .st annotations (ground truth, not modeled)" },
  { stage: "EEG brain response", version: "Welch PSD, 4 bands" },
  { stage: "Autonomic response", version: "Pan-Tompkins-style R-peak detection" },
  { stage: "Phenotyping", version: "K-means, fixed seed 42" },
];

export default function SettingsPage() {
  const [auditLog, setAuditLog] = useState<Awaited<ReturnType<typeof api.getAuditLog>> | null>(null);
  const [assistantStatus, setAssistantStatus] = useState<Awaited<ReturnType<typeof api.getAssistantStatus>> | null>(null);

  useEffect(() => {
    api.getAuditLog(20).then(setAuditLog).catch(() => setAuditLog([]));
    api.getAssistantStatus().then(setAssistantStatus).catch(() => setAssistantStatus(null));
  }, []);

  return (
    <div className="mx-auto max-w-3xl space-y-4">
      <div>
        <h1 className="text-xl font-semibold text-slate-900">Settings</h1>
        <p className="mt-1 text-sm text-slate-600">Data governance, pipeline versions, and access.</p>
      </div>

      <Card>
        <div className="text-sm font-semibold text-slate-900">Data governance</div>
        <ul className="mt-2 space-y-1 text-xs text-slate-600">
          <li>• Uploaded data is private by default and never used to train models without explicit opt-in.</li>
          <li>• Every mutating action is written to an append-only audit log (below).</li>
          <li>• Delete any study and its data at any time from the Signal Viewer list.</li>
          <li>• Access requires a Bearer token when `API_AUTH_TOKEN` is set on the backend.</li>
        </ul>
      </Card>

      <Card>
        <div className="text-sm font-semibold text-slate-900">Research Assistant</div>
        <p className="mt-1 text-xs text-slate-600">
          {assistantStatus === null
            ? "Checking…"
            : assistantStatus.configured
              ? `Using ${assistantStatus.provider === "ollama" ? "a local Ollama model" : "Anthropic"} (${assistantStatus.model}) for narration.`
              : "No local Ollama server or API key found — narration falls back to deterministic templates of the same structured data."}
        </p>
      </Card>

      <Card>
        <div className="text-sm font-semibold text-slate-900">Pipeline versions</div>
        <table className="mt-2 w-full text-xs">
          <tbody className="divide-y divide-slate-100">
            {PIPELINE_VERSIONS.map((p) => (
              <tr key={p.stage}>
                <td className="py-1.5 text-slate-500">{p.stage}</td>
                <td className="py-1.5 font-mono text-slate-700">{p.version}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </Card>

      <Card className="overflow-hidden !p-0">
        <div className="border-b border-slate-100 px-4 py-2 text-sm font-semibold text-slate-900">
          Recent audit log
        </div>
        <table className="w-full text-xs">
          <thead className="bg-slate-50 text-left text-slate-400">
            <tr>
              <th className="px-4 py-1.5 font-normal">Time</th>
              <th className="px-4 py-1.5 font-normal">Method</th>
              <th className="px-4 py-1.5 font-normal">Path</th>
              <th className="px-4 py-1.5 font-normal">Status</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {auditLog?.map((row) => (
              <tr key={row.id}>
                <td className="px-4 py-1.5 text-slate-500">{new Date(row.created_at).toLocaleTimeString()}</td>
                <td className="px-4 py-1.5 font-mono text-slate-700">{row.method}</td>
                <td className="px-4 py-1.5 font-mono text-slate-600">{row.path}</td>
                <td className="px-4 py-1.5 text-slate-600">{row.status_code}</td>
              </tr>
            ))}
            {auditLog?.length === 0 && (
              <tr>
                <td colSpan={4} className="px-4 py-3 text-center text-slate-400">
                  No mutating requests recorded yet.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </Card>
    </div>
  );
}
