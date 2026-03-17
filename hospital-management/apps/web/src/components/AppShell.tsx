"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { ReactNode } from "react";

import { AppRole, clearSession, getRole } from "@/src/lib/auth";

const navItems: Array<{ href: string; label: string; roles: AppRole[] }> = [
  { href: "/dashboard", label: "Dashboard", roles: ["doctor", "admin", "laboratory", "medical"] },
  { href: "/op", label: "OP Desk", roles: ["admin", "operations"] },
  { href: "/doctor", label: "Doctor Queue", roles: ["doctor", "admin"] },
  { href: "/laboratory", label: "Laboratory", roles: ["admin", "laboratory"] },
  { href: "/medical-bill", label: "Medical Bill", roles: ["doctor", "admin", "medical"] },
  { href: "/expenses", label: "Expenses", roles: ["doctor", "admin"] },
  { href: "/admin/users", label: "Users", roles: ["admin"] },
  { href: "/reports/daily-print", label: "Reports", roles: ["doctor", "admin", "laboratory"] },
];

export function AppShell({ children }: { children: ReactNode }) {
  const router = useRouter();
  const pathname = usePathname();
  const role = getRole();
  const visibleNavItems = navItems.filter((item) => role && item.roles.includes(role));

  function handleLogout() {
    clearSession();
    router.replace("/login");
  }

  return (
    <div className="console-layout">
      <aside className="console-sidebar">
        <div className="brand-block">
          <span className="brand-dot" />
          <div>
            <p className="brand-title">Sri Laxmi Hospital</p>
            <p className="brand-subtitle">Happy Mother and Safe Children</p>
          </div>
        </div>

        <nav className="console-nav">
          {visibleNavItems.map((item) => {
            const active = pathname === item.href;
            return (
              <Link key={item.href} href={item.href} className={active ? "nav-item active" : "nav-item"}>
                {item.label}
              </Link>
            );
          })}
        </nav>
      </aside>

      <section className="console-main">
        <header className="console-topbar">
          <div>
            <p className="topbar-label">Happy Mother and Safe Children</p>
            <p className="topbar-title">Operations Workspace</p>
          </div>
          <div className="topbar-actions">
            <span className="role-pill">Role: {role ?? "unknown"}</span>
            <button className="secondary-btn" onClick={handleLogout}>
              Logout
            </button>
          </div>
        </header>

        <div className="console-content">{children}</div>
      </section>
    </div>
  );
}
