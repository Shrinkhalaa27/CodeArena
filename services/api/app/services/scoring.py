"""Pure contest scoring. Scoreboards are *derived* from submissions on every read, so
duplicate worker deliveries or recomputation can never double-count points."""

from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID


@dataclass(frozen=True)
class ScoredSubmission:
    user_id: UUID
    problem_id: UUID
    created_at: datetime
    accepted: bool
    counts_as_attempt: bool = True  # False for INTERNAL_ERROR / compile errors policy below


@dataclass
class ProblemCell:
    problem_id: UUID
    solved: bool = False
    wrong_attempts: int = 0
    solved_minutes: int | None = None
    solved_at: datetime | None = None


@dataclass
class StandingRow:
    user_id: UUID
    score: int = 0
    penalty: int = 0
    last_accepted_at: datetime | None = None
    cells: dict[UUID, ProblemCell] = field(default_factory=dict)
    rank: int = 0


def compute_standings(
    submissions: list[ScoredSubmission],
    problem_points: dict[UUID, int],
    start_at: datetime,
    end_at: datetime,
    penalty_minutes: int,
    registered: set[UUID] | None = None,
    visible_until: datetime | None = None,
) -> list[StandingRow]:
    """Rules (docs/SPEC.md FR-05):
    * only submissions inside [start_at, end_at] and (optionally) <= visible_until count
    * 1 point per solved problem (or configured points)
    * penalty = elapsed whole minutes at first accepted + penalty_minutes per earlier wrong try
    * submissions after the first accepted one on the same problem are ignored
    * INTERNAL_ERROR submissions are not attempts (counts_as_attempt=False)
    * order: score desc, penalty asc, last accepted asc, user id asc (stable)
    """
    rows: dict[UUID, StandingRow] = {}
    for uid in registered or set():
        rows[uid] = StandingRow(user_id=uid)

    for s in sorted(submissions, key=lambda x: (x.created_at, str(x.user_id))):
        if s.problem_id not in problem_points:
            continue
        if not (start_at <= s.created_at <= end_at):
            continue
        if visible_until is not None and s.created_at > visible_until:
            continue
        if registered is not None and s.user_id not in registered:
            continue
        row = rows.setdefault(s.user_id, StandingRow(user_id=s.user_id))
        cell = row.cells.setdefault(s.problem_id, ProblemCell(problem_id=s.problem_id))
        if cell.solved:
            continue
        if s.accepted:
            cell.solved = True
            cell.solved_at = s.created_at
            cell.solved_minutes = int((s.created_at - start_at).total_seconds() // 60)
        elif s.counts_as_attempt:
            cell.wrong_attempts += 1

    for row in rows.values():
        for pid, cell in row.cells.items():
            if cell.solved:
                row.score += problem_points[pid]
                row.penalty += (cell.solved_minutes or 0) + cell.wrong_attempts * penalty_minutes
                if row.last_accepted_at is None or cell.solved_at > row.last_accepted_at:
                    row.last_accepted_at = cell.solved_at

    ordered = sorted(
        rows.values(),
        key=lambda r: (
            -r.score,
            r.penalty,
            r.last_accepted_at.timestamp() if r.last_accepted_at else float("inf"),
            str(r.user_id),
        ),
    )
    # Ties on (score, penalty, last_accepted) share a rank; display order stays stable.
    prev_key, prev_rank = None, 0
    for i, row in enumerate(ordered, start=1):
        key = (row.score, row.penalty, row.last_accepted_at)
        row.rank = prev_rank if key == prev_key else i
        prev_key, prev_rank = key, row.rank
    return ordered
