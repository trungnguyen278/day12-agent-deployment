"""Real LLM client — gọi OpenAI Chat Completions API.

Signature giống mock: `ask(question: str) -> str`.
Client khởi tạo lazy để không crash lúc import nếu thiếu key (dev mode).
"""
import logging

from openai import OpenAI, OpenAIError

from app.config import settings

logger = logging.getLogger(__name__)

_client: OpenAI | None = None

SYSTEM_PROMPT = (
    "You are a helpful AI assistant. Answer concisely and accurately. "
    "Respond in the same language as the user's question."
)


def _get_client() -> OpenAI:
    global _client
    if _client is None:
        if not settings.openai_api_key:
            raise RuntimeError(
                "OPENAI_API_KEY is not set. Configure it via environment variable."
            )
        _client = OpenAI(api_key=settings.openai_api_key, timeout=30.0)
    return _client


def ask(question: str) -> str:
    """Send a question to OpenAI and return the assistant's answer."""
    client = _get_client()
    try:
        resp = client.chat.completions.create(
            model=settings.llm_model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": question},
            ],
            max_tokens=500,
            temperature=0.7,
        )
    except OpenAIError as e:
        logger.error(f"OpenAI call failed: {e}")
        raise

    answer = resp.choices[0].message.content or ""
    if resp.usage:
        logger.info(
            '{"event":"llm_usage","prompt_tokens":%d,"completion_tokens":%d,"model":"%s"}'
            % (resp.usage.prompt_tokens, resp.usage.completion_tokens, resp.model)
        )
    return answer
