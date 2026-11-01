import enum
import uuid
from datetime import UTC, datetime

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Table,
    Text,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import TypeDecorator

from app.db import Base


class UTCDateTime(TypeDecorator):
    """Timezone-aware UTC datetimes on every backend (SQLite drops tzinfo)."""

    impl = DateTime(timezone=True)
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is not None and value.tzinfo is None:
            value = value.replace(tzinfo=UTC)
        return value.astimezone(UTC) if value is not None else None

    def process_result_value(self, value, dialect):
        if value is not None and value.tzinfo is None:
            value = value.replace(tzinfo=UTC)
        return value


def utcnow() -> datetime:
    return datetime.now(UTC)


def uid() -> uuid.UUID:
    return uuid.uuid4()


class Role(str, enum.Enum):
    USER = "user"
    SETTER = "setter"
    CONTEST_ADMIN = "contest_admin"
    ADMIN = "admin"


class Difficulty(str, enum.Enum):
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"


class ProblemStatus(str, enum.Enum):
    DRAFT = "draft"
    REVIEW = "review"
    PUBLISHED = "published"
    ARCHIVED = "archived"


class Verdict(str, enum.Enum):
    QUEUED = "QUEUED"
    COMPILING = "COMPILING"
    RUNNING = "RUNNING"
    ACCEPTED = "ACCEPTED"
    WRONG_ANSWER = "WRONG_ANSWER"
    TIME_LIMIT_EXCEEDED = "TIME_LIMIT_EXCEEDED"
    MEMORY_LIMIT_EXCEEDED = "MEMORY_LIMIT_EXCEEDED"
    RUNTIME_ERROR = "RUNTIME_ERROR"
    COMPILATION_ERROR = "COMPILATION_ERROR"
    INTERNAL_ERROR = "INTERNAL_ERROR"


FINAL_VERDICTS = {
    Verdict.ACCEPTED,
    Verdict.WRONG_ANSWER,
    Verdict.TIME_LIMIT_EXCEEDED,
    Verdict.MEMORY_LIMIT_EXCEEDED,
    Verdict.RUNTIME_ERROR,
    Verdict.COMPILATION_ERROR,
    Verdict.INTERNAL_ERROR,
}


class User(Base):
    __tablename__ = "users"
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uid)
    email: Mapped[str] = mapped_column(String(320), unique=True)  # stored normalised (lowercase)
    handle: Mapped[str] = mapped_column(String(32))
    handle_lower: Mapped[str] = mapped_column(String(32), unique=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(20), default=Role.USER.value)
    bio: Mapped[str] = mapped_column(String(280), default="")
    country: Mapped[str | None] = mapped_column(String(2), nullable=True)
    is_public: Mapped[bool] = mapped_column(Boolean, default=True)
    rating: Mapped[int] = mapped_column(Integer, default=1200)
    rated_contests: Mapped[int] = mapped_column(Integer, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow)


class RefreshToken(Base):
    __tablename__ = "refresh_tokens"
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uid)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    token_hash: Mapped[str] = mapped_column(String(64), unique=True)
    expires_at: Mapped[datetime] = mapped_column(UTCDateTime)
    revoked: Mapped[bool] = mapped_column(Boolean, default=False)


problem_tags = Table(
    "problem_tags",
    Base.metadata,
    Column("problem_id", ForeignKey("problems.id", ondelete="CASCADE"), primary_key=True),
    Column("tag_id", ForeignKey("tags.id", ondelete="CASCADE"), primary_key=True),
)


class Tag(Base):
    __tablename__ = "tags"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(40), unique=True)


class Problem(Base):
    __tablename__ = "problems"
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uid)
    slug: Mapped[str] = mapped_column(String(80), unique=True)
    title: Mapped[str] = mapped_column(String(200))
    statement: Mapped[str] = mapped_column(Text)
    input_format: Mapped[str] = mapped_column(Text, default="")
    output_format: Mapped[str] = mapped_column(Text, default="")
    constraints: Mapped[str] = mapped_column(Text, default="")
    difficulty: Mapped[str] = mapped_column(String(10))
    time_limit_ms: Mapped[int] = mapped_column(Integer, default=2000)
    memory_limit_kb: Mapped[int] = mapped_column(Integer, default=262144)
    status: Mapped[str] = mapped_column(String(10), default=ProblemStatus.DRAFT.value)
    hints: Mapped[list] = mapped_column(JSON, default=list)
    # Official editorial is stored here but is NEVER serialised by public schemas.
    editorial: Mapped[str] = mapped_column(Text, default="")
    created_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow)

    tags: Mapped[list[Tag]] = relationship(secondary=problem_tags, lazy="selectin")
    test_cases: Mapped[list["TestCase"]] = relationship(
        back_populates="problem", cascade="all, delete-orphan", order_by="TestCase.ordinal"
    )

    __table_args__ = (
        CheckConstraint("time_limit_ms > 0 AND time_limit_ms <= 15000", name="ck_time_limit"),
        CheckConstraint("memory_limit_kb > 0", name="ck_memory_limit"),
        Index("ix_problems_status_difficulty", "status", "difficulty"),
    )


