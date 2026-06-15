"""
cogs/views/sung_thu.py
Hệ thống Sủng Thú — 9 hệ × 2 tier = 18 sủng thú
"""
from __future__ import annotations
from typing import Any

from cogs.views._common import *
from utils.config import (
    SUNG_THU, SUNG_THU_BY_ID, SUNG_THU_BY_HE,
    SUNG_THU_HE_BUFF, SUNG_THU_SET_BONUS, SUNG_THU_SKILL,
    SUNG_THU_LEVEL_MULT, SUNG_THU_TIER2_MULT,
    SUNG_THU_LEVELUP_COST, SUNG_THU_LEVELUP_COST_T2, SUNG_THU_LEVELUP_CG_YEU_CAU,
    NGUYEN_LIEU, LINH_CAN, LINH_CAN_BY_ID, CANH_GIOI, CAP_NHO,
)
from utils.bot_emojis import E_LINH_THACH, E_CONG_KICH, E_PHONG_NGU, E_SINH_LUC
import json as _json
import logging

log = logging.getLogger("hoso")

TIER_EMOJI = {1: "⭐", 2: "💫"}
TIER_COLOR = {1: 0x4FC3F7, 2: 0xFFD700}
TIER_NAME  = {1: "Thường", 2: "Huyền Thoại"}

HE_EMOJI = {
    "kim": "⚔️", "moc": "🌿", "thuy": "💧", "hoa": "🔥",
    "tho": "🌍", "phong": "🌪️", "loi": "⚡", "quang": "☀️", "am": "🌑"
}
HE_TEN = {
    "kim": "Kim", "moc": "Mộc", "thuy": "Thủy", "hoa": "Hỏa",
    "tho": "Thổ", "phong": "Phong", "loi": "Lôi", "quang": "Quang", "am": "Ám"
}


def _parse_sung_thu(ts: dict[str, Any]) -> dict:
    """Parse sung_thu từ DB → dict {id: {level, obtained_at}}."""
    raw = ts.get("sung_thu", {})
    if isinstance(raw, str):
        try: return _json.loads(raw) if raw else {}
        except: return {}
    return raw if isinstance(raw, dict) else {}


def _calc_sung_thu_buff(ts: dict[str, Any]) -> dict:
    """Tính tổng buff từ tất cả sủng thú đang active."""
    result = {
        "at_pct": 0.0, "def_pct": 0.0, "hp_pct": 0.0,
        "bao_kich": 0.0, "khang_bao": 0.0,
        "hoi_tam": 0, "ho_tam": 0,
        "drop_rate": 0.0, "exp_pct": 0.0,
        "bc_phong_bonus": 0, "boss_dmg_pct": 0.0,
    }
    active_id = ts.get("sung_thu_active", -1)
    if active_id < 0:
        return result
    kho = _parse_sung_thu(ts)
    st_data = kho.get(str(active_id))
    if not st_data:
        return result
    st = SUNG_THU_BY_ID.get(active_id)
    if not st:
        return result

    level = st_data.get("level", 1)
    mult  = SUNG_THU_LEVEL_MULT.get(level, 1.0)
    if st["tier"] == 2:
        mult *= SUNG_THU_TIER2_MULT

    base_buff = SUNG_THU_HE_BUFF.get(st["he"], {})
    for k, v in base_buff.items():
        if k in result:
            result[k] += v * mult

    # Set bonus nếu cùng hệ với linh căn
    lc_ids = ts.get("linh_can_so_huu", [])
    if st["he"] in lc_ids:
        set_bonus = SUNG_THU_SET_BONUS.get(st["he"], {})
        for k, v in set_bonus.items():
            if k in result:
                result[k] += v

    return result


