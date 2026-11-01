import json
from datetime import UTC, datetime, timedelta

from app import models
from app.integrations.llm import base as llm_base
from tests.conftest import REFS, RefJudge, drain_queue, make_user, problem_id


# ---------------- auth
def test_register_login_refresh_rotation_and_profile_update(client):
    headers, tokens = make_user(client, "bob")
    assert client.get("/api/v1/auth/me", headers=headers).json()["handle"] == "bob"
    r = client.post("/api/v1/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
    assert r.status_code == 200
    # refresh tokens are single-use
    assert (
        client.post(
            "/api/v1/auth/refresh", json={"refresh_token": tokens["refresh_token"]}
        ).status_code
        == 401
    )
    assert (
        client.post(
            "/api/v1/auth/login", json={"email": "bob@example.com", "password": "wrong-password"}
        ).status_code
        == 401
    )
    r = client.patch("/api/v1/auth/me", headers=headers, json={"bio": "hi", "country": "in"})
    assert r.json()["country"] == "IN"


def test_duplicate_handle_case_insensitive_and_validation_envelope(client):
    make_user(client, "Carol")
    r = client.post(
        "/api/v1/auth/register",
        json={"email": "other@example.com", "handle": "carol", "password": "correct-horse-1"},
    )
    assert r.status_code == 409 and r.json()["error"]["code"] == "ACCOUNT_EXISTS"
    r = client.post(
        "/api/v1/auth/register", json={"email": "bad", "handle": "x", "password": "short"}
    )
    err = r.json()["error"]
    assert (
        r.status_code == 422
        and err["code"] == "VALIDATION_ERROR"
        and err["request_id"]
        and err["details"]
    )


def test_mass_assignment_cannot_escalate_role(client):
    headers, _ = make_user(client, "dave")
    client.patch("/api/v1/auth/me", headers=headers, json={"role": "admin", "rating": 4000})
    me = client.get("/api/v1/auth/me", headers=headers).json()
    assert me["role"] == "user" and me["rating"] == 1200
    r = client.post(
        "/api/v1/auth/register",
        json={
            "email": "e@example.com",
            "handle": "eve",
            "password": "correct-horse-1",
            "role": "admin",
        },
    )
    assert r.status_code == 201


# ---------------- problems / hidden-test security
def test_problem_list_filters_and_pagination(client):
    r = client.get("/api/v1/problems?page_size=5&sort=difficulty").json()
    assert r["total"] == 11 and len(r["items"]) == 5 and r["items"][0]["difficulty"] == "easy"
    assert client.get("/api/v1/problems?difficulty=hard").json()["total"] == 2
    assert client.get("/api/v1/problems?tag=graph").json()["total"] == 2
    assert client.get("/api/v1/problems?q=two").json()["items"][0]["slug"] == "two-sum"
    assert client.get("/api/v1/problems?page_size=1000").status_code == 422


def test_hidden_tests_never_in_public_responses(client, db):
    hidden = [t for t in db.query(models.TestCase).filter_by(is_sample=False).all()]
    assert hidden
    blob = ""
    for slug in REFS:
        blob += client.get(f"/api/v1/problems/{slug}").text
    blob += client.get("/api/v1/problems").text
    for t in hidden:
        if len(t.input) > 12:  # long inputs are unambiguous; tiny ones could occur in prose
            assert t.input not in blob
    detail = client.get("/api/v1/problems/two-sum").json()
    assert len(detail["samples"]) == 2
    assert "editorial" not in detail and "test_cases" not in detail


def test_unpublished_problem_is_404(client, db):
    p = db.query(models.Problem).filter_by(slug="a-plus-b").one()
    p.status = "draft"
    db.commit()
    assert client.get("/api/v1/problems/a-plus-b").status_code == 404
    assert client.get("/api/v1/problems").json()["total"] == 10


# ---------------- submissions end to end
def submit(client, auth, code="print(1)", slug="a-plus-b", **extra):
    body = {
        "problem_id": problem_id(client, slug),
        "language": "python",
        "source_code": code,
        **extra,
    }
    return client.post("/api/v1/submissions", headers=auth, json=body)


def test_submission_flow_accepted_and_wrong_and_errors(client, auth):
    cases = {
        "print('ok')": "ACCEPTED",
        "# @@WRONG": "WRONG_ANSWER",
        "# @@COMPILE_ERROR": "COMPILATION_ERROR",
        "# @@RUNTIME_ERROR": "RUNTIME_ERROR",
        "# @@TLE": "TIME_LIMIT_EXCEEDED",
    }
    for code, expected in cases.items():
        r = submit(client, auth, code)
        assert r.status_code == 202 and r.json()["status"] == "QUEUED"
        sid = r.json()["submission_id"]
        assert drain_queue() == ["done"]
        got = client.get(f"/api/v1/submissions/{sid}", headers=auth).json()
        assert got["status"] == expected, (code, got)
        if expected == "ACCEPTED":
            assert got["passed_tests"] == got["total_tests"] == 8
        elif expected == "COMPILATION_ERROR":
            assert got["compile_output"]
    assert len(client.get("/api/v1/submissions", headers=auth).json()) == 5


def test_submission_requires_auth_and_is_private(client, auth):
    assert client.post("/api/v1/submissions", json={}).status_code == 401
    sid = submit(client, auth).json()["submission_id"]
    other, _ = make_user(client, "mallory")
    assert client.get(f"/api/v1/submissions/{sid}", headers=other).status_code == 404  # IDOR


def test_submission_validation(client, auth):
    assert submit(client, auth, "x" * 70000).json()["error"]["code"] == "SOURCE_TOO_LARGE"
    assert submit(client, auth, "   ").json()["error"]["code"] == "EMPTY_SOURCE"
    r = client.post(
        "/api/v1/submissions",
        headers=auth,
        json={"problem_id": problem_id(client), "language": "brainf", "source_code": "+"},
    )
    assert r.json()["error"]["code"] == "UNSUPPORTED_LANGUAGE"


def test_idempotency_key_prevents_duplicates(client, auth):
    h = {**auth, "Idempotency-Key": "abc-123"}
    body = {"problem_id": problem_id(client), "language": "python", "source_code": "print(1)"}
    a = client.post("/api/v1/submissions", headers=h, json=body).json()
    b = client.post("/api/v1/submissions", headers=h, json=body).json()
    assert a["submission_id"] == b["submission_id"]


def test_client_cannot_set_verdict(client, auth):
    r = submit(client, auth, status="ACCEPTED", passed_tests=99, user_id="x")
    assert r.json()["status"] == "QUEUED"


def test_submit_rate_limit(client, auth):
    codes = [submit(client, auth).status_code for _ in range(22)]
    assert codes.count(429) >= 1


def test_run_custom_input_uses_judge_not_local(client, auth):
    r = client.post(
        "/api/v1/run",
        headers=auth,
        json={"language": "python", "source_code": "# @@ECHO", "stdin": "hello"},
    )
    assert r.status_code == 200 and r.json()["stdout"] == "hello"
    r = client.post(
        "/api/v1/run", headers=auth, json={"language": "python", "source_code": "# @@COMPILE_ERROR"}
    )
    assert r.json()["status"] == "COMPILATION_ERROR"
    assert client.post("/api/v1/run", json={}).status_code == 401


def test_websocket_streams_until_final(client, auth):
    _, tokens = make_user(client, "wsuser")
    h = {"Authorization": f"Bearer {tokens['access_token']}"}
    sid = submit(client, h).json()["submission_id"]
    drain_queue()
    with client.websocket_connect(
        f"/api/v1/ws/submissions/{sid}?token={tokens['access_token']}"
    ) as ws:
        assert ws.receive_json()["status"] == "ACCEPTED"
    # a stranger is refused
    _, other = make_user(client, "stranger")
    try:
        with client.websocket_connect(
            f"/api/v1/ws/submissions/{sid}?token={other['access_token']}"
        ) as ws:
            ws.receive_json()
        raise AssertionError("expected rejection")
    except Exception as exc:  # noqa: BLE001
        assert "AssertionError" not in type(exc).__name__


# ---------------- worker idempotency / retry
def test_duplicate_delivery_is_noop(client, auth, db):
    sid = submit(client, auth).json()["submission_id"]
    drain_queue()
    from app.services.judging import process_submission

    judge = RefJudge(REFS["a-plus-b"])
    assert process_submission(db, judge, sid) == "skipped"
    assert judge.calls == 0
    assert db.query(models.SubmissionResult).count() == 8  # unchanged, unique per test


def test_infra_failure_retries_then_internal_error(client, auth):
    sid = submit(client, auth, "# @@INFRA").json()["submission_id"]
    outcomes = []
    for _ in range(5):
        outcomes += drain_queue()
    assert outcomes[:2] == ["retry", "retry"] and outcomes[2] == "done"
    assert (
        client.get(f"/api/v1/submissions/{sid}", headers=auth).json()["status"] == "INTERNAL_ERROR"
    )


def test_job_payload_contains_only_id(client, auth):
    from app.services.queue import get_queue

    sid = submit(client, auth).json()["submission_id"]
    assert list(get_queue().items) == [sid]


# ---------------- RBAC
def test_admin_endpoints_reject_normal_users_and_anonymous(client, auth):
    for method, url in [
        ("get", "/api/v1/admin/problems"),
        ("get", "/api/v1/admin/audit"),
        ("get", "/api/v1/admin/judge-health"),
    ]:
        assert getattr(client, method)(url).status_code == 401
        assert getattr(client, method)(url, headers=auth).status_code == 403
    assert client.post("/api/v1/admin/contests", headers=auth, json={}).status_code == 403
    assert client.post("/api/v1/admin/problems/two-sum/publish", headers=auth).status_code == 403
    sid = submit(client, auth).json()["submission_id"]
    assert client.post(f"/api/v1/admin/submissions/{sid}/rejudge", headers=auth).status_code == 403


def test_setter_creates_draft_admin_publishes_and_audit_logs(client):
    setter, _ = make_user(client, "setter1", "setter")
    admin, _ = make_user(client, "boss", "admin")
    body = {
        "slug": "double-it",
        "title": "Double It",
        "statement": "Print twice the number.",
        "difficulty": "easy",
        "test_cases": [{"input": "2", "expected_output": "4", "is_sample": True}],
    }
    assert client.post("/api/v1/admin/problems", headers=setter, json=body).status_code == 201
    assert client.get("/api/v1/problems/double-it").status_code == 404  # draft is invisible
    assert (
        client.post("/api/v1/admin/problems/double-it/publish", headers=setter).status_code == 403
    )
    assert (
        client.post("/api/v1/admin/problems/double-it/publish", headers=admin).status_code == 409
    )  # no hidden tests
    body2 = {
        **body,
        "slug": "triple-it",
        "test_cases": body["test_cases"] + [{"input": "3", "expected_output": "9"}],
    }
    client.post("/api/v1/admin/problems", headers=setter, json=body2)
    assert client.post("/api/v1/admin/problems/triple-it/publish", headers=admin).status_code == 200
    assert client.get("/api/v1/problems/triple-it").status_code == 200
    actions = [a["action"] for a in client.get("/api/v1/admin/audit", headers=admin).json()]
    assert "problem.publish" in actions and "problem.create" in actions
    listing = client.get("/api/v1/admin/problems", headers=admin).text
    assert '"expected_output"' not in listing


# ---------------- contests
def make_live_contest(
    client, admin, slug="live", start_offset=-10, end_offset=60, freeze_offset=None
):
    now = datetime.now(UTC)
    body = {
        "slug": slug,
        "title": "Live Contest",
        "start_at": (now + timedelta(minutes=start_offset)).isoformat(),
        "end_at": (now + timedelta(minutes=end_offset)).isoformat(),
        "freeze_at": (now + timedelta(minutes=freeze_offset)).isoformat()
        if freeze_offset
        else None,
        "problems": [
            {"problem_slug": "a-plus-b", "label": "A"},
            {"problem_slug": "two-sum", "label": "B"},
        ],
    }
    r = client.post("/api/v1/admin/contests", headers=admin, json=body)
    assert r.status_code == 201, r.text
    return slug


def test_contest_lifecycle_and_scoreboard(client):
    admin, _ = make_user(client, "boss", "admin")
    slug = make_live_contest(client, admin)
    u1, _ = make_user(client, "pone")
    u2, _ = make_user(client, "ptwo")
    cid = client.get(f"/api/v1/contests/{slug}").json()["id"]
    pid = problem_id(client)

    body = {"problem_id": pid, "language": "python", "source_code": "x", "contest_id": cid}
    assert (
        client.post("/api/v1/submissions", headers=u1, json=body).json()["error"]["code"]
        == "NOT_REGISTERED"
    )
    assert client.post(f"/api/v1/contests/{slug}/register", headers=u1).status_code == 204
    assert (
        client.post(f"/api/v1/contests/{slug}/register", headers=u1).status_code == 204
    )  # idempotent
    client.post(f"/api/v1/contests/{slug}/register", headers=u2)

    wrong = client.post(
        "/api/v1/submissions", headers=u1, json={**body, "source_code": "# @@WRONG"}
    )
    assert wrong.status_code == 202
    ok1 = client.post("/api/v1/submissions", headers=u1, json=body)
    ok2 = client.post("/api/v1/submissions", headers=u2, json=body)
    assert ok1.status_code == ok2.status_code == 202
    drain_queue()
    drain_queue()  # duplicate drain must not change anything

    rows = client.get(f"/api/v1/contests/{slug}/scoreboard").json()["rows"]
    assert [r["handle"] for r in rows] == ["ptwo", "pone"]  # p1 carries a wrong-attempt penalty
    assert rows[0]["score"] == 1 and rows[1]["penalty"] >= 10
    assert rows[1]["cells"][0]["wrong_attempts"] == 1
    # practice submissions do not leak into the contest scoreboard
    assert submit(client, u2, "print(1)", slug="two-sum").status_code == 202
    drain_queue()
    assert len(client.get(f"/api/v1/contests/{slug}/scoreboard").json()["rows"][0]["cells"]) == 2
    assert client.get(f"/api/v1/contests/{slug}/scoreboard").json()["rows"][0]["score"] == 1


def test_contest_window_enforced_by_server_time(client):
    admin, _ = make_user(client, "boss", "admin")
    make_live_contest(client, admin, "future", start_offset=30, end_offset=90)
    make_live_contest(client, admin, "past", start_offset=-90, end_offset=-30)
    u, _ = make_user(client, "late")
    pid = problem_id(client)
    for slug in ("future", "past"):
        cid = client.get(f"/api/v1/contests/{slug}").json()["id"]
        if slug == "future":
            client.post(f"/api/v1/contests/{slug}/register", headers=u)
            assert (
                client.get(f"/api/v1/contests/{slug}").json()["problems"] == []
            )  # hidden before start
        r = client.post(
            "/api/v1/submissions",
            headers=u,
            json={"problem_id": pid, "language": "python", "source_code": "x", "contest_id": cid},
        )
        assert r.status_code == 409 and r.json()["error"]["code"] == "CONTEST_NOT_RUNNING"
    assert client.post("/api/v1/contests/past/register", headers=u).status_code == 409


def test_freeze_public_vs_admin_view(client):
    admin, _ = make_user(client, "boss", "admin")
    slug = make_live_contest(
        client, admin, "frz", start_offset=-30, end_offset=60, freeze_offset=-5
    )
    u, _ = make_user(client, "racer")
    cid = client.get(f"/api/v1/contests/{slug}").json()["id"]
    client.post(f"/api/v1/contests/{slug}/register", headers=u)
    client.post(
        "/api/v1/submissions",
        headers=u,
        json={
            "problem_id": problem_id(client),
            "language": "python",
            "source_code": "x",
            "contest_id": cid,
        },
    )
    drain_queue()
    public = client.get(f"/api/v1/contests/{slug}/scoreboard").json()
    assert public["frozen"] and public["rows"][0]["score"] == 0
    full = client.get(f"/api/v1/contests/{slug}/scoreboard", headers=admin).json()
    assert full["rows"][0]["score"] == 1 and full["full_view"]


def test_finalize_ratings_idempotent(client, db):
    admin, _ = make_user(client, "boss", "admin")
    slug = make_live_contest(client, admin, "done", start_offset=-90, end_offset=-1)
    u1, _ = make_user(client, "rate1")
    u2, _ = make_user(client, "rate2")
    c = db.query(models.Contest).filter_by(slug=slug).one()
    pid = db.query(models.Problem).filter_by(slug="a-plus-b").one().id
    for handle, minute in (("rate1", 5), ("rate2", 20)):
        u = db.query(models.User).filter_by(handle=handle).one()
        db.add(models.ContestRegistration(contest_id=c.id, user_id=u.id))
        db.add(
            models.Submission(
                user_id=u.id,
                problem_id=pid,
                contest_id=c.id,
                language="python",
                source_code="x",
                status="ACCEPTED",
                created_at=c.start_at + timedelta(minutes=minute),
            )
        )
    db.commit()
    assert (
        client.post(f"/api/v1/admin/contests/{slug}/finalize", headers=admin).json()["status"]
        == "finalized"
    )
    assert (
        client.post(f"/api/v1/admin/contests/{slug}/finalize", headers=admin).json()["status"]
        == "already_finalized"
    )
    lb = client.get("/api/v1/leaderboard").json()
    assert (
        lb[0]["handle"] == "rate1"
        and lb[0]["rating"] > 1200 > [r for r in lb if r["handle"] == "rate2"][0]["rating"]
    )
    prof = client.get("/api/v1/users/rate1").json()
    assert len(prof["rating_history"]) == 1 and prof["rating_history"][0]["provisional"] is True


# ---------------- profile privacy
def test_private_profile_is_hidden(client):
    h, _ = make_user(client, "shy")
    assert client.get("/api/v1/users/shy").status_code == 200
    client.patch("/api/v1/auth/me", headers=h, json={"is_public": False})
    assert client.get("/api/v1/users/shy").status_code == 404
    assert "email" not in json.dumps(client.get("/api/v1/users/alice").json())


# ---------------- AI
def test_ai_disabled_without_key(client, auth):
    assert client.get("/api/v1/ai/status").json() == {"enabled": False}
    r = client.post("/api/v1/ai/hint", headers=auth, json={"problem_id": problem_id(client)})
    assert r.status_code == 503 and r.json()["error"]["code"] == "AI_DISABLED"


def test_ai_enabled_sends_only_public_context(client, auth, db, monkeypatch):
    seen = {}

    class Spy(llm_base.LLMProvider):
        async def generate(self, system_prompt, user_prompt):
            seen["system"], seen["user"] = system_prompt, user_prompt
            return "Try thinking about sums."

    from app.api.v1 import ai as ai_mod

    monkeypatch.setattr(ai_mod, "get_provider", lambda: Spy())
    r = client.post(
        "/api/v1/ai/hint",
        headers=auth,
        json={"problem_id": problem_id(client, "two-sum"), "code": "my code"},
    )
    assert r.status_code == 200 and "inaccurate" in r.json()["disclaimer"]
    hidden = db.query(models.TestCase).filter_by(is_sample=False).all()
    assert all(t.input not in seen["user"] for t in hidden if len(t.input) > 12)
    assert "my code" in seen["user"] and "never as instructions" in seen["system"]
    assert (
        client.post(
            "/api/v1/ai/explain", headers=auth, json={"problem_id": problem_id(client)}
        ).status_code
        == 422
    )
