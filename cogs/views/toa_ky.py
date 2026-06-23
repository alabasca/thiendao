"""
cogs/views/toa_ky.py
Hệ thống Tọa Kỵ — Mount System
"""
from __future__ import annotations
from typing import Any

from cogs.views._common import *
from utils.config import (
    TOA_KY, TOA_KY_BY_ID, TOA_KY_BY_HE,
    TOA_KY_LEVEL_MULT, TOA_KY_LEVELUP_CG_YEU_CAU,
    TOA_KY_NGUYEN_LIEU, TOA_KY_NL_BY_ID, TOA_KY_LEVELUP_COST,
    TOA_KY_BANNER,
    TOA_KY_RARITY_POOL, TOA_KY_DUPE_TINH_HOA,
    CANH_GIOI, NGUYEN_LIEU,
)
from utils.bot_emojis import E_LINH_THACH
import json as _json
import logging

log = logging.getLogger("hoso")

HE_EMOJI = {
    "kim": "⚔️", "moc": "🌿", "thuy": "💧", "hoa": "🔥",
    "tho": "🌍", "phong": "🌪️", "loi": "⚡", "quang": "☀️", "am": "🌑"
}
HE_TEN = {
    "kim": "Kim", "moc": "Mộc", "thuy": "Thủy", "hoa": "Hỏa",
    "tho": "Thổ", "phong": "Phong", "loi": "Lôi", "quang": "Quang", "am": "Ám"
}


def _parse_toa_ky(ts: dict[str, Any]) -> dict:
    """Parse toa_ky từ DB → dict {id: {level, obtained_at}}."""
    raw = ts.get("toa_ky", {})
    if isinstance(raw, str):
        try: return _json.loads(raw) if raw else {}
        except: return {}
    return raw if isinstance(raw, dict) else {}


def _parse_toa_ky_herb(ts: dict[str, Any]) -> dict:
    """Parse toa_ky_herb từ DB → dict {nl_id: count}."""
    raw = ts.get("toa_ky_herb", {})
    if isinstance(raw, str):
        try: return _json.loads(raw) if raw else {}
        except: return {}
    return raw if isinstance(raw, dict) else {}


def _embed_toa_ky_list(ts: dict[str, Any], user: discord.User) -> discord.Embed:
    """Embed danh sách tọa kỵ đang sở hữu."""
    kho = _parse_toa_ky(ts)
    active_id = ts.get("toa_ky_active", -1)
    embed = discord.Embed(title="🐉 TỌA KỴ", color=0xFF6B35)
    embed.set_author(name=ts["dao_hieu"], icon_url=user.display_avatar.url)

    if not kho:
        embed.description = "*(Chưa có tọa kỵ nào — dùng nút **🎰 Gacha** để quay!)*"
        return embed

    lines = []
    for tk_id_str, tk_data in kho.items():
        tk_id = int(tk_id_str)
        tk = TOA_KY_BY_ID.get(tk_id)
        if not tk:
            continue
        level = tk_data.get("level", 1)
        is_active = (tk_id == active_id)
        active_mark = " ◀ ACTIVE" if is_active else ""
        lines.append(
            f"{tk['emoji']} **{tk['ten']}**"
            f" [{HE_TEN[tk['he']]}·Lv{level}]{active_mark}"
        )

    embed.description = "\n".join(lines)

    # Buff hiện tại từ active
    if active_id >= 0:
        from cogs.hoso_utils import _calc_toa_ky_buff
        buff = _calc_toa_ky_buff(ts)
        buff_parts = []
        if buff.get("at_pct"):    buff_parts.append(f"ATK +{buff['at_pct']:.1f}%")
        if buff.get("def_pct"):   buff_parts.append(f"DEF +{buff['def_pct']:.1f}%")
        if buff.get("hp_pct"):    buff_parts.append(f"HP +{buff['hp_pct']:.1f}%")
        if buff.get("bao_kich"):  buff_parts.append(f"BK +{buff['bao_kich']:.1f}%")
        if buff.get("khang_bao"): buff_parts.append(f"KB +{buff['khang_bao']:.1f}%")
        if buff.get("hoi_tam"):   buff_parts.append(f"HT +{int(buff['hoi_tam'])}")
        if buff.get("ho_tam"):    buff_parts.append(f"HoT +{int(buff['ho_tam'])}")
        if buff.get("drop_rate"): buff_parts.append(f"Drop +{buff['drop_rate']:.1f}%")
        if buff.get("exp_pct"):   buff_parts.append(f"TV +{buff['exp_pct']:.1f}%")
        if buff_parts:
            embed.add_field(name="✨ Buff hiện tại", value="  ".join(buff_parts), inline=False)

    # Nguyên liệu hiện có
    herb = _parse_toa_ky_herb(ts)
    if herb:
        herb_lines = []
        for nl in TOA_KY_NGUYEN_LIEU:
            cnt = herb.get(nl["id"], 0)
            if cnt > 0:
                herb_lines.append(f"{nl['emoji']} {nl['ten']}: {cnt}")
        if herb_lines:
            embed.add_field(name="📦 Nguyên Liệu", value="  ".join(herb_lines), inline=False)

    embed.set_footer(text="🎰 Gacha để nhận tọa kỵ mới | ⬆️ Nâng cấp để tăng buff")
    return embed


