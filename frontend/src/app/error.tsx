"use client";

import { RefreshCw, TriangleAlert } from "lucide-react";

export default function ErrorPage({ reset }: { reset: () => void }) {
  return (
    <div className="flex min-h-[60vh] flex-col items-center justify-center text-center">
      <span className="grid size-20 place-items-center rounded-3xl bg-red-50 text-red-500">
        <TriangleAlert size={34} />
      </span>
      <h1 className="mt-5 text-2xl font-black">화면을 표시하지 못했습니다.</h1>
      <p className="mt-2 text-sm text-slate-500">잠시 후 다시 시도해주세요.</p>
      <button
        type="button"
        onClick={reset}
        className="mt-6 inline-flex items-center gap-2 rounded-xl bg-blue-600 px-5 py-3 text-sm font-bold text-white"
      >
        <RefreshCw size={17} /> 다시 시도
      </button>
    </div>
  );
}
