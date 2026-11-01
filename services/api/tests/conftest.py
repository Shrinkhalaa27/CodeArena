import os

os.environ.update(
    DATABASE_URL="sqlite://",
    QUEUE_BACKEND="memory",
    JUDGE_BACKEND="fake",
    JWT_SECRET="test-secret-test-secret-test-secret-123",
    APP_ENV="test",
)

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app import models  # noqa: E402,F401
from app.db import Base, SessionLocal, engine  # noqa: E402
from app.main import app  # noqa: E402
from app.seed import seed  # noqa: E402
from app.seed_data import PROBLEMS  # noqa: E402
from app.services import queue as queue_mod  # noqa: E402
from app.services.judge import FakeJudge, RunResult  # noqa: E402
from app.services.ratelimit import reset_limiter  # noqa: E402

REFS = {p["slug"]: p["ref"] for p in PROBLEMS}


class RefJudge(FakeJudge):
    """Test double that 'solves' a problem using the trusted reference function, while still
    honouring the FakeJudge marker comments. It never executes submitted source."""

    def __init__(self, ref):
        super().__init__()
        self.ref = ref

    def run(self, *, language, source, stdin, time_limit_ms, memory_limit_kb) -> RunResult:
        r = super().run(
            language=language,
            source=source,
            stdin=stdin,
            time_limit_ms=time_limit_ms,
            memory_limit_kb=memory_limit_kb,
        )
        if "@@" not in source:
            r.stdout = self.ref(stdin)
        return r


@pytest.fixture(autouse=True)
def fresh_db():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    queue_mod.set_queue(queue_mod.MemoryQueue())
    reset_limiter()
    with SessionLocal() as db:
        seed(db)
    yield


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def db():
    with SessionLocal() as session:
        yield session


def make_user(client, handle="alice", role=None):
    r = client.post(
        "/api/v1/auth/register",
        json={"email": f"{handle}@example.com", "handle": handle, "password": "correct-horse-1"},
    )
    assert r.status_code == 201, r.text
    tokens = r.json()
    if role:
        with SessionLocal() as db:
            u = db.query(models.User).filter_by(handle_lower=handle.lower()).one()
            u.role = role
            db.commit()
        tokens = client.post(
            "/api/v1/auth/login",
            json={"email": f"{handle}@example.com", "password": "correct-horse-1"},
        ).json()
    return {"Authorization": f"Bearer {tokens['access_token']}"}, tokens


@pytest.fixture
def auth(client):
    return make_user(client)[0]


def problem_id(client, slug="a-plus-b"):
    return client.get(f"/api/v1/problems/{slug}").json()["id"]


def drain_queue(slug_ref=None, judge=None):
    """Run the worker loop synchronously against the in-memory queue."""
    from app.workers.judge_worker import handle_one

    q = queue_mod.get_queue()
    outcomes = []
    while (job := q.reserve()) is not None:
        with SessionLocal() as db:
            sub = db.get(models.Submission, __import__("uuid").UUID(job))
            slug = db.get(models.Problem, sub.problem_id).slug
        outcomes.append(handle_one(q, judge or RefJudge(REFS[slug]), job, 3))
    return outcomes