def _embed_tk_detail(tk: dict, level: int, ts: dict[str, Any]) -> discord.Embed:
    """Embed chi tiết 1 tọa kỵ."""
    mult = TOA_KY_LEVEL_MULT.get(level, 1.0)

    embed = discord.Embed(
        title=f"{tk['emoji']} {tk['ten']}",
        description=tk["mo_ta"],
        color=0xFF6B35)
    embed.add_field(name="Hệ", value=f"{HE_EMOJI[tk['he']]} {HE_TEN[tk['he']]}", inline=True)
    embed.add_field(name="Level", value=f"{level}/10", inline=True)

    # Điều kiện nâng cấp tiếp theo
    if level < 10:
        next_lv = level + 1
        cg_yc = TOA_KY_LEVELUP_CG_YEU_CAU.get(next_lv, 0)
        cost_next = TOA_KY_LEVELUP_COST.get(next_lv, {})
        cg_ten = CANH_GIOI[cg_yc]["ten"] if cg_yc < len(CANH_GIOI) else ""
        cost_str = "  ".join(
            f"{TOA_KY_NL_BY_ID[k]['emoji']} ×{v}" for k, v in cost_next.items()
        ) if cost_next else "*(miễn phí)*"
        cg_str = f"  •  🏯 {cg_ten}" if cg_yc > 0 else ""
        embed.add_field(
            name=f"⬆️ Nâng lên Lv{next_lv}",
            value=f"{cost_str}{cg_str}",
            inline=False)

    # Buff tại level hiện tại
    base = tk.get("effect", {})
    buff_parts = []
    for k, v in base.items():
        val = v * mult
        label = {"at_pct":"ATK","def_pct":"DEF","hp_pct":"HP",
                 "bao_kich":"Bạo Kích","khang_bao":"Kháng Bạo",
                 "hoi_tam":"Hội Tâm","ho_tam":"Hộ Tâm",
                 "drop_rate":"Drop%","exp_pct":"EXP"}.get(k, k)
        unit = "%" if "pct" in k or k in ("bao_kich","khang_bao") else ""
        buff_parts.append(f"{label} +{val:.1f}{unit}")
    embed.add_field(name="📊 Buff", value="  ".join(buff_parts) if buff_parts else "—", inline=False)

    # Hiệu ứng đặc biệt
    passive = tk.get("passive_effect", "")
    active_eff = tk.get("active_effect", "")
    if passive:
        embed.add_field(name="🔵 Passive", value=passive, inline=False)
    if active_eff:
        embed.add_field(name="🔴 Active Skill", value=active_eff, inline=False)

    return embed


