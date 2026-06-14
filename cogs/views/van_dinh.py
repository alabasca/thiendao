"""
van_dinh.py
══════════════════════════════════════════════════════
Đột phá Vấn Đỉnh Tiên Tôn — cảnh giới tột cùng.

Điều kiện: tong_tu_vi >= 999,999,999 (không cần đan)
Tỉ lệ: 1% lần đầu, +1.5% mỗi lần trùng sinh
Kết quả:
  - Thành công / Thất bại đều → Trùng Sinh về Luyện Khí Sơ Kỳ
  - Gửi thông báo toàn server qua world chat
"""
from __future__ import annotations

import random
import logging

import discord

from cogs.views._common import (
    get_tu_si, update_tu_si, safe_followup,
)
from utils.config import VAN_DINH_TUVI_YEU_CAU, fmt
from utils.database import thuc_hien_trung_sinh

log = logging.getLogger("van_dinh")


# ══════════════════════════════════════════════════════
#  BROADCAST HELPER
# ══════════════════════════════════════════════════════

async def _broadcast_van_dinh(bot, noi_dung: str) -> None:
    """Gửi thông báo sự kiện Vấn Đỉnh tới tất cả world chat channels."""
    try:
        from utils.database import get_world_chat_channels, mark_webhook_inactive
        import aiohttp, asyncio

        channels = await get_world_chat_channels()
        targets  = [c for c in channels if c.get("active")]
        if not targets:
            return

        connector = aiohttp.TCPConnector(limit=20)
        async with aiohttp.ClientSession(connector=connector) as session:
            async def _send(c):
                try:
                    payload = {"content": noi_dung, "username": "✨ Thiên Đạo Thông Báo"}
                    thread_id = c.get("thread_id")
                    url = c["webhook_url"]
                    if thread_id:
                        url += f"?thread_id={thread_id}"
                    async with session.post(url, json=payload, timeout=aiohttp.ClientTimeout(total=8)) as resp:
                        return resp.status in (200, 204)
                except Exception:
                    return False

            results = await asyncio.gather(*[_send(c) for c in targets], return_exceptions=True)

        for c, ok in zip(targets, results):
            if ok is False:
                await mark_webhook_inactive(c["guild_id"])
    except Exception as e:
        log.warning(f"VanDinh broadcast failed: {e}")


# ══════════════════════════════════════════════════════
#  EMBEDS
# ══════════════════════════════════════════════════════

def _embed_chuan_bi(ts: dict) -> discord.Embed:
    dao_hieu  = ts.get("dao_hieu", "Vô Danh")
    tong_tv   = ts.get("exp", 0)  # tu vi hiện có của Đăng Tiên Hậu Kỳ
    so_lan    = ts.get("so_lan_trung_sinh", 0)
    ti_le     = ts.get("ti_le_van_dinh", 0.001)
    ti_le_pct = round(ti_le * 100, 2)

    du_tuvi = tong_tv >= VAN_DINH_TUVI_YEU_CAU

    embed = discord.Embed(
        title="✨ VẤN ĐỈNH TIÊN TÔN",
        description=(
            "Con đường cùng tột của tu tiên.\n"
            "Dù thành công hay thất bại, thế giới sẽ **ép buộc trùng sinh**.\n\n"
            "⚠️ **Cảnh báo:** Mọi linh thạch, phường thị, giao dịch sẽ bị xóa!"
        ),
        color=0xFFFFFF,
    )
    embed.add_field(
        name="📊 Điều kiện",
        value=(
            f"{'✅' if du_tuvi else '❌'} Tu vi hiện có: **{fmt(tong_tv)}** / {fmt(VAN_DINH_TUVI_YEU_CAU)}\n"
            f"🎲 Tỉ lệ thành công: **{ti_le_pct}%**\n"
            f"🔄 Số lần đã trùng sinh: **{so_lan}**\n"
            f"📈 Bonus all-stat tích lũy: **+{vd_bonus:.2f}%**"
        ),
        inline=False,
    )
    embed.add_field(
        name="💡 Sau khi trùng sinh",
        value=(
            "• Giữ lại: đạo hiệu, thể chất, sủng thú, linh căn (điểm về 0)\n"
            "• Giữ lại: tài nguyên đột phá thể chất trong kho\n"
            "• Tỉ lệ Vấn Đỉnh lần sau tăng **+1.5%**\n"
            "• Thành công: nhận **+5% all-stat** vĩnh viễn\n"
            "• Thất bại: nhận **+1% all-stat** vĩnh viễn\n"
            "• Tỉ lệ drop linh quả tăng **×1.5**, không giới hạn cảnh giới\n"
            "• Xóa: linh thạch, phiên chợ, giao dịch gần đây"
        ),
        inline=False,
    )
    embed.set_footer(text=f"Đạo hiệu: {dao_hieu}")
    return embed, du_tuvi


# ══════════════════════════════════════════════════════
#  VIEW
# ══════════════════════════════════════════════════════

