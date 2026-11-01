import uuid
from datetime import UTC, datetime, timedelta

import httpx
import pytest

from app.models import Verdict
from app.services.judge import Judge0Client, JudgeInfraError, map_judge0_status
from app.services.normalize import normalize_output, outputs_match
from app.services.rating import compute_rating_changes
from app.services.scoring import ScoredSubmission, compute_standings

T0 = datetime(2026, 1, 1, 10, 0, tzinfo=UTC)
END = T0 + timedelta(hours=2)
A, B = uuid.UUID(int=1), uuid.UUID(int=2)
U1, U2, U3 = uuid.UUID(int=11), uuid.UUID(int=12), uuid.UUID(int=13)


def sub(user, problem, minute, ok):
    return ScoredSubmission(user, problem, T0 + timedelta(minutes=minute), ok)


def board(subs, **kw):
    return compute_standings(subs, {A: 1, B: 1}, T0, END, 10, **kw)


# ---- normalisation
def test_normalize_strips_trailing_whitespace_only():
    assert normalize_output("1 2  \r\n3\n\n\n") == "1 2\n3"
    assert outputs_match("a b\n", "a b")
    assert not outputs_match("a  b", "a b")  # internal whitespace is meaningful


# ---- scoring
def test_penalty_and_wrong_attempts():
    rows = board([sub(U1, A, 5, False), sub(U1, A, 20, True)])
    assert rows[0].score == 1 and rows[0].penalty == 20 + 10


def test_ranking_order_and_tiebreaks():
    rows = board(
        [sub(U1, A, 30, True), sub(U2, A, 10, True), sub(U3, A, 10, True), sub(U3, B, 50, True)]
    )
    assert [r.user_id for r in rows] == [U3, U2, U1]  # score, then penalty
    assert rows[0].rank == 1


def test_identical_scores_share_rank_with_stable_order():
    rows = board([sub(U2, A, 10, True), sub(U1, A, 10, True)])
    assert [r.user_id for r in rows] == [U1, U2] and [r.rank for r in rows] == [1, 1]


def test_later_accepts_and_wrongs_after_acceptance_ignored():
    rows = board([sub(U1, A, 5, True), sub(U1, A, 6, False), sub(U1, A, 7, True)])
    assert rows[0].score == 1 and rows[0].penalty == 5 and rows[0].cells[A].wrong_attempts == 0


def test_contest_boundaries():
    rows = board([sub(U1, A, -1, True), sub(U2, A, 121, True), sub(U3, A, 120, True)])
    assert [r.user_id for r in rows] == [U3]


def test_duplicate_delivery_does_not_double_count():
    s = sub(U1, A, 5, True)
    rows = board([s, s])
    assert rows[0].score == 1


def test_freeze_hides_later_submissions():
    rows = board(
        [sub(U1, A, 5, True), sub(U2, A, 100, True)], visible_until=T0 + timedelta(minutes=90)
    )
    assert [r.user_id for r in rows] == [U1]


def test_non_attempt_does_not_add_penalty():
    s = ScoredSubmission(U1, A, T0 + timedelta(minutes=2), False, counts_as_attempt=False)
    rows = board([s, sub(U1, A, 10, True)])
    assert rows[0].penalty == 10


# ---- rating
def test_rating_winner_gains_loser_drops():
    new = compute_rating_changes([("a", 1200, 1), ("b", 1200, 2)])
    assert new["a"] > 1200 > new["b"]
    assert compute_rating_changes([("a", 1200, 1)]) == {"a": 1200}


# ---- judge status mapping
def test_status_mapping():
    assert map_judge0_status(5, 0, 1000) == Verdict.TIME_LIMIT_EXCEEDED
    assert map_judge0_status(6, 0, 1000) == Verdict.COMPILATION_ERROR
    assert map_judge0_status(11, 100, 1000) == Verdict.RUNTIME_ERROR
    assert map_judge0_status(11, 2000, 1000) == Verdict.MEMORY_LIMIT_EXCEEDED
    with pytest.raises(JudgeInfraError):
        map_judge0_status(13, 0, 1000)


def test_judge0_client_end_to_end_with_mock_transport():
    import base64

    calls = []

    def handler(request: httpx.Request):
        calls.append((request.method, request.url.path))
        if request.method == "POST":
            return httpx.Response(201, json={"token": "t1"})
        out = base64.b64encode(b"3\n").decode()
        return httpx.Response(
            200, json={"status": {"id": 3}, "stdout": out, "time": "0.012", "memory": 900}
        )

    client = httpx.Client(base_url="http://judge", transport=httpx.MockTransport(handler))
    r = Judge0Client(base_url="http://judge", client=client).run(
        language="python", source="print(3)", stdin="", time_limit_ms=1000, memory_limit_kb=65536
    )
    assert r.status == Verdict.ACCEPTED and r.stdout == "3\n" and r.runtime_ms == 12
    assert calls[0] == ("POST", "/submissions")


def test_judge0_network_failure_is_infra_error():
    def handler(request):
        raise httpx.ConnectError("down")

    client = httpx.Client(base_url="http://judge", transport=httpx.MockTransport(handler))
    with pytest.raises(JudgeInfraError):
        Judge0Client(base_url="http://judge", client=client).run(
            language="python", source="x", stdin="", time_limit_ms=1000, memory_limit_kb=65536
        )
