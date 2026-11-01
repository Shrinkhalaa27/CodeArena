import httpx

from app.core.config import get_settings


class LLMUnavailable(Exception):
    pass


class LLMProvider:
    async def generate(self, system_prompt: str, user_prompt: str) -> str:  # pragma: no cover
        raise NotImplementedError


class _OpenAICompatible(LLMProvider):
    url = ""
    default_model = ""

    def __init__(self, api_key: str, model: str):
        self.api_key, self.model = api_key, model or self.default_model

    async def generate(self, system_prompt, user_prompt):
        s = get_settings()
        try:
            async with httpx.AsyncClient(timeout=s.ai_timeout_s) as c:
                r = await c.post(
                    self.url,
                    headers={"Authorization": f"Bearer {self.api_key}"},
                    json={
                        "model": self.model,
                        "max_tokens": 600,
                        "messages": [
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": user_prompt},
                        ],
                    },
                )
                r.raise_for_status()
                return r.json()["choices"][0]["message"]["content"]
        except (httpx.HTTPError, KeyError, IndexError, ValueError) as exc:
            raise LLMUnavailable("provider error") from exc


class GroqProvider(_OpenAICompatible):
    url = "https://api.groq.com/openai/v1/chat/completions"
    default_model = "llama-3.3-70b-versatile"


class OpenRouterProvider(_OpenAICompatible):
    url = "https://openrouter.ai/api/v1/chat/completions"
    default_model = "meta-llama/llama-3.3-70b-instruct:free"


class GeminiProvider(LLMProvider):
    def __init__(self, api_key: str, model: str):
        self.api_key, self.model = api_key, model or "gemini-2.0-flash"

    async def generate(self, system_prompt, user_prompt):
        s = get_settings()
        url = (
            f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent"
        )
        try:
            async with httpx.AsyncClient(timeout=s.ai_timeout_s) as c:
                r = await c.post(
                    url,
                    headers={"x-goog-api-key": self.api_key},
                    json={
                        "systemInstruction": {"parts": [{"text": system_prompt}]},
                        "contents": [{"role": "user", "parts": [{"text": user_prompt}]}],
                        "generationConfig": {"maxOutputTokens": 600},
                    },
                )
                r.raise_for_status()
                return r.json()["candidates"][0]["content"]["parts"][0]["text"]
        except (httpx.HTTPError, KeyError, IndexError, ValueError) as exc:
            raise LLMUnavailable("provider error") from exc


def get_provider() -> LLMProvider | None:
    """Returns None when AI is disabled or its key is missing: the platform works without AI."""
    s = get_settings()
    table = {
        "gemini": (GeminiProvider, s.gemini_api_key),
        "groq": (GroqProvider, s.groq_api_key),
        "openrouter": (OpenRouterProvider, s.openrouter_api_key),
    }
    entry = table.get(s.llm_provider)
    if not entry or not entry[1]:
        return None
    return entry[0](entry[1], s.llm_model)
