"use client";

import {
  ArrowLeft,
  ArrowRight,
  Award,
  BarChart3,
  CheckCircle2,
  ChevronDown,
  ClipboardCheck,
  Lightbulb,
  LoaderCircle,
  MessageSquareText,
  RefreshCw,
  Sparkles,
  Target,
  TriangleAlert,
} from "lucide-react";
import Link from "next/link";
import { useEffect, useState } from "react";

import { getInterview } from "@/lib/interview-api";
import { storeInterviewSession } from "@/lib/session-storage";
import type { FinalInterviewFeedback, InterviewSession } from "@/types/interview";

interface InterviewResultProps {
  sessionId: string;
}

function scoreLabel(score: number): string {
  if (score >= 90) return "매우 우수";
  if (score >= 80) return "우수";
  if (score >= 70) return "양호";
  if (score >= 60) return "보통";
  return "보완 필요";
}

export function InterviewResult({ sessionId }: InterviewResultProps) {
  const [session, setSession] = useState<InterviewSession>();
  const [error, setError] = useState("");

  useEffect(() => {
    let active = true;
    getInterview(sessionId)
      .then((data) => {
        if (!active) return;
        storeInterviewSession(data);
        setSession(data);
      })
      .catch((requestError: unknown) => {
        if (active) {
          setError(
            requestError instanceof Error
              ? requestError.message
              : "결과 리포트를 불러오지 못했습니다.",
          );
        }
      });
    return () => {
      active = false;
    };
  }, [sessionId]);

  if (!session && !error) {
    return (
      <div className="flex min-h-[60vh] flex-col items-center justify-center">
        <LoaderCircle className="animate-spin text-blue-600" size={38} />
        <p className="mt-4 font-semibold text-slate-600">결과 리포트를 불러오는 중입니다...</p>
      </div>
    );
  }

  if (error || !session) {
    return <ResultError message={error} />;
  }

  if (session.status !== "COMPLETED" || !session.final_feedback) {
    return (
      <div className="mx-auto max-w-xl rounded-3xl border border-blue-100 bg-white p-8 text-center shadow-sm">
        <MessageSquareText className="mx-auto text-blue-500" size={38} />
        <h1 className="mt-4 text-xl font-extrabold">아직 면접이 진행 중입니다.</h1>
        <p className="mt-2 text-sm text-slate-500">
          모든 질문에 답변하면 최종 리포트를 확인할 수 있습니다.
        </p>
        <Link
          href={`/interviews/${sessionId}`}
          className="mt-6 inline-flex items-center gap-2 rounded-xl bg-blue-600 px-5 py-3 text-sm font-bold text-white"
        >
          면접 이어하기 <ArrowRight size={17} />
        </Link>
      </div>
    );
  }

  return <CompletedResult feedback={session.final_feedback} />;
}

