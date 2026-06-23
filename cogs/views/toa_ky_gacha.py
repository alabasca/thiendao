"""
cogs/views/toa_ky_gacha.py
Gacha Banner System cho Tọa Kỵ
"""
from __future__ import annotations
from typing import Any
import random
import time

from cogs.views._common import *
from utils.config import (
    TOA_KY, TOA_KY_BY_ID, TOA_KY_BY_HE,
    TOA_KY_LEVEL_MULT,
    TOA_KY_BANNER,
    TOA_KY_RARITY_POOL, TOA_KY_DUPE_TINH_HOA,
    fmt,
)
from utils.bot_emojis import E_LINH_THACH
from utils.database import get_tu_si, update_tu_si, add_linh_thach
import json as _json
import logging

log = logging.getLogger("hoso")

HE_TEN = {
    "kim": "Kim", "moc": "Mộc", "thuy": "Thủy", "hoa": "Hỏa",
    "tho": "Thổ", "phong": "Phong", "loi": "Lôi", "quang": "Quang", "am": "Ám"
}


def _parse_toa_ky(ts: dict[str, Any]) -> dict:
    raw = ts.get("toa_ky", {})
    if isinstance(raw, str):
        try: return _json.loads(raw) if raw else {}
        except: return {}
    return raw if isinstance(raw, dict) else {}



BANNER_ROTATION_HOURS = 12

def _get_current_featured(ts):
    featured_id = ts.get('toa_ky_banner_featured_id', -1)
    reset_ts = ts.get('toa_ky_banner_reset_ts', 0) or 0
    now = int(time.time())
    if featured_id < 0 or now - reset_ts >= BANNER_ROTATION_HOURS * 3600:
        # Rotate: pick random mount
        all_ids = list(TOA_KY_BY_ID.keys())
        featured_id = random.choice(all_ids)
        from utils.database import update_tu_si
        update_tu_si(ts['user_id'], toa_ky_banner_featured_id=featured_id, toa_ky_banner_reset_ts=now)
    mount = TOA_KY_BY_ID.get(featured_id)
    time_left = BANNER_ROTATION_HOURS * 3600 - (now - reset_ts)
    return mount, max(0, time_left)

def _roll_rarity(pity: int) -> str:
    """Roll rarity theo pity system."""
    banner = TOA_KY_BANNER
    if pity >= banner["pity_hard"]:
        # Hard pity: guaranteed mount ≥ Linh
        r = random.random() * 100
        if r < 5.0:
            return "Thần"
        elif r < 50.0:
            return "Tiên"
        else:
            return "Linh"

    # Soft pity: từ pity_soft, rate tăng dần
    if pity >= banner["pity_soft"]:
        bonus = (pity - banner["pity_soft"] + 1) * 5.0  # +5% mỗi lần
    else:
        bonus = 0.0

    rates = banner["rates"].copy()
    rates["Linh"] += bonus
    rates["Phàm"] = max(0, rates["Phàm"] - bonus)

    r = random.random() * 100
    cum = 0.0
    for rarity, rate in rates.items():
        cum += rate
        if r < cum:
            return rarity
    return "Phàm"


def _roll_mount(rarity: str) -> dict:
    """Roll mount trong rarity pool."""
    pool = TOA_KY_RARITY_POOL.get(rarity, [])
    if not pool:
        # Fallback to Phàm pool
        pool = TOA_KY_RARITY_POOL.get("Phàm", [1, 2, 7])
    mount_id = random.choice(pool)
    return TOA_KY_BY_ID[mount_id]


