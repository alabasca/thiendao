"""
Ý Cảnh (意境) — Skill Tree System
Mở sau lần trùng sinh đầu tiên.
Dùng Đá Ngộ Đạo để nâng cấp node, mỗi node tốn 1 điểm skill.
Điểm skill tối đa = 5 + (số lần trùng sinh × 3).
"""
from __future__ import annotations

import json
import logging
from typing import Any

import discord

from utils.config import (
    Y_CANH_NHANH, Y_CANH_ALL_NODES, Y_CANH_BY_NHANH,
    y_canh_diem_toi_da, DA_NGO_DAO_ID, fmt,
)
from utils.embeds import e_loi, e_ok, e_warn, safe_followup

log = logging.getLogger("y_canh")

EFFECT_LABELS = {
    "at_pct":      "ATK",
    "def_pct":     "DEF",
    "hp_pct":      "HP",
    "exp_pct":     "EXP",
    "drop_rate":   "Tỉ lệ rơi",
    "the_luc_hoi": "Hồi thể lực nhanh",
    "lt_nhan":     "Linh thạch nhận",
    "hoi_tam":     "Hội Tâm",
    "ho_tam":      "Hộ Tâm",
    "bao_kich":    "Bạo Kích",
    "khang_bao":   "Kháng Bạo",
    "linh_luc_pct":"Linh Lực",
    "crit_dmg":    "Sát thương Bạo Kích",
    "hut_mau_crit":"Hút máu crit",
    "cd_giam":     "Giảm CD",
    "hoi_sinh_luc":"Hồi Sinh Lực",
}


def _get_y_canh(ts: dict) -> dict:
    raw = ts.get("y_canh", {})
    if isinstance(raw, dict):
        return raw
    try:
        return json.loads(raw) if raw else {}
    except Exception:
        return {}


def _tinh_diem_da_dung(y_canh: dict) -> int:
    return sum(y_canh.values())


def _tinh_effect(y_canh: dict) -> dict:
    """Tính tổng effect từ tất cả nodes đã unlock."""
    eff = {}
    for node_id, level in y_canh.items():
        if level <= 0:
            continue
        nd = Y_CANH_ALL_NODES.get(node_id)
        if not nd:
            continue
        base = nd["effect"]
        for k, v in base.items():
            eff[k] = eff.get(k, 0) + v * level
    return eff


def _embed_y_canh(ts: dict) -> discord.Embed:
    y_canh = _get_y_canh(ts)
    so_lan_ts = ts.get("so_lan_trung_sinh", 0)
    da_dung = _tinh_diem_da_dung(y_canh)
    toi_da = y_canh_diem_toi_da(so_lan_ts)
    con_lai = max(0, toi_da - da_dung)
    da_ngo_dao = ts.get("nguyen_lieu", {}).get(DA_NGO_DAO_ID, 0) if isinstance(ts.get("nguyen_lieu"), dict) else 0

    embed = discord.Embed(
        title="🧠 Ý CẢNH — Giới Thuật",
        description=(
            f"Điểm skill: **{da_dung}/{toi_da}** (còn **{con_lai}**)\n"
            f"Đá Ngộ Đạo: **{da_ngo_dao}** viên\n\n"
            "Chọn nhánh bên dưới để xem và nâng cấp nodes."
        ),
        color=0x9B59B6,
    )

    for nhanh in Y_CANH_NHANH:
        lines = []
        for nd in nhanh["nodes"]:
            lv = y_canh.get(nd["id"], 0)
            max_lv = nd["max_lv"]
            cost = nd["cost"][lv] if lv < len(nd["cost"]) else "MAX"
            eff_parts = []
            for k, v in nd["effect"].items():
                label = EFFECT_LABELS.get(k, k)
                val = v * max(lv, 1)
                if k in ("exp_pct", "drop_rate", "at_pct", "def_pct", "hp_pct",
                         "khang_bao", "linh_luc_pct", "crit_dmg",
                         "hut_mau_crit", "lt_nhan", "bao_kich"):
                    eff_parts.append(f"{label}: +{val}%")
                elif k == "the_luc_hoi":
                    eff_parts.append(f"{label}: -{val}s/điểm")
                elif k == "cd_giam":
                    eff_parts.append(f"{label}: -{val}s")
                else:
                    eff_parts.append(f"{label}: +{val}")
            eff_str = ", ".join(eff_parts)
            status = f"**Lv.{lv}/{max_lv}**" if lv < max_lv else f"**MAX**"
            lines.append(f"{status} {nd['ten']} — {eff_str} *(cost: {cost})*")
        embed.add_field(
            name=nhanh['ten'],
            value="\n".join(lines),
            inline=False,
        )

    return embed


