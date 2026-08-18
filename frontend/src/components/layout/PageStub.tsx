import { Card } from "./Card";

interface PageStubProps {
  title: string;
  description: string;
  phase: number;
  specSection?: string;
}

/**
 * Placeholder for a screen whose pipeline stage hasn't been built yet.
 * Replaced page-by-page as each roadmap phase (see README §8) lands.
 */
export function PageStub({ title, description, phase, specSection }: PageStubProps) {
  return (
    <div className="mx-auto max-w-2xl">
      <div className="mb-4 flex items-center gap-3">
        <h1 className="text-xl font-semibold text-slate-900">{title}</h1>
        <span className="rounded-full bg-slate-100 px-2.5 py-0.5 text-xs font-medium text-slate-500">
          Phase {phase} — not yet implemented
        </span>
      </div>
      <Card>
        <p className="text-sm text-slate-600">{description}</p>
        {specSection && (
          <p className="mt-3 text-xs text-slate-400">Spec reference: {specSection}</p>
        )}
      </Card>
    </div>
  );
}
