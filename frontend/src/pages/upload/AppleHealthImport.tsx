import { AlertCircle, Loader2, Moon, Watch } from "lucide-react";
import { useRef, useState } from "react";
import { useNavigate } from "react-router-dom";

import { api } from "@/api/client";
import { Card } from "@/components/layout/Card";
import type { AppleHealthSession } from "@/types/study";

function formatSession(s: AppleHealthSession): { date: string; time: string } {
  const start = new Date(s.start);
  return {
    date: start.toLocaleDateString(undefined, { weekday: "short", month: "short", day: "numeric" }),
    time: start.toLocaleTimeString(undefined, { hour: "numeric", minute: "2-digit" }),
  };
}

export default function AppleHealthImport() {
  const navigate = useNavigate();
  const inputRef = useRef<HTMLInputElement>(null);
  const [scanning, setScanning] = useState(false);
  const [sourceId, setSourceId] = useState<string | null>(null);
  const [sessions, setSessions] = useState<AppleHealthSession[] | null>(null);
  const [importingIndex, setImportingIndex] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function handleFile(file: File) {
    setScanning(true);
    setError(null);
    setSessions(null);
    try {
      const result = await api.scanAppleHealth(file);
      setSourceId(result.source_id);
      setSessions(result.sessions);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not scan this export.");
    } finally {
      setScanning(false);
    }
  }

  async function importNight(index: number) {
    if (!sourceId) return;
    setImportingIndex(index);
    setError(null);
    try {
      const study = await api.importAppleHealthNight(sourceId, index);
      navigate(`/viewer/${study.id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Import failed.");
      setImportingIndex(null);
    }
  }

  return (
    <Card className="mt-4">
      <div className="flex items-center gap-2">
        <Watch className="h-4 w-4 text-slate-400" />
        <div className="text-sm font-semibold text-slate-900">Import from Apple Health</div>
      </div>
      <p className="mt-1 text-xs text-slate-500">
        Health app → profile icon (top right) → Export All Health Data → AirDrop{" "}
        <code className="rounded bg-slate-100 px-1">export.zip</code> here. Apple Watch's own sleep
        stages (not EEG), plus heart rate / SpO2 / respiratory rate spot-checks resampled onto a
        coarse grid — a different kind of data than real PSG, shown separately from the
        continuous-signal pipelines built for that.
      </p>

      {!sessions && (
        <button
          onClick={() => inputRef.current?.click()}
          disabled={scanning}
          className="mt-3 inline-flex items-center gap-1.5 rounded-md border border-slate-300 px-3 py-1.5 text-sm font-medium text-slate-700 hover:bg-slate-50 disabled:opacity-50"
        >
          {scanning && <Loader2 className="h-3.5 w-3.5 animate-spin" />}
          {scanning ? "Scanning export…" : "Choose export.zip / export.xml"}
        </button>
      )}
      <input
        ref={inputRef}
        type="file"
        accept=".zip,.xml"
        className="hidden"
        onChange={(e) => {
          const file = e.target.files?.[0];
          if (file) handleFile(file);
          e.target.value = "";
        }}
      />

      {error && (
        <div className="mt-3 flex items-start gap-1.5 rounded-md bg-red-50 px-3 py-2 text-xs text-red-700">
          <AlertCircle className="mt-0.5 h-3.5 w-3.5 shrink-0" />
          {error}
        </div>
      )}

      {sessions && (
        <div className="mt-3">
          <div className="mb-2 flex items-center justify-between text-xs text-slate-500">
            <span>{sessions.length} sleep sessions found — pick one to import</span>
            <button
              onClick={() => {
                setSessions(null);
                setSourceId(null);
              }}
              className="text-brand-600 hover:underline"
            >
              choose a different file
            </button>
          </div>
          <div className="max-h-80 space-y-1 overflow-y-auto">
            {sessions.map((s) => {
              const { date, time } = formatSession(s);
              const busy = importingIndex === s.index;
              return (
                <button
                  key={s.index}
                  onClick={() => importNight(s.index)}
                  disabled={importingIndex !== null}
                  className="flex w-full items-center justify-between rounded-md border border-slate-200 px-3 py-2 text-left text-sm hover:border-brand-300 hover:bg-brand-50 disabled:opacity-50"
                >
                  <span className="flex items-center gap-2">
                    <Moon className="h-3.5 w-3.5 text-slate-400" />
                    <span className="font-medium text-slate-800">{date}</span>
                    <span className="text-slate-500">{time}</span>
                  </span>
                  <span className="flex items-center gap-2 text-xs text-slate-500">
                    {s.duration_hours}h · {s.record_count} records
                    {busy && <Loader2 className="h-3.5 w-3.5 animate-spin" />}
                  </span>
                </button>
              );
            })}
          </div>
        </div>
      )}
    </Card>
  );
}