def gacha_pull(ts: dict[str, Any], count: int = 1) -> tuple[list[dict], int, dict]:
    """Thực hiện pull gacha. Trả về (results, new_pity, updated_kho)."""
    pity = ts.get("toa_ky_pity", 0) or 0
    kho = _parse_toa_ky(ts)
    results = []

    for _ in range(count):
        pity += 1
        rarity = _roll_rarity(pity)
        mount = _roll_mount(rarity)

        is_duplicate = str(mount["id"]) in kho
        if is_duplicate:
            tinh_hoa = TOA_KY_DUPE_TINH_HOA.get(rarity, 10)
            results.append({
                "mount": mount, "rarity": rarity,
                "duplicate": True, "tinh_hoa": tinh_hoa,
            })
        else:
            # New mount!
            kho[str(mount["id"])] = {"level": 1, "obtained_at": int(time.time())}
            results.append({
                "mount": mount, "rarity": rarity,
                "duplicate": False, "tinh_hoa": 0,
            })
            pity = 0  # Reset pity

    # Boost featured mount
    featured_id = ts.get('toa_ky_banner_featured_id', -1)
    if featured_id >= 0 and featured_id in TOA_KY_BY_ID:
        for r in results:
            if not r['duplicate'] and r['mount']['id'] == featured_id:
                pass  # already got it
            elif not r['duplicate'] and r['rarity'] in ('Linh', 'Tiên', 'Thần'):
                if random.random() < 0.5:
                    r['mount'] = TOA_KY_BY_ID[featured_id]
    return results, pity, kho


def _embed_banner(ts: dict[str, Any]) -> discord.Embed:
    """Embed hiển thị banner gacha."""
    banner = TOA_KY_BANNER
    pity = ts.get("toa_ky_pity", 0) or 0
    lt = ts.get("linh_thach", 0)

    embed = discord.Embed(
        title="🎰 BÌNH DÂN TỌA KỴ",
        description=(
            f"**Chi phí:** {fmt(banner['chi_phi'])} LT/lần  |  "
            f"**10 lần:** {fmt(banner['chi_phi_10'])} LT (-10%)\n\n"
            f"**Linh thạch hiện tại:** {fmt(lt)} {E_LINH_THACH}\n"
            f"**Pity:** {pity}/{banner['pity_hard']}"
        ),
        color=0xFFD700)

    # Danh sách mount có thể nhận
    lines = []
    for rarity in ["Thần", "Tiên", "Linh", "Phàm"]:
        pool = TOA_KY_RARITY_POOL.get(rarity, [])
        if not pool:
            continue
        mount_names = []
        for mid in pool:
            tk = TOA_KY_BY_ID.get(mid)
            if tk:
                mount_names.append(f"{tk['emoji']} {tk['ten']}")
        rate = banner["rates"].get(rarity, 0)
        lines.append(f"**{rarity}** ({rate}%): {', '.join(mount_names)}")

    embed.add_field(name="📊 Tỷ Lệ Nhận", value="\n".join(lines), inline=False)

    # Soft pity info
    if pity >= banner["pity_soft"]:
        bonus = (pity - banner["pity_soft"] + 1) * 5.0
        embed.add_field(
            name="🔥 Soft Pity Active!",
            value=f"Rate mount ≥ Linh tăng **+{bonus:.0f}%** (từ lần {pity})",
            inline=False)

    embed.set_footer(text=f"Hard pity: lần {banner['pity_hard']} guaranteed mount ≥ Linh")
    return embed


RARITY_COLOR = {"Phàm": 0x888888, "Linh": 0x4FC3F7, "Tiên": 0xFFD700, "Thần": 0xFF4444}


