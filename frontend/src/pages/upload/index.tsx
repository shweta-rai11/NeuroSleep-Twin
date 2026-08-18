import { AlertCircle, FileUp, Loader2, UploadCloud } from "lucide-react";
import { useRef, useState } from "react";
import { useNavigate } from "react-router-dom";

import { api } from "@/api/client";
import { Card } from "@/components/layout/Card";
import AppleHealthImport from "./AppleHealthImport";

const ACCEPTED_HINT = ".edf · .hea/.dat (or zipped) · .csv + .json · audio/video (.mp4/.m4a/.mov/.mp3/.wav)";
const ACCEPTED_EXTENSIONS = [
  ".edf", ".hea", ".dat", ".zip", ".csv", ".json", ".mp4", ".m4a", ".mov", ".mp3", ".wav", ".aac",
];
const POLL_INTERVAL_MS = 2000;

type Stage = "idle" | "uploading" | "ingesting" | "error";

export default function UploadPage() {
  const navigate = useNavigate();
  const inputRef = useRef<HTMLInputElement>(null);
  const [files, setFiles] = useState<File[]>([]);
  const [displayName, setDisplayName] = useState("");
  const [stage, setStage] = useState<Stage>("idle");
  const [error, setError] = useState<string | null>(null);
  const [dragOver, setDragOver] = useState(false);

  function addFiles(fileList: FileList | File[]) {
    const incoming = Array.from(fileList);
    const rejected = incoming.filter(
      (f) => !ACCEPTED_EXTENSIONS.some((ext) => f.name.toLowerCase().endsWith(ext)),
    );
    if (rejected.length > 0) {
      setError(
        `${rejected.map((f) => f.name).join(", ")} — not an accepted file type. Accepted: ${ACCEPTED_HINT}`,
      );
      return;
    }
    setFiles((prev) => [...prev, ...incoming]);
    setError(null);
  }

  function removeFile(name: string) {
    setFiles((prev) => prev.filter((f) => f.name !== name));
  }

  async function submit() {
    if (files.length === 0) return;
    setStage("uploading");
    setError(null);
    try {
      const job = await api.uploadStudy(files, displayName || undefined);
      setStage("ingesting");
      let taskId = job.task_id;
      // eslint-disable-next-line no-constant-condition
      while (true) {
        await new Promise((resolve) => setTimeout(resolve, POLL_INTERVAL_MS));
        const status = await api.getIngestJob(taskId);
        if (status.status === "ready" && status.study_id) {
          navigate(`/viewer/${status.study_id}`);
          return;
        }
        if (status.status === "error" || status.status === "failure") {
          setError(status.error ?? "Ingestion failed — check the file format and try again.");
          setStage("error");
          return;
        }
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Upload failed. Is the backend running on :8000?");
      setStage("error");
    }
  }

  const busy = stage === "uploading" || stage === "ingesting";

  return (
    <div className="mx-auto max-w-2xl">
      <h1 className="text-xl font-semibold text-slate-900">Upload Your Sleep Study</h1>
      <p className="mt-1 text-sm text-slate-600">
        Real PSG data (EDF/WFDB/CSV+JSON) runs through the exact same full pipeline as public
        data. Uploaded data is private by default and is never used to train models without your
        explicit opt-in.
      </p>
      <p className="mt-2 text-xs text-slate-500">
        A voice memo or phone video gets a different, much rougher analysis instead — acoustic
        breathing-pause detection from the audio, not the EEG/ECG/SpO2 pipeline. It's a hint at
        best, not a finding: quiet normal breathing and a real pause can sound identical.
      </p>

      <Card className="mt-4">
        <div
          onDragOver={(e) => {
            e.preventDefault();
            setDragOver(true);
          }}
          onDragLeave={() => setDragOver(false)}
          onDrop={(e) => {
            e.preventDefault();
            setDragOver(false);
            addFiles(e.dataTransfer.files);
          }}
          onClick={() => inputRef.current?.click()}
          className={`flex cursor-pointer flex-col items-center gap-2 rounded-lg border-2 border-dashed px-6 py-10 text-center transition-colors ${
            dragOver ? "border-brand-400 bg-brand-50" : "border-slate-200 hover:border-slate-300"
          }`}
        >
          <UploadCloud className="h-8 w-8 text-slate-400" />
          <div className="text-sm font-medium text-slate-700">
            Drop files here, or click to choose
          </div>
          <div className="text-xs text-slate-400">Accepted: {ACCEPTED_HINT}</div>
          <input
            ref={inputRef}
            type="file"
            multiple
            accept={ACCEPTED_EXTENSIONS.join(",")}
            className="hidden"
            onChange={(e) => {
              if (e.target.files) addFiles(e.target.files);
              e.target.value = ""; // allow re-selecting the same (corrected) file after a rejection
            }}
          />
        </div>

        {files.length > 0 && (
          <ul className="mt-3 space-y-1">
            {files.map((f) => (
              <li
                key={f.name}
                className="flex items-center justify-between rounded-md bg-slate-50 px-3 py-1.5 text-xs text-slate-600"
              >
                <span className="flex items-center gap-1.5">
                  <FileUp className="h-3.5 w-3.5 text-slate-400" />
                  {f.name} <span className="text-slate-400">({Math.round(f.size / 1024)} KB)</span>
                </span>
                {!busy && (
                  <button onClick={() => removeFile(f.name)} className="text-slate-400 hover:text-red-500">
                    ✕
                  </button>
                )}
              </li>
            ))}
          </ul>
        )}

        <div className="mt-4">
          <label className="text-xs font-medium text-slate-500">Display name (optional)</label>
          <input
            type="text"
            value={displayName}
            onChange={(e) => setDisplayName(e.target.value)}
            placeholder="e.g. My night of 2026-08-10"
            disabled={busy}
            className="mt-1 w-full rounded-md border border-slate-300 px-3 py-1.5 text-sm"
          />
        </div>

        {error && (
          <div className="mt-3 flex items-start gap-1.5 rounded-md bg-red-50 px-3 py-2 text-xs text-red-700">
            <AlertCircle className="mt-0.5 h-3.5 w-3.5 shrink-0" />
            {error}
          </div>
        )}

        <button
          onClick={submit}
          disabled={files.length === 0 || busy}
          className="mt-4 inline-flex items-center gap-1.5 rounded-md bg-brand-600 px-4 py-2 text-sm font-medium text-white hover:bg-brand-700 disabled:cursor-not-allowed disabled:opacity-50"
        >
          {busy && <Loader2 className="h-4 w-4 animate-spin" />}
          {stage === "uploading" && "Uploading…"}
          {stage === "ingesting" && "Processing…"}
          {(stage === "idle" || stage === "error") && "Upload & Analyze"}
        </button>
      </Card>

      <AppleHealthImport />
    </div>
  );
}
