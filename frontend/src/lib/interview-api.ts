import type { InterviewSession } from "@/types/interview";

const API_BASE_URL = (
  process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8000"
).replace(/\/$/, "");

export class InterviewApiError extends Error {
  constructor(
    message: string,
    public readonly status: number,
  ) {
    super(message);
    this.name = "InterviewApiError";
  }
}

function errorMessage(body: unknown): string {
  if (
    typeof body === "object" &&
    body !== null &&
    "detail" in body
  ) {
    const detail = (body as { detail: unknown }).detail;
    if (typeof detail === "string") return detail;
    if (Array.isArray(detail)) {
      return detail
        .map((item) => {
          if (typeof item === "object" && item !== null && "msg" in item) {
            return String((item as { msg: unknown }).msg);
          }
          return String(item);
        })
        .join(" ");
    }
  }
  return "요청을 처리하지 못했습니다. 잠시 후 다시 시도해주세요.";
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`${API_BASE_URL}${path}`, {
      cache: "no-store",
      ...init,
    });
  } catch {
    throw new InterviewApiError(
      "FastAPI 서버에 연결할 수 없습니다. 백엔드 실행 상태를 확인해주세요.",
      0,
    );
  }

  const body = (await response.json().catch(() => null)) as unknown;
  if (!response.ok) {
    throw new InterviewApiError(errorMessage(body), response.status);
  }
  return body as T;
}

export function startInterview(
  resumeFile: File,
  jobPostingUrl: string,
): Promise<InterviewSession> {
  const formData = new FormData();
  formData.append("resume_file", resumeFile);
  formData.append("job_posting_url", jobPostingUrl);

  return request<InterviewSession>("/api/interviews/start", {
    method: "POST",
    body: formData,
  });
}

export function submitAnswer(
  sessionId: string,
  answer: string,
): Promise<InterviewSession> {
  return request<InterviewSession>(`/api/interviews/${sessionId}/answers`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ answer }),
  });
}

export function getInterview(sessionId: string): Promise<InterviewSession> {
  return request<InterviewSession>(`/api/interviews/${sessionId}`);
}
