from __future__ import annotations
from typing import Any

from cogs.views._common import *
import re as _re
import logging
from typing import TYPE_CHECKING
log = logging.getLogger("hoso")

PHI_ROI_TONG = 10_000  # Linh thạch phí rời tông

if TYPE_CHECKING:
    from cogs.hoso import HoSoView

class TongMonView(discord.ui.View):
    def __init__(self, parent: "HoSoView", ts: dict[str, Any], actor_id: int = None):
        super().__init__(timeout=120)
        self.parent   = parent
        self.ts       = ts
        self.actor_id = actor_id or parent.owner_id
        for tm in TONG_MON:
            is_current = (tm["id"] == ts["tong_mon"])
            btn = discord.ui.Button(
                label=f"{tm['emoji']} {tm['ten']}",
                style=discord.ButtonStyle.primary if is_current else discord.ButtonStyle.secondary,
                row=0)
            btn.callback = self._make_cb(tm["id"])
            self.add_item(btn)
        back = discord.ui.Button(label="◀ Quay Lại", style=discord.ButtonStyle.danger, row=1)
        back.callback = self._back
        self.add_item(back)

    def _make_cb(self, tm_id: int):
        async def cb(inter: discord.Interaction):
            if inter.user.id != self.actor_id:
                return await inter.response.send_message("❌", ephemeral=True)
            ts = await get_tu_si(inter.user.id)
            if ts["tong_mon"] == tm_id:
                return await inter.response.send_message("Đã ở tông này rồi!", ephemeral=True)

            tm = TONG_MON[tm_id]
            phi = PHI_ROI_TONG if ts["tong_mon"] >= 0 else 0

            # Nếu đang ở tông → cần xác nhận trước
            if phi > 0:
                if ts["linh_thach"] < phi:
                    return await inter.response.send_message(
                        embed=e_loi("❌ Không đủ Linh Thạch",
                            f"Rời tông cũ tốn **{fmt(phi)} {E_LINH_THACH}**.\n"
                            f"Bạn chỉ có **{fmt(ts['linh_thach'])} {E_LINH_THACH}**."),
                        ephemeral=True)

                # Gửi confirm view
                confirm_view = _ConfirmRoiTong(
                    parent=self.parent,
                    ts=ts,
                    tm_id=tm_id,
                    phi=phi,
                    actor_id=self.actor_id)
                old_tm = TONG_MON[ts["tong_mon"]] if 0 <= ts["tong_mon"] < len(TONG_MON) else None
                old_str = f"**{old_tm['emoji']} {old_tm['ten']}**" if old_tm else "tông hiện tại"
                embed = discord.Embed(
                    title="⚠️ Xác Nhận Đổi Tông",
                    description=(
                        f"Bạn muốn rời {old_str} để gia nhập **{tm['emoji']} {tm['ten']}**?\n\n"
                        f"💸 Phí rời tông: **{fmt(phi)} {E_LINH_THACH}**\n"
                        f"✨ Buff mới: **{BUFF_LABELS[tm['buff']]}** ×{tm['buff_val']}\n"
                        f"📖 *{tm.get('mo_ta', '')}*"
                    ),
                    color=0xFEE75C)
                return await inter.response.send_message(
                    embed=embed, view=confirm_view, ephemeral=True)

            # Lần đầu vào tông — không cần confirm
            await _join_tong(inter, self.parent, ts, tm_id, phi, self.actor_id)
        return cb

    async def _back(self, inter: discord.Interaction):
        await _back_to_hoso(inter, self.parent)


class _ConfirmRoiTong(discord.ui.View):
    """View xác nhận rời tông — hiện sau khi bấm tông mới."""
    def __init__(self, parent, ts: dict[str, Any], tm_id: int, phi: int, actor_id: int):
        super().__init__(timeout=60)
        self.parent   = parent
        self.ts       = ts
        self.tm_id    = tm_id
        self.phi      = phi
        self.actor_id = actor_id

        btn_yes = discord.ui.Button(
            label=f"✅ Xác nhận (mất {fmt(phi)} LT)",
            style=discord.ButtonStyle.danger, row=0)
        btn_no  = discord.ui.Button(
            label="❌ Hủy", style=discord.ButtonStyle.secondary, row=0)
        btn_yes.callback = self._on_confirm
        btn_no.callback  = self._on_cancel
        self.add_item(btn_yes)
        self.add_item(btn_no)

    async def _on_confirm(self, inter: discord.Interaction):
        if inter.user.id != self.actor_id:
            return await inter.response.send_message("❌", ephemeral=True)
        ts = await get_tu_si(inter.user.id)
        if ts["linh_thach"] < self.phi:
            return await inter.response.send_message(
                embed=e_loi("❌ Không đủ Linh Thạch",
                    f"Cần **{fmt(self.phi)} {E_LINH_THACH}** nhưng chỉ còn **{fmt(ts['linh_thach'])}**."),
                ephemeral=True)
        await _join_tong(inter, self.parent, ts, self.tm_id, self.phi, self.actor_id)

    async def _on_cancel(self, inter: discord.Interaction):
        await inter.response.edit_message(
            embed=discord.Embed(description="❌ Đã hủy đổi tông.", color=0xED4245),
            view=None)

    async def on_timeout(self):
        pass


async def _join_tong(inter: discord.Interaction, parent, ts: dict[str, Any], tm_id: int, phi: int, actor_id: int):
    """Thực hiện gia nhập tông — dùng chung cho lần đầu và sau confirm."""
    tm = TONG_MON[tm_id]
    # Dùng add_linh_thach(-phi) để atomic, tránh race condition ghi đè LT
    if phi > 0:
        await add_linh_thach(inter.user.id, -phi)
    await update_tu_si(inter.user.id, tong_mon=tm_id)

    phi_str = f"\n💸 Đã trừ **{fmt(phi)} {E_LINH_THACH}** phí rời tông." if phi else ""
    msg = (
        f"**{tm['emoji']} {tm['ten']}** đã chào đón ngươi!\n"
        f"✨ Buff: **{BUFF_LABELS[tm['buff']]}** ×{tm['buff_val']}\n"
        f"📖 *{tm.get('mo_ta', '')}*"
        f"{phi_str}"
    )
    embed = e_ok("🌸 Gia Nhập Tông Môn", msg)

    try:
        await inter.response.edit_message(embed=embed, view=None)
    except Exception:
        try:
            await inter.response.send_message(embed=embed, ephemeral=True)
        except Exception:
            await safe_followup(inter, embed=embed, ephemeral=True)

    if inter.user.id == actor_id and inter.user.id == parent.owner_id:
        await parent._reload()
        parent._rebuild()


# ══════════════════════════════════════════════════════════════
#  BÍ CẢNH VIEWS
# ══════════════════════════════════════════════════════════════
BC_CHON_IMG = "images/chon_bi_canh.png"
