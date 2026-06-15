"""
Bảng xếp hạng — BXH View & Builder.
Tách ra khỏi hoso.py để giảm kích thước file.
"""
from __future__ import annotations

import discord

from utils.config import get_cg, get_cg_ten, fmt
from utils.bot_emojis import E_TT_LINH_THACH, E_TU_VI
from utils.embeds import safe_followup
from utils.database import (
    get_bang_xep_hang, get_bxh_tong_tu_vi, get_bxh_linh_thach,
    get_bxh_linh_can, get_bxh_chien_luc,
)

_BXH_MEDALS = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟"]


async def _build_bxh_embed(loai: str) -> tuple:
    """Tạo embed BXH cho loại cho trước. Trả về (embed, BXHView)."""
    if loai == "canh_gioi":
        data  = await get_bang_xep_hang(top=10)
        title = "🏆 Bảng Xếp Hạng — Cảnh Giới"
        color = 0xFFD700
        lines = []
        for i, t in enumerate(data):
            cg = get_cg(t["canh_gioi"])
            lines.append(
                f"{_BXH_MEDALS[i]} {cg['emoji']} **{t['dao_hieu']}**  "
                f"{get_cg_ten(t['canh_gioi'], t['cap_nho'])}  "
                f"{E_TT_LINH_THACH}{fmt(t['linh_thach'])}"
            )

    elif loai == "tong_tu_vi":
        data  = await get_bxh_tong_tu_vi(top=10)
        title = "📿 Bảng Xếp Hạng — Tổng Tu Vi"
        color = 0x9B59B6
        lines = []
        for i, t in enumerate(data):
            cg = get_cg(t["canh_gioi"])
            lines.append(
                f"{_BXH_MEDALS[i]} {cg['emoji']} **{t['dao_hieu']}**  "
                f"{get_cg_ten(t['canh_gioi'], t['cap_nho'])}  "
                f"{E_TU_VI}{fmt(t['tong_tu_vi'])}"
            )

    elif loai == "linh_thach":
        data  = await get_bxh_linh_thach(top=10)
        title = "💎 Bảng Xếp Hạng — Linh Thạch"
        color = 0x1ABC9C
        lines = []
        for i, t in enumerate(data):
            cg = get_cg(t["canh_gioi"])
            lines.append(
                f"{_BXH_MEDALS[i]} {cg['emoji']} **{t['dao_hieu']}**  "
                f"{get_cg_ten(t['canh_gioi'], t['cap_nho'])}  "
                f"{E_TT_LINH_THACH}{fmt(t['linh_thach'])}"
            )

    elif loai == "linh_can":
        data  = await get_bxh_linh_can(top=10)
        title = "🌿 Bảng Xếp Hạng — Tổng Linh Căn"
        color = 0x2ECC71
        lines = []
        for i, t in enumerate(data):
            cg = get_cg(t["canh_gioi"])
            lines.append(
                f"{_BXH_MEDALS[i]} {cg['emoji']} **{t['dao_hieu']}**  "
                f"{get_cg_ten(t['canh_gioi'], t['cap_nho'])}  "
                f"🌿{t['tong_linh_can']} căn"
            )

    elif loai == "chien_luc":
        data  = await get_bxh_chien_luc(top=10)
        title = "🔥 Bảng Xếp Hạng — Chiến Lực"
        color = 0xE74C3C
        lines = []
        for i, t in enumerate(data):
            cg = get_cg(t["canh_gioi"])
            lines.append(
                f"{_BXH_MEDALS[i]} {cg['emoji']} **{t['dao_hieu']}**  "
                f"{get_cg_ten(t['canh_gioi'], t['cap_nho'])}  "
                f"🔥{fmt(t['chien_luc'])}"
            )

    else:
        lines = []
        title = "🏆 Bảng Xếp Hạng"
        color = 0xFFD700

    embed = discord.Embed(
        title=title,
        description="\n".join(lines) if lines else "*(chưa có dữ liệu)*",
        color=color,
    )
    embed.set_footer(text="Top 10 toàn server")
    view = BXHView(active=loai)
    return embed, view


class BXHView(discord.ui.View):
    """View hiển thị 3 nút chuyển tab BXH."""

    def __init__(self, active: str = "canh_gioi"):
        super().__init__(timeout=120)
        self._active = active
        self._add_buttons()

    def _add_buttons(self):
        tabs = [
            ("canh_gioi",  "🏆 Cảnh Giới",  discord.ButtonStyle.primary),
            ("chien_luc",  "🔥 Chiến Lực",  discord.ButtonStyle.secondary),
            ("tong_tu_vi", "📿 Tổng Tu Vi",  discord.ButtonStyle.secondary),
            ("linh_thach", "💎 Linh Thạch",  discord.ButtonStyle.secondary),
            ("linh_can",   "🌿 Linh Căn",    discord.ButtonStyle.secondary),
        ]
        for loai, label, style in tabs:
            btn = discord.ui.Button(
                label=label,
                style=discord.ButtonStyle.success if loai == self._active else style,
                disabled=(loai == self._active),
                custom_id=f"bxh_{loai}",
            )
            btn.callback = self._make_cb(loai)
            self.add_item(btn)

    def _make_cb(self, loai: str):
        async def _cb(inter: discord.Interaction):
            try:
                await inter.response.defer(ephemeral=True)
            except discord.NotFound:
                return
            try:
                embed, view = await _build_bxh_embed(loai)
                await safe_followup(inter, embed=embed, view=view, ephemeral=True)
            except Exception as e:
                await safe_followup(inter, f"❌ Lỗi: {e}", ephemeral=True)
        return _cb
