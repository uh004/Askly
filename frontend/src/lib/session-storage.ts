import type {
  InterviewSession,
  StoredInterviewSession,
} from "@/types/interview";

export const LAST_SESSION_KEY = "askly:v1:last-interview-session";
export const SESSION_CHANGE_EVENT = "askly:interview-session-change";

export function storeInterviewSession(session: InterviewSession): void {
  const stored: StoredInterviewSession = {
    sessionId: session.session_id,
    status: session.status,
    updatedAt: new Date().toISOString(),
  };
  window.localStorage.setItem(LAST_SESSION_KEY, JSON.stringify(stored));
  window.dispatchEvent(new Event(SESSION_CHANGE_EVENT));
}

export function parseStoredInterviewSession(
  value: string | null,
): StoredInterviewSession | null {
  if (!value) return null;

  try {
    const parsed = JSON.parse(value) as Partial<StoredInterviewSession>;
    if (
      typeof parsed.sessionId !== "string" ||
      (parsed.status !== "WAITING_ANSWER" && parsed.status !== "COMPLETED") ||
      typeof parsed.updatedAt !== "string" ||
      Number.isNaN(Date.parse(parsed.updatedAt))
    ) {
      return null;
    }
    return parsed as StoredInterviewSession;
  } catch {
    return null;
  }
}

export function getStoredInterviewSessionSnapshot(): string | null {
  return window.localStorage.getItem(LAST_SESSION_KEY);
}

export function subscribeStoredInterviewSession(onChange: () => void): () => void {
  window.addEventListener("storage", onChange);
  window.addEventListener(SESSION_CHANGE_EVENT, onChange);
  return () => {
    window.removeEventListener("storage", onChange);
    window.removeEventListener(SESSION_CHANGE_EVENT, onChange);
  };
}
