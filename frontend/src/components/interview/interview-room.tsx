"use client";

import {
  ArrowLeft,
  Bot,
  CheckCircle2,
  ChevronRight,
  CircleDot,
  Clock3,
  Lightbulb,
  LoaderCircle,
  MessageSquareText,
  Save,
  Send,
} from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { FormEvent, useEffect, useState } from "react";

import { getInterview, submitAnswer } from "@/lib/interview-api";
import { storeInterviewSession } from "@/lib/session-storage";
import type { InterviewSession, QuestionType } from "@/types/interview";

interface InterviewRoomProps {
  sessionId: string;
}

const questionTypeLabels: Record<QuestionType, string> = {
  INITIAL: "첫 질문",
  FOLLOW_UP: "꼬리 질문",
  NEXT: "다음 역량 질문",
};

export function InterviewRoom({ sessionId }: InterviewRoomProps) {
  const router = useRouter();
  const [session, setSession] = useState<InterviewSession>();
  const draftKey = `askly:v1:draft:${sessionId}`;
  const [answer, setAnswer] = useState(() =>
    typeof window === "undefined"
      ? ""
      : window.localStorage.getItem(draftKey) ?? "",
  );
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    let active = true;
    getInterview(sessionId)
      .then((data) => {
        if (!active) return;
        storeInterviewSession(data);
        if (data.status === "COMPLETED") {
          router.replace(`/interviews/${sessionId}/result`);
          return;
        }
        setSession(data);
      })
      .catch((requestError: unknown) => {
        if (active) {
          setError(
            requestError instanceof Error
              ? requestError.message
              : "면접 정보를 불러오지 못했습니다.",
          );
        }
      })
      .finally(() => {
        if (active) setLoading(false);
      });

    return () => {
      active = false;
    };
  }, [router, sessionId]);

  function saveDraft() {
    window.localStorage.setItem(draftKey, answer);
    setSaved(true);
    window.setTimeout(() => setSaved(false), 1600);
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const normalized = answer.trim();
    if (!normalized) {
      setError("답변을 입력해주세요.");
      return;
    }

    setSubmitting(true);
    setError("");
    try {
      const nextSession = await submitAnswer(sessionId, normalized);
      storeInterviewSession(nextSession);
      window.localStorage.removeItem(draftKey);
      setAnswer("");

      if (nextSession.status === "COMPLETED") {
        router.push(`/interviews/${sessionId}/result`);
        return;
      }
      setSession(nextSession);
    } catch (requestError) {
      setError(
        requestError instanceof Error
          ? requestError.message
          : "답변을 제출하지 못했습니다.",
      );
    } finally {
      setSubmitting(false);
    }
  }

  if (loading) {
    return <InterviewLoading message="면접 정보를 불러오는 중입니다..." />;
  }

  if (!session || !session.question) {
    return (
      <div className="mx-auto max-w-xl rounded-3xl border border-red-100 bg-white p-8 text-center shadow-sm">
        <MessageSquareText className="mx-auto text-red-400" size={38} />
        <h1 className="mt-4 text-xl font-extrabold">면접을 불러올 수 없습니다.</h1>
        <p className="mt-2 text-sm leading-6 text-slate-500">{error}</p>
        <Link
          href="/interviews/new"
          className="mt-6 inline-flex rounded-xl bg-blue-600 px-5 py-3 text-sm font-bold text-white"
        >
          새 면접 시작하기
        </Link>
      </div>
    );
  }

  const currentNumber = session.progress.question_count + 1;
  const question = session.question;

  return (
    <div className="animate-fade-up">
      <div className="mb-7 flex flex-wrap items-start justify-between gap-4">
        <div className="flex items-start gap-3">
          <Link
            href="/"
            aria-label="대시보드로 나가기"
            className="mt-1 grid size-10 place-items-center rounded-full border border-slate-200 bg-white text-slate-600 hover:text-blue-600"
          >
            <ArrowLeft size={19} />
          </Link>
          <div>
            <div className="flex flex-wrap items-center gap-3">
              <h1 className="text-2xl font-black tracking-tight sm:text-3xl">
                AI 맞춤 모의면접
              </h1>
              <span className="rounded-full bg-blue-50 px-3 py-1 text-xs font-bold text-blue-600">
                진행 중
              </span>
            </div>
            <p className="mt-2 text-sm text-slate-500">
              실제 경험을 중심으로 차분하고 구체적으로 답변해보세요.
            </p>
          </div>
        </div>
      </div>

      <section className="mb-6 rounded-2xl border border-slate-100 bg-white p-5 shadow-sm">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div>
            <p className="text-xs font-bold uppercase tracking-wider text-slate-400">진행 상태</p>
            <p className="mt-1 font-extrabold">
              질문 {currentNumber} · 답변 완료 {session.progress.question_count}개
            </p>
          </div>
          <div className="flex items-center gap-4 text-sm">
            <span className="flex items-center gap-2 text-slate-500">
              <MessageSquareText size={17} className="text-blue-500" />
              꼬리 질문 {session.progress.followup_count}개
            </span>
            <span className="flex items-center gap-2 text-slate-500">
              <CircleDot size={17} className="text-blue-500" />
              핵심 역량 {session.progress.target_competency_count}개
            </span>
          </div>
        </div>
      </section>

      <div className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_320px]">
        <div className="space-y-5">
          <section className="rounded-3xl border border-blue-100 bg-white p-6 shadow-sm sm:p-8">
            <div className="flex gap-5">
              <span className="hidden size-20 shrink-0 place-items-center rounded-3xl bg-gradient-to-br from-blue-100 to-indigo-100 text-blue-600 sm:grid">
                <Bot size={42} strokeWidth={1.5} />
              </span>
              <div className="min-w-0 flex-1">
                <div className="mb-4 flex flex-wrap items-center gap-2">
                  <span className="rounded-full bg-blue-600 px-3 py-1 text-xs font-bold text-white">
                    Q{currentNumber}
                  </span>
                  <span className="rounded-full bg-blue-50 px-3 py-1 text-xs font-bold text-blue-600">
                    {questionTypeLabels[question.question_type]}
                  </span>
                  <span className="rounded-full bg-slate-100 px-3 py-1 text-xs font-semibold text-slate-600">
                    {question.competency}
                  </span>
                </div>
                <h2 className="text-xl font-extrabold leading-relaxed text-slate-950 sm:text-2xl">
                  {question.question}
                </h2>
              </div>
            </div>
          </section>

          <form onSubmit={handleSubmit} className="rounded-3xl border border-slate-100 bg-white p-6 shadow-sm sm:p-8">
            <div className="mb-4 flex items-center justify-between gap-3">
              <h2 className="flex items-center gap-2 font-extrabold">
                <MessageSquareText size={19} className="text-blue-600" />
                나의 답변
              </h2>
              <span className="flex items-center gap-1.5 text-xs text-slate-400">
                <Clock3 size={14} /> 충분히 생각한 뒤 제출하세요
              </span>
            </div>
            <textarea
              value={answer}
              onChange={(event) => setAnswer(event.target.value)}
              maxLength={10000}
              rows={11}
              disabled={submitting}
              placeholder={
                "답변을 입력하세요.\n상황, 맡은 역할, 행동, 결과를 순서대로 설명하면 좋습니다."
              }
              className="w-full resize-y rounded-2xl border border-slate-200 bg-slate-50/40 p-5 text-sm leading-7 outline-none transition placeholder:text-slate-300 focus:border-blue-500 focus:bg-white focus:ring-4 focus:ring-blue-50 disabled:opacity-60"
            />
            <div className="mt-3 flex items-center justify-between text-xs text-slate-400">
              <span>{answer.length.toLocaleString()} / 10,000자</span>
              {saved && <span className="font-semibold text-emerald-600">임시 저장됐습니다.</span>}
            </div>
            {error && (
              <p role="alert" className="mt-4 rounded-xl bg-red-50 px-4 py-3 text-sm font-medium text-red-600">
                {error}
              </p>
            )}
            <div className="mt-5 flex justify-end gap-3">
              <button
                type="button"
                onClick={saveDraft}
                disabled={!answer || submitting}
                className="inline-flex items-center gap-2 rounded-xl border border-slate-200 px-4 py-3 text-sm font-bold text-slate-600 hover:bg-slate-50 disabled:opacity-40"
              >
                <Save size={17} /> 임시 저장
              </button>
              <button
                type="submit"
                disabled={!answer.trim() || submitting}
                className="inline-flex min-w-36 items-center justify-center gap-2 rounded-xl bg-blue-600 px-5 py-3 text-sm font-bold text-white shadow-lg shadow-blue-100 hover:bg-blue-700 disabled:cursor-not-allowed disabled:bg-blue-300"
              >
                {submitting ? (
                  <LoaderCircle className="animate-spin" size={18} />
                ) : (
                  <Send size={18} />
                )}
                {submitting ? "평가 중..." : "답변 제출"}
              </button>
            </div>
          </form>
        </div>

        <aside className="space-y-5">
          <section className="rounded-3xl border border-slate-100 bg-white p-6 shadow-sm">
            <h2 className="font-extrabold">평가 대상 역량</h2>
            <div className="mt-5 space-y-3">
              {session.target_competencies.map((competency) => {
                const active = competency === question.competency;
                return (
                  <div
                    key={competency}
                    className={`flex items-center gap-3 rounded-xl px-3 py-3 text-sm font-semibold ${
                      active ? "bg-blue-50 text-blue-700" : "text-slate-500"
                    }`}
                  >
                    {active ? (
                      <CircleDot size={18} className="shrink-0" />
                    ) : (
                      <CheckCircle2 size={18} className="shrink-0 text-slate-300" />
                    )}
                    <span className="flex-1">{competency}</span>
                    {active && <ChevronRight size={16} />}
                  </div>
                );
              })}
            </div>
          </section>

          <section className="rounded-3xl border border-amber-100 bg-amber-50 p-6">
            <h2 className="flex items-center gap-2 font-extrabold text-amber-900">
              <Lightbulb size={19} /> 답변 팁
            </h2>
            <ul className="mt-4 space-y-3 text-sm leading-6 text-amber-900/70">
              <li>상황과 본인의 역할을 구분해보세요.</li>
              <li>직접 수행한 행동을 구체적으로 설명하세요.</li>
              <li>결과나 배운 점으로 답변을 마무리하세요.</li>
            </ul>
          </section>
        </aside>
      </div>
    </div>
  );
}

function InterviewLoading({ message }: { message: string }) {
  return (
    <div className="flex min-h-[60vh] flex-col items-center justify-center text-center">
      <span className="grid size-20 place-items-center rounded-3xl bg-blue-100 text-blue-600">
        <LoaderCircle className="animate-spin" size={34} />
      </span>
      <h1 className="mt-6 text-xl font-extrabold">{message}</h1>
      <p className="mt-2 text-sm text-slate-500">잠시만 기다려주세요.</p>
    </div>
  );
}
