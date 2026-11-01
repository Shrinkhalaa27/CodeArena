"""Idempotent seed: `python -m app.seed`. Safe to run repeatedly."""

from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.security import hash_password
from app.db import SessionLocal
from app.models import (
    Contest,
    ContestProblem,
    Problem,
    ProblemStatus,
    Role,
    Tag,
    TestCase,
    User,
)
from app.seed_data import PROBLEMS, build_cases


def _user(db: Session, email: str, handle: str, password: str, role: Role, rating: int = 1200):
    u = db.scalar(select(User).where(User.email == email.lower()))
    if u is None:
        u = User(
            email=email.lower(),
            handle=handle,
            handle_lower=handle.lower(),
            password_hash=hash_password(password),
            role=role.value,
            rating=rating,
        )
        db.add(u)
    return u


def seed(db: Session) -> dict:
    s = get_settings()
    created = {"problems": 0, "contests": 0}
    for spec in PROBLEMS:
        if db.scalar(select(Problem.id).where(Problem.slug == spec["slug"])):
            continue
        tags = [db.scalar(select(Tag).where(Tag.name == n)) or Tag(name=n) for n in spec["tags"]]
        cases = build_cases(spec)
        db.add(
            Problem(
                slug=spec["slug"],
                title=spec["title"],
                statement=spec["statement"],
                input_format=spec["input_format"],
                output_format=spec["output_format"],
                constraints=spec["constraints"],
                difficulty=spec["difficulty"],
                time_limit_ms=spec.get("time_limit_ms", 2000),
                hints=spec.get("hints", []),
                status=ProblemStatus.PUBLISHED.value,
                tags=tags,
                test_cases=[TestCase(ordinal=i, **c) for i, c in enumerate(cases, start=1)],
            )
        )
        db.flush()
        created["problems"] += 1

    now = datetime.now(UTC)
    contests = [
        (
            "weekly-round-1",
            "Weekly Round #1",
            now + timedelta(days=3),
            now + timedelta(days=3, hours=2),
            ["a-plus-b", "two-sum", "maximum-subarray", "shortest-path"],
        ),
        (
            "warmup-round",
            "Warm-up Round (finished)",
            now - timedelta(days=10),
            now - timedelta(days=10) + timedelta(hours=2),
            ["a-plus-b", "valid-parentheses", "minimum-coins"],
        ),
    ]
    for slug, title, start, end, slugs in contests:
        if db.scalar(select(Contest.id).where(Contest.slug == slug)):
            continue
        c = Contest(
            slug=slug,
            title=title,
            description="Practice contest seeded for local development.",
            start_at=start,
            end_at=end,
            freeze_at=end - timedelta(minutes=30),
            is_rated=True,
        )
        for label, ps in zip("ABCDEF", slugs, strict=False):
            p = db.scalar(select(Problem).where(Problem.slug == ps))
            c.problems.append(ContestProblem(problem_id=p.id, label=label, points=1))
        db.add(c)
        created["contests"] += 1

    if s.bootstrap_admin_email and s.bootstrap_admin_password:
        _user(db, s.bootstrap_admin_email, "admin", s.bootstrap_admin_password, Role.ADMIN)
    if s.seed_demo_users and not s.is_production:
        _user(db, "demo@codearena.dev", "demo", "demo-password-1", Role.USER)
        _user(db, "setter@codearena.dev", "setter", "setter-password-1", Role.SETTER)
    db.commit()
    return created


if __name__ == "__main__":
    with SessionLocal() as session:
        print(seed(session))
