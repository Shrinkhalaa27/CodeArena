"""Documented Elo-like contest rating. Pure functions; the DB write is idempotent via a
unique (user_id, contest_id) constraint."""

MIN_RATED_CONTESTS_FOR_FINAL = 5
K_FACTOR = 32


def expected_score(rating_a: float, rating_b: float) -> float:
    return 1.0 / (1.0 + 10 ** ((rating_b - rating_a) / 400.0))


def compute_rating_changes(participants: list[tuple[str, int, int]]) -> dict[str, int]:
    """participants: (user_id, current_rating, rank). Lower rank is better, equal ranks tie.
    Returns {user_id: new_rating}. Each player is compared against every other player."""
    n = len(participants)
    if n < 2:
        return {uid: rating for uid, rating, _ in participants}
    out: dict[str, int] = {}
    for uid, rating, rank in participants:
        delta = 0.0
        for other_uid, other_rating, other_rank in participants:
            if other_uid == uid:
                continue
            actual = 1.0 if rank < other_rank else 0.5 if rank == other_rank else 0.0
            delta += actual - expected_score(rating, other_rating)
        out[uid] = round(rating + K_FACTOR * delta / (n - 1))
    return out
