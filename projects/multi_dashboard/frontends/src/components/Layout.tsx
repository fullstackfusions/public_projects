import {
  ChevronDown,
  Compass,
  LogOut,
  Menu,
  Search,
  User,
  X,
} from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { NavLink, Outlet, useLocation, useNavigate } from "react-router-dom";
import {
  FEATURE_HUB_PATH,
  FEATURE_NAV_GROUPS,
  QUICK_ACCESS_ITEMS,
} from "../config/featureNavigation";
import { useAuth } from "../context/AuthContext";
import { classNames } from "../utils/classNames";

export function Layout() {
  const [isMenuOpen, setIsMenuOpen] = useState(false);
  const [isUserMenuOpen, setIsUserMenuOpen] = useState(false);
  const [query, setQuery] = useState("");
  const [expandedGroups, setExpandedGroups] = useState<Record<string, boolean>>(
    () =>
      FEATURE_NAV_GROUPS.reduce<Record<string, boolean>>((acc, group) => {
        acc[group.id] = true;
        return acc;
      }, {})
  );
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();

  const handleLogout = async () => {
    await logout();
    navigate("/login");
  };

  const getUserInitials = () => {
    if (user?.full_name) {
      const names = user.full_name.split(" ");
      return names
        .map((n) => n[0])
        .join("")
        .toUpperCase()
        .slice(0, 2);
    }
    return user?.username?.slice(0, 2).toUpperCase() || "U";
  };

  useEffect(() => {
    const activeGroup = FEATURE_NAV_GROUPS.find((group) =>
      group.items.some((item) => item.path === location.pathname)
    );
    if (activeGroup && !expandedGroups[activeGroup.id]) {
      setExpandedGroups((prev) => ({ ...prev, [activeGroup.id]: true }));
    }
  }, [expandedGroups, location.pathname]);

  const filteredGroups = useMemo(() => {
    const normalizedQuery = query.trim().toLowerCase();
    if (!normalizedQuery) return FEATURE_NAV_GROUPS;

    return FEATURE_NAV_GROUPS.map((group) => ({
      ...group,
      items: group.items.filter((item) => {
        const searchable = [
          item.label,
          item.description,
          ...item.keywords,
          group.label,
        ]
          .join(" ")
          .toLowerCase();
        return searchable.includes(normalizedQuery);
      }),
    })).filter((group) => group.items.length > 0);
  }, [query]);

  return (
    <div className="flex h-screen flex-col bg-gradient-to-br from-slate-100 via-indigo-50 to-indigo-100 text-slate-800">
      {/* Fixed Header */}
      <header className="flex-shrink-0 h-16 bg-slate-900/50 backdrop-blur-sm z-30">
        <div className="w-full px-10 flex items-center justify-between h-full">
          <div className="h-full flex items-center">
            <button
              type="button"
              className="inline-flex h-10 w-10 items-center justify-center rounded-full bg-slate-900/50 text-white shadow-md hover:bg-slate-900/60 focus:outline-none focus:ring-2 focus:ring-brand/40"
              onClick={() => setIsMenuOpen(true)}
              aria-label="Open menu"
            >
              <Menu aria-hidden size={18} />
            </button>
          </div>

          <NavLink
            to={FEATURE_HUB_PATH}
            className="hidden md:inline-flex items-center gap-2 rounded-full border border-white/30 bg-white/10 px-4 py-2 text-sm font-semibold text-white transition hover:bg-white/20 focus:outline-none focus:ring-2 focus:ring-brand/40"
          >
            <Compass size={14} />
            Feature Hub
          </NavLink>

          <div className="h-full flex items-center relative">
            <button
              type="button"
              className="inline-flex h-10 w-10 items-center justify-center rounded-full bg-white/90 text-slate-900 shadow-sm hover:bg-white focus:outline-none focus:ring-2 focus:ring-brand/40"
              aria-label="User menu"
              onClick={() => setIsUserMenuOpen(!isUserMenuOpen)}
            >
              <span className="text-sm font-semibold">{getUserInitials()}</span>
            </button>

            {/* User dropdown menu */}
            {isUserMenuOpen && (
              <>
                <div
                  className="fixed inset-0 z-40"
                  onClick={() => setIsUserMenuOpen(false)}
                  aria-hidden
                />
                <div className="absolute right-0 top-full mt-2 w-64 rounded-xl border border-white/20 bg-slate-900/90 backdrop-blur-md shadow-lg z-50 overflow-hidden">
                  <div className="px-4 py-3 border-b border-white/10">
                    <div className="flex items-center gap-3">
                      <div className="flex h-10 w-10 items-center justify-center rounded-full bg-brand text-white">
                        <User size={18} />
                      </div>
                      <div className="flex flex-col">
                        <span className="text-sm font-semibold text-white">
                          {user?.full_name || user?.username}
                        </span>
                        <span className="text-xs text-slate-300">
                          {user?.email}
                        </span>
                        <span className="text-xs text-slate-400 capitalize">
                          {user?.role}
                        </span>
                      </div>
                    </div>
                  </div>
                  <button
                    type="button"
                    onClick={handleLogout}
                    className="w-full flex items-center gap-3 px-4 py-3 text-left text-sm text-white hover:bg-white/10 transition"
                  >
                    <LogOut size={16} />
                    <span>Sign out</span>
                  </button>
                </div>
              </>
            )}
          </div>
        </div>
      </header>

      {/* Hamburger-triggered overlay panel */}
      {isMenuOpen && (
        <div className="fixed inset-0 z-40 flex">
          <div
            className="absolute inset-0 bg-black/20 backdrop-blur-sm"
            onClick={() => setIsMenuOpen(false)}
            aria-hidden
          />

          <aside
            className={classNames(
              "relative z-50 flex flex-col gap-8 bg-slate-900/70 backdrop-blur-md text-slate-50 shadow-sidebar transition-transform duration-300 overflow-y-auto w-80 max-w-[24rem] px-8 py-10 border border-white/10",
              isMenuOpen ? "translate-x-0" : "-translate-x-full"
            )}
          >
            <div className="flex items-center justify-between gap-4">
              <div className="flex flex-col gap-2">
                <h1 className="text-2xl font-semibold text-white">
                  Productivity Hub
                </h1>
                <p className="text-sm text-slate-200/70">
                  Explore grouped tools and keep navigation manageable.
                </p>
              </div>
              <button
                type="button"
                className="inline-flex flex-shrink-0 h-10 w-10 min-h-[40px] min-w-[40px] items-center justify-center rounded-full bg-white/10 text-white transition hover:bg-white/20 focus:outline-none focus:ring-2 focus:ring-brand/40"
                onClick={() => setIsMenuOpen(false)}
                aria-label="Close menu"
              >
                <X aria-hidden size={18} />
              </button>
            </div>

            <NavLink
              to={FEATURE_HUB_PATH}
              onClick={() => setIsMenuOpen(false)}
              className={({ isActive }) =>
                classNames(
                  "inline-flex items-center justify-center gap-2 rounded-xl border border-white/15 bg-white/10 px-4 py-3 text-sm font-semibold transition hover:bg-white/20",
                  isActive && "border-brand bg-brand text-white"
                )
              }
            >
              <Compass size={16} />
              Open Feature Hub
            </NavLink>

            <div className="relative">
              <Search
                size={16}
                className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-slate-300"
              />
              <input
                type="text"
                value={query}
                onChange={(event) => setQuery(event.target.value)}
                placeholder="Search features..."
                className="w-full rounded-xl border border-white/15 bg-white/10 py-2.5 pl-10 pr-3 text-sm text-white placeholder:text-slate-300/80 focus:outline-none focus:ring-2 focus:ring-brand/40"
              />
            </div>

            {query.trim() === "" && (
              <section className="space-y-2">
                <p className="text-xs font-semibold uppercase tracking-wide text-slate-300">
                  Quick Access
                </p>
                <div className="grid grid-cols-2 gap-2">
                  {QUICK_ACCESS_ITEMS.map((item) => (
                    <NavLink
                      key={item.path}
                      to={item.path}
                      onClick={() => setIsMenuOpen(false)}
                      className={({ isActive }) =>
                        classNames(
                          "rounded-lg border border-white/10 bg-white/10 px-3 py-2 text-xs font-semibold transition hover:bg-white/20",
                          isActive && "border-brand bg-brand text-white"
                        )
                      }
                    >
                      {item.label}
                    </NavLink>
                  ))}
                </div>
              </section>
            )}

            <nav className="flex flex-col gap-3">
              {filteredGroups.length === 0 && (
                <div className="rounded-xl border border-dashed border-white/20 bg-white/5 px-4 py-5 text-sm text-slate-200/90">
                  No features matched your search.
                </div>
              )}

              {filteredGroups.map((group) => (
                <section
                  key={group.id}
                  className="rounded-xl border border-white/10 bg-white/5"
                >
                  <button
                    type="button"
                    onClick={() =>
                      setExpandedGroups((prev) => ({
                        ...prev,
                        [group.id]: !prev[group.id],
                      }))
                    }
                    className="flex w-full items-center justify-between gap-3 px-4 py-3 text-left"
                  >
                    <div className="min-w-0">
                      <p className="truncate text-sm font-semibold text-white">
                        {group.label}
                      </p>
                      <p className="truncate text-xs text-slate-300">
                        {group.description}
                      </p>
                    </div>
                    <ChevronDown
                      size={16}
                      className={classNames(
                        "text-slate-300 transition",
                        expandedGroups[group.id] && "rotate-180"
                      )}
                    />
                  </button>

                  {expandedGroups[group.id] && (
                    <div className="space-y-2 border-t border-white/10 px-3 py-3">
                      {group.items.map((item) => (
                        <NavLink
                          key={item.path}
                          to={item.path}
                          onClick={() => setIsMenuOpen(false)}
                          className={({ isActive }) =>
                            classNames(
                              "block w-full rounded-lg border border-white/10 bg-white/10 px-4 py-3 text-left transition hover:bg-white/20",
                              isActive && "border-transparent bg-brand text-white"
                            )
                          }
                          title={item.label}
                        >
                          <div className="flex flex-col gap-1">
                            <span className="text-sm font-semibold leading-tight break-words">
                              {item.label}
                            </span>
                            <small className="text-xs font-normal text-slate-200/70 whitespace-normal leading-snug break-words">
                              {item.description}
                            </small>
                          </div>
                        </NavLink>
                      ))}
                    </div>
                  )}
                </section>
              ))}
            </nav>
          </aside>
        </div>
      )}

      {/* Main content area - fills remaining height */}
      <main className="flex-1 overflow-y-auto px-10 py-6">
        <Outlet />
      </main>
    </div>
  );
}