class YCanhView(discord.ui.View):
    def __init__(self, parent, ts: dict, actor_id: int = None):
        super().__init__(timeout=120)
        self.parent = parent
        self.ts = ts
        self.actor_id = actor_id or parent.owner_id
        self._build()

    def _build(self):
        self.clear_items()
        for nhanh in Y_CANH_NHANH:
            btn = discord.ui.Button(
                label=f"{nhanh['emoji']} {nhanh['ten']}",
                style=discord.ButtonStyle.secondary,
                row=0,
            )
            btn.callback = self._make_nhanh_cb(nhanh)
            self.add_item(btn)

        btn_reset = discord.ui.Button(
            label="🔄 Reset Skill Tree",
            style=discord.ButtonStyle.danger,
            row=1,
        )
        btn_reset.callback = self._on_reset
        self.add_item(btn_reset)

        btn_back = discord.ui.Button(
            label="◀ Quay lại",
            style=discord.ButtonStyle.secondary,
            row=1,
        )
        btn_back.callback = self._on_back
        self.add_item(btn_back)

    def _make_nhanh_cb(self, nhanh):
        async def cb(inter: discord.Interaction):
            if inter.user.id != self.actor_id:
                return await inter.response.send_message("❌", ephemeral=True)
            await inter.response.defer(ephemeral=True)
            ts = await self._reload()
            view = YCanhNhanhView(self, ts, nhanh, self.actor_id)
            embed = self._embed_nhanh(ts, nhanh)
            await safe_followup(inter, embed=embed, view=view, ephemeral=True)
        return cb

    def _embed_nhanh(self, ts, nhanh):
        y_canh = _get_y_canh(ts)
        so_lan_ts = ts.get("so_lan_trung_sinh", 0)
        da_dung = _tinh_diem_da_dung(y_canh)
        toi_da = y_canh_diem_toi_da(so_lan_ts)
        con_lai = max(0, toi_da - da_dung)
        da_ngo_dao = ts.get("nguyen_lieu", {}).get(DA_NGO_DAO_ID, 0) if isinstance(ts.get("nguyen_lieu"), dict) else 0

        embed = discord.Embed(
            title=f"{nhanh['emoji']} {nhanh['ten']}",
            description=(
                f"{nhanh['mo_ta']}\n\n"
                f"Điểm: **{da_dung}/{toi_da}** (còn **{con_lai}**) | "
                f"Đá Ngộ Đạo: **{da_ngo_dao}**"
            ),
            color=0x9B59B6,
        )

        for nd in nhanh["nodes"]:
            lv = y_canh.get(nd["id"], 0)
            max_lv = nd["max_lv"]
            if lv < max_lv:
                cost = nd["cost"][lv]
                status = f"**Lv.{lv}/{max_lv}** — Chi phí: **{cost}** đá"
            else:
                status = "**MAX**"
            eff_parts = []
            for k, v in nd["effect"].items():
                label = EFFECT_LABELS.get(k, k)
                val = v * max(lv, 1)
                if k in ("exp_pct", "drop_rate", "at_pct", "def_pct", "hp_pct",
                         "khang_bao", "linh_luc_pct", "crit_dmg",
                         "hut_mau_crit", "lt_nhan"):
                    eff_parts.append(f"{label}: +{val}%")
                elif k == "the_luc_hoi":
                    eff_parts.append(f"{label}: -{val}s/điểm")
                elif k == "bao_kich":
                    eff_parts.append(f"{label}: +{val}%")
                elif k == "cd_giam":
                    eff_parts.append(f"{label}: -{val}s")
                else:
                    eff_parts.append(f"{label}: +{val}")
            embed.add_field(
                name=f"{nd['ten']}",
                value=f"{status}\n{', '.join(eff_parts)}",
                inline=False,
            )

        return embed

    async def _reload(self):
        from utils.database import get_tu_si
        fresh = await get_tu_si(self.actor_id)
        if fresh:
            self.ts = fresh
        return fresh or self.ts

    async def _on_reset(self, inter: discord.Interaction):
        if inter.user.id != self.actor_id:
            return await inter.response.send_message("❌", ephemeral=True)
        await inter.response.defer(ephemeral=True)
        ts = await self._reload()
        y_canh = _get_y_canh(ts)
        if not y_canh:
            return await safe_followup(inter, "⚠️ Skill tree đã trống!", ephemeral=True)

        da_ngo_dao = ts.get("nguyen_lieu", {}).get(DA_NGO_DAO_ID, 0) if isinstance(ts.get("nguyen_lieu"), dict) else 0
        if da_ngo_dao < 1:
            return await safe_followup(inter, "❌ Cần **1 Đá Reset Skill Tree** để reset!", ephemeral=True)

        view = ConfirmResetView(self, ts, self.actor_id)
        embed = discord.Embed(
            title="⚠️ Reset Skill Tree",
            description=(
                "Bạn muốn reset toàn bộ Ý Cảnh?\n\n"
                "• Tất cả nodes sẽ về **Level 0**\n"
                "• Điểm skill sẽ được hoàn lại\n"
                "• Cần **1 Đá Reset Skill Tree**"
            ),
            color=0xFEE75C,
        )
        await safe_followup(inter, embed=embed, view=view, ephemeral=True)

    async def _on_back(self, inter: discord.Interaction):
        from cogs.hoso_utils import _back_to_hoso
        await _back_to_hoso(inter, self.parent)


