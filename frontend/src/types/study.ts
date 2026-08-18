export interface ChannelInfo {
  id: number;
  name: string;
  signal_type: string | null;
  mapping_confidence: number;
  mapping_confirmed: boolean;
  unit: string | null;
  sampling_rate: number;
  n_samples: number;
}

export interface AnnotationInfo {
  id: number;
  onset_sec: number;
  duration_sec: number;
  label: string;
  source: string;
}

export interface StudyListItem {
  id: number;
  dataset_id: string;
  record_name: string;
  source: "public" | "upload";
  display_name: string | null;
  status: "pending" | "downloading" | "ingested" | "error";
  channel_mapping_confirmed: boolean;
  duration_sec: number | null;
}

export interface StudyDetail extends StudyListItem {
  error_message: string | null;
  channels: ChannelInfo[];
  annotations: AnnotationInfo[];
}

export interface IngestJob {
  task_id: string;
  status: string;
  study_id?: number | null;
  error?: string | null;
}

export interface ChannelQc {
  channel_id: number;
  name: string;
  signal_type: string | null;
  missing_pct: number;
  flatline_pct: number;
  clipping_pct: number;
  drift_score: number;
  artifact_pct: number;
  score: number;
  label: string;
  issues: string[];
}

export interface StudyQc {
  study_id: number;
  overall_score: number;
  overall_label: string;
  channels: ChannelQc[];
}

export interface ChannelRef {
  id: number;
  name: string;
}

export interface RespiratoryEvent {
  id: number;
  onset_sec: number;
  duration_sec: number;
  event_type: "apnea" | "hypopnea";
  depth_ratio: number;
  spo2_baseline: number | null;
  spo2_nadir: number | null;
  desaturation_depth: number | null;
  desaturation_slope: number | null;
  recovery_sec: number | null;
  eeg_delta_rel: number | null;
  eeg_theta_rel: number | null;
  eeg_alpha_rel: number | null;
  eeg_beta_rel: number | null;
  arousal_probability: number | null;
  hr_baseline_bpm: number | null;
  hr_peak_bpm: number | null;
  hr_response_bpm: number | null;
}

export interface RespiratoryEventsResult {
  study_id: number;
  available: boolean;
  message: string | null;
  channel_used: ChannelRef | null;
  algorithm_version: string | null;
  summary: { count: number; apnea_count: number; hypopnea_count: number; events_per_hour: number } | null;
  events: RespiratoryEvent[];
}

export interface OxygenBurdenResult {
  study_id: number;
  available: boolean;
  message: string | null;
  channel_used: ChannelRef | null;
  summary: {
    mean_spo2: number;
    min_spo2: number;
    pct_time_below_90: number;
    odi: number;
    artifact_pct: number;
  } | null;
  events: RespiratoryEvent[];
}

export interface EventFeatureResult {
  study_id: number;
  available: boolean;
  message: string | null;
  channel_used: ChannelRef | null;
  events: RespiratoryEvent[];
}

export interface SleepStagesResult {
  study_id: number;
  available: boolean;
  message: string | null;
  epochs: { onset_sec: number; duration_sec: number; stage: string }[];
  stage_minutes: Record<string, number>;
}

export interface BurdenMetric {
  available: boolean;
  value: number | null;
  message: string | null;
}

export interface BeyondAhiResult {
  study_id: number;
  available: boolean;
  message: string | null;
  ahi: BurdenMetric | null;
  odi: BurdenMetric | null;
  oxygen_time_below_90: BurdenMetric | null;
  oxygen_mean_desaturation: BurdenMetric | null;
  arousal_burden: BurdenMetric | null;
  autonomic_burden: BurdenMetric | null;
  recovery_burden: BurdenMetric | null;
}

export interface AcousticPause {
  onset_sec: number;
  duration_sec: number;
  depth_ratio: number;
}

export interface AcousticAnalysisResult {
  study_id: number;
  available: boolean;
  message: string | null;
  channel_used: ChannelRef | null;
  summary: {
    pause_count: number;
    pauses_per_hour: number;
    mean_pause_duration_sec: number;
    pct_time_in_pause: number;
  } | null;
  pauses: AcousticPause[];
}

export interface PhenotypeCluster {
  cluster_index: number;
  label: string;
  size: number;
  centroid: number[];
}

export interface PhenotypeEvent {
  event_id: number;
  study_id: number;
  study_label: string;
  onset_sec: number;
  event_type: string;
  cluster_index: number;
  fingerprint: number[];
}

export interface PhenotypesResult {
  available: boolean;
  message: string | null;
  k: number;
  axes: string[];
  clusters: PhenotypeCluster[];
  events: PhenotypeEvent[];
}

export interface BenchmarkResult {
  study_id: number;
  available: boolean;
  message: string | null;
  n_epochs: number;
  n_positive_epochs: number;
  confusion: { tp: number; fp: number; fn: number; tn: number } | null;
  sensitivity: number | null;
  specificity: number | null;
  precision: number | null;
  auroc: number | null;
  auprc: number | null;
  roc_curve: { x: number[]; y: number[] } | null;
  pr_curve: { x: number[]; y: number[] } | null;
  calibration_predicted: number[];
  calibration_observed: number[];
}

export interface NightSummary {
  study_id: number;
  record_name: string;
  duration_sec: number;
  events_per_hour: number | null;
  mean_spo2: number | null;
  odi: number | null;
  stage_pct: Record<string, number>;
}

export interface LongitudinalResult {
  available: boolean;
  message: string | null;
  patients: { patient_key: string; nights: NightSummary[] }[];
}

export interface AppleHealthSession {
  index: number;
  start: string;
  end: string;
  duration_hours: number;
  record_count: number;
}

export interface SignalWindow {
  channel_id: number;
  start_sec: number;
  end_sec: number;
  sampling_rate: number;
  point_interval_sec: number;
  t: number[];
  v: number[];
}