class ToaKyView(discord.ui.View):
    """View quản lý tọa kỵ."""

    def __init__(self, parent, ts: dict[str, Any], user: discord.User, actor_id: int = None):
        super().__init__(timeout=120)
        self.parent   = parent
        self.ts       = ts
        self.user     = user
        self.actor_id = actor_id or parent.owner_id
        self._build()

    def _build(self):
        self.clear_items()
        kho = _parse_toa_ky(self.ts)
        active_id = self.ts.get("toa_ky_active", -1)

        # Dropdown chọn tọa kỵ (nếu có)
        if kho:
            opts = []
            for tk_id_str, tk_data in kho.items():
                tk_id = int(tk_id_str)
                tk = TOA_KY_BY_ID.get(tk_id)
                if not tk: continue
                level = tk_data.get("level", 1)
                is_active = (tk_id == active_id)
                opts.append(discord.SelectOption(
                    label=f"{tk['ten']} Lv{level}",
                    value=tk_id_str,
                    emoji=tk["emoji"],
                    description=f"{HE_TEN[tk['he']]} · {'ACTIVE' if is_active else 'Click để chọn'}",
                    default=is_active
                ))
            if opts:
                sel = discord.ui.Select(
                    placeholder="Chọn tọa kỵ để xem / đặt active...",
                    options=opts[:25], row=0)
                sel.callback = self._on_select
                self.add_item(sel)

        # Nút nâng cấp
        btn_up = discord.ui.Button(
            label="⬆️ Nâng Cấp", style=discord.ButtonStyle.primary, row=1,
            disabled=(active_id < 0))
        btn_up.callback = self._on_levelup
        self.add_item(btn_up)

        # Nút gacha
        btn_gacha = discord.ui.Button(
            label="🎰 Gacha", style=discord.ButtonStyle.success, row=1)
        btn_gacha.callback = self._on_gacha
        self.add_item(btn_gacha)

        # Nút danh sách tất cả
        btn_list = discord.ui.Button(
            label="📖 Danh Sách", style=discord.ButtonStyle.secondary, row=1)
        btn_list.callback = self._on_list_all
        self.add_item(btn_list)

        # Nút hướng dẫn
        btn_guide = discord.ui.Button(
            label="❓ Hướng Dẫn", style=discord.ButtonStyle.secondary, row=2)
        btn_guide.callback = self._on_guide
        self.add_item(btn_guide)

        # Quay lại
        btn_back = discord.ui.Button(
            label="◀ Quay Lại", style=discord.ButtonStyle.secondary, row=2)
        btn_back.callback = self._on_back
        self.add_item(btn_back)

    async def _on_select(self, inter: discord.Interaction):
        if inter.user.id != self.actor_id:
            return await inter.response.send_message("❌", ephemeral=True)
        try:
            await inter.response.defer(ephemeral=True)
        except Exception:
            log.exception("Lỗi toa_ky")
        tk_id = int(inter.data["values"][0])
        kho = _parse_toa_ky(self.ts)
        tk_data = kho.get(str(tk_id), {})
        tk = TOA_KY_BY_ID.get(tk_id)
        if not tk:
            return await safe_followup(inter, "❌ Không tìm thấy!", ephemeral=True)
        level = tk_data.get("level", 1)

        # Đặt làm active
        await update_tu_si(inter.user.id, toa_ky_active=tk_id)
        ts_new = await get_tu_si(inter.user.id)

        embed_detail = _embed_tk_detail(tk, level, ts_new)
        embed_detail.set_footer(text=f"✅ Đã đặt {tk['ten']} làm tọa kỵ active!")

        new_view = ToaKyView(self.parent, ts_new, self.user, self.actor_id)
        self.stop()
        try:
            await inter.edit_original_response(embed=_embed_toa_ky_list(ts_new, self.user), view=new_view)
        except Exception:
            log.exception("Lỗi toa_ky")
        await safe_followup(inter, embed=embed_detail, ephemeral=True)

    async def _on_levelup(self, inter: discord.Interaction):
        if inter.user.id != self.actor_id:
            return await inter.response.send_message("❌", ephemeral=True)
        try:
            await inter.response.defer(ephemeral=True)
        except Exception:
            log.exception("Lỗi toa_ky")
        active_id = self.ts.get("toa_ky_active", -1)
        if active_id < 0:
            return await safe_followup(inter, "❌ Chưa chọn tọa kỵ active!", ephemeral=True)

        ts_fresh = await get_tu_si(inter.user.id)
        kho = _parse_toa_ky(ts_fresh)
        tk_data = kho.get(str(active_id))
        if not tk_data:
            return await safe_followup(inter, "❌ Không tìm thấy tọa kỵ!", ephemeral=True)

        level = tk_data.get("level", 1)
        if level >= 10:
            return await safe_followup(inter, "❌ Đã đạt level tối đa (10)!", ephemeral=True)

        target_level = level + 1

        # Kiểm tra yêu cầu cảnh giới
        cg_yeu_cau = TOA_KY_LEVELUP_CG_YEU_CAU.get(target_level, 0)
        cg_hien = ts_fresh.get("canh_gioi", 0)
        if cg_hien < cg_yeu_cau:
            cg_ten = CANH_GIOI[cg_yeu_cau]["ten"] if cg_yeu_cau < len(CANH_GIOI) else f"CG{cg_yeu_cau}"
            cg_hien_ten = CANH_GIOI[cg_hien]["ten"] if cg_hien < len(CANH_GIOI) else f"CG{cg_hien}"
            return await safe_followup(inter,
                f"❌ **Cảnh giới chưa đủ!**\n"
                f"Nâng tọa kỵ lên **Lv{target_level}** yêu cầu **{cg_ten}**.\n"
                f"Cảnh giới hiện tại: **{cg_hien_ten}**.",
                ephemeral=True)

        cost = TOA_KY_LEVELUP_COST.get(target_level, {})
        herb = _parse_toa_ky_herb(ts_fresh)

        # Kiểm tra nguyên liệu
        missing = []
        for nl_id, so_luong in cost.items():
            co = herb.get(nl_id, 0)
            if co < so_luong:
                nl_cfg = TOA_KY_NL_BY_ID.get(nl_id)
                ten = nl_cfg["ten"] if nl_cfg else nl_id
                missing.append(f"{ten}: cần {so_luong}, có {co}")
        if missing:
            return await safe_followup(inter,
                f"❌ Thiếu nguyên liệu:\n" + "\n".join(missing), ephemeral=True)

        # Trừ nguyên liệu
        herb_new = herb.copy()
        for nl_id, so_luong in cost.items():
            herb_new[nl_id] = herb_new.get(nl_id, 0) - so_luong
            if herb_new[nl_id] <= 0:
                del herb_new[nl_id]

        # Nâng level
        kho_new = kho.copy()
        kho_new[str(active_id)] = {**tk_data, "level": target_level}
        await update_tu_si(inter.user.id, toa_ky_herb=herb_new, toa_ky=kho_new)
        ts_new = await get_tu_si(inter.user.id)

        tk = TOA_KY_BY_ID.get(active_id)
        embed = discord.Embed(
            title=f"⬆️ NÂNG CẤP THÀNH CÔNG!",
            description=(
                f"{tk['emoji']} **{tk['ten']}** đã lên **Lv{target_level}**!\n"
                f"Buff tăng lên ×{TOA_KY_LEVEL_MULT[target_level]:.1f}"
            ),
            color=0x57F287)
        new_view = ToaKyView(self.parent, ts_new, self.user, self.actor_id)
        self.stop()
        try:
            await inter.edit_original_response(embed=_embed_toa_ky_list(ts_new, self.user), view=new_view)
        except Exception:
            log.exception("Lỗi toa_ky")
        await safe_followup(inter, embed=embed, ephemeral=True)

    async def _on_gacha(self, inter: discord.Interaction):
        """Mở banner gacha."""
        if inter.user.id != self.actor_id:
            return await inter.response.send_message("❌", ephemeral=True)
        try:
            from cogs.views.toa_ky_gacha import ToaKyGachaView, _embed_banner
            ts_fresh = await get_tu_si(inter.user.id)
            embed = _embed_banner(ts_fresh)
            view = ToaKyGachaView(self.parent, ts_fresh, self.user, self.actor_id)
            await inter.response.send_message(embed=embed, view=view, ephemeral=True)
        except Exception as e:
            log.error(f"_on_gacha user={inter.user.id}: {e}", exc_info=True)
            await inter.response.send_message(f"❌ Lỗi: {e}", ephemeral=True)

    async def _on_list_all(self, inter: discord.Interaction):
        if inter.user.id != self.actor_id:
            return await inter.response.send_message("❌", ephemeral=True)
        try:
            await inter.response.defer(ephemeral=True)
        except Exception:
            log.exception("Lỗi toa_ky")
        kho = _parse_toa_ky(self.ts)
        lines = []
        for tk in TOA_KY:
            owned = str(tk["id"]) in kho
            mark = "✅" if owned else "❌"
            line = f"{mark} {tk['emoji']} **{tk['ten']}** [{HE_TEN[tk['he']]}·{tk['cap']}]"
            lines.append(line)

        embeds = []
        e1 = discord.Embed(title="📖 Danh Sách Tọa Kỵ", description="\n".join(lines), color=0xFF6B35)
        e1.set_footer(text="✅ = đã sở hữu | ❌ = chưa có")
        embeds.append(e1)
        await safe_followup(inter, embeds=embeds, ephemeral=True)

    async def _on_guide(self, inter: discord.Interaction):
        if inter.user.id != self.actor_id:
            return await inter.response.send_message("❌", ephemeral=True)
        try:
            await inter.response.defer(ephemeral=True)
        except Exception:
            log.exception("Lỗi toa_ky")

        e1 = discord.Embed(
            title="🐉 HƯỚNG DẪN TỌA KỴ",
            description=(
                "Tọa Kỵ là mount đồng hành, cho **buff passive thường trực** và **kỹ năng active** trong chiến đấu.\n\n"
                "**Cách có tọa kỵ:**\n"
                "• 🎰 Dùng **Gacha** bằng Linh Thạch để quay tọa kỵ\n"
                "• Banner thường: **500 LT/lần** hoặc **4,500 LT/10 lần**\n\n"
                "**Cách dùng:**\n"
                "• Chọn tọa kỵ trong dropdown → tự động đặt làm **active**\n"
                "• Chỉ **1 tọa kỵ active** tại 1 thời điểm\n"
                "• Nâng cấp bằng nguyên liệu từ **Bí Cảnh Tọa Kỵ**\n\n"
                "**Hiệu ứng đặc biệt:**\n"
                "• Mỗi hệ có **passive** và **active skill** riêng\n"
                "• Level càng cao → buff càng mạnh (×1.0 → ×5.5)"
            ),
            color=0xFF6B35)
        e1.set_footer(text="Buff: Lv1×1.0 | Lv3×1.5 | Lv5×2.2 | Lv7×3.2 | Lv10×5.5")

        e2 = discord.Embed(
            title="🎰 GACHA BANNER",
            description=(
                "**Banner Thường:**\n"
                f"• Chi phí: **{fmt(0)} LT/lần**\n"
                f"• 10 lần: **{fmt(TOA_KY_BANNER['chi_phi_10'])} LT** (giảm 10%)\n"
                f"• Soft pity: từ lần **{TOA_KY_BANNER['pity_soft']}**\n"
                f"• Hard pity: lần **{TOA_KY_BANNER['pity_hard']}** guaranteed\n\n"
                "**Tỷ lệ theo Rarity:**\n"
                "• Phàm (70%): Mộc Linh Lộc, Huyền Ngư, Minh Nguyệt Lộc\n"
                "• Linh (25%): Kim Lân, Hỏa Phượng, Địa Hành Quy, Phong Long\n"
                "• Tiên (4.5%): Lôi Đế, Hắc Diệm Sư\n"
                "• Thần (0.5%): Mở rộng sau\n\n"
                "**Duplicate:** Nhận **Tinh Hoa Tọa Kỵ** thay vì mount trùng"
            ),
            color=0x57F287)

        await safe_followup(inter, embeds=[e1, e2], ephemeral=True)

    async def _on_back(self, inter: discord.Interaction):
        from cogs.hoso_utils import _back_to_hoso
        await _back_to_hoso(inter, self.parent)
