"use client";

import {
  ArrowRight,
  Check,
  ExternalLink,
  FileText,
  Link2,
  LoaderCircle,
  Play,
  Trash2,
  UploadCloud,
} from "lucide-react";
import { useRouter } from "next/navigation";
import { ChangeEvent, DragEvent, FormEvent, useRef, useState } from "react";

import { startInterview } from "@/lib/interview-api";
import { storeInterviewSession } from "@/lib/session-storage";

const MAX_FILE_SIZE = 10 * 1024 * 1024;

function validatePdf(file: File): string | null {
  if (!file.name.toLowerCase().endsWith(".pdf")) {
    return "PDF 파일만 업로드할 수 있습니다.";
  }
  if (file.size > MAX_FILE_SIZE) {
    return "PDF 파일은 10MB 이하여야 합니다.";
  }
  if (file.size === 0) return "비어 있는 파일은 업로드할 수 없습니다.";
  return null;
}

export function StartInterviewForm() {
  const router = useRouter();
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [file, setFile] = useState<File>();
  const [jobUrl, setJobUrl] = useState("");
  const [dragging, setDragging] = useState(false);
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  function selectFile(selected?: File) {
    if (!selected) return;
    const message = validatePdf(selected);
    if (message) {
      setFile(undefined);
      setError(message);
      return;
    }
    setFile(selected);
    setError("");
  }

  function handleFileChange(event: ChangeEvent<HTMLInputElement>) {
    selectFile(event.target.files?.[0]);
  }

  function handleDrop(event: DragEvent<HTMLDivElement>) {
    event.preventDefault();
    setDragging(false);
    selectFile(event.dataTransfer.files?.[0]);
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!file) {
      setError("이력서 또는 자기소개서 PDF를 선택해주세요.");
      return;
    }

    try {
      const parsedUrl = new URL(jobUrl);
      if (!['http:', 'https:'].includes(parsedUrl.protocol)) throw new Error();
    } catch {
      setError("http 또는 https 형식의 채용공고 URL을 입력해주세요.");
      return;
    }

    setSubmitting(true);
    setError("");
    try {
      const session = await startInterview(file, jobUrl.trim());
      storeInterviewSession(session);
      router.push(`/interviews/${session.session_id}`);
    } catch (requestError) {
      setError(
        requestError instanceof Error
          ? requestError.message
          : "면접 준비 중 오류가 발생했습니다.",
      );
      setSubmitting(false);
    }
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-5">
      <section className="rounded-3xl border border-slate-100 bg-white p-6 shadow-sm sm:p-8">
        <div className="mb-6 flex items-start gap-4">
          <span className="grid size-11 shrink-0 place-items-center rounded-full bg-blue-600 text-lg font-black text-white shadow-md shadow-blue-200">
            1
          </span>
          <div>
            <h2 className="text-xl font-extrabold">이력서 / 자기소개서 업로드</h2>
            <p className="mt-1 text-sm text-slate-500">
              여러 문서가 있다면 하나의 PDF로 합쳐주세요.
            </p>
          </div>
        </div>

        <div
          role="button"
          tabIndex={0}
          onClick={() => fileInputRef.current?.click()}
          onKeyDown={(event) => {
            if (event.key === "Enter" || event.key === " ") {
              fileInputRef.current?.click();
            }
          }}
          onDragEnter={() => setDragging(true)}
          onDragLeave={() => setDragging(false)}
          onDragOver={(event) => event.preventDefault()}
          onDrop={handleDrop}
          className={`cursor-pointer rounded-2xl border-2 border-dashed px-6 py-10 text-center transition ${
            dragging
              ? "border-blue-500 bg-blue-50"
              : "border-blue-200 bg-blue-50/30 hover:border-blue-400 hover:bg-blue-50"
          }`}
        >
          <input
            ref={fileInputRef}
            type="file"
            accept="application/pdf,.pdf"
            onChange={handleFileChange}
            className="hidden"
          />
          <UploadCloud className="mx-auto text-blue-600" size={38} />
          <p className="mt-4 font-bold text-slate-800">
            PDF 파일을 드래그하거나 클릭해 선택하세요.
          </p>
          <p className="mt-2 text-xs text-slate-400">PDF 형식 · 최대 10MB</p>
        </div>

        {file && (
          <div className="mt-4 flex items-center gap-3 rounded-2xl border border-emerald-100 bg-emerald-50/50 p-4">
            <span className="grid size-11 shrink-0 place-items-center rounded-xl bg-white text-red-500 shadow-sm">
              <FileText size={22} />
            </span>
            <div className="min-w-0 flex-1">
              <p className="truncate text-sm font-bold">{file.name}</p>
              <p className="mt-1 text-xs text-slate-500">
                {(file.size / 1024 / 1024).toFixed(2)} MB
              </p>
            </div>
            <Check className="text-emerald-500" size={20} />
            <button
              type="button"
              aria-label="파일 제거"
              onClick={() => {
                setFile(undefined);
                if (fileInputRef.current) fileInputRef.current.value = "";
              }}
              className="rounded-lg p-2 text-slate-400 hover:bg-white hover:text-red-500"
            >
              <Trash2 size={18} />
            </button>
          </div>
        )}
      </section>

      <section className="rounded-3xl border border-slate-100 bg-white p-6 shadow-sm sm:p-8">
        <div className="mb-6 flex items-start gap-4">
          <span className="grid size-11 shrink-0 place-items-center rounded-full bg-blue-600 text-lg font-black text-white shadow-md shadow-blue-200">
            2
          </span>
          <div>
            <h2 className="text-xl font-extrabold">채용공고 URL 입력</h2>
            <p className="mt-1 text-sm text-slate-500">
              지원하려는 직무의 채용공고 주소를 입력해주세요.
            </p>
          </div>
        </div>

        <label className="flex items-center gap-3 rounded-2xl border border-slate-200 bg-white px-4 py-3.5 focus-within:border-blue-500 focus-within:ring-4 focus-within:ring-blue-50">
          <Link2 className="shrink-0 text-blue-600" size={20} />
          <input
            type="url"
            value={jobUrl}
            onChange={(event) => setJobUrl(event.target.value)}
            placeholder="https://www.example.com/jobs/123"
            required
            className="w-full min-w-0 bg-transparent text-sm outline-none placeholder:text-slate-300"
          />
          {jobUrl && <ExternalLink className="shrink-0 text-slate-300" size={17} />}
        </label>
      </section>

      {error && (
        <p role="alert" className="rounded-2xl border border-red-100 bg-red-50 px-4 py-3 text-sm font-medium text-red-600">
          {error}
        </p>
      )}

      <button
        type="submit"
        disabled={submitting}
        className="flex w-full items-center justify-center gap-2 rounded-2xl bg-blue-600 px-6 py-4 font-bold text-white shadow-lg shadow-blue-200 transition hover:bg-blue-700 disabled:cursor-wait disabled:bg-blue-400"
      >
        {submitting ? (
          <>
            <LoaderCircle className="animate-spin" size={20} />
            서류를 분석하고 면접을 준비하는 중입니다...
          </>
        ) : (
          <>
            <Play size={19} fill="currentColor" />
            면접 준비 시작
            <ArrowRight size={19} />
          </>
        )}
      </button>
      <p className="text-center text-xs text-slate-400">
        분석에는 약 1~2분이 걸릴 수 있습니다. 페이지를 닫지 말아주세요.
      </p>
    </form>
  );
}
