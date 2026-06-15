"""
View đột phá thể chất — mở từ hồ sơ chính
"""
from __future__ import annotations
from typing import Any

from cogs.views._common import *
import re
import json
from utils.config import (
    THE_CHAT_BY_ID, DOTPHA_TC_NGUYEN_LIEU, DOTPHA_TC_POOL,
    DOTPHA_TC_NL_BY_ID, DOTPHA_TC_APEX_RATE_OVERRIDE,
)
from utils.bot_emojis import (
    E_TULOICAMQUY, E_HUYETHONXAHUONG, E_COCTRUCTANG,
    E_NGUNGCANNHU, E_HUYETCHIHOALINH,
)

log = logging.getLogger("hoso")

def _dtc_kho(ts: dict[str, Any]) -> dict:
    """Parse dotpha_tc_nl từ DB (str JSON hoặc dict)."""
    raw = ts.get("dotpha_tc_nl", {})
    if isinstance(raw, dict): return raw
    try: return json.loads(raw) if raw else {}
    except Exception: return {}

# Pool key theo số nguyên liệu
def _get_pool_key(n: int) -> str:
    """1 NL → low · 3 NL → mid · 5 NL → apex. Pool chỉ thay đổi tại 1/3/5."""
    if n >= 5: return "apex"
    if n >= 3: return "mid"
    return "low"

# Tier labels cho embed
_TIER = {
    "low":  ("⚔️ Pool Cơ Bản",   "Cửu Biến · Thiên Mệnh · Băng Hỏa",   "8%"),
    "mid":  ("🔥 Pool Mở Rộng",  "+ Lôi Ngục · Huyền Âm · Thái Dương", "2%"),
    "apex": ("✨ Pool Tối Đa",    "+ Hỗn Độn · Vô Thủy",                 "5%"),
}


def _spin(pool_key: str) -> str:
    """Random thể chất theo pool, trả về tc_id.
    Với pool apex: override rate của Hỗn Độn/Vô Thủy lên 5%.
    """
    pool = DOTPHA_TC_POOL[pool_key]
    tcs  = [tc for tc in pool if tc in THE_CHAT_BY_ID]
    if pool_key == "apex":
        weights = [
            DOTPHA_TC_APEX_RATE_OVERRIDE.get(tc, THE_CHAT_BY_ID[tc]["rate"])
            for tc in tcs
        ]
    else:
        weights = [THE_CHAT_BY_ID[tc]["rate"] for tc in tcs]
    return random.choices(tcs, weights=weights, k=1)[0]


def _embed_chon(ts: dict[str, Any]) -> discord.Embed:
    tc_cur = THE_CHAT_BY_ID.get(ts.get("the_chat", ""))
    tc_str = f"{tc_cur['emoji']} **{tc_cur['ten']}** [{tc_cur['rate']}%]" if tc_cur else "*(chưa xác định)*"
    kho    = _dtc_kho(ts)

    embed = discord.Embed(
        title="🧬 ĐỘT PHÁ THỂ CHẤT",
        description=(
            "Kích hoạt tiềm năng căn cơ bằng tài nguyên thiên địa.\n"
            "**Mỗi lần đột phá chỉ tiêu thụ ×1 mỗi tài nguyên đã chọn.**\n"
            "Kết quả **ngẫu nhiên** — số tài nguyên càng nhiều, pool càng tốt."
        ),
        color=0xF0A500)
    embed.add_field(name="Thể chất hiện tại", value=tc_str, inline=False)

    nl_lines = []
    for nl in DOTPHA_TC_NGUYEN_LIEU:
        so_huu = kho.get(nl["id"], 0)
        status = f"**{so_huu}**" if so_huu > 0 else "~~0~~"
        nl_lines.append(f"{nl['emoji']} {nl['ten']} — {status}")
    embed.add_field(name="📦 Tài nguyên trong kho", value="\n".join(nl_lines), inline=False)

    embed.add_field(
        name="🎲 Pool theo số tài nguyên chọn",
        value=(
            "⚔️ **1 NL:** Pool cơ bản — Cửu Biến · Thiên Mệnh · Băng Hỏa *(8%)*\n"
            "🔥 **3 NL:** Pool mở rộng — thêm Lôi Ngục · Huyền Âm · Thái Dương *(2%)*\n"
            "✨ **5 NL:** Pool tối đa — thêm Hỗn Độn · Vô Thủy *(5%)*\n"
            "*(2 NL → cơ bản · 4 NL → mở rộng)*\n"
            "⚠️ *Mỗi lần đột phá tiêu ×1 tài nguyên đã chọn — dù nhận hay hủy.*"
        ),
        inline=False)
    embed.set_footer(text="Tích vào tài nguyên muốn dùng rồi bấm Đột Phá.")
    return embed


