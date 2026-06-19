import { ArrowRight, Compass } from "lucide-react";
import { NavLink } from "react-router-dom";
import {
  FEATURE_NAV_GROUPS,
  QUICK_ACCESS_ITEMS,
} from "../../config/featureNavigation";
import { classNames } from "../../utils/classNames";

export function FeatureHubPage() {
  return (
    <div className="space-y-8">
      <section className="rounded-2xl border border-slate-200 bg-white/80 p-6 shadow-card backdrop-blur-sm">
        <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
          <div className="space-y-2">
            <div className="inline-flex items-center gap-2 rounded-full bg-sky-100 px-3 py-1 text-xs font-semibold uppercase tracking-wide text-sky-800">
              <Compass size={14} />
              Feature Hub
            </div>
            <h1 className="text-2xl font-semibold text-slate-900 md:text-3xl">
              Find the right tool quickly
            </h1>
            <p className="text-sm text-slate-600 md:text-base">
              Features are grouped by workflow so navigation stays manageable as
              the product grows.
            </p>
          </div>
        </div>
      </section>

      <section className="space-y-4">
        <h2 className="text-sm font-semibold uppercase tracking-wide text-slate-500">
          Quick Access
        </h2>
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
          {QUICK_ACCESS_ITEMS.map((item) => (
            <NavLink
              key={item.path}
              to={item.path}
              className="group rounded-xl border border-slate-200 bg-white p-4 shadow-sm transition hover:-translate-y-0.5 hover:border-brand/40 hover:shadow-card"
            >
              <div className="flex items-start justify-between gap-3">
                <div className="space-y-1">
                  <p className="font-semibold text-slate-900">{item.label}</p>
                  <p className="text-sm text-slate-600">{item.description}</p>
                </div>
                <ArrowRight
                  size={16}
                  className="mt-1 text-slate-400 transition group-hover:translate-x-0.5 group-hover:text-brand"
                />
              </div>
            </NavLink>
          ))}
        </div>
      </section>

      <section className="space-y-4">
        <h2 className="text-sm font-semibold uppercase tracking-wide text-slate-500">
          All Features
        </h2>
        <div className="space-y-4">
          {FEATURE_NAV_GROUPS.map((group) => (
            <div
              key={group.id}
              className="rounded-2xl border border-slate-200 bg-white/90 p-5 shadow-sm"
            >
              <div className="mb-4">
                <h3 className="text-lg font-semibold text-slate-900">
                  {group.label}
                </h3>
                <p className="text-sm text-slate-600">{group.description}</p>
              </div>

              <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
                {group.items.map((item) => (
                  <NavLink
                    key={item.path}
                    to={item.path}
                    className={({ isActive }) =>
                      classNames(
                        "rounded-xl border border-slate-200 p-4 transition hover:border-brand/40 hover:bg-slate-50",
                        isActive && "border-brand bg-brand/5"
                      )
                    }
                  >
                    <p className="font-semibold text-slate-900">{item.label}</p>
                    <p className="mt-1 text-sm text-slate-600">
                      {item.description}
                    </p>
                  </NavLink>
                ))}
              </div>
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}
