import type { PropsWithChildren } from "react";

import { SafetyBanner } from "./SafetyBanner";
import { Sidebar } from "./Sidebar";

export function AppShell({ children }: PropsWithChildren) {
  return (
    <div className="flex h-full flex-col">
      <header className="no-print flex items-center justify-between border-b border-slate-200 bg-white px-4 py-3">
        <div>
          <div className="text-lg font-semibold text-slate-900">NeuroSleep Twin</div>
          <div className="text-xs text-slate-500">
            Mapping how the sleeping brain responds to disrupted breathing.
          </div>
        </div>
        <span className="rounded-full bg-slate-900 px-3 py-1 text-xs font-medium text-white">
          Research Prototype
        </span>
      </header>
      <div className="no-print">
        <SafetyBanner />
      </div>
      <div className="flex min-h-0 flex-1">
        <div className="no-print">
          <Sidebar />
        </div>
        <main className="min-w-0 flex-1 overflow-y-auto bg-slate-50 p-6 print:overflow-visible print:bg-white print:p-0">
          {children}
        </main>
      </div>
    </div>
  );
}
