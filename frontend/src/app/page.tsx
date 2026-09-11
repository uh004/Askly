import {
  ArrowRight,
  BarChart3,
  Bot,
  CalendarDays,
  Flame,
  Play,
  Sparkles,
} from "lucide-react";
import Link from "next/link";

import { RecentInterview } from "@/components/interview/recent-interview";

const stats = [
  {
    label: "완료한 면접",
    value: "—",
    description: "DB 연결 후 자동 집계",
    icon: CalendarDays,
    iconClass: "bg-blue-50 text-blue-600",
  },
  {
    label: "평균 점수",
    value: "—",
    description: "완료한 면접 기준",
    icon: BarChart3,
    iconClass: "bg-emerald-50 text-emerald-600",
  },
  {
    label: "연속 연습일",
    value: "—",
    description: "기록 기능 준비 중",
    icon: Flame,
    iconClass: "bg-orange-50 text-orange-500",
  },
];

export default function DashboardPage() {
  return (
    <div className="space-y-7 animate-fade-up">
      <section>
        <p className="mb-1 text-sm font-semibold text-blue-600">ASKLY DASHBOARD</p>
        <h1 className="text-3xl font-black tracking-tight text-slate-950 sm:text-4xl">
          안녕하세요!
        </h1>
        <p className="mt-2 text-base text-slate-500 sm:text-lg">
          오늘도 한 걸음 더 성장하는 연습을 시작해보세요.
        </p>
      </section>

      <section className="relative overflow-hidden rounded-[2rem] bg-gradient-to-r from-blue-700 via-blue-600 to-indigo-500 px-7 py-9 text-white shadow-xl shadow-blue-200/50 sm:px-10 sm:py-11">
        <div className="relative z-10 max-w-2xl">
          <div className="mb-4 flex items-center gap-2 text-xs font-bold tracking-[0.18em] text-blue-100">
            <Sparkles size={15} />
            PRACTICE TODAY, A BRIGHTER TOMORROW
          </div>
          <h2 className="text-3xl font-black leading-tight tracking-tight sm:text-4xl">
            AI와 함께하는
            <br />더 실전 같은 모의면접
          </h2>
          <p className="mt-4 text-blue-100">
            이력서와 채용공고에 맞춘 질문으로 지금 바로 연습해보세요.
          </p>
          <Link
            href="/interviews/new"
            className="mt-7 inline-flex items-center gap-2 rounded-xl bg-white px-5 py-3.5 text-sm font-bold text-blue-700 shadow-lg transition hover:-translate-y-0.5 hover:shadow-xl"
          >
            <Play size={17} fill="currentColor" />
            새 모의면접 시작
            <ArrowRight size={17} />
          </Link>
        </div>
        <div className="absolute -bottom-20 -right-12 size-72 rounded-full bg-white/10" />
        <div className="absolute right-8 top-1/2 hidden -translate-y-1/2 rounded-[2rem] border border-white/20 bg-white/10 p-8 backdrop-blur-md md:block">
          <Bot size={86} strokeWidth={1.4} />
        </div>
      </section>

      <section className="grid gap-4 md:grid-cols-3">
        {stats.map((stat) => {
          const Icon = stat.icon;
          return (
            <article
              key={stat.label}
              className="rounded-2xl border border-slate-100 bg-white p-6 shadow-sm"
            >
              <div className="flex items-center gap-4">
                <span className={`grid size-14 place-items-center rounded-2xl ${stat.iconClass}`}>
                  <Icon size={25} />
                </span>
                <div>
                  <p className="text-sm font-semibold text-slate-500">{stat.label}</p>
                  <p className="mt-0.5 text-3xl font-black text-slate-950">{stat.value}</p>
                </div>
              </div>
              <p className="mt-4 text-xs text-slate-400">{stat.description}</p>
            </article>
          );
        })}
      </section>

      <section className="rounded-2xl border border-slate-100 bg-white p-6 shadow-sm sm:p-7">
        <div className="mb-5">
          <h2 className="text-xl font-extrabold">최근 면접</h2>
          <p className="mt-1 text-sm text-slate-500">
            이 브라우저에서 마지막으로 진행한 면접입니다.
          </p>
        </div>
        <RecentInterview />
      </section>
    </div>
  );
}