def _embed_ket_qua(tc_new: dict, tc_old: dict, n_used: int, pool_key: str) -> discord.Embed:
    rate   = tc_new["rate"]
    # Với apex pool, hiển thị rate override nếu là TC hiếm
    display_rate = DOTPHA_TC_APEX_RATE_OVERRIDE.get(tc_new["id"], rate) if pool_key == "apex" else rate
    is_leg  = rate <= 0.5
    is_rare = rate <= 2.0
    color   = 0xE879F9 if is_leg else (0xF0A500 if is_rare else 0x57F287)
    title   = ("✨ HUYỀN THOẠI! " if is_leg else ("🔥 " if is_rare else "")) + tc_new["ten"]

    tier_name, _, tier_pct = _TIER.get(pool_key, ("—", "—", "—"))

    embed = discord.Embed(title="🧬 KẾT QUẢ ĐỘT PHÁ", color=color)
    embed.add_field(
        name="Thể chất mới",
        value=f"{tc_new['emoji']} **{title}** [{display_rate}%]",
        inline=False)
    embed.add_field(
        name="So sánh",
        value=(
            f"{tc_old['emoji']} {tc_old['ten']} [{tc_old.get('rate', '?')}%]\n"
            f"↓\n"
            f"{tc_new['emoji']} **{tc_new['ten']}** [{display_rate}%]"
        ),
        inline=False)
    embed.add_field(
        name="💡 Thông tin",
        value=(
            f"Dùng **{n_used}** tài nguyên — {tier_name} *(pool {tier_pct})*\n"
            f"Tài nguyên đã tiêu thụ dù nhận hay hủy."
        ),
        inline=False)
    embed.set_footer(text="Nhận để áp dụng · Hủy để giữ thể chất cũ.")
    return embed


class DotPhaTCView(discord.ui.View):
    """View đột phá thể chất — phase 1 chọn tài nguyên."""
    def __init__(self, parent, ts: dict[str, Any], actor_id: int = None):
        super().__init__(timeout=120)
        self.parent   = parent
        self.ts       = ts
        self.actor_id = actor_id or parent.owner_id
        self.selected = set()
        self._build()

    def _build(self):
        self.clear_items()
        kho = _dtc_kho(self.ts).copy()

        opts = []
        for nl in DOTPHA_TC_NGUYEN_LIEU:
            so = kho.get(nl["id"], 0)
            em_str   = nl["emoji"]
            em_match = re.match(r"<:(\w+):(\d+)>", em_str)
            pe = discord.PartialEmoji(name=em_match.group(1), id=int(em_match.group(2))) if em_match else None
            opts.append(discord.SelectOption(
                label=nl["ten"],
                value=nl["id"],
                description=f"Trong kho: {so}  {'✅' if so > 0 else '❌ Hết'}",
                emoji=pe,
                default=(nl["id"] in self.selected),
            ))
        sel = discord.ui.Select(
            placeholder="Chọn tài nguyên muốn dùng...",
            options=opts,
            min_values=0,
            max_values=len(opts),
            row=0)
        sel.callback = self._on_select
        self.add_item(sel)

        n          = len(self.selected)
        pool_key   = _get_pool_key(n)
        tier_name, tier_desc, tier_pct = _TIER.get(pool_key, ("—", "—", "—"))
        can_spin   = n > 0 and all(kho.get(nl_id, 0) > 0 for nl_id in self.selected)

        # Label nút đột phá: hiển thị pool hiện tại
        if n == 0:
            btn_label = "🔥 Đột Phá"
        else:
            btn_label = f"🔥 Đột Phá ({n} NL · {tier_name} · {tier_pct})"

        btn_spin = discord.ui.Button(
            label=btn_label,
            style=discord.ButtonStyle.primary,
            disabled=not can_spin,
            row=1)
        btn_spin.callback = self._on_spin

        btn_back = discord.ui.Button(
            label="◀ Quay lại",
            style=discord.ButtonStyle.secondary,
            row=1)
        btn_back.callback = self._on_back

        self.add_item(btn_spin)
        self.add_item(btn_back)

    async def _on_select(self, inter: discord.Interaction):
        if inter.user.id != self.actor_id:
            return await inter.response.send_message("❌", ephemeral=True)
        self.selected = set(inter.data["values"])
        self._build()
        await inter.response.edit_message(embed=_embed_chon(self.ts), view=self)

    async def _on_spin(self, inter: discord.Interaction):
        if inter.user.id != self.actor_id:
            return await inter.response.send_message("❌", ephemeral=True)
        if not await safe_defer(inter, ephemeral=True):
            return

        ts_fresh = await get_tu_si(inter.user.id)
        kho      = _dtc_kho(ts_fresh).copy()

        # Kiểm tra đủ tài nguyên
        for nl_id in self.selected:
            if kho.get(nl_id, 0) < 1:
                nl   = DOTPHA_TC_NL_BY_ID.get(nl_id)
                name = nl["ten"] if nl else nl_id
                return await safe_followup(inter, 
                    f"❌ Không đủ **{name}** (cần ×1, kho: {kho.get(nl_id, 0)})!", ephemeral=True)

        # Trừ ×1 mỗi loại đã chọn
        for nl_id in self.selected:
            kho[nl_id] = kho[nl_id] - 1
        await update_tu_si(inter.user.id, dotpha_tc_nl=kho)

        # Spin
        pool_key  = _get_pool_key(len(self.selected))
        tc_new_id = _spin(pool_key)
        tc_new    = THE_CHAT_BY_ID[tc_new_id]
        tc_old    = THE_CHAT_BY_ID.get(ts_fresh.get("the_chat", ""),
                                        {"ten": "?", "emoji": "?", "rate": 0})

        view_kq = DotPhaTCKetQuaView(
            self.parent, tc_new_id, tc_old,
            len(self.selected), pool_key, ts_fresh, actor_id=self.actor_id)
        await inter.edit_original_response(
            embed=_embed_ket_qua(tc_new, tc_old, len(self.selected), pool_key),
            view=view_kq)

    async def _on_back(self, inter: discord.Interaction):
        from cogs.hoso_utils import _back_to_hoso
        await _back_to_hoso(inter, self.parent)


