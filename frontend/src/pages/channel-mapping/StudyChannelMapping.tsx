import { CheckCircle2, ShieldAlert, ShieldCheck, ShieldQuestion } from "lucide-react";
import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";

import { api } from "@/api/client";
import { Card } from "@/components/layout/Card";
import type { ChannelInfo, StudyDetail } from "@/types/study";

function ConfidenceBadge({ confidence }: { confidence: number }) {
  if (confidence >= 0.8) {
    return (
      <span className="inline-flex items-center gap-1 rounded-full bg-emerald-50 px-2 py-0.5 text-xs font-medium text-emerald-700">
        <ShieldCheck className="h-3 w-3" /> {Math.round(confidence * 100)}%
      </span>
    );
  }
  if (confidence >= 0.5) {
    return (
      <span className="inline-flex items-center gap-1 rounded-full bg-amber-50 px-2 py-0.5 text-xs font-medium text-amber-700">
        <ShieldAlert className="h-3 w-3" /> {Math.round(confidence * 100)}%
      </span>
    );
  }
  return (
    <span className="inline-flex items-center gap-1 rounded-full bg-slate-100 px-2 py-0.5 text-xs font-medium text-slate-500">
      <ShieldQuestion className="h-3 w-3" /> unmapped
    </span>
  );
}

export default function StudyChannelMapping() {
  const { studyId } = useParams<{ studyId: string }>();
  const id = Number(studyId);
  const navigate = useNavigate();

  const [study, setStudy] = useState<StudyDetail | null>(null);
  const [types, setTypes] = useState<string[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [savingId, setSavingId] = useState<number | null>(null);
  const [confirming, setConfirming] = useState(false);

  useEffect(() => {
    api.getStudy(id).then(setStudy).catch(() => setError("Could not load this study."));
    api.listChannelTypes().then(setTypes).catch(() => setTypes([]));
  }, [id]);

  async function updateType(channel: ChannelInfo, signalType: string) {
    setSavingId(channel.id);
    try {
      await api.updateChannelMapping(id, channel.id, signalType || null);
      setStudy((prev) =>
        prev
          ? {
              ...prev,
              channels: prev.channels.map((c) =>
                c.id === channel.id
                  ? { ...c, signal_type: signalType || null, mapping_confidence: 1, mapping_confirmed: true }
                  : c,
              ),
            }
          : prev,
      );
    } finally {
      setSavingId(null);
    }
  }

  async function confirmAll() {
    setConfirming(true);
    try {
      const updated = await api.confirmChannelMapping(id);
      setStudy(updated);
      navigate(`/qc/${id}`);
    } finally {
      setConfirming(false);
    }
  }

  if (error) return <p className="text-sm text-red-600">{error}</p>;
  if (!study) return <p className="text-sm text-slate-400">Loading…</p>;

  const allMapped = study.channels.every((c) => c.signal_type);

  return (
    <div className="mx-auto max-w-3xl">
      <h1 className="text-xl font-semibold text-slate-900">Channel Mapping</h1>
      <p className="mt-1 text-sm text-slate-600">
        {study.display_name || study.record_name} — review the detected channel types below.
        Low-confidence guesses are never applied silently; pick the correct type before
        continuing.
      </p>

      <Card className="mt-4 overflow-hidden !p-0">
        <table className="w-full text-sm">
          <thead className="bg-slate-50 text-left text-xs font-medium uppercase tracking-wide text-slate-500">
            <tr>
              <th className="px-4 py-2">Raw channel</th>
              <th className="px-4 py-2">Detected</th>
              <th className="px-4 py-2">Confirmed type</th>
              <th className="px-4 py-2">Rate / unit</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {study.channels.map((c) => (
              <tr key={c.id}>
                <td className="px-4 py-2.5 font-medium text-slate-900">{c.name}</td>
                <td className="px-4 py-2.5">
                  <ConfidenceBadge confidence={c.mapping_confidence} />
                </td>
                <td className="px-4 py-2.5">
                  <div className="flex items-center gap-2">
                    <select
                      value={c.signal_type ?? ""}
                      onChange={(e) => updateType(c, e.target.value)}
                      disabled={savingId === c.id}
                      className="rounded-md border border-slate-300 px-2 py-1 text-xs"
                    >
                      <option value="">— select —</option>
                      {types.map((t) => (
                        <option key={t} value={t}>
                          {t}
                        </option>
                      ))}
                    </select>
                    {c.mapping_confirmed && <CheckCircle2 className="h-4 w-4 text-emerald-500" />}
                  </div>
                </td>
                <td className="px-4 py-2.5 text-xs text-slate-500">
                  {c.sampling_rate} Hz{c.unit ? ` · ${c.unit}` : ""}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </Card>

      <div className="mt-4 flex items-center justify-between">
        <p className="text-xs text-slate-400">
          {allMapped ? "All channels have a type." : "Some channels still need a type selected."}
        </p>
        <button
          onClick={confirmAll}
          disabled={!allMapped || confirming}
          className="rounded-md bg-brand-600 px-4 py-2 text-sm font-medium text-white hover:bg-brand-700 disabled:cursor-not-allowed disabled:opacity-50"
        >
          {confirming ? "Confirming…" : "Confirm Mapping & Continue"}
        </button>
      </div>
    </div>
  );
}