def _get_active_skill(ts: dict[str, Any]) -> dict | None:
    """Lấy active skill của sủng thú đang active (chỉ Tier 2 có)."""
    active_id = ts.get("sung_thu_active", -1)
    if active_id < 0:
        return None
    st = SUNG_THU_BY_ID.get(active_id)
    if not st or st["tier"] < 2:
        return None
    return SUNG_THU_SKILL.get(st["he"], {}).get("active")


def _embed_sung_thu_list(ts: dict[str, Any], user: discord.User) -> discord.Embed:
    """Embed danh sách sủng thú đang sở hữu."""
    kho = _parse_sung_thu(ts)
    active_id = ts.get("sung_thu_active", -1)
    embed = discord.Embed(title="🐾 SỦNG THÚ", color=0x7B68EE)
    embed.set_author(name=ts["dao_hieu"], icon_url=user.display_avatar.url)

    if not kho:
        embed.description = "*(Chưa có sủng thú nào — đi bí cảnh hoặc đánh boss để tìm kiếm!)*"
        return embed

    # Linh căn để check set bonus
    lc_ids = set(ts.get("linh_can_so_huu", []))

    lines = []
    for st_id_str, st_data in kho.items():
        st_id = int(st_id_str)
        st = SUNG_THU_BY_ID.get(st_id)
        if not st:
            continue
        level = st_data.get("level", 1)
        is_active = (st_id == active_id)
        set_mark = " 🔗" if st["he"] in lc_ids else ""
        active_mark = " ◀ ACTIVE" if is_active else ""
        lines.append(
            f"{TIER_EMOJI[st['tier']]} {st['emoji']} **{st['ten']}**"
            f" [{HE_TEN[st['he']]}·Lv{level}]{set_mark}{active_mark}"
        )

    embed.description = "\n".join(lines)

    # Buff hiện tại từ active
    if active_id >= 0:
        buff = _calc_sung_thu_buff(ts)
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
        if buff.get("boss_dmg_pct"): buff_parts.append(f"Boss +{buff['boss_dmg_pct']:.0f}%")
        if buff_parts:
            embed.add_field(name="✨ Buff hiện tại", value="  ".join(buff_parts), inline=False)

    embed.set_footer(text="🔗 = cùng hệ linh căn (Set Bonus kích hoạt)")
    return embed


def _embed_st_detail(st: dict, level: int, ts: dict[str, Any]) -> discord.Embed:
    """Embed chi tiết 1 sủng thú."""
    mult = SUNG_THU_LEVEL_MULT.get(level, 1.0)
    if st["tier"] == 2:
        mult *= SUNG_THU_TIER2_MULT

    embed = discord.Embed(
        title=f"{TIER_EMOJI[st['tier']]} {st['emoji']} {st['ten']}",
        description=st["mo_ta"],
        color=TIER_COLOR[st["tier"]])
    embed.add_field(name="Hệ", value=f"{HE_EMOJI[st['he']]} {HE_TEN[st['he']]}", inline=True)
    embed.add_field(name="Tier", value=TIER_NAME[st["tier"]], inline=True)
    embed.add_field(name="Level", value=f"{level}/10", inline=True)

    # Điều kiện nâng cấp tiếp theo
    if level < 10:
        next_lv = level + 1
        cg_yc = SUNG_THU_LEVELUP_CG_YEU_CAU.get(next_lv, 0)
        cost_next = SUNG_THU_LEVELUP_COST.get(next_lv, {})
        cg_ten = CANH_GIOI[cg_yc]["ten"] if cg_yc < len(CANH_GIOI) else ""
        cost_str = "  ".join(
            f"{NGUYEN_LIEU[int(k)]['emoji']} ×{v}" for k, v in cost_next.items()
        ) if cost_next else "*(miễn phí)*"
        cg_str = f"  •  🏯 {cg_ten}" if cg_yc > 0 else ""
        embed.add_field(
            name=f"⬆️ Nâng lên Lv{next_lv}",
            value=f"{cost_str}{cg_str}",
            inline=False)

    # Buff tại level hiện tại
    base = SUNG_THU_HE_BUFF.get(st["he"], {})
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

    # Set bonus
    lc_ids = set(ts.get("linh_can_so_huu", []))
    set_b = SUNG_THU_SET_BONUS.get(st["he"], {})
    if set_b:
        set_parts = []
        for k, v in set_b.items():
            label = {"at_pct":"ATK","def_pct":"DEF","hp_pct":"HP",
                     "bao_kich":"Bạo Kích","exp_pct":"EXP",
                     "drop_rate":"Drop%","hoi_tam":"Hội Tâm",
                     "bc_phong_bonus":"+1 phòng BC","boss_dmg_pct":"Sát thương Boss"}.get(k, k)
            unit = "%" if "pct" in k else ""
            set_parts.append(f"{label} +{v}{unit}")
        has_set = st["he"] in lc_ids
        set_str = ("  ".join(set_parts)) + (" ✅" if has_set else " ❌ (cần linh căn cùng hệ)")
        embed.add_field(name="🔗 Set Bonus", value=set_str, inline=False)

    # Skill
    skill = SUNG_THU_SKILL.get(st["he"], {})
    passive = skill.get("passive")
    active  = skill.get("active")
    if passive:
        embed.add_field(name=f"🔵 Passive: {passive['ten']}", value=passive["mo_ta"], inline=False)
    if active and st["tier"] == 2:
        embed.add_field(
            name=f"🔴 Active: {active['ten']} (CD {active['cd']} lượt)",
            value=active["mo_ta"], inline=False)
    elif st["tier"] == 1:
        embed.add_field(name="🔴 Active", value="*(Chỉ Huyền Thoại mới có)*", inline=False)

    return embed



