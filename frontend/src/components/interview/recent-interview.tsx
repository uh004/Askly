"use client";

import { ArrowRight, ClipboardList } from "lucide-react";
import Link from "next/link";

import { useStoredInterviewSession } from "@/hooks/use-stored-interview-session";

export function RecentInterview() {
  const session = useStoredInterviewSession();

  if (!session) {
    return (
      <div className="flex flex-col items-center justify-center rounded-2xl border border-dashed border-slate-200 bg-slate-50/60 px-6 py-10 text-center">
        <ClipboardList className="mb-3 text-slate-300" size={30} />
        <p className="font-semibold text-slate-700">아직 진행한 면접이 없습니다.</p>
        <Link
          href="/interviews/new"
          className="mt-3 text-sm font-bold text-blue-600 hover:text-blue-700"
        >
          첫 모의면접 시작하기
        </Link>
      </div>
    );
  }

  const completed = session.status === "COMPLETED";
  const href = completed
    ? `/interviews/${session.sessionId}/result`
    : `/interviews/${session.sessionId}`;

  return (
    <Link
      href={href}
      className="group flex items-center gap-4 rounded-2xl border border-blue-100 bg-blue-50/50 p-4 transition hover:border-blue-200 hover:bg-blue-50"
    >
      <span className="grid size-12 shrink-0 place-items-center rounded-xl bg-white text-blue-600 shadow-sm">
        <ClipboardList size={22} />
      </span>
      <span className="min-w-0 flex-1">
        <strong className="block truncate text-sm text-slate-900">
          {completed ? "완료한 모의면접" : "진행 중인 모의면접"}
        </strong>
        <span className="mt-1 block text-xs text-slate-500">
          {new Intl.DateTimeFormat("ko-KR", {
            dateStyle: "medium",
            timeStyle: "short",
          }).format(new Date(session.updatedAt))}
        </span>
      </span>
      <span className="rounded-full bg-white px-3 py-1 text-xs font-bold text-blue-600">
        {completed ? "결과 보기" : "이어하기"}
      </span>
      <ArrowRight
        className="text-blue-500 transition group-hover:translate-x-1"
        size={18}
      />
    </Link>
  );
}
