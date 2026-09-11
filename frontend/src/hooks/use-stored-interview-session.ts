"use client";

import { useMemo, useSyncExternalStore } from "react";

import {
  getStoredInterviewSessionSnapshot,
  parseStoredInterviewSession,
  subscribeStoredInterviewSession,
} from "@/lib/session-storage";

export function useStoredInterviewSession() {
  const rawValue = useSyncExternalStore(
    subscribeStoredInterviewSession,
    getStoredInterviewSessionSnapshot,
    () => null,
  );
  return useMemo(() => parseStoredInterviewSession(rawValue), [rawValue]);
}
