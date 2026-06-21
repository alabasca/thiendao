"""
Cửa Hàng Ý Cảnh — Mua Đá Ngộ Đạo và Đá Reset Skill Tree.
Dùng linh thạch. Giới hạn mua theo ngày (reset 00:00).
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone, timedelta

import discord

from utils.config import (
    DA_NGO_DAO_ID, DA_NGO_DAO_GIA, DA_NGO_DAO_DAILY_LIMIT,
    DA_RESET_SKILL_TREE_ID, DA_RESET_SKILL_TREE_GIA, DA_RESET_SKILL_TREE_DAILY_LIMIT,
    fmt,
)
from utils.embeds import e_loi, e_ok, safe_followup

log = logging.getLogger("cua_hang_y_canh")

_DAILY_KEY = "_daily_shop"

SHOP_ITEMS = [
    {
        "id": DA_NGO_DAO_ID,
        "ten": "Đá Ngộ Đạo",
        "emoji": "💎",
        "mo_ta": "Dùng để nâng cấp nodes trong Ý Cảnh (100 Đá = 1 điểm Ý Cảnh)",
        "gia": DA_NGO_DAO_GIA,
        "daily_limit": DA_NGO_DAO_DAILY_LIMIT,
    },
    {
        "id": DA_RESET_SKILL_TREE_ID,
        "ten": "Đá Reset Skill Tree",
        "emoji": "🔄",
        "mo_ta": "Reset toàn bộ Ý Cảnh về Level 0, hoàn điểm",
        "gia": DA_RESET_SKILL_TREE_GIA,
        "daily_limit": DA_RESET_SKILL_TREE_DAILY_LIMIT,
    },
]


def _today_str() -> str:
    """Trả về ngày hôm nay theo múi giờ VN (UTC+7)."""
    return (datetime.now(timezone(timedelta(hours=7)))).strftime("%Y-%m-%d")


def _get_daily_shop(ts: dict) -> dict:
    """Lấy dict daily shop từ nguyen_lieu, reset nếu sang ngày mới."""
    nl = ts.get("nguyen_lieu", {}) if isinstance(ts.get("nguyen_lieu"), dict) else {}
    raw = nl.get(_DAILY_KEY)
    if not raw:
        return {}
    try:
        data = json.loads(raw) if isinstance(raw, str) else raw
    except Exception:
        return {}
    today = _today_str()
    if data.get("date") != today:
        return {}
    return data.get("purchases", {})


def _get_daily_remaining(ts: dict, item_id: str, daily_limit: int) -> int:
    """Số lượng còn lại có thể mua hôm nay."""
    purchases = _get_daily_shop(ts)
    bought = purchases.get(item_id, 0)
    return max(0, daily_limit - bought)


def _embed_shop(ts: dict) -> discord.Embed:
    lt = ts.get("linh_thach", 0)
    nl = ts.get("nguyen_lieu", {}) if isinstance(ts.get("nguyen_lieu"), dict) else {}
    purchases = _get_daily_shop(ts)
    today = _today_str()
    embed = discord.Embed(
        title="🏪 CỬA HÀNG Ý CẢNH",
        description=(
            f"Linh thạch hiện có: **{fmt(lt)}** 💎\n"
            f"📅 Giới hạn mua hàng ngày — reset tự động lúc **00:00**"
        ),
        color=0x1ABC9C,
    )
    for item in SHOP_ITEMS:
        so_huu = nl.get(item["id"], 0)
        bought_today = purchases.get(item["id"], 0)
        remaining = max(0, item["daily_limit"] - bought_today)
        embed.add_field(
            name=f"{item['emoji']} {item['ten']} — {fmt(item['gia'])} LT",
            value=(
                f"{item['mo_ta']}\n"
                f"Đang có: **{so_huu}**\n"
                f"Hôm nay đã mua: **{bought_today}/{item['daily_limit']}** "
                f"(còn **{remaining}**)"
            ),
            inline=False,
        )
    return embed


class CuaHangYCanhView(discord.ui.View):
    def __init__(self, parent, ts: dict, actor_id: int = None):
        super().__init__(timeout=120)
        self.parent = parent
        self.ts = ts
        self.actor_id = actor_id or parent.owner_id
        self._build()

    def _build(self):
        self.clear_items()
        for item in SHOP_ITEMS:
            remaining = _get_daily_remaining(self.ts, item["id"], item["daily_limit"])
            btn = discord.ui.Button(
                label=f"🛒 {item['ten']} — {fmt(item['gia'])} LT",
                style=discord.ButtonStyle.success if remaining > 0 else discord.ButtonStyle.secondary,
                row=0,
                disabled=(remaining <= 0),
            )
            btn.callback = self._make_buy_cb(item)
            self.add_item(btn)

        btn_back = discord.ui.Button(
            label="◀ Quay lại",
            style=discord.ButtonStyle.secondary,
            row=1,
        )
        btn_back.callback = self._on_back
        self.add_item(btn_back)

    def _make_buy_cb(self, item):
        async def cb(inter: discord.Interaction):
            if inter.user.id != self.actor_id:
                return await inter.response.send_message("❌", ephemeral=True)
            remaining = _get_daily_remaining(self.ts, item["id"], item["daily_limit"])
            if remaining <= 0:
                return await inter.response.send_message(
                    f"❌ Đã mua hết giới hạn hôm nay ({item['daily_limit']})! "
                    "Thử lại sau 00:00.", ephemeral=True)
            max_buy = min(remaining, 10)
            view = BuyConfirmView(self, item, self.actor_id, remaining)
            embed = discord.Embed(
                title=f"🛒 Mua {item['ten']}",
                description=(
                    f"**{item['ten']}** — {fmt(item['gia'])} LT mỗi viên\n\n"
                    f"Bạn muốn mua bao nhiêu?\n"
                    f"(Linh thạch: **{fmt(self.ts.get('linh_thach', 0))}** | "
                    f"Còn今日: **{remaining}**)"
                ),
                color=0x1ABC9C,
            )
            await inter.response.send_message(embed=embed, view=view, ephemeral=True)
        return cb

    async def _on_back(self, inter: discord.Interaction):
        from cogs.hoso_utils import _back_to_hoso
        await _back_to_hoso(inter, self.parent)


class BuyConfirmView(discord.ui.View):
    def __init__(self, parent_view, item, actor_id, remaining):
        super().__init__(timeout=30)
        self.parent_view = parent_view
        self.item = item
        self.actor_id = actor_id
        self.remaining = remaining
        if remaining < 10:
            for child in self.children:
                if hasattr(child, 'label') and child.label == "×10":
                    child.disabled = True
                if hasattr(child, 'label') and child.label == "×5" and remaining < 5:
                    child.disabled = True

    @discord.ui.button(label="×1", style=discord.ButtonStyle.success, row=0)
    async def buy_1(self, inter: discord.Interaction, button: discord.ui.Button):
        await self._buy(inter, 1)

    @discord.ui.button(label="×5", style=discord.ButtonStyle.success, row=0)
    async def buy_5(self, inter: discord.Interaction, button: discord.ui.Button):
        await self._buy(inter, 5)

    @discord.ui.button(label="×10", style=discord.ButtonStyle.primary, row=0)
    async def buy_10(self, inter: discord.Interaction, button: discord.ui.Button):
        await self._buy(inter, 10)

    @discord.ui.button(label="❌ Hủy", style=discord.ButtonStyle.secondary, row=1)
    async def cancel(self, inter: discord.Interaction, button: discord.ui.Button):
        for item in self.children:
            item.disabled = True
        self.stop()
        await inter.response.edit_message(
            embed=e_ok("Đã Hủy", "Không mua gì."), view=self)

    async def _buy(self, inter: discord.Interaction, qty: int):
        if inter.user.id != self.actor_id:
            return await inter.response.send_message("❌", ephemeral=True)
        await inter.response.defer(ephemeral=True)

        from utils.database import get_tu_si, update_tu_si
        ts = await get_tu_si(self.actor_id)
        if not ts:
            self.stop()
            return await safe_followup(inter, "❌ Không tìm thấy hồ sơ!", ephemeral=True)

        lt = ts.get("linh_thach", 0)
        total_cost = self.item["gia"] * qty
        if lt < total_cost:
            return await safe_followup(inter,
                f"❌ Không đủ linh thạch! Cần **{fmt(total_cost)}**, có **{fmt(lt)}**.",
                ephemeral=True)

        # Kiểm tra daily limit
        remaining = _get_daily_remaining(ts, self.item["id"], self.item["daily_limit"])
        if remaining <= 0:
            return await safe_followup(inter,
                f"❌ Đã mua hết giới hạn hôm nay ({self.item['daily_limit']})! "
                "Thử lại sau 00:00.", ephemeral=True)
        actual = min(qty, remaining)

        # Cập nhật nguyen_lieu
        nl = ts.get("nguyen_lieu", {}) if isinstance(ts.get("nguyen_lieu"), dict) else {}
        nl[self.item["id"]] = nl.get(self.item["id"], 0) + actual

        # Cập nhật daily shop tracking
        today = _today_str()
        raw_daily = nl.get(_DAILY_KEY)
        try:
            daily_data = json.loads(raw_daily) if isinstance(raw_daily, str) and raw_daily else (raw_daily or {})
        except Exception:
            daily_data = {}
        if daily_data.get("date") != today:
            daily_data = {"date": today, "purchases": {}}
        purchases = daily_data.get("purchases", {})
        purchases[self.item["id"]] = purchases.get(self.item["id"], 0) + actual
        daily_data["purchases"] = purchases
        nl[_DAILY_KEY] = json.dumps(daily_data, ensure_ascii=False)

        await update_tu_si(self.actor_id, linh_thach=lt - total_cost, nguyen_lieu=nl)

        for item in self.children:
            item.disabled = True
        self.stop()

        new_remaining = self.remaining - actual
        msg = f"Đã mua **{actual}× {self.item['emoji']} {self.item['ten']}**\nTrừ **{fmt(total_cost)}** Linh Thạch."
        if actual < qty:
            msg += f"\n⚠️ Hôm nay chỉ còn **{self.remaining}** — mua được **{actual}**."
        msg += f"\nHôm nay còn mua được: **{new_remaining}**"
        await safe_followup(inter, embed=e_ok("Mua Thành Công", msg), ephemeral=True)
