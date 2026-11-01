from collections import Counter

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.errors import ApiError
from app.db import get_db
from app.models import Problem, RatingChange, Submission, User, Verdict
from app.schemas import LeaderboardRow, PublicProfile

router = APIRouter(tags=["community"])


@router.get("/leaderboard", response_model=list[LeaderboardRow])
def global_leaderboard(limit: int = Query(default=50, ge=1, le=100), db: Session = Depends(get_db)):
    users = list(
        db.scalars(
            select(User)
            .where(User.is_public.is_(True), User.is_active.is_(True))
            .order_by(User.rating.desc(), User.handle_lower.asc())
            .limit(limit)
        )
    )
    solved = dict(
        db.execute(
            select(Submission.user_id, func.count(func.distinct(Submission.problem_id)))
            .where(
                Submission.status == Verdict.ACCEPTED.value,
                Submission.user_id.in_([u.id for u in users] or [None]),
            )
            .group_by(Submission.user_id)
        ).all()
    )
    return [
        LeaderboardRow(rank=i, handle=u.handle, rating=u.rating, solved=solved.get(u.id, 0))
        for i, u in enumerate(users, start=1)
    ]


@router.get("/users/{handle}", response_model=PublicProfile)
def profile(handle: str, db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(User.handle_lower == handle.lower()))
    if user is None or not user.is_public:  # private profiles look identical to missing ones
        raise ApiError(404, "NOT_FOUND", "User not found.")
    subs = db.execute(
        select(
            Submission.problem_id, Submission.status, Submission.language, Submission.created_at
        ).where(Submission.user_id == user.id)
    ).all()
    diff = dict(db.execute(select(Problem.id, Problem.difficulty)).all())
    solved_ids = {pid for pid, st, _, _ in subs if st == Verdict.ACCEPTED.value}
    by_diff = Counter(diff.get(pid, "easy") for pid in solved_ids)
    history = [
        {
            "contest_id": str(r.contest_id),
            "old": r.old_rating,
            "new": r.new_rating,
            "rank": r.rank,
            "provisional": r.provisional,
            "at": r.created_at.isoformat(),
        }
        for r in db.scalars(
            select(RatingChange)
            .where(RatingChange.user_id == user.id)
            .order_by(RatingChange.created_at)
        )
    ]
    return PublicProfile(
        handle=user.handle,
        bio=user.bio,
        country=user.country,
        rating=user.rating,
        joined=user.created_at,
        solved_by_difficulty={d: by_diff.get(d, 0) for d in ("easy", "medium", "hard")},
        accepted_submissions=sum(1 for _, st, _, _ in subs if st == Verdict.ACCEPTED.value),
        total_submissions=len(subs),
        rating_history=history,
        activity=dict(Counter(t.date().isoformat() for *_, t in subs)),
        languages=dict(Counter(lang for _, _, lang, _ in subs)),
    )
