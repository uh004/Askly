import { InterviewRoom } from "@/components/interview/interview-room";

interface InterviewPageProps {
  params: Promise<{ sessionId: string }>;
}

export default async function InterviewPage({ params }: InterviewPageProps) {
  const { sessionId } = await params;
  return <InterviewRoom sessionId={sessionId} />;
}
