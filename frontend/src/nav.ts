export interface NavItem {
  path: string;
  label: string;
  description: string;
  /** Roadmap phase (see README §8) that primarily builds out this screen. */
  phase: number;
}

export interface NavGroup {
  title: string;
  items: NavItem[];
}

export const NAV_GROUPS: NavGroup[] = [
  {
    title: "Overview",
    items: [
      { path: "/", label: "Home", description: "System status and entry point into both data modes.", phase: 1 },
    ],
  },
  {
    title: "Data",
    items: [
      { path: "/datasets", label: "Public Datasets", description: "Curated catalog of licensed research datasets (e.g. MIT-BIH PSG).", phase: 2 },
      { path: "/upload", label: "Upload Study", description: "Bring your own EDF/EDF+/WFDB/CSV sleep recording.", phase: 3 },
    ],
  },
  {
    title: "Preparation",
    items: [
      { path: "/channel-mapping", label: "Channel Mapping", description: "Confidence-scored, editable mapping of raw channel names to standard signal types.", phase: 4 },
      { path: "/qc", label: "Signal QC", description: "Research signal-quality assessment and study readiness score.", phase: 5 },
    ],
  },
  {
    title: "Explore",
    items: [
      { path: "/viewer", label: "Signal Viewer & Night Map", description: "Synchronized multi-channel viewer; click any night-map point to jump to that event.", phase: 6 },
    ],
  },
  {
    title: "Analysis",
    items: [
      { path: "/sleep-staging", label: "Sleep Staging", description: "Hypnogram with respiratory events overlaid; REM vs NREM comparisons.", phase: 8 },
      { path: "/events", label: "Respiratory Events", description: "Candidate event detection, per-event extraction, and event fingerprints.", phase: 7 },
      { path: "/oxygen-burden", label: "Oxygen Burden", description: "Desaturation depth, slope, recovery, and area-under-threshold burden.", phase: 7 },
      { path: "/brain-response", label: "Brain Response", description: "Event-centered cortical/EEG spectral response and arousal analysis.", phase: 9 },
      { path: "/autonomic", label: "Autonomic Response", description: "Heart-rate response, HRV, and cardiovascular recovery around events.", phase: 10 },
      { path: "/beyond-ahi", label: "Beyond AHI", description: "Compares AHI/ODI against oxygen, arousal, autonomic, and recovery burden.", phase: 11 },
    ],
  },
  {
    title: "Modeling",
    items: [
      { path: "/phenotyping", label: "Phenotyping", description: "Unsupervised clustering into descriptive, renamable neuro-respiratory phenotypes.", phase: 12 },
      { path: "/benchmark-lab", label: "Benchmark Lab", description: "Model vs. ground-truth annotation performance, with patient-level validation.", phase: 13 },
    ],
  },
  {
    title: "Longitudinal & AI",
    items: [
      { path: "/longitudinal", label: "Longitudinal", description: "Multi-night phenotype stability and variability tracking.", phase: 14 },
      { path: "/research-assistant", label: "Research Assistant", description: "Structured-query AI assistant that only narrates pipeline output, with evidence.", phase: 15 },
    ],
  },
  {
    title: "Output",
    items: [
      { path: "/digital-twin", label: "Digital Twin", description: "Conceptual 3D brain-body model animating the respiratory-to-recovery cascade.", phase: 16 },
      { path: "/reports", label: "Research Report", description: "Exportable report with full provenance across every analysis stage.", phase: 17 },
    ],
  },
  {
    title: "System",
    items: [
      { path: "/settings", label: "Settings", description: "Clinical/Research mode toggle, data governance, and model/version info.", phase: 1 },
    ],
  },
];

export const ALL_NAV_ITEMS: NavItem[] = NAV_GROUPS.flatMap((g) => g.items);
