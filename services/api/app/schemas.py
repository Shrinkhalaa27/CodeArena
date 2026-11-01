"""Public/API schemas. NOTE: there is deliberately no schema that exposes non-sample test
cases, official editorials, password hashes or source code of other users."""

import re
import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

HANDLE_RE = re.compile(r"^[A-Za-z0-9_]{3,24}$")


class ORM(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# ---------- auth / users
class RegisterIn(BaseModel):
    email: EmailStr
    handle: str
    password: str = Field(min_length=8, max_length=128)

    @field_validator("handle")
    @classmethod
    def _handle(cls, v: str) -> str:
        if not HANDLE_RE.match(v):
            raise ValueError("Handle must be 3-24 letters, digits or underscores")
        return v


class LoginIn(BaseModel):
    email: EmailStr
    password: str = Field(max_length=128)


class RefreshIn(BaseModel):
    refresh_token: str


class TokenOut(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class UserMe(ORM):
    id: uuid.UUID
    email: str
    handle: str
    role: str
    bio: str
    country: str | None
    is_public: bool
    rating: int
    created_at: datetime


class UserUpdate(BaseModel):
    # mass-assignment safe: role/rating/email are not accepted here
    bio: str | None = Field(default=None, max_length=280)
    country: str | None = Field(default=None, min_length=2, max_length=2)
    is_public: bool | None = None


class PublicProfile(BaseModel):
    handle: str
    bio: str
    country: str | None
    rating: int
    joined: datetime
    solved_by_difficulty: dict[str, int]
    accepted_submissions: int
    total_submissions: int
    rating_history: list[dict]
    activity: dict[str, int]  # ISO date -> submission count
    languages: dict[str, int]


# ---------- problems
class TagOut(ORM):
    name: str


class SampleOut(BaseModel):
    input: str
    expected_output: str


class ProblemSummary(BaseModel):
    id: uuid.UUID
    slug: str
    title: str
    difficulty: str
    tags: list[str]
    acceptance_rate: float | None = None
    status: str | None = None  # solved / attempted / None for the signed-in user


class ProblemPage(BaseModel):
    items: list[ProblemSummary]
    total: int
    page: int
    page_size: int


class ProblemDetail(BaseModel):
    id: uuid.UUID
    slug: str
    title: str
    statement: str
    input_format: str
    output_format: str
    constraints: str
    difficulty: str
    time_limit_ms: int
    memory_limit_kb: int
    tags: list[str]
    samples: list[SampleOut]
    languages: list[str]
    templates: dict[str, str]


# ---------- submissions
class SubmissionIn(BaseModel):
    problem_id: uuid.UUID
    language: str
    source_code: str
    contest_id: uuid.UUID | None = None


class SubmissionCreated(BaseModel):
    submission_id: uuid.UUID
    status: str
    created_at: datetime
    status_url: str


class SubmissionOut(ORM):
    id: uuid.UUID
    problem_id: uuid.UUID
    contest_id: uuid.UUID | None
    status: str
    language: str
    passed_tests: int
    total_tests: int
    runtime_ms: int | None
    memory_kb: int | None
    compile_output: str | None = None
    created_at: datetime
    finished_at: datetime | None


class SubmissionDetail(SubmissionOut):
    source_code: str


class RunIn(BaseModel):
    language: str
    source_code: str
    stdin: str = ""
    problem_id: uuid.UUID | None = None


class RunOut(BaseModel):
    status: str
    stdout: str
    compile_output: str
    runtime_ms: int | None
    memory_kb: int | None


# ---------- contests
class ContestSummary(BaseModel):
    id: uuid.UUID
    slug: str
    title: str
    description: str
    start_at: datetime
    end_at: datetime
    freeze_at: datetime | None
    phase: str
    is_rated: bool
    participants: int
    registered: bool = False


class ContestProblemOut(BaseModel):
    label: str
    points: int
    problem_id: uuid.UUID
    slug: str
    title: str
    difficulty: str


class ContestDetail(ContestSummary):
    penalty_minutes: int
    problems: list[ContestProblemOut]  # empty until the contest starts (unless admin)
    server_time: datetime


class ScoreboardCell(BaseModel):
    label: str
    solved: bool
    wrong_attempts: int
    minutes: int | None


class ScoreboardRow(BaseModel):
    rank: int
    handle: str
    score: int
    penalty: int
    cells: list[ScoreboardCell]


class Scoreboard(BaseModel):
    contest: str
    phase: str
    frozen: bool
    full_view: bool
    rows: list[ScoreboardRow]


class LeaderboardRow(BaseModel):
    rank: int
    handle: str
    rating: int
    solved: int


# ---------- admin
class TestCaseIn(BaseModel):
    __test__ = False
    input: str
    expected_output: str
    is_sample: bool = False


class ProblemIn(BaseModel):
    slug: str = Field(pattern=r"^[a-z0-9][a-z0-9-]{1,78}$")
    title: str = Field(min_length=3, max_length=200)
    statement: str = Field(min_length=10)
    input_format: str = ""
    output_format: str = ""
    constraints: str = ""
    difficulty: str = Field(pattern="^(easy|medium|hard)$")
    time_limit_ms: int = Field(default=2000, ge=100, le=15000)
    memory_limit_kb: int = Field(default=262144, ge=16384, le=1048576)
    tags: list[str] = []
    hints: list[str] = []
    editorial: str = ""
    test_cases: list[TestCaseIn] = Field(min_length=1)


class ContestProblemIn(BaseModel):
    problem_slug: str
    label: str = Field(pattern="^[A-Z][0-9]?$")
    points: int = Field(default=1, ge=1, le=1000)


class ContestIn(BaseModel):
    slug: str = Field(pattern=r"^[a-z0-9][a-z0-9-]{1,78}$")
    title: str = Field(min_length=3, max_length=200)
    description: str = ""
    start_at: datetime
    end_at: datetime
    freeze_at: datetime | None = None
    penalty_minutes: int = Field(default=10, ge=0, le=120)
    is_rated: bool = True
    problems: list[ContestProblemIn] = []


class AiRequest(BaseModel):
    problem_id: uuid.UUID
    code: str | None = Field(default=None, max_length=8000)
    level: int = Field(default=1, ge=1, le=3)


class AiResponse(BaseModel):
    text: str
    disclaimer: str = (
        "AI-generated and potentially inaccurate. It never affects verdicts or ratings."
    )
    remaining_quota: int
