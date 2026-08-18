import { NavLink } from "react-router-dom";

import { NAV_GROUPS } from "@/nav";
import { cn } from "@/utils/cn";

export function Sidebar() {
  return (
    <nav className="w-64 shrink-0 overflow-y-auto border-r border-slate-200 bg-white px-3 py-4">
      {NAV_GROUPS.map((group) => (
        <div key={group.title} className="mb-5">
          <div className="mb-1 px-2 text-[11px] font-semibold uppercase tracking-wide text-slate-400">
            {group.title}
          </div>
          <div className="space-y-0.5">
            {group.items.map((item) => (
              <NavLink
                key={item.path}
                to={item.path}
                end={item.path === "/"}
                className={({ isActive }) =>
                  cn(
                    "block rounded-md px-2 py-1.5 text-sm transition-colors",
                    isActive
                      ? "bg-brand-50 font-medium text-brand-700"
                      : "text-slate-600 hover:bg-slate-100 hover:text-slate-900",
                  )
                }
              >
                {item.label}
              </NavLink>
            ))}
          </div>
        </div>
      ))}
    </nav>
  );
}
