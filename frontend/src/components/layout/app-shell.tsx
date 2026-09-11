"use client";

import {
  BarChart3,
  Bot,
  ChevronDown,
  CirclePlus,
  ClipboardList,
  FileClock,
  Home,
  Menu,
  Search,
  Settings,
  X,
} from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useState } from "react";

import { useStoredInterviewSession } from "@/hooks/use-stored-interview-session";

interface AppShellProps {
  children: React.ReactNode;
}

interface NavigationItem {
  label: string;
  href?: string;
  icon: typeof Home;
  active: (pathname: string) => boolean;
}

export function AppShell({ children }: AppShellProps) {
  const pathname = usePathname();
  const [mobileOpen, setMobileOpen] = useState(false);
  const storedSession = useStoredInterviewSession();
  const recentSessionHref = storedSession
    ? storedSession.status === "COMPLETED"
      ? `/interviews/${storedSession.sessionId}/result`
      : `/interviews/${storedSession.sessionId}`
    : undefined;

  const navigation: NavigationItem[] = [
    {
      label: "대시보드",
      href: "/",
      icon: Home,
      active: (current) => current === "/",
    },
    {
      label: "새 모의면접",
      href: "/interviews/new",
      icon: CirclePlus,
      active: (current) => current === "/interviews/new",
    },
    {
      label: "면접 진행",
      href: recentSessionHref,
      icon: ClipboardList,
      active: (current) =>
        current.startsWith("/interviews/") &&
        current !== "/interviews/new" &&
        !current.endsWith("/result"),
    },
    {
      label: "결과 리포트",
      href:
        recentSessionHref?.endsWith("/result") ? recentSessionHref : undefined,
      icon: BarChart3,
      active: (current) => current.endsWith("/result"),
    },
    {
      label: "면접 기록",
      icon: FileClock,
      active: () => false,
    },
    {
      label: "설정",
      icon: Settings,
      active: () => false,
    },
  ];

  return (
    <div className="min-h-screen bg-[var(--page-background)] text-slate-950">
      <button
        type="button"
        aria-label="메뉴 열기"
        onClick={() => setMobileOpen(true)}
        className="fixed left-4 top-4 z-40 grid size-11 place-items-center rounded-2xl border border-slate-200 bg-white text-slate-700 shadow-sm lg:hidden"
      >
        <Menu size={20} />
      </button>

      {mobileOpen && (
        <button
          type="button"
          aria-label="메뉴 닫기"
          onClick={() => setMobileOpen(false)}
          className="fixed inset-0 z-40 bg-slate-950/25 backdrop-blur-sm lg:hidden"
        />
      )}

      <aside
        className={`fixed inset-y-0 left-0 z-50 flex w-64 flex-col border-r border-blue-100/80 bg-white px-4 py-6 shadow-[12px_0_40px_rgba(30,64,175,0.04)] transition-transform lg:translate-x-0 ${
          mobileOpen ? "translate-x-0" : "-translate-x-full"
        }`}
      >
        <button
          type="button"
          aria-label="메뉴 닫기"
          onClick={() => setMobileOpen(false)}
          className="absolute right-4 top-4 text-slate-500 lg:hidden"
        >
          <X size={22} />
        </button>

        <Link href="/" className="mb-10 flex items-center gap-3 px-2">
          <span className="grid size-10 rotate-45 place-items-center rounded-xl bg-gradient-to-br from-blue-600 to-indigo-500 shadow-lg shadow-blue-200">
            <span className="block size-4 -rotate-45 rounded-md border-[3px] border-white" />
          </span>
          <span>
            <strong className="block text-2xl tracking-tight">Askly</strong>
            <span className="text-[11px] text-slate-500">AI 면접 파트너</span>
          </span>
        </Link>

        <nav className="space-y-1.5" aria-label="주요 메뉴">
          {navigation.map((item) => {
            const Icon = item.icon;
            const isActive = item.active(pathname);
            const className = `flex w-full items-center gap-3 rounded-xl px-3 py-3 text-sm font-semibold transition ${
              isActive
                ? "bg-blue-50 text-blue-700"
                : item.href
                  ? "text-slate-600 hover:bg-slate-50 hover:text-slate-950"
                  : "cursor-not-allowed text-slate-300"
            }`;
            const content = (
              <>
                <Icon size={19} strokeWidth={isActive ? 2.5 : 2} />
                <span>{item.label}</span>
                {!item.href && (
                  <span className="ml-auto rounded-full bg-slate-100 px-2 py-0.5 text-[10px] font-medium text-slate-400">
                    준비중
                  </span>
                )}
              </>
            );

            return item.href ? (
              <Link
                key={item.label}
                href={item.href}
                className={className}
                onClick={() => setMobileOpen(false)}
              >
                {content}
              </Link>
            ) : (
              <span key={item.label} className={className}>
                {content}
              </span>
            );
          })}
        </nav>

        <div className="mt-auto overflow-hidden rounded-2xl bg-gradient-to-br from-blue-50 to-indigo-100 p-4">
          <Bot className="mb-3 text-blue-600" size={30} />
          <p className="text-sm font-bold leading-6 text-slate-800">
            AI와 함께,
            <br />더 자신 있는 내일을
          </p>
        </div>
      </aside>

      <div className="lg:pl-64">
        <header className="sticky top-0 z-30 flex h-20 items-center justify-between border-b border-white/80 bg-[var(--page-background)]/90 px-5 pl-20 backdrop-blur-xl sm:px-8 sm:pl-20 lg:px-10">
          <div className="hidden w-full max-w-md items-center gap-3 rounded-2xl border border-slate-200/80 bg-white px-4 py-3 text-slate-400 shadow-sm sm:flex">
            <Search size={18} />
            <span className="text-sm">궁금한 기능이나 내용을 검색해보세요.</span>
          </div>
          <div className="ml-auto flex items-center gap-3 rounded-2xl px-2 py-2">
            <span className="grid size-10 place-items-center rounded-full bg-gradient-to-br from-blue-100 to-indigo-100 text-sm font-bold text-blue-700">
              A
            </span>
            <span className="hidden sm:block">
              <strong className="block text-sm">게스트님</strong>
              <span className="text-xs text-slate-500">오늘도 힘내세요!</span>
            </span>
            <ChevronDown className="hidden text-slate-400 sm:block" size={17} />
          </div>
        </header>
        <main className="mx-auto min-h-[calc(100vh-5rem)] max-w-[1440px] px-5 py-8 sm:px-8 lg:px-10 lg:py-10">
          {children}
        </main>
      </div>
    </div>
  );
}