function CompletedResult({ feedback }: { feedback: FinalInterviewFeedback }) {
  const score = Math.round(feedback.overall_score);
  const strongestCompetency = Object.entries(feedback.competency_scores).sort(
    ([, first], [, second]) => second - first,
  )[0];

  return (
    <div className="space-y-6 animate-fade-up">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <p className="mb-1 text-sm font-semibold text-blue-600">INTERVIEW REPORT</p>
          <h1 className="text-3xl font-black tracking-tight sm:text-4xl">면접 결과 리포트</h1>
          <p className="mt-2 text-slate-500">수고하셨습니다. 답변을 바탕으로 정리한 결과입니다.</p>
        </div>
        <Link
          href="/"
          className="inline-flex items-center gap-2 rounded-xl border border-slate-200 bg-white px-4 py-3 text-sm font-bold text-slate-600 hover:bg-slate-50"
        >
          <ArrowLeft size={17} /> 대시보드로
        </Link>
      </div>

      <section className="relative overflow-hidden rounded-[2rem] bg-gradient-to-r from-blue-700 via-blue-600 to-indigo-500 p-7 text-white shadow-xl shadow-blue-200/50 sm:p-10">
        <div className="relative z-10 grid gap-8 lg:grid-cols-[1fr_auto] lg:items-center">
          <div>
            <div className="mb-4 flex items-center gap-2 text-sm font-bold text-blue-100">
              <Sparkles size={17} /> AI 종합 피드백
            </div>
            <p className="max-w-3xl text-base leading-8 text-blue-50 sm:text-lg">
              {feedback.overall_summary}
            </p>
          </div>
          <div className="flex min-w-48 items-center gap-5 rounded-3xl border border-white/20 bg-white/10 px-6 py-5 backdrop-blur-sm">
            <Award size={42} />
            <div>
              <p className="text-sm text-blue-100">종합 평가 점수</p>
              <p className="text-5xl font-black">{score}<span className="text-xl">점</span></p>
              <span className="mt-1 inline-block rounded-full bg-white/15 px-3 py-1 text-xs font-bold">
                {scoreLabel(score)}
              </span>
            </div>
          </div>
        </div>
        <div className="absolute -bottom-24 -right-16 size-72 rounded-full bg-white/10" />
      </section>

      <section className="grid gap-4 md:grid-cols-3">
        <SummaryCard
          icon={ClipboardCheck}
          label="완료한 질문"
          value={`${feedback.interview_statistics.question_count}개`}
          description={`꼬리 질문 ${feedback.interview_statistics.followup_count}개 포함`}
          color="blue"
        />
        <SummaryCard
          icon={Target}
          label="평가한 역량"
          value={`${feedback.interview_statistics.evaluated_competency_count}개`}
          description="면접 전략의 핵심 역량 기준"
          color="emerald"
        />
        <SummaryCard
          icon={Award}
          label="가장 우수한 역량"
          value={strongestCompetency?.[0] ?? "—"}
          description={strongestCompetency ? `${Math.round(strongestCompetency[1])}점` : "평가 없음"}
          color="amber"
        />
      </section>

      <div className="grid gap-6 xl:grid-cols-[minmax(0,1.1fr)_minmax(360px,0.9fr)]">
        <section className="rounded-3xl border border-slate-100 bg-white p-6 shadow-sm sm:p-8">
          <div className="mb-6 flex items-center gap-3">
            <span className="grid size-11 place-items-center rounded-xl bg-blue-50 text-blue-600">
              <BarChart3 size={22} />
            </span>
            <div>
              <h2 className="text-xl font-extrabold">역량별 평가</h2>
              <p className="text-sm text-slate-500">핵심 역량별 최종 점수입니다.</p>
            </div>
          </div>
          <div className="space-y-6">
            {feedback.competency_feedback.map((item) => (
              <div key={item.competency}>
                <div className="mb-2 flex items-center justify-between gap-4">
                  <span className="font-bold text-slate-800">{item.competency}</span>
                  <span className="text-lg font-black text-blue-600">
                    {Math.round(item.final_score)}점
                  </span>
                </div>
                <div className="h-2.5 overflow-hidden rounded-full bg-slate-100">
                  <div
                    className="h-full rounded-full bg-gradient-to-r from-blue-500 to-indigo-500"
                    style={{ width: `${Math.min(100, Math.max(0, item.final_score))}%` }}
                  />
                </div>
                <p className="mt-2 text-sm leading-6 text-slate-500">{item.summary}</p>
              </div>
            ))}
          </div>
        </section>

        <div className="space-y-5">
          <FeedbackList
            title="강점"
            items={feedback.key_strengths}
            icon={CheckCircle2}
            className="border-emerald-100 bg-emerald-50/70 text-emerald-950"
          />
          <FeedbackList
            title="보완 포인트"
            items={feedback.key_improvement_areas}
            icon={TriangleAlert}
            className="border-rose-100 bg-rose-50/70 text-rose-950"
          />
        </div>
      </div>

      <section className="rounded-3xl border border-slate-100 bg-white p-6 shadow-sm sm:p-8">
        <div className="mb-6 flex items-center gap-3">
          <span className="grid size-11 place-items-center rounded-xl bg-indigo-50 text-indigo-600">
            <Lightbulb size={22} />
          </span>
          <div>
            <h2 className="text-xl font-extrabold">다음 연습 액션 플랜</h2>
            <p className="text-sm text-slate-500">다음 면접 전에 실천해보세요.</p>
          </div>
        </div>
        <div className="grid gap-4 md:grid-cols-3">
          {feedback.action_plan.map((item, index) => (
            <article key={`${item.action}-${index}`} className="rounded-2xl bg-slate-50 p-5">
              <span className="mb-4 grid size-8 place-items-center rounded-full bg-blue-600 text-sm font-black text-white">
                {index + 1}
              </span>
              <h3 className="font-bold leading-6">{item.action}</h3>
              <p className="mt-2 text-sm leading-6 text-slate-500">{item.purpose}</p>
            </article>
          ))}
        </div>
      </section>

      <section className="rounded-3xl border border-slate-100 bg-white p-6 shadow-sm sm:p-8">
        <div className="mb-6 flex items-center gap-3">
          <span className="grid size-11 place-items-center rounded-xl bg-blue-50 text-blue-600">
            <MessageSquareText size={22} />
          </span>
          <div>
            <h2 className="text-xl font-extrabold">질문별 피드백</h2>
            <p className="text-sm text-slate-500">각 답변의 평가 내용을 확인하세요.</p>
          </div>
        </div>
        <div className="space-y-3">
          {feedback.question_feedback.map((item) => (
            <details key={item.question_number} className="group rounded-2xl border border-slate-200 bg-white open:border-blue-200 open:bg-blue-50/30">
              <summary className="flex cursor-pointer list-none items-center gap-4 p-5">
                <span className="grid size-9 shrink-0 place-items-center rounded-full bg-blue-50 text-xs font-black text-blue-600">
                  Q{item.question_number}
                </span>
                <span className="min-w-0 flex-1">
                  <strong className="line-clamp-1 block text-sm">{item.question}</strong>
                  <span className="mt-1 block text-xs text-slate-500">{item.competency}</span>
                </span>
                <span className="rounded-full bg-slate-100 px-3 py-1 text-xs font-black text-slate-700">
                  {Math.round(item.overall_score)}점
                </span>
                <ChevronDown className="text-slate-400 transition group-open:rotate-180" size={18} />
              </summary>
              <div className="border-t border-blue-100 px-5 py-5 text-sm leading-7">
                <p className="font-semibold text-slate-800">{item.summary}</p>
                {item.improvement_focus && (
                  <p className="mt-3 rounded-xl bg-white p-4 text-slate-600">
                    <strong className="text-blue-700">다음 답변의 초점:</strong>{" "}
                    {item.improvement_focus}
                  </p>
                )}
              </div>
            </details>
          ))}
        </div>
      </section>

      <section className="rounded-3xl bg-slate-950 px-6 py-7 text-center text-white sm:px-8">
        <p className="mx-auto max-w-3xl leading-7 text-slate-300">{feedback.closing_message}</p>
        <Link
          href="/interviews/new"
          className="mt-5 inline-flex items-center gap-2 rounded-xl bg-blue-600 px-5 py-3 text-sm font-bold text-white hover:bg-blue-500"
        >
          <RefreshCw size={17} /> 새 면접 연습하기
        </Link>
      </section>
    </div>
  );
}