def _build_guide_embeds(ts: dict[str, Any]) -> list:
    """Tạo danh sách embed hướng dẫn sủng thú — chia nhỏ tránh 1024 ký tự/field."""
    lc_ids = set(ts.get("linh_can_so_huu", []))
    active_id = ts.get("sung_thu_active", -1)
    kho = _parse_sung_thu(ts)

    embeds = []

    # ── Embed 1: Tổng quan ─────────────────────────────────────────
    e1 = discord.Embed(
        title="🐾 HƯỚNG DẪN SỦNG THÚ",
        description=(
            "Sủng Thú là pet đồng hành, cho **buff passive thường trực** và **kỹ năng active** trong chiến đấu.\n\n"
            "**Cách có sủng thú:**\n"
            "• ⭐ **Thường** — Drop từ Bí Cảnh (5% boss)\n"
            "• 💫 **Huyền Thoại** — Drop từ World Boss (0.5%)\n\n"
            "**Cách dùng:**\n"
            "• Chọn sủng thú trong dropdown → tự động đặt làm **active**\n"
            "• Chỉ **1 sủng thú active** tại 1 thời điểm\n"
            "• Nâng cấp bằng nguyên liệu từ **Khai Hoang** (24h/lần)"
        ),
        color=0x7B68EE)
    e1.add_field(
        name="⭐ vs 💫 Sức mạnh",
        value=(
            "**Tier 1 Thường**: Buff × hệ số level (Lv1: ×1.0 → Lv10: ×5.0)\n"
            "**Tier 2 Huyền Thoại**: Buff × hệ số level × **1.6** (mạnh hơn 60%)\n"
            "Chi phí nâng cấp Huyền Thoại = **×10** Thường"
        ),
        inline=False)
    e1.add_field(
        name="🔗 Set Bonus",
        value=(
            "Khi sủng thú **cùng hệ** với linh căn đang sở hữu → kích hoạt **Set Bonus** cộng thêm.\n"
            "Ví dụ: Sủng Thú hệ Kim + Linh Căn Kim = AT +8% bonus thêm."
        ),
        inline=False)
    e1.set_footer(text="Hệ số level: Lv1×1.0 | Lv3×1.55 | Lv5×2.30 | Lv7×3.25 | Lv10×5.0")
    embeds.append(e1)

    # ── Embed 2: Buff từng hệ (3 hệ/embed tránh 1024 ký tự) ────────
    HE_ORDER = ["kim", "moc", "thuy", "hoa", "tho", "phong", "loi", "quang", "am"]
    BUFF_LABEL = {
        "at_pct": "ATK", "def_pct": "DEF", "hp_pct": "HP",
        "bao_kich": "Bạo Kích", "khang_bao": "Kháng Bạo",
        "hoi_tam": "Hội Tâm", "ho_tam": "Hộ Tâm",
        "drop_rate": "Drop%", "exp_pct": "EXP", "boss_dmg_pct": "Sát thương Boss"
    }
    SET_LABEL = {
        "at_pct": "ATK", "def_pct": "DEF", "hp_pct": "HP",
        "bao_kich": "Bạo Kích", "exp_pct": "EXP",
        "drop_rate": "Drop%", "hoi_tam": "Hội Tâm",
        "khang_bao": "Kháng Bạo", "ho_tam": "Hộ Tâm",
        "boss_dmg_pct": "Sát thương Boss",
    }

    def buff_line(he):
        base = SUNG_THU_HE_BUFF.get(he, {})
        parts = []
        for k, v in base.items():
            unit = "%" if ("pct" in k or k in ("bao_kich", "khang_bao")) else ""
            parts.append(f"{BUFF_LABEL.get(k, k)} +{v}{unit}/lv")
        return "  |  ".join(parts)

    def set_line(he):
        sb = SUNG_THU_SET_BONUS.get(he, {})
        parts = []
        for k, v in sb.items():
            unit = "%" if ("pct" in k) else ""
            parts.append(f"{SET_LABEL.get(k, k)} +{v}{unit}")
        has = "✅" if he in lc_ids else "❌ cần LC cùng hệ"
        return ("  |  ".join(parts)) + f" ({has})"

    def skill_line(he, tier):
        sk = SUNG_THU_SKILL.get(he, {})
        passive = sk.get("passive")
        active_sk = sk.get("active")
        lines = []
        if passive:
            lines.append(f"🔵 **Passive — {passive['ten']}**: {passive['mo_ta']}")
        if active_sk and tier == 2:
            cd = active_sk.get("cd", "?")
            lines.append(f"🔴 **Active — {active_sk['ten']}** (CD {cd} lượt): {active_sk['mo_ta']}")
        elif tier == 1:
            lines.append("🔴 Active: *(Chỉ Huyền Thoại mới có)*")
        return "\n".join(lines)

    # Chia thành 3 embed × 3 hệ mỗi embed
    for chunk_start in range(0, 9, 3):
        e = discord.Embed(
            title=f"📊 Buff Sủng Thú ({chunk_start+1}–{chunk_start+3}/9)",
            color=0x4FC3F7)
        for he in HE_ORDER[chunk_start:chunk_start+3]:
            sts_he = SUNG_THU_BY_HE.get(he, [])
            t1 = next((s for s in sts_he if s["tier"] == 1), None)
            t2 = next((s for s in sts_he if s["tier"] == 2), None)
            name_str = (
                f"{HE_EMOJI[he]} **Hệ {HE_TEN[he]}**  "
                + (f"⭐{t1['emoji']}{t1['ten']} " if t1 else "")
                + (f"  💫{t2['emoji']}{t2['ten']}" if t2 else "")
            )
            val = (
                f"**Buff/lv:** {buff_line(he)}\n"
                f"**Set Bonus:** {set_line(he)}\n"
                f"{skill_line(he, 2)}"  # luôn show cả active (tier 2 info)
            )
            # Cắt tránh 1024
            if len(val) > 1020:
                val = val[:1017] + "..."
            e.add_field(name=name_str, value=val, inline=False)
        embeds.append(e)

    # ── Embed 5: Nguyên liệu nâng cấp ──────────────────────────────
    NGUYEN_LIEU_NAMES = ["🌿Linh Thảo", "🔥Hỏa Tinh Thạch", "⚫Huyền Thiết",
                         "🕸️Thiên Tằm Tơ", "🦴Long Cốt", "✨Thần Tinh Sa"]
    e5 = discord.Embed(title="⬆️ Chi Phí Nâng Cấp Sủng Thú", color=0xFFD700)

    t1_lines = []
    t2_lines = []
    for lv in range(2, 11):
        c1 = SUNG_THU_LEVELUP_COST.get(lv, {})
        c2 = SUNG_THU_LEVELUP_COST_T2.get(lv, {})
        cg_yc = SUNG_THU_LEVELUP_CG_YEU_CAU.get(lv, 0)
        from utils.config import CANH_GIOI as _CG
        cg_str = f" [{_CG[cg_yc]['ten']}+]" if cg_yc > 0 else ""
        t1_str = "  ".join(f"{NGUYEN_LIEU_NAMES[int(k)]}×{v}" for k,v in c1.items())
        t2_str = "  ".join(f"{NGUYEN_LIEU_NAMES[int(k)]}×{v}" for k,v in c2.items())
        t1_lines.append(f"Lv{lv}{cg_str}: {t1_str}")
        t2_lines.append(f"Lv{lv}{cg_str}: {t2_str}")

    t1_val = "\n".join(t1_lines)
    t2_val = "\n".join(t2_lines)
    if len(t1_val) > 1020: t1_val = t1_val[:1017] + "..."
    if len(t2_val) > 1020: t2_val = t2_val[:1017] + "..."

    e5.add_field(name="⭐ Tier Thường", value=t1_val, inline=False)
    e5.add_field(name="💫 Tier Huyền Thoại (×10)", value=t2_val, inline=False)
    e5.set_footer(text="Nguyên liệu lấy từ Khai Hoang hàng ngày")
    embeds.append(e5)

    return embeds


