import { Bot, ChartNoAxesCombined, FileSearch, MessageSquareText } from "lucide-react";
import Link from "next/link";

import { StartInterviewForm } from "@/components/interview/start-interview-form";

const preparationSteps = [
  { label: "문서 파싱", description: "PDF 문서에서 지원자 정보를 추출합니다.", icon: FileSearch },
  { label: "구조화 분석", description: "경험과 채용공고의 핵심 요구사항을 분석합니다.", icon: ChartNoAxesCombined },
  { label: "질문 생성", description: "검증할 역량에 맞춘 면접 질문을 준비합니다.", icon: MessageSquareText },
];

export default function NewInterviewPage() {
  return (
    <div className="animate-fade-up">
      <Link
        href="/"
        className="mb-5 inline-flex text-sm font-semibold text-slate-500 hover:text-blue-600"
      >
        ← 대시보드로 돌아가기
      </Link>
      <div className="mb-8">
        <p className="mb-1 text-sm font-semibold text-blue-600">NEW INTERVIEW</p>
        <h1 className="text-3xl font-black tracking-tight sm:text-4xl">새 모의면접 시작</h1>
        <p className="mt-3 max-w-2xl text-slate-500 sm:text-lg">
          지원 서류와 희망 채용공고를 바탕으로 맞춤형 면접을 준비합니다.
        </p>
      </div>

      <div className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_360px]">
        <StartInterviewForm />

        <aside className="space-y-5">
          <section className="overflow-hidden rounded-3xl bg-gradient-to-br from-blue-100 to-indigo-100 p-7">
            <Bot className="mb-8 text-blue-600" size={58} strokeWidth={1.5} />
            <h2 className="text-2xl font-black leading-snug">
              당신의 가능성을
              <br />더 깊이, 더 정확하게
            </h2>
            <p className="mt-3 text-sm leading-6 text-slate-600">
              문서에 확인되는 사실을 기반으로 실제 면접처럼 질문합니다.
            </p>
          </section>

          <section className="rounded-3xl border border-slate-100 bg-white p-6 shadow-sm">
            <h2 className="text-lg font-extrabold">이런 순서로 준비돼요</h2>
            <div className="mt-5 space-y-5">
              {preparationSteps.map((step, index) => {
                const Icon = step.icon;
                return (
                  <div key={step.label} className="flex gap-4">
                    <span className="grid size-11 shrink-0 place-items-center rounded-xl bg-blue-50 text-blue-600">
                      <Icon size={20} />
                    </span>
                    <div>
                      <strong className="text-sm">
                        {index + 1}. {step.label}
                      </strong>
                      <p className="mt-1 text-xs leading-5 text-slate-500">
                        {step.description}
                      </p>
                    </div>
                  </div>
                );
              })}
            </div>
          </section>
        </aside>
      </div>
    </div>
  );
}
