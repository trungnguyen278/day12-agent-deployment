"""
Cost Guard — Bảo vệ budget LLM.

Đếm chi phí ước tính mỗi ngày, block khi vượt budget.
Trong production với nhiều instances: thay bằng Redis-based.
"""
import time
import logging
from fastapi import HTTPException
from app.config import settings

logger = logging.getLogger(__name__)

_daily_cost = 0.0
_cost_reset_day = time.strftime("%Y-%m-%d")

# Giá token (GPT-4o-mini)
PRICE_PER_1K_INPUT = 0.00015
PRICE_PER_1K_OUTPUT = 0.0006


def check_and_record_cost(input_tokens: int, output_tokens: int):
    """
    Kiểm tra budget và ghi nhận chi phí.
    Raise 503 nếu vượt daily_budget_usd.
    """
    global _daily_cost, _cost_reset_day

    today = time.strftime("%Y-%m-%d")
    if today != _cost_reset_day:
        _daily_cost = 0.0
        _cost_reset_day = today

    if _daily_cost >= settings.daily_budget_usd:
        raise HTTPException(503, "Daily budget exhausted. Try tomorrow.")

    cost = (input_tokens / 1000) * PRICE_PER_1K_INPUT + (output_tokens / 1000) * PRICE_PER_1K_OUTPUT
    _daily_cost += cost


def get_daily_cost() -> float:
    return _daily_cost
