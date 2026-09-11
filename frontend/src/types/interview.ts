export type QuestionType = "INITIAL" | "FOLLOW_UP" | "NEXT";

export type InterviewStatus = "WAITING_ANSWER" | "COMPLETED";

export interface InterviewQuestion {
  question: string;
  competency: string;
  question_type: QuestionType;
}

export interface InterviewProgress {
  question_count: number;
  followup_count: number;
  target_competency_count: number;
}

export interface QuestionFeedback {
  question_number: number;
  question: string;
  answer: string;
  competency: string;
  question_type: QuestionType;
  overall_score: number;
  summary: string;
  strengths: string[];
  improvement_points: string[];
  missing_points: string[];
  answer_evidence: string[];
  improvement_focus: string;
}

export interface CompetencyFeedback {
  competency: string;
  summary: string;
  strengths: string[];
  improvement_points: string[];
  evidence: string[];
  final_score: number;
}

export interface FeedbackActionItem {
  action: string;
  purpose: string;
}

export interface InterviewStatistics {
  question_count: number;
  evaluation_count: number;
  followup_count: number;
  evaluated_competency_count: number;
}

export interface FinalInterviewFeedback {
  overall_summary: string;
  overall_score: number;
  competency_scores: Record<string, number>;
  competency_feedback: CompetencyFeedback[];
  question_feedback: QuestionFeedback[];
  key_strengths: string[];
  key_improvement_areas: string[];
  recurring_strengths: string[];
  recurring_improvement_patterns: string[];
  action_plan: FeedbackActionItem[];
  closing_message: string;
  interview_statistics: InterviewStatistics;
}

export interface InterviewSession {
  session_id: string;
  status: InterviewStatus;
  question: InterviewQuestion | null;
  progress: InterviewProgress;
  target_competencies: string[];
  end_reason: string | null;
  final_feedback: FinalInterviewFeedback | null;
}

export interface StoredInterviewSession {
  sessionId: string;
  status: InterviewStatus;
  updatedAt: string;
}
