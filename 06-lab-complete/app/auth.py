"""API Key Authentication module."""
from fastapi import HTTPException, Security
from fastapi.security.api_key import APIKeyHeader
from app.config import settings

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


def verify_api_key(api_key: str = Security(api_key_header)) -> str:
    """
    Dependency: kiểm tra API key từ header X-API-Key.
    Return api_key nếu hợp lệ, raise 401 nếu không.
    """
    if not api_key or api_key != settings.agent_api_key:
        raise HTTPException(
            status_code=401,
            detail="Invalid or missing API key. Include header: X-API-Key: <key>",
        )
    return api_key