interface SummaryCardProps {
  icon: typeof Award;
  label: string;
  value: string;
  description: string;
  color: "blue" | "emerald" | "amber";
}

function SummaryCard({ icon: Icon, label, value, description, color }: SummaryCardProps) {
  const colors = {
    blue: "bg-blue-50 text-blue-600",
    emerald: "bg-emerald-50 text-emerald-600",
    amber: "bg-amber-50 text-amber-600",
  };
  return (
    <article className="flex items-center gap-4 rounded-2xl border border-slate-100 bg-white p-5 shadow-sm">
      <span className={`grid size-12 shrink-0 place-items-center rounded-xl ${colors[color]}`}>
        <Icon size={23} />
      </span>
      <div className="min-w-0">
        <p className="text-xs font-semibold text-slate-500">{label}</p>
        <p className="mt-0.5 truncate text-xl font-black">{value}</p>
        <p className="mt-1 truncate text-xs text-slate-400">{description}</p>
      </div>
    </article>
  );
}

interface FeedbackListProps {
  title: string;
  items: string[];
  icon: typeof CheckCircle2;
  className: string;
}

function FeedbackList({ title, items, icon: Icon, className }: FeedbackListProps) {
  return (
    <section className={`rounded-3xl border p-6 ${className}`}>
      <h2 className="flex items-center gap-2 text-lg font-extrabold">
        <Icon size={20} /> {title}
      </h2>
      {items.length ? (
        <ul className="mt-4 space-y-3 text-sm leading-6">
          {items.map((item) => (
            <li key={item} className="flex gap-2">
              <span aria-hidden>•</span><span>{item}</span>
            </li>
          ))}
        </ul>
      ) : (
        <p className="mt-4 text-sm opacity-60">표시할 내용이 없습니다.</p>
      )}
    </section>
  );
}

function ResultError({ message }: { message: string }) {
  return (
    <div className="mx-auto max-w-xl rounded-3xl border border-red-100 bg-white p-8 text-center shadow-sm">
      <TriangleAlert className="mx-auto text-red-400" size={38} />
      <h1 className="mt-4 text-xl font-extrabold">결과를 불러올 수 없습니다.</h1>
      <p className="mt-2 text-sm leading-6 text-slate-500">{message}</p>
      <Link href="/" className="mt-6 inline-flex rounded-xl bg-blue-600 px-5 py-3 text-sm font-bold text-white">
        대시보드로 이동
      </Link>
    </div>
  );
}