class SungThuView(discord.ui.View):
    """View quản lý sủng thú."""

    def __init__(self, parent, ts: dict[str, Any], user: discord.User, actor_id: int = None):
        super().__init__(timeout=120)
        self.parent   = parent
        self.ts       = ts
        self.user     = user
        self.actor_id = actor_id or parent.owner_id
        self._build()

    def _build(self):
        self.clear_items()
        kho = _parse_sung_thu(self.ts)
        active_id = self.ts.get("sung_thu_active", -1)

        # Dropdown chọn sủng thú (nếu có)
        if kho:
            opts = []
            for st_id_str, st_data in kho.items():
                st_id = int(st_id_str)
                st = SUNG_THU_BY_ID.get(st_id)
                if not st: continue
                level = st_data.get("level", 1)
                is_active = (st_id == active_id)
                opts.append(discord.SelectOption(
                    label=f"{st['ten']} Lv{level}",
                    value=st_id_str,
                    emoji=st["emoji"],
                    description=f"{HE_TEN[st['he']]} · {TIER_NAME[st['tier']]}",
                    default=is_active
                ))
            if opts:
                sel = discord.ui.Select(
                    placeholder="Chọn sủng thú để xem / đặt active...",
                    options=opts[:25], row=0)
                sel.callback = self._on_select
                self.add_item(sel)

        # Nút nâng cấp
        btn_up = discord.ui.Button(
            label="⬆️ Nâng Cấp", style=discord.ButtonStyle.primary, row=1,
            disabled=(active_id < 0))
        btn_up.callback = self._on_levelup
        self.add_item(btn_up)

        # Nút danh sách sủng thú có thể tìm
        btn_list = discord.ui.Button(
            label="📖 Danh Sách", style=discord.ButtonStyle.secondary, row=1)
        btn_list.callback = self._on_list_all
        self.add_item(btn_list)

        # Nút hướng dẫn toàn bộ hệ thống sủng thú
        btn_guide = discord.ui.Button(
            label="❓ Hướng Dẫn", style=discord.ButtonStyle.secondary, row=1)
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
            log.exception("Lỗi sung_thu")
        st_id = int(inter.data["values"][0])
        kho = _parse_sung_thu(self.ts)
        st_data = kho.get(str(st_id), {})
        st = SUNG_THU_BY_ID.get(st_id)
        if not st:
            return await safe_followup(inter, "❌ Không tìm thấy!", ephemeral=True)
        level = st_data.get("level", 1)

        # Đặt làm active
        await update_tu_si(inter.user.id, sung_thu_active=st_id)
        ts_new = await get_tu_si(inter.user.id)

        embed_detail = _embed_st_detail(st, level, ts_new)
        embed_detail.set_footer(text=f"✅ Đã đặt {st['ten']} làm sủng thú active!")

        # Tạo view mới hoàn toàn để tránh interaction failed
        new_view = SungThuView(self.parent, ts_new, self.user, self.actor_id)
        self.stop()
        try:
            await inter.edit_original_response(embed=_embed_sung_thu_list(ts_new, self.user), view=new_view)
        except Exception:
            log.exception("Lỗi sung_thu")
        await safe_followup(inter, embed=embed_detail, ephemeral=True)

    async def _on_levelup(self, inter: discord.Interaction):
        if inter.user.id != self.actor_id:
            return await inter.response.send_message("❌", ephemeral=True)
        try:
            await inter.response.defer(ephemeral=True)
        except Exception:
            log.exception("Lỗi sung_thu")
        active_id = self.ts.get("sung_thu_active", -1)
        if active_id < 0:
            return await safe_followup(inter, "❌ Chưa chọn sủng thú active!", ephemeral=True)

        ts_fresh = await get_tu_si(inter.user.id)
        kho = _parse_sung_thu(ts_fresh)
        st_data = kho.get(str(active_id))
        if not st_data:
            return await safe_followup(inter, "❌ Không tìm thấy sủng thú!", ephemeral=True)

        level = st_data.get("level", 1)
        if level >= 10:
            return await safe_followup(inter, "❌ Đã đạt level tối đa (10)!", ephemeral=True)

        target_level = level + 1

        # Kiểm tra yêu cầu cảnh giới
        cg_yeu_cau = SUNG_THU_LEVELUP_CG_YEU_CAU.get(target_level, 0)
        cg_hien = ts_fresh.get("canh_gioi", 0)
        if cg_hien < cg_yeu_cau:
            cg_ten = CANH_GIOI[cg_yeu_cau]["ten"] if cg_yeu_cau < len(CANH_GIOI) else f"CG{cg_yeu_cau}"
            cg_hien_ten = CANH_GIOI[cg_hien]["ten"] if cg_hien < len(CANH_GIOI) else f"CG{cg_hien}"
            return await safe_followup(inter, 
                f"❌ **Cảnh giới chưa đủ!**\n"
                f"Nâng sủng thú lên **Lv{target_level}** yêu cầu **{cg_ten}**.\n"
                f"Cảnh giới hiện tại: **{cg_hien_ten}**.",
                ephemeral=True)

        # Dùng bảng cost theo tier: Huyền Thoại dùng COST_T2
        st_obj = SUNG_THU_BY_ID.get(active_id)
        cost_table = SUNG_THU_LEVELUP_COST_T2 if st_obj and st_obj.get("tier") == 2 else SUNG_THU_LEVELUP_COST
        cost = cost_table.get(target_level, {})
        nl = ts_fresh.get("nguyen_lieu", {})

        # Kiểm tra nguyên liệu
        missing = []
        for nl_idx, so_luong in cost.items():
            co = nl.get(nl_idx, 0)
            if co < so_luong:
                ten = NGUYEN_LIEU[int(nl_idx)]["ten"]
                missing.append(f"{ten}: cần {so_luong}, có {co}")
        if missing:
            return await safe_followup(inter, 
                f"❌ Thiếu nguyên liệu:\n" + "\n".join(missing), ephemeral=True)

        # Trừ nguyên liệu
        nl_new = nl.copy()
        for nl_idx, so_luong in cost.items():
            nl_new[nl_idx] = nl_new.get(nl_idx, 0) - so_luong
            if nl_new[nl_idx] <= 0:
                del nl_new[nl_idx]

        # Nâng level
        kho_new = kho.copy()
        kho_new[str(active_id)] = {**st_data, "level": target_level}
        await update_tu_si(inter.user.id, nguyen_lieu=nl_new, sung_thu=kho_new)
        ts_new = await get_tu_si(inter.user.id)

        st = SUNG_THU_BY_ID.get(active_id)
        embed = discord.Embed(
            title=f"⬆️ NÂNG CẤP THÀNH CÔNG!",
            description=(
                f"{st['emoji']} **{st['ten']}** đã lên **Lv{target_level}**!\n"
                f"Buff tăng lên ×{SUNG_THU_LEVEL_MULT[target_level]:.1f}"
            ),
            color=0x57F287)
        # Tạo view mới hoàn toàn để tránh interaction failed
        new_view = SungThuView(self.parent, ts_new, self.user, self.actor_id)
        self.stop()
        try:
            await inter.edit_original_response(embed=_embed_sung_thu_list(ts_new, self.user), view=new_view)
        except Exception:
            log.exception("Lỗi sung_thu")
        await safe_followup(inter, embed=embed, ephemeral=True)

    async def _on_list_all(self, inter: discord.Interaction):
        if inter.user.id != self.actor_id:
            return await inter.response.send_message("❌", ephemeral=True)
        try:
            await inter.response.defer(ephemeral=True)
        except Exception:
            log.exception("Lỗi sung_thu")
        kho = _parse_sung_thu(self.ts)
        lines_t1 = []
        lines_t2 = []
        for st in SUNG_THU:
            owned = str(st["id"]) in kho
            mark = "✅" if owned else "❌"
            src = "BC" if st["drop_bc"] else "Boss"
            line = f"{mark} {st['emoji']} **{st['ten']}** [{HE_TEN[st['he']]}·{src}]"
            if st["tier"] == 1:
                lines_t1.append(line)
            else:
                lines_t2.append(line)

        embeds = []
        if lines_t1:
            e1 = discord.Embed(title="⭐ Sủng Thú Thường", description="\n".join(lines_t1), color=0x4FC3F7)
            e1.set_footer(text="✅ = đã sở hữu | Nguồn: BC = Bí Cảnh, Boss = World Boss")
            embeds.append(e1)
        if lines_t2:
            e2 = discord.Embed(title="💫 Sủng Thú Huyền Thoại", description="\n".join(lines_t2), color=0xFFD700)
            e2.set_footer(text="Drop từ Boss hoặc Ghép (⚗️)")
            embeds.append(e2)
        await safe_followup(inter, embeds=embeds, ephemeral=True)

    async def _on_guide(self, inter: discord.Interaction):
        """Hướng dẫn toàn bộ hệ thống sủng thú — chia nhiều embed tránh 1024 ký tự."""
        if inter.user.id != self.actor_id:
            return await inter.response.send_message("❌", ephemeral=True)
        try:
            await inter.response.defer(ephemeral=True)
        except Exception:
            log.exception("Lỗi sung_thu")

        embeds = _build_guide_embeds(self.ts)
        await safe_followup(inter, embeds=embeds, ephemeral=True)

    async def _on_back(self, inter: discord.Interaction):
        from cogs.hoso_utils import _back_to_hoso
        await _back_to_hoso(inter, self.parent)