class ToaKyGachaView(discord.ui.View):
    """View cho banner gacha."""

    def __init__(self, parent, ts: dict[str, Any], user: discord.User, actor_id: int = None):
        super().__init__(timeout=120)
        self.parent   = parent
        self.ts       = ts
        self.user     = user
        self.actor_id = actor_id or parent.owner_id

        # Nút quay 1 lần
        btn1 = discord.ui.Button(
            label=f"🎰 Quay 1 ({fmt(0)} LT)",
            style=discord.ButtonStyle.success, row=0)
        btn1.callback = self._on_pull_1
        self.add_item(btn1)

        # Nút quay 10 lần
        btn10 = discord.ui.Button(
            label=f"🎰 Quay 10 ({fmt(TOA_KY_BANNER['chi_phi_10'])} LT)",
            style=discord.ButtonStyle.primary, row=0)
        btn10.callback = self._on_pull_10
        self.add_item(btn10)

        # Nút quay lại
        btn_back = discord.ui.Button(
            label="◀ Quay Lại", style=discord.ButtonStyle.secondary, row=1)
        btn_back.callback = self._on_back
        self.add_item(btn_back)

    async def _on_pull_1(self, inter: discord.Interaction):
        if inter.user.id != self.actor_id:
            return await inter.response.send_message("❌", ephemeral=True)
        await self._do_pull(inter, 1)

    async def _on_pull_10(self, inter: discord.Interaction):
        if inter.user.id != self.actor_id:
            return await inter.response.send_message("❌", ephemeral=True)
        await self._do_pull(inter, 10)

    async def _do_pull(self, inter: discord.Interaction, count: int):
        try:
            await inter.response.defer(ephemeral=True)
        except Exception:
            log.exception("Lỗi gacha")

        ts_fresh = await get_tu_si(inter.user.id)
        lt = ts_fresh.get("linh_thach", 0)
        banner = TOA_KY_BANNER
        cost = banner["chi_phi_10"]

        if lt < cost:
            return await safe_followup(inter,
                f"❌ **Linh thạch không đủ!**\nCần: **{fmt(cost)} LT** | Hiện có: **{fmt(lt)} LT**",
                ephemeral=True)

        # Trừ LT
        await add_linh_thach(inter.user.id, -cost)

        # Pull
        results, new_pity, kho = gacha_pull(ts_fresh, count)

        # Cập nhật DB
        total_tinh_hoa = 0
        new_mounts = []
        for r in results:
            if r["duplicate"]:
                total_tinh_hoa += r["tinh_hoa"]
            else:
                new_mounts.append(r["mount"])

        await update_tu_si(inter.user.id,
            toa_ky=kho,
            toa_ky_pity=new_pity)

        # Build embed kết quả
        embed = discord.Embed(
            title=f"🎰 KẾT QUẢ QUAY ×{count}",
            color=0xFFD700)

        result_lines = []
        for i, r in enumerate(results, 1):
            mount = r["mount"]
            rarity = r["rarity"]
            color_tag = {"Phàm":"⬜","Linh":"🟦","Tiên":"🟨","Thần":"🟥"}.get(rarity, "")
            if r["duplicate"]:
                result_lines.append(
                    f"{i}. {mount['emoji']} **{mount['ten']}** {color_tag} [{rarity}]"
                    f" — 🔁 Trùng → +{r['tinh_hoa']} Tinh Hoa")
            else:
                result_lines.append(
                    f"{i}. {mount['emoji']} **{mount['ten']}** {color_tag} [{rarity}]"
                    f" — ✨ **MỚI!**")

        embed.description = "\n".join(result_lines)

        if new_mounts:
            embed.add_field(
                name="🎉 Tọa Kỵ Mới!",
                value="\n".join(f"{m['emoji']} **{m['ten']}** [{HE_TEN[m['he']]}]" for m in new_mounts),
                inline=False)

        if total_tinh_hoa > 0:
            embed.add_field(
                name="♻️ Tinh Hoa Nhận Được",
                value=f"**+{total_tinh_hoa}** Tinh Hoa Tọa Kỵ",
                inline=False)

        # Pity info
        embed.set_footer(text=f"Pity: {new_pity}/{banner['pity_hard']} | LT còn: {fmt(ts_fresh.get('linh_thach', 0) - cost)}")

        await safe_followup(inter, embed=embed, ephemeral=True)

    async def _on_back(self, inter: discord.Interaction):
        if inter.user.id != self.actor_id:
            return await inter.response.send_message("❌", ephemeral=True)
        try:
            from cogs.views.toa_ky import ToaKyView, _embed_toa_ky_list
            ts_fresh = await get_tu_si(inter.user.id)
            embed = _embed_toa_ky_list(ts_fresh, self.user)
            view = ToaKyView(self.parent, ts_fresh, self.user, self.actor_id)
            self.stop()
            await inter.response.edit_message(embed=embed, view=view)
        except Exception as e:
            log.error(f"_on_back gacha user={inter.user.id}: {e}", exc_info=True)
