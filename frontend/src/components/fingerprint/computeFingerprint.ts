import type { RespiratoryEvent } from "@/types/study";
import type { RadarAxis } from "./RadarChart";

const clip01 = (v: number) => Math.max(0, Math.min(1, v));

/** Normalizes an event's raw feature columns into a 0-1 vector for the
 * radar-chart fingerprint (README §13) — fixed, disclosed scales, not a
 * learned embedding. */
export function computeFingerprint(event: RespiratoryEvent): RadarAxis[] {
  return [
    { label: "Severity", value: clip01(1 - event.depth_ratio) },
    { label: "Duration", value: clip01(event.duration_sec / 60) },
    { label: "Desaturation", value: event.desaturation_depth != null ? clip01(event.desaturation_depth / 30) : 0 },
    { label: "HR response", value: event.hr_response_bpm != null ? clip01(event.hr_response_bpm / 40) : 0 },
    { label: "Arousal", value: event.arousal_probability ?? 0 },
  ];
}