class YCanhNhanhView(discord.ui.View):
    """View chi tiết 1 nhánh Ý Cảnh — cho phép nâng cấp từng node."""
    def __init__(self, parent_view, ts, nhanh, actor_id):
        super().__init__(timeout=120)
        self.parent_view = parent_view
        self.ts = ts
        self.nhanh = nhanh
        self.actor_id = actor_id
        self._build()

    def _build(self):
        self.clear_items()
        y_canh = _get_y_canh(self.ts)
        for nd in self.nhanh["nodes"]:
            lv = y_canh.get(nd["id"], 0)
            if lv < nd["max_lv"]:
                btn = discord.ui.Button(
                    label=f"⬆ {nd['ten']}",
                    style=discord.ButtonStyle.success,
                    row=0,
                )
                btn.callback = self._make_upgrade_cb(nd)
                self.add_item(btn)

        btn_back = discord.ui.Button(
            label="◀ Quay lại",
            style=discord.ButtonStyle.secondary,
            row=2,
        )
        btn_back.callback = self._on_back
        self.add_item(btn_back)

    def _make_upgrade_cb(self, nd):
        async def cb(inter: discord.Interaction):
            if inter.user.id != self.actor_id:
                return await inter.response.send_message("❌", ephemeral=True)
            await inter.response.defer(ephemeral=True)

            ts = await self.parent_view._reload()
            y_canh = _get_y_canh(ts)
            current_lv = y_canh.get(nd["id"], 0)

            if current_lv >= nd["max_lv"]:
                return await safe_followup(inter, "⚠️ Đã max level!", ephemeral=True)

            cost = nd["cost"][current_lv]
            so_lan_ts = ts.get("so_lan_trung_sinh", 0)
            da_dung = _tinh_diem_da_dung(y_canh)
            toi_da = y_canh_diem_toi_da(so_lan_ts)
            con_lai = toi_da - da_dung

            if con_lai < 1:
                return await safe_followup(inter, "❌ Hết điểm skill! Trùng sinh để nhận thêm điểm.", ephemeral=True)

            da_ngo_dao = ts.get("nguyen_lieu", {}).get(DA_NGO_DAO_ID, 0) if isinstance(ts.get("nguyen_lieu"), dict) else 0
            if da_ngo_dao < cost:
                return await safe_followup(inter, f"❌ Cần **{cost}** Đá Ngộ Đạo (hiện có **{da_ngo_dao}**).", ephemeral=True)

            # Upgrade
            y_canh[nd["id"]] = current_lv + 1
            new_nl = ts.get("nguyen_lieu", {}).copy() if isinstance(ts.get("nguyen_lieu"), dict) else {}
            new_nl[DA_NGO_DAO_ID] = new_nl.get(DA_NGO_DAO_ID, 0) - cost
            if new_nl[DA_NGO_DAO_ID] <= 0:
                new_nl.pop(DA_NGO_DAO_ID, None)

            from utils.database import update_tu_si
            await update_tu_si(self.actor_id, y_canh=json.dumps(y_canh), nguyen_lieu=new_nl)

            ts = await self.parent_view._reload()
            embed = self.parent_view._embed_nhanh(ts, self.nhanh)
            view = YCanhNhanhView(self.parent_view, ts, self.nhanh, self.actor_id)
            await safe_followup(inter,
                embed=e_ok("Nâng Cấp", f"✅ **{nd['ten']}** đã lên **Lv.{current_lv + 1}**!"),
                ephemeral=True)
        return cb

    async def _on_back(self, inter: discord.Interaction):
        if inter.user.id != self.actor_id:
            return await inter.response.send_message("❌", ephemeral=True)
        await inter.response.defer(ephemeral=True)
        ts = await self.parent_view._reload()
        y_canh = _get_y_canh(ts)
        so_lan_ts = ts.get("so_lan_trung_sinh", 0)
        da_dung = _tinh_diem_da_dung(y_canh)
        toi_da = y_canh_diem_toi_da(so_lan_ts)
        con_lai = max(0, toi_da - da_dung)
        da_ngo_dao = ts.get("nguyen_lieu", {}).get(DA_NGO_DAO_ID, 0) if isinstance(ts.get("nguyen_lieu"), dict) else 0

        embed = discord.Embed(
            title="🧠 Ý CẢNH — Giới Thuật",
            description=(
                f"Điểm skill: **{da_dung}/{toi_da}** (còn **{con_lai}**)\n"
                f"Đá Ngộ Đạo: **{da_ngo_dao}** viên\n\n"
                "Chọn nhánh bên dưới để xem và nâng cấp nodes."
            ),
            color=0x9B59B6,
        )
        view = YCanhView(self.parent_view, ts, self.actor_id)
        await safe_followup(inter, embed=embed, view=view, ephemeral=True)


