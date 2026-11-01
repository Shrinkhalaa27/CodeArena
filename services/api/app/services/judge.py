"""Judge adapters. Untrusted code is NEVER executed in this process: the Judge0 adapter talks
to an isolated, private Judge0 CE service. The FakeJudge exists only for tests/dev demos and
refuses to be used in production (see Settings.validate_for_runtime)."""

import base64
import time
from dataclasses import dataclass
from typing import Protocol

import httpx

from app.core.config import get_settings
from app.models import Verdict

LANGUAGE_IDS = {"python": 71, "cpp": 54, "java": 62, "javascript": 63}
SUPPORTED_LANGUAGES = tuple(LANGUAGE_IDS)

STARTER_TEMPLATES = {
    "python": "import sys\n\n\ndef main():\n    data = sys.stdin.read().split()\n    # TODO\n    print()\n\n\nmain()\n",
    "cpp": "#include <bits/stdc++.h>\nusing namespace std;\n\nint main() {\n    ios::sync_with_stdio(false);\n    cin.tie(nullptr);\n    // TODO\n    return 0;\n}\n",
    "java": "import java.util.*;\n\npublic class Main {\n    public static void main(String[] args) {\n        Scanner sc = new Scanner(System.in);\n        // TODO\n    }\n}\n",
    "javascript": "const lines = require('fs').readFileSync(0, 'utf8').split('\\n');\n// TODO\nconsole.log();\n",
}


class JudgeInfraError(Exception):
    """Transient infrastructure failure (network, judge down). Retryable, never the user's fault."""


@dataclass
class RunResult:
    status: Verdict  # ACCEPTED here only means "ran to completion"; callers compare output
    stdout: str = ""
    compile_output: str = ""
    runtime_ms: int | None = None
    memory_kb: int | None = None


class Judge(Protocol):
    def run(
        self, *, language: str, source: str, stdin: str, time_limit_ms: int, memory_limit_kb: int
    ) -> RunResult: ...


# Judge0 status ids: https://ce.judge0.com
def map_judge0_status(status_id: int, memory_kb: int | None, memory_limit_kb: int) -> Verdict:
    if status_id in (1, 2):
        raise JudgeInfraError("still processing")
    if status_id == 3:
        return Verdict.ACCEPTED
    if status_id == 4:
        return Verdict.ACCEPTED  # judge0 flags WA only if expected_output was supplied
    if status_id == 5:
        return Verdict.TIME_LIMIT_EXCEEDED
    if status_id == 6:
        return Verdict.COMPILATION_ERROR
    if 7 <= status_id <= 12:
        if memory_kb is not None and memory_kb >= memory_limit_kb:
            return Verdict.MEMORY_LIMIT_EXCEEDED
        return Verdict.RUNTIME_ERROR
    if status_id in (13, 14):
        raise JudgeInfraError(f"judge internal error (status {status_id})")
    raise JudgeInfraError(f"unknown judge status {status_id}")


def _b64(s: str) -> str:
    return base64.b64encode(s.encode()).decode()


def _unb64(s: str | None) -> str:
    return base64.b64decode(s).decode(errors="replace") if s else ""


class Judge0Client:
    def __init__(self, base_url: str | None = None, token: str | None = None, client=None):
        s = get_settings()
        self.base_url = (base_url or s.judge0_base_url).rstrip("/")
        headers = (
            {"X-Auth-Token": token or s.judge0_auth_token} if (token or s.judge0_auth_token) else {}
        )
        self.client = client or httpx.Client(base_url=self.base_url, headers=headers, timeout=10.0)
        self.poll_timeout = s.judge_poll_timeout_s

    def run(self, *, language, source, stdin, time_limit_ms, memory_limit_kb) -> RunResult:
        lang_id = LANGUAGE_IDS.get(language)
        if lang_id is None:
            raise ValueError("unsupported language")
        body = {
            "language_id": lang_id,
            "source_code": _b64(source),
            "stdin": _b64(stdin),
            "cpu_time_limit": time_limit_ms / 1000,
            "wall_time_limit": max(time_limit_ms / 1000 * 3, 5),
            "memory_limit": memory_limit_kb,
        }
        try:
            r = self.client.post(
                "/submissions", params={"base64_encoded": "true", "wait": "false"}, json=body
            )
            r.raise_for_status()
            token = r.json()["token"]
            deadline = time.monotonic() + self.poll_timeout
            delay = 0.2
            while True:
                g = self.client.get(
                    f"/submissions/{token}",
                    params={
                        "base64_encoded": "true",
                        "fields": "status,stdout,stderr,compile_output,time,memory",
                    },
                )
                g.raise_for_status()
                data = g.json()
                if data["status"]["id"] not in (1, 2):
                    break
                if time.monotonic() > deadline:
                    raise JudgeInfraError("judge poll timeout")
                time.sleep(delay)
                delay = min(delay * 1.5, 1.5)
        except (httpx.HTTPError, KeyError, ValueError) as exc:
            raise JudgeInfraError(str(exc)) from exc

        memory = data.get("memory")
        status = map_judge0_status(data["status"]["id"], memory, memory_limit_kb)
        t = data.get("time")
        return RunResult(
            status=status,
            stdout=_unb64(data.get("stdout")),
            compile_output=(_unb64(data.get("compile_output")) or _unb64(data.get("stderr")))[
                :4000
            ],
            runtime_ms=int(float(t) * 1000) if t is not None else None,
            memory_kb=memory,
        )

    def healthy(self) -> bool:
        try:
            return self.client.get("/system_info", timeout=3.0).status_code == 200
        except httpx.HTTPError:
            return False


class FakeJudge:
    """Deterministic stand-in for tests and UI demos when Judge0 is not running.
    It does NOT execute source code. It recognises a few marker comments so every verdict
    path can be exercised, and otherwise 'solves' problems by echoing a lookup table."""

    def __init__(self, answers: dict[str, str] | None = None):
        self.answers = answers or {}
        self.calls = 0

    def run(self, *, language, source, stdin, time_limit_ms, memory_limit_kb) -> RunResult:
        self.calls += 1
        if "@@COMPILE_ERROR" in source:
            return RunResult(Verdict.COMPILATION_ERROR, compile_output="fake: compilation failed")
        if "@@RUNTIME_ERROR" in source:
            return RunResult(Verdict.RUNTIME_ERROR, runtime_ms=5, memory_kb=1000)
        if "@@TLE" in source:
            return RunResult(Verdict.TIME_LIMIT_EXCEEDED, runtime_ms=time_limit_ms)
        if "@@INFRA" in source:
            raise JudgeInfraError("fake infra failure")
        if "@@WRONG" in source:
            return RunResult(Verdict.ACCEPTED, stdout="wrong", runtime_ms=7, memory_kb=1200)
        if "@@ECHO" in source:
            return RunResult(Verdict.ACCEPTED, stdout=stdin, runtime_ms=3, memory_kb=900)
        return RunResult(
            Verdict.ACCEPTED, stdout=self.answers.get(stdin, ""), runtime_ms=4, memory_kb=1000
        )


def get_judge() -> Judge:
    s = get_settings()
    if s.judge_backend == "fake":
        return FakeJudge()
    return Judge0Client()
