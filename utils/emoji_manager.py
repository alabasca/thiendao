"""
utils/emoji_manager.py
Cung cấp helper tra cứu emoji theo key stat.
Import get_stat_emoji từ đây thay vì hardcode rải rác.
"""

from __future__ import annotations

from utils.bot_emojis import (
    E_SINH_LUC, E_LINH_LUC, E_CONG_KICH, E_PHONG_NGU, E_LINH_THACH,
    E_HOI_TAM, E_HO_TAM, E_BAO_KICH, E_KHANG_BAO,
)

# ── Bảng tra cứu key → emoji ──────────────────────────────────
_STAT_EMOJI: dict[str, str] = {
    "sinh_luc":  E_SINH_LUC,
    "linh_luc":  E_LINH_LUC,
    "cong_kich": E_CONG_KICH,
    "phong_ngu": E_PHONG_NGU,
    "linh_thach":E_LINH_THACH,
    "hoi_tam":   E_HOI_TAM,
    "ho_tam":    E_HO_TAM,
    "bao_kich":  E_BAO_KICH,
    "khang_bao": E_KHANG_BAO,
}


def get_stat_emoji(key: str) -> str:
    """Trả về chuỗi emoji Discord cho stat *key*.
    Nếu key không tồn tại trả về chuỗi rỗng (không crash)."""
    return _STAT_EMOJI.get(key, "")


async def setup_emojis(bot) -> None:  # noqa: ANN001
    """Hook gọi khi bot ready — hiện tại không cần fetch gì thêm
    vì emoji đã hardcode bằng ID cố định trong bot_emojis.py."""
    pass