class ConfirmResetView(discord.ui.View):
    def __init__(self, parent_view, ts, actor_id):
        super().__init__(timeout=30)
        self.parent_view = parent_view
        self.ts = ts
        self.actor_id = actor_id

    @discord.ui.button(label="✅ Xác nhận Reset", style=discord.ButtonStyle.danger)
    async def confirm(self, inter: discord.Interaction, button: discord.ui.Button):
        if inter.user.id != self.actor_id:
            return await inter.response.send_message("❌", ephemeral=True)

        await inter.response.defer(ephemeral=True)
        ts = await self.parent_view._reload()
        da_ngo_dao = ts.get("nguyen_lieu", {}).get(DA_NGO_DAO_ID, 0) if isinstance(ts.get("nguyen_lieu"), dict) else 0

        if da_ngo_dao < 1:
            self.stop()
            return await safe_followup(inter, "❌ Không còn Đá Reset Skill Tree!", ephemeral=True)

        # Trừ đá + reset y_canh
        new_nl = ts.get("nguyen_lieu", {}).copy() if isinstance(ts.get("nguyen_lieu"), dict) else {}
        new_nl[DA_NGO_DAO_ID] = new_nl.get(DA_NGO_DAO_ID, 0) - 1
        if new_nl[DA_NGO_DAO_ID] <= 0:
            new_nl.pop(DA_NGO_DAO_ID, None)

        from utils.database import update_tu_si
        await update_tu_si(self.actor_id, y_canh="{}", nguyen_lieu=new_nl)

        for item in self.children:
            item.disabled = True
        self.stop()

        await safe_followup(inter,
            embed=e_ok("Reset Thành Công", "✅ Ý Cảnh đã được reset về Level 0! Điểm skill đã hoàn lại."),
            ephemeral=True)

    @discord.ui.button(label="❌ Hủy", style=discord.ButtonStyle.secondary)
    async def cancel(self, inter: discord.Interaction, button: discord.ui.Button):
        if inter.user.id != self.actor_id:
            return await inter.response.send_message("❌", ephemeral=True)
        for item in self.children:
            item.disabled = True
        self.stop()
        await inter.response.edit_message(
            embed=e_ok("Đã Hủy", "Skill tree vẫn nguyên."), view=self)