class VanDinhView(discord.ui.View):
    """View đột phá Vấn Đỉnh Tiên Tôn."""

    def __init__(self, parent, ts: dict, actor_id: int = None):
        super().__init__(timeout=120)
        self.parent   = parent
        self.ts       = ts
        self.actor_id = actor_id or parent.owner_id
        self._build()

    def _build(self):
        self.clear_items()
        tong_tv = self.ts.get("exp", 0)
        du_tuvi = tong_tv >= VAN_DINH_TUVI_YEU_CAU

        btn_dotpha = discord.ui.Button(
            label="✨ Vấn Đỉnh!",
            style=discord.ButtonStyle.danger,
            disabled=not du_tuvi,
            row=0,
        )
        btn_dotpha.callback = self._on_dotpha

        btn_back = discord.ui.Button(
            label="◀ Quay lại",
            style=discord.ButtonStyle.secondary,
            row=0,
        )
        btn_back.callback = self._on_back

        self.add_item(btn_dotpha)
        self.add_item(btn_back)

    async def _on_dotpha(self, inter: discord.Interaction):
        if inter.user.id != self.actor_id:
            return await inter.response.send_message("❌", ephemeral=True)

        try:
            await inter.response.defer(ephemeral=True)
        except Exception:
            log.exception("Lỗi van_dinh")

        # Kiểm tra lại tu vi
        ts_fresh = await get_tu_si(inter.user.id)
        if not ts_fresh:
            return await safe_followup(inter, "❌ Không tìm thấy hồ sơ!", ephemeral=True)

        tong_tv = ts_fresh.get("exp", 0)
        if tong_tv < VAN_DINH_TUVI_YEU_CAU:
            return await safe_followup(
                inter,
                f"❌ Chưa đủ tu vi! Cần **{fmt(VAN_DINH_TUVI_YEU_CAU)}**, hiện có **{fmt(tong_tv)}**.",
                ephemeral=True,
            )

        dao_hieu = ts_fresh.get("dao_hieu", "Vô Danh")
        ti_le    = ts_fresh.get("ti_le_van_dinh", 0.01)

        # Roll
        thanh_cong = random.random() < ti_le

        bonus_stat = 5.0 if thanh_cong else 1.0

        # Thực hiện trùng sinh (dù thành công hay thất bại)
        await thuc_hien_trung_sinh(inter.user.id, bonus_all_stat_pct=bonus_stat)

        # Broadcast toàn server
        if thanh_cong:
            noi_dung = (
                f"✨ **{dao_hieu}** đã đứng trên đỉnh của thế giới, "
                f"thế giới không thể chịu được sức mạnh ấy và bị ép buộc trùng sinh!"
            )
        else:
            noi_dung = (
                f"💀 **{dao_hieu}** đã cố gắng tránh né ý chí của thế giới này "
                f"nhưng vẫn thất bại khi đột phá Vấn Đỉnh — trùng sinh bắt đầu!"
            )

        # Gửi broadcast (fire and forget)
        bot = inter.client
        import asyncio
        asyncio.create_task(_broadcast_van_dinh(bot, noi_dung))

        # Hiển thị kết quả
        if thanh_cong:
            embed = discord.Embed(
                title="✨ ĐỘT PHÁ THÀNH CÔNG!",
                description=(
                    f"**{dao_hieu}** đã chạm tới đỉnh của thế giới!\n\n"
                    "Nhưng thế giới không thể chịu đựng — **Trùng Sinh** đã bắt đầu...\n\n"
                    "Bạn đã được đưa trở về **Luyện Khí Sơ Kỳ**.\n"
                    "Bạn nhận thêm **+5% all-stat** vĩnh viễn.\n"
                    "Tỉ lệ đột phá Vấn Đỉnh lần sau đã tăng thêm **+1.5%**!"
                ),
                color=0xFFD700,
            )
        else:
            embed = discord.Embed(
                title="💀 ĐỘT PHÁ THẤT BẠI",
                description=(
                    f"**{dao_hieu}** không thể vượt qua ý chí thiên đạo...\n\n"
                    "**Trùng Sinh** bắt đầu — trở về **Luyện Khí Sơ Kỳ**.\n"
                    "Bạn nhận thêm **+1% all-stat** vĩnh viễn.\n"
                    "Tỉ lệ đột phá Vấn Đỉnh lần sau đã tăng thêm **+1.5%**!"
                ),
                color=0x888888,
            )

        ts_after = await get_tu_si(inter.user.id)
        if ts_after:
            ti_le_moi = ts_after.get("ti_le_van_dinh", 0.01)
            so_lan_moi = ts_after.get("so_lan_trung_sinh", 0)
            vd_bonus_moi = float(ts_after.get("van_dinh_all_stat_pct", 0.0) or 0.0)
            embed.add_field(
                name="📊 Sau trùng sinh",
                value=(
                    f"🔄 Đã trùng sinh: **{so_lan_moi}** lần\n"
                    f"🎲 Tỉ lệ Vấn Đỉnh tiếp theo: **{round(ti_le_moi*100, 2)}%**\n"
                    f"📈 Bonus all-stat hiện tại: **+{vd_bonus_moi:.2f}%**"
                ),
                inline=False,
            )

        await inter.edit_original_response(embed=embed, view=None)

    async def _on_back(self, inter: discord.Interaction):
        from cogs.hoso_utils import _back_to_hoso
        await _back_to_hoso(inter, self.parent)