class DotPhaTCKetQuaView(discord.ui.View):
    """Phase 2 — nhận hoặc hủy thể chất mới."""
    def __init__(self, parent, tc_new_id: str, tc_old: dict,
                 n_used: int, pool_key: str, ts: dict[str, Any], actor_id: int = None):
        super().__init__(timeout=120)
        self.parent    = parent
        self.tc_new_id = tc_new_id
        self.tc_old    = tc_old
        self.n_used    = n_used
        self.pool_key  = pool_key
        self.ts        = ts
        self.actor_id  = actor_id or parent.owner_id

        btn_accept = discord.ui.Button(
            label="✅ Nhận Thể Chất Mới",
            style=discord.ButtonStyle.success, row=0)
        btn_reject = discord.ui.Button(
            label="🗑️ Hủy Kết Quả",
            style=discord.ButtonStyle.danger, row=0)
        btn_accept.callback = self._on_accept
        btn_reject.callback = self._on_reject
        self.add_item(btn_accept)
        self.add_item(btn_reject)

    async def _on_accept(self, inter: discord.Interaction):
        if inter.user.id != self.actor_id:
            return await inter.response.send_message("❌", ephemeral=True)
        if not await safe_defer(inter, ephemeral=True):
            return
        await update_tu_si(inter.user.id, the_chat=self.tc_new_id)
        tc_new       = THE_CHAT_BY_ID[self.tc_new_id]
        display_rate = DOTPHA_TC_APEX_RATE_OVERRIDE.get(self.tc_new_id, tc_new["rate"]) \
                       if self.pool_key == "apex" else tc_new["rate"]
        embed = discord.Embed(
            title="✅ Đột Phá Thành Công!",
            description=(
                f"{tc_new['emoji']} **{tc_new['ten']}** [{display_rate}%]\n"
                "Thể chất mới đã được áp dụng!"
            ),
            color=0x57F287)
        await inter.edit_original_response(embed=embed, view=None)

    async def _on_reject(self, inter: discord.Interaction):
        if inter.user.id != self.actor_id:
            return await inter.response.send_message("❌", ephemeral=True)
        if not await safe_defer(inter, ephemeral=True):
            return
        embed = discord.Embed(
            title="🗑️ Đã Hủy Kết Quả",
            description=(
                f"Giữ nguyên {self.tc_old['emoji']} **{self.tc_old['ten']}**.\n"
                "Tài nguyên đã tiêu thụ."
            ),
            color=0x888780)
        await inter.edit_original_response(embed=embed, view=None)
