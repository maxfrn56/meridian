"use client";

import { api, TOKEN_KEY } from "@/lib/api";
import type { User } from "@/lib/types";
import { cn } from "@/lib/utils";
import { useQuery } from "@tanstack/react-query";
import { CreditCard, GitCompare, LayoutDashboard, LogOut, Radar, ScanSearch, Settings, Users } from "lucide-react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { PageFallback } from "@/components/fallback";

const CLIENT_NAV = [
  { href: "/dashboard", label: "Vue d'ensemble", icon: LayoutDashboard },
  { href: "/tracking", label: "Suivi", icon: Radar },
  { href: "/comparison", label: "Comparaison", icon: GitCompare },
  { href: "/audit", label: "Audit", icon: ScanSearch },
  { href: "/billing", label: "Forfait", icon: CreditCard },
  { href: "/settings", label: "Réglages", icon: Settings },
] as const;

const ADMIN_NAV = [
  { href: "/admin", label: "Pilotage", icon: LayoutDashboard },
  { href: "/admin/prospects", label: "Prospection", icon: Users },
] as const;

function Mark() {
  return (
    <span className="grid size-8 place-items-center rounded-lg bg-primary text-primary-foreground">
      <svg viewBox="0 0 24 24" className="size-4" aria-hidden="true">
        <circle cx="12" cy="12" r="3" fill="currentColor" />
        <path d="M12 3v3M12 18v3M3 12h3M18 12h3" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" />
        <circle cx="12" cy="12" r="8" fill="none" stroke="currentColor" strokeWidth="1.4" />
      </svg>
    </span>
  );
}

function NavLinks({
  items,
  onNavigate,
}: {
  items: readonly { href: string; label: string; icon: typeof LayoutDashboard }[];
  onNavigate?: () => void;
}) {
  const pathname = usePathname();
  return (
    <>
      {items.map((item) => {
        const active = pathname === item.href;
        const Icon = item.icon;
        return (
          <Link
            key={item.href}
            href={item.href}
            onClick={onNavigate}
            className={cn(
              "flex items-center gap-2 rounded-lg px-3 py-2 text-sm text-muted-foreground hover:bg-muted hover:text-foreground",
              active && "bg-muted text-foreground",
            )}
          >
            <Icon className="size-4" />
            {item.label}
          </Link>
        );
      })}
    </>
  );
}

export function DashboardShell({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const pathname = usePathname();
  const [ready, setReady] = useState(false);
  const [authed, setAuthed] = useState(false);

  useEffect(() => {
    const ok = Boolean(localStorage.getItem(TOKEN_KEY));
    setAuthed(ok);
    setReady(true);
    if (!ok) router.replace("/login");
  }, [router]);

  const me = useQuery({
    queryKey: ["me"],
    queryFn: () => api<User>("/auth/me"),
    enabled: authed,
  });
  const admin = me.data?.role === "admin";
  const onAdmin = pathname.startsWith("/admin") || pathname === "/prospects";

  useEffect(() => {
    if (!me.data) return;
    if (admin && !onAdmin) router.replace("/admin");
    if (!admin && onAdmin) router.replace("/dashboard");
  }, [admin, me.data, onAdmin, router]);

  if (!ready || !authed || me.isPending || !me.data || admin !== onAdmin) return <PageFallback />;

  function logout() {
    localStorage.removeItem(TOKEN_KEY);
    router.replace("/login");
  }

  const navigation = admin ? ADMIN_NAV : CLIENT_NAV;
  const home = admin ? "/admin" : "/dashboard";

  return (
    <div className="min-h-screen lg:grid lg:grid-cols-[248px_1fr]">
      <aside className="no-print sticky top-0 hidden h-screen flex-col border-r border-border bg-[#0e1211] px-3 py-4 lg:flex">
        <Link href={home} className="mb-8 flex items-center gap-2.5 px-2">
          <Mark />
          <span>
            <span className="block text-sm font-semibold tracking-tight">Meridian</span>
            <span className="block text-xs text-muted-foreground">{admin ? "Administration" : "Visibilité GEO"}</span>
          </span>
        </Link>
        <nav className="flex flex-1 flex-col gap-1">
          <NavLinks items={navigation} />
        </nav>
        <div className="mt-4 border-t border-border pt-4">
          <p className="truncate px-2 text-sm">{me.data?.name ?? "Compte"}</p>
          <p className="truncate px-2 text-xs text-muted-foreground">{me.data?.email}</p>
          <button
            type="button"
            onClick={logout}
            className="mt-3 flex w-full items-center gap-2 rounded-lg px-2 py-2 text-sm text-muted-foreground hover:bg-muted hover:text-foreground"
          >
            <LogOut className="size-4" />
            Se déconnecter
          </button>
        </div>
      </aside>
      <div className="min-w-0">
        <div className="no-print flex items-center justify-between gap-3 border-b border-border px-4 py-3 lg:hidden">
          <Link href={home} className="flex items-center gap-2 font-semibold">
            <Mark />
            Meridian
          </Link>
          <button type="button" onClick={logout} className="text-sm text-muted-foreground">
            Sortir
          </button>
        </div>
        <nav className="no-print flex gap-1 overflow-x-auto border-b border-border px-3 py-2 lg:hidden">
          <NavLinks items={navigation} />
        </nav>
        <main>{children}</main>
      </div>
    </div>
  );
}
