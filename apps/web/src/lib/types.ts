// Mirrors services/api/app/schemas.py. Only public fields exist here: there is no type for
// hidden test cases because the API never sends them.
export type Difficulty = "easy" | "medium" | "hard";

export interface ProblemSummary {
  id: string; slug: string; title: string; difficulty: Difficulty;
  tags: string[]; acceptance_rate: number | null; status: "solved" | "attempted" | null;
}
export interface ProblemPage { items: ProblemSummary[]; total: number; page: number; page_size: number }
export interface ProblemDetail {
  id: string; slug: string; title: string; statement: string; input_format: string;
  output_format: string; constraints: string; difficulty: Difficulty; time_limit_ms: number;
  memory_limit_kb: number; tags: string[]; samples: { input: string; expected_output: string }[];
  languages: string[]; templates: Record<string, string>;
}
export type Verdict =
  | "QUEUED" | "COMPILING" | "RUNNING" | "ACCEPTED" | "WRONG_ANSWER" | "TIME_LIMIT_EXCEEDED"
  | "MEMORY_LIMIT_EXCEEDED" | "RUNTIME_ERROR" | "COMPILATION_ERROR" | "INTERNAL_ERROR";
export interface Submission {
  id: string; problem_id: string; contest_id: string | null; status: Verdict; language: string;
  passed_tests: number; total_tests: number; runtime_ms: number | null; memory_kb: number | null;
  compile_output: string | null; created_at: string; finished_at: string | null;
}
export interface RunResult { status: string; stdout: string; compile_output: string; runtime_ms: number | null; memory_kb: number | null }
export interface User { id: string; email: string; handle: string; role: string; bio: string; country: string | null; is_public: boolean; rating: number; created_at: string }
export interface Contest {
  id: string; slug: string; title: string; description: string; start_at: string; end_at: string;
  freeze_at: string | null; phase: "scheduled" | "running" | "frozen" | "ended" | "cancelled";
  is_rated: boolean; participants: number; registered: boolean;
}
export interface ContestDetail extends Contest {
  penalty_minutes: number; server_time: string;
  problems: { label: string; points: number; problem_id: string; slug: string; title: string; difficulty: Difficulty }[];
}
export interface Scoreboard {
  contest: string; phase: string; frozen: boolean; full_view: boolean;
  rows: { rank: number; handle: string; score: number; penalty: number; cells: { label: string; solved: boolean; wrong_attempts: number; minutes: number | null }[] }[];
}
export interface LeaderboardRow { rank: number; handle: string; rating: number; solved: number }
export interface Profile {
  handle: string; bio: string; country: string | null; rating: number; joined: string;
  solved_by_difficulty: Record<Difficulty, number>; accepted_submissions: number; total_submissions: number;
  rating_history: { old: number; new: number; rank: number; provisional: boolean; at: string }[];
  activity: Record<string, number>; languages: Record<string, number>;
}
export interface AiResponse { text: string; disclaimer: string; remaining_quota: number }
