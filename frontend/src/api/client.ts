import type { DatasetEntry } from "@/types/dataset";
import type {
  BenchmarkResult,
  BeyondAhiResult,
  EventFeatureResult,
  IngestJob,
  LongitudinalResult,
  OxygenBurdenResult,
  PhenotypesResult,
  RespiratoryEventsResult,
  SignalWindow,
  SleepStagesResult,
  StudyDetail,
  StudyListItem,
  StudyQc,
} from "@/types/study";

// Vite dev server proxies /api -> the FastAPI backend (see vite.config.ts).
const API_BASE = "/api/v1";

// Must match the backend's API_AUTH_TOKEN (see backend/.env.example). Empty
// in both places means auth is disabled — fine for zero-friction local dev.
const API_TOKEN = import.meta.env.VITE_API_TOKEN as string | undefined;

function authHeaders(): HeadersInit {
  return API_TOKEN ? { Authorization: `Bearer ${API_TOKEN}` } : {};
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: { ...authHeaders(), ...init?.headers },
  });
  if (res.status === 401) {
    throw new Error("Unauthorized — check that VITE_API_TOKEN matches the backend's API_AUTH_TOKEN.");
  }
  if (!res.ok) {
    throw new Error(`Request to ${path} failed with status ${res.status}`);
  }
  return res.json() as Promise<T>;
}

export interface HealthStatus {
  status: string;
  service: string;
  environment: string;
}

export const api = {
  health: () => request<HealthStatus>("/health"),
  listDatasets: () => request<DatasetEntry[]>("/datasets"),
  getDataset: (id: string) => request<DatasetEntry>(`/datasets/${id}`),

  ingestRecord: (datasetId: string, recordName: string) =>
    request<IngestJob>(`/datasets/${datasetId}/records/${recordName}/ingest`, { method: "POST" }),
  getIngestJob: (taskId: string) => request<IngestJob>(`/ingest-jobs/${taskId}`),
  uploadStudy: (files: File[], displayName?: string) => {
    const form = new FormData();
    files.forEach((f) => form.append("files", f));
    if (displayName) form.append("display_name", displayName);
    return request<IngestJob>("/uploads", { method: "POST", body: form });
  },
  listStudies: () => request<StudyListItem[]>("/studies"),
  getStudy: (studyId: number) => request<StudyDetail>(`/studies/${studyId}`),
  deleteStudy: (studyId: number) =>
    fetch(`${API_BASE}/studies/${studyId}`, { method: "DELETE", headers: authHeaders() }).then((res) => {
      if (!res.ok) throw new Error(`Delete failed with status ${res.status}`);
    }),
  getSignalWindow: (studyId: number, channelId: number, startSec: number, endSec: number, maxPoints = 2000) =>
    request<SignalWindow>(
      `/studies/${studyId}/channels/${channelId}/signal?start_sec=${startSec}&end_sec=${endSec}&max_points=${maxPoints}`,
    ),

  listChannelTypes: () => request<string[]>("/channel-types"),
  updateChannelMapping: (studyId: number, channelId: number, signalType: string | null) =>
    request(`/studies/${studyId}/channels/${channelId}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ signal_type: signalType }),
    }),
  confirmChannelMapping: (studyId: number) =>
    request<StudyDetail>(`/studies/${studyId}/confirm-mapping`, { method: "POST" }),
  getStudyQc: (studyId: number) => request<StudyQc>(`/studies/${studyId}/qc`),
  getRespiratoryEvents: (studyId: number) =>
    request<RespiratoryEventsResult>(`/studies/${studyId}/respiratory-events`),
  getOxygenBurden: (studyId: number) => request<OxygenBurdenResult>(`/studies/${studyId}/oxygen-burden`),
  getSleepStages: (studyId: number) => request<SleepStagesResult>(`/studies/${studyId}/sleep-stages`),
  getBrainResponse: (studyId: number) => request<EventFeatureResult>(`/studies/${studyId}/brain-response`),
  getAutonomicResponse: (studyId: number) => request<EventFeatureResult>(`/studies/${studyId}/autonomic-response`),
  getBeyondAhi: (studyId: number) => request<BeyondAhiResult>(`/studies/${studyId}/beyond-ahi`),

  getBenchmark: (studyId: number) => request<BenchmarkResult>(`/studies/${studyId}/benchmark`),
  getLongitudinal: () => request<LongitudinalResult>("/longitudinal"),

  getAuditLog: (limit = 50) =>
    request<{ id: number; created_at: string; method: string; path: string; status_code: number; client_host: string | null }[]>(
      `/audit-log?limit=${limit}`,
    ),

  getAssistantStatus: () =>
    request<{ configured: boolean; provider: "ollama" | "anthropic" | null; model: string | null }>("/assistant/status"),
  askAssistant: (studyId: number, question: string) =>
    request<{ answer: string; configured: boolean; evidence: Record<string, unknown> }>(
      `/studies/${studyId}/assistant/ask`,
      { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ question }) },
    ),

  getPhenotypes: (k: number) => request<PhenotypesResult>(`/phenotypes?k=${k}`),
  renameCluster: (k: number, clusterIndex: number, label: string) =>
    request(`/phenotypes/${k}/clusters/${clusterIndex}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ label }),
    }),
};
