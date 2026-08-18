export function SafetyBanner() {
  return (
    <div className="border-b border-amber-200 bg-amber-50 px-4 py-2 text-xs text-amber-900">
      <span className="font-semibold">Research Prototype.</span>{" "}
      This application is designed for research and educational exploration of sleep
      physiology. It does not independently diagnose obstructive sleep apnea or
      neurological disease and does not replace professional interpretation of
      polysomnography or other medical assessments.
    </div>
  );
}
