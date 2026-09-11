import { InterviewResult } from "@/components/report/interview-result";

interface InterviewResultPageProps {
  params: Promise<{ sessionId: string }>;
}

export default async function InterviewResultPage({
  params,
}: InterviewResultPageProps) {
  const { sessionId } = await params;
  return <InterviewResult sessionId={sessionId} />;
}