class TestCase(Base):
    __tablename__ = "test_cases"
    __test__ = False  # not a pytest class
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uid)
    problem_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("problems.id", ondelete="CASCADE"))
    ordinal: Mapped[int] = mapped_column(Integer)
    input: Mapped[str] = mapped_column(Text)
    expected_output: Mapped[str] = mapped_column(Text)
    is_sample: Mapped[bool] = mapped_column(Boolean, default=False)
    problem: Mapped[Problem] = relationship(back_populates="test_cases")

    __table_args__ = (UniqueConstraint("problem_id", "ordinal", name="uq_testcase_order"),)


class Contest(Base):
    __tablename__ = "contests"
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uid)
    slug: Mapped[str] = mapped_column(String(80), unique=True)
    title: Mapped[str] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(Text, default="")
    start_at: Mapped[datetime] = mapped_column(UTCDateTime)
    end_at: Mapped[datetime] = mapped_column(UTCDateTime)
    freeze_at: Mapped[datetime | None] = mapped_column(UTCDateTime, nullable=True)
    penalty_minutes: Mapped[int] = mapped_column(Integer, default=10)
    is_rated: Mapped[bool] = mapped_column(Boolean, default=True)
    cancelled: Mapped[bool] = mapped_column(Boolean, default=False)
    results_published: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow)

    problems: Mapped[list["ContestProblem"]] = relationship(
        cascade="all, delete-orphan", order_by="ContestProblem.label", lazy="selectin"
    )

    __table_args__ = (CheckConstraint("end_at > start_at", name="ck_contest_window"),)


class ContestProblem(Base):
    __tablename__ = "contest_problems"
    contest_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("contests.id", ondelete="CASCADE"), primary_key=True
    )
    problem_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("problems.id"), primary_key=True)
    label: Mapped[str] = mapped_column(String(4))
    points: Mapped[int] = mapped_column(Integer, default=1)
    problem: Mapped[Problem] = relationship(lazy="joined")

    __table_args__ = (UniqueConstraint("contest_id", "label", name="uq_contest_label"),)


class ContestRegistration(Base):
    __tablename__ = "contest_registrations"
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uid)
    contest_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("contests.id", ondelete="CASCADE"))
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    registered_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow)

    __table_args__ = (UniqueConstraint("contest_id", "user_id", name="uq_registration"),)


class Submission(Base):
    __tablename__ = "submissions"
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uid)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    problem_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("problems.id"))
    contest_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("contests.id"), nullable=True)
    language: Mapped[str] = mapped_column(String(20))
    source_code: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(24), default=Verdict.QUEUED.value)
    passed_tests: Mapped[int] = mapped_column(Integer, default=0)
    total_tests: Mapped[int] = mapped_column(Integer, default=0)
    runtime_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    memory_kb: Mapped[int | None] = mapped_column(Integer, nullable=True)
    compile_output: Mapped[str | None] = mapped_column(Text, nullable=True)
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    idempotency_key: Mapped[str | None] = mapped_column(String(80), nullable=True)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow)
    finished_at: Mapped[datetime | None] = mapped_column(UTCDateTime, nullable=True)

    __table_args__ = (
        UniqueConstraint("user_id", "idempotency_key", name="uq_submission_idem"),
        Index("ix_submissions_user_created", "user_id", "created_at"),
        Index("ix_submissions_contest", "contest_id", "problem_id", "created_at"),
    )


class SubmissionResult(Base):
    __tablename__ = "submission_results"
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uid)
    submission_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("submissions.id", ondelete="CASCADE")
    )
    test_case_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("test_cases.id"))
    status: Mapped[str] = mapped_column(String(24))
    runtime_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    memory_kb: Mapped[int | None] = mapped_column(Integer, nullable=True)

    __table_args__ = (UniqueConstraint("submission_id", "test_case_id", name="uq_result"),)


class RatingChange(Base):
    __tablename__ = "rating_history"
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uid)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    contest_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("contests.id"))
    old_rating: Mapped[int] = mapped_column(Integer)
    new_rating: Mapped[int] = mapped_column(Integer)
    rank: Mapped[int] = mapped_column(Integer)
    provisional: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow)

    __table_args__ = (UniqueConstraint("user_id", "contest_id", name="uq_rating_once"),)


class AuditLog(Base):
    __tablename__ = "audit_logs"
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uid)
    actor_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    action: Mapped[str] = mapped_column(String(60))
    target: Mapped[str] = mapped_column(String(120), default="")
    meta: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow)


class AiUsage(Base):
    __tablename__ = "ai_usage"
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uid)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    kind: Mapped[str] = mapped_column(String(20))
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow)
    __table_args__ = (Index("ix_ai_usage_user_time", "user_id", "created_at"),)
