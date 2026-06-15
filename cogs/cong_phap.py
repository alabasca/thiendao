from __future__ import annotations
from typing import Any

import logging
log = logging.getLogger("cong_phap")
import discord
from utils.embeds import safe_followup

from utils.bot_emojis import E_LINH_THACH, CP_CAP_EMOJI, CP_PHAM_EMOJI, E_CAP_THIEN, E_CAP_DIA, E_CAP_HUYEN, E_CAP_HOANG

from data.cong_phap_data import (
    PHAM_DMG_MULT, CAP_DMG_MULT,
    LOAI_SK, LOAI_SK_LABEL,
    LOAI_CD, LOAI_DMGM,
    PHAM_EMOJI, CAP_COLOR, CONG_PHAP,
)

_CP_BY_ID: dict = {}

def _build_index():
    global _CP_BY_ID
    _CP_BY_ID = {cp["id"]: cp for cp in CONG_PHAP}

_build_index()

def _cp_emoji(cap: str, pham: str) -> str | None:
    return CP_PHAM_EMOJI.get((cap, pham)) or None

# Alias giữ tương thích với code cũ
LOAI_CONG_PHAP = {
    "vo_ky":      {"ten": "Võ Kỹ",      "emoji": "<:dia:1482343940999876791>"},
    "than_phap":  {"ten": "Thần Pháp",  "emoji": "<:huyen:1482343942434590751>"},
    "tuyet_ky":   {"ten": "Tuyệt Kỹ",  "emoji": "<:thien:1482343941792595988>"},
    "than_thong": {"ten": "Thần Thông", "emoji": "<:hoang:1482343940299423744>"},
}


def fmt_passive(cp: dict[str, Any]) -> str:
    """Hiển thị passive stats của công pháp với emoji."""
    from utils.bot_emojis import (E_CONG_KICH, E_PHONG_NGU, E_SINH_LUC, E_LINH_LUC,
                                   E_HOI_TAM, E_HO_TAM, E_BAO_KICH, E_KHANG_BAO, CP_PHAM_EMOJI)
    p = cp.get("passive", {})
    em = CP_PHAM_EMOJI.get((cp["cap"], cp["pham"]), "")
    parts = []
    if p.get("atk_pct"):  parts.append(f"{E_CONG_KICH} ATK +{p['atk_pct']}%")
    if p.get("def_pct"):  parts.append(f"{E_PHONG_NGU} DEF +{p['def_pct']}%")
    if p.get("hp_pct"):   parts.append(f"{E_SINH_LUC} HP +{p['hp_pct']}%")
    if p.get("linh_luc"): parts.append(f"{E_LINH_LUC} Linh Lực +{p['linh_luc']}")
    if p.get("hoi_tam"):  parts.append(f"{E_HOI_TAM} Hội Tâm +{p['hoi_tam']:,}đ ({p['hoi_tam']/1000:.1f}%)")
    if p.get("ho_tam"):   parts.append(f"{E_HO_TAM} Hộ Tâm +{p['ho_tam']:,}đ ({p['ho_tam']/1000:.1f}%)")
    if p.get("bao_kich"): parts.append(f"{E_BAO_KICH} Bạo Kích +{p['bao_kich']}%")
    if p.get("khang_bao"):parts.append(f"{E_KHANG_BAO} Kháng Bạo +{p['khang_bao']}%")
    return (f"{em} " + "  ".join(parts)) if parts else "—"

def fmt_pham(cp: dict[str, Any]) -> str:
    """Hiện phẩm có emoji màu."""
    colors = {"Hạ": "⚪", "Trung": "🟢", "Thượng": "🔵", "Cực": "🟣"}
    return f"{colors.get(cp['pham'], '')} {cp['pham']}"

def get_cp(cp_id: int) -> dict | None:
    return _CP_BY_ID.get(cp_id)

def get_cp_active(ts: dict[str, Any]) -> dict[str, Any] | None:
    """Trả về công pháp đang active."""
    return _CP_BY_ID.get(ts.get("cong_phap_active", -1))

def get_cps_owned(ts: dict[str, Any]) -> list:
    """Danh sách công pháp đã học, sắp xếp phẩm cao → thấp."""
    owned = ts.get("cong_phap_hoc", [])
    pham_order = {"Cực": 3, "Thượng": 2, "Trung": 1, "Hạ": 0}
    result = [_CP_BY_ID[i] for i in owned if i in _CP_BY_ID]
    return sorted(result, key=lambda c: (pham_order.get(c["pham"], 0), c["cg_idx"]), reverse=True)

CP_HOC_MAX = 20  # Tối đa 20 công pháp

def can_learn(ts: dict[str, Any], cp: dict[str, Any]) -> tuple:
    owned = ts.get("cong_phap_hoc", [])
    if cp["id"] in owned:
        return False, "Bạn đã học công pháp này rồi!"
    if len(owned) >= CP_HOC_MAX:
        return False, f"Bạn đã đạt giới hạn **{CP_HOC_MAX} công pháp**! Dùng **Lãng Quên** để nhường chỗ."
    # Khóa cảnh giới: công pháp thuộc cảnh giới nào thì cần đạt cảnh giới đó
    player_cg = ts.get("canh_gioi", 0)
    cp_cg     = cp.get("cg_idx", 0)
    if player_cg < cp_cg:
        from utils.config import CANH_GIOI
        cg_yc = CANH_GIOI[cp_cg]["ten"] if cp_cg < len(CANH_GIOI) else f"CG{cp_cg}"
        return False, f"Cần đạt **{cg_yc}** để học công pháp này."
    if ts.get("linh_thach", 0) < cp["gia_mua"]:
        return False, f"Cần {cp['gia_mua']:,} {E_LINH_THACH} để mua."
    return True, ""

def get_active_skill(ts: dict[str, Any], loai: str) -> dict[str, Any] | None:
    """Lấy kỹ năng theo loại từ công pháp active."""
    cp = get_cp_active(ts)
    if not cp:
        return None
    return cp["ky_nang"].get(loai)

# Hệ số passive theo khoảng cách CG (Option D)
# CP cùng CG player: 100%, diff=1: 50%, diff=2: 20%, diff=3+: 5%
_CP_PASSIVE_DECAY = [1.0, 0.5, 0.2, 0.05]

def calc_cp_bonus(ts: dict[str, Any]) -> dict[str, Any]:
    """Tổng passive bonus từ tất cả công pháp đã học — có decay theo CG diff.

    CP cùng cảnh giới player: 100% passive
    Cách 1 CG: 50%  (ví dụ: player CG5, CP CG4)
    Cách 2 CG: 20%
    Cách 3+ CG: 5%  (CP quá thấp gần như không đóng góp)
    """
    bonus = {
        "at_pct": 0.0, "def_pct": 0.0, "hp_pct": 0.0,
        "at_flat": 0,  "df_flat": 0,   "hp_flat": 0,
        "linh_luc": 0, "hoi_tam": 0,   "ho_tam": 0,
        "bao_kich": 0.0, "khang_bao": 0.0,
        # legacy keys for hoso_utils compatibility
        "bk_flat": 0, "ht_flat": 0, "kb_pct": 0,
    }
    owned      = ts.get("cong_phap_hoc", [])
    if not isinstance(owned, list): owned = []
    player_cg  = ts.get("canh_gioi", 0)
    for cp_id in owned:
        cp = _CP_BY_ID.get(cp_id)
        if not cp: continue
        p    = cp.get("passive", {})
        diff = max(0, player_cg - cp.get("cg_idx", 0))
        mult = _CP_PASSIVE_DECAY[min(diff, len(_CP_PASSIVE_DECAY) - 1)]
        bonus["at_pct"]    += p.get("atk_pct", 0) * mult
        bonus["def_pct"]   += p.get("def_pct", 0) * mult
        bonus["hp_pct"]    += p.get("hp_pct",  0) * mult
        bonus["linh_luc"]  += p.get("linh_luc",0) * mult
        bonus["hoi_tam"]   += p.get("hoi_tam", 0) * mult
        bonus["ho_tam"]    += p.get("ho_tam",  0) * mult
        bonus["bao_kich"]  += p.get("bao_kich",0) * mult
        bonus["khang_bao"] += p.get("khang_bao",0)* mult
        # legacy keys
        bonus["bk_flat"]   += p.get("bao_kich",0) * mult
        bonus["ht_flat"]   += p.get("hoi_tam", 0) * mult
        bonus["kb_pct"]    += p.get("khang_bao",0)* mult
    return bonus


# ══════════════════════════════════════════════════════════════
#  DB HELPERS
# ══════════════════════════════════════════════════════════════
async def _reload_ts(user_id: int, fallback: dict) -> dict:
    from utils.database import get_tu_si
    fresh = await get_tu_si(user_id)
    return fresh if fresh else fallback

async def _update_cp(user_id: int, **kwargs):
    from utils.database import update_tu_si_wait
    await update_tu_si_wait(user_id, **kwargs)


# ══════════════════════════════════════════════════════════════
#  VIEW
# ══════════════════════════════════════════════════════════════
class CongPhapView(discord.ui.View):
    """Giao diện mua / trang bị / chọn active công pháp."""

    def __init__(self, parent, ts: dict[str, Any]):
        super().__init__(timeout=300)  # 5 phút
        self.parent = parent
        self.ts     = ts
        self._build_main()

    # ── Main menu ────────────────────────────────────────────
    def _build_main(self):
        self.clear_items()
        opts = [
            discord.SelectOption(label="Thiên — ×1.55", value="Thiên", emoji=discord.PartialEmoji.from_str(E_CAP_THIEN)),
            discord.SelectOption(label="Địa — ×1.40",   value="Địa",   emoji=discord.PartialEmoji.from_str(E_CAP_DIA)),
            discord.SelectOption(label="Huyền — ×1.25", value="Huyền", emoji=discord.PartialEmoji.from_str(E_CAP_HUYEN)),
            discord.SelectOption(label="Hoàng — ×1.10", value="Hoàng", emoji=discord.PartialEmoji.from_str(E_CAP_HOANG)),
        ]
        sel = discord.ui.Select(placeholder="Mua công pháp — Chọn hệ...", options=opts, row=0)
        sel.callback = self._on_cap
        self.add_item(sel)

        btn_active = discord.ui.Button(label="Đặt Active", emoji="⚡",
            style=discord.ButtonStyle.primary, row=1)
        btn_active.callback = self._on_chon_active

        btn_ds = discord.ui.Button(label="Đã học", emoji="📖",
            style=discord.ButtonStyle.secondary, row=1)
        btn_ds.callback = self._on_ds_hoc

        btn_back = discord.ui.Button(label="Quay lại", emoji="◀️",
            style=discord.ButtonStyle.secondary, row=1)
        btn_back.callback = self._on_back

        self.add_item(btn_active)
        self.add_item(btn_ds)
        self.add_item(btn_back)

    # ── Chọn hệ ──────────────────────────────────────────────
    async def _on_cap(self, inter: discord.Interaction):
        try:

            await inter.response.defer(ephemeral=True)

        except Exception:
            log.exception("Lỗi cong_phap")
        cap = inter.data["values"][0]
        self.ts = await _reload_ts(inter.user.id, self.ts)
        # Dropdown phẩm
        self.clear_items()
        _PHAM_LABEL = {"Hạ":"⚪ Hạ — ×1","Trung":"🟢 Trung — ×2","Thượng":"🔵 Thượng — ×4","Cực":"🟣 Cực — ×8"}
        opts = [discord.SelectOption(
            label=_PHAM_LABEL[p],
            value=f"{cap}|{p}") for p in ["Hạ","Trung","Thượng","Cực"]]
        sel = discord.ui.Select(placeholder=f"[{cap}] Chọn phẩm...", options=opts, row=0)
        sel.callback = self._on_pham
        btn_back = discord.ui.Button(label="Quay lại", style=discord.ButtonStyle.secondary, row=1)
        btn_back.callback = self._back_to_main
        self.add_item(sel)
        self.add_item(btn_back)
        embed = discord.Embed(
            title=f"{CP_CAP_EMOJI.get(cap,'')} Hệ {cap} — Chọn phẩm",
            description=(
                f"Hệ số hệ chiến đấu: **×{CAP_DMG_MULT.get(cap,1.0)}** (nhân với hệ số phẩm)\n"
                f"⚪ **Hạ** — ×{PHAM_DMG_MULT['Hạ']} × ×{CAP_DMG_MULT.get(cap,1.0)} = **×{PHAM_DMG_MULT['Hạ']*CAP_DMG_MULT.get(cap,1.0):.3g}**\n"
                f"🟢 **Trung** — ×{PHAM_DMG_MULT['Trung']} × ×{CAP_DMG_MULT.get(cap,1.0)} = **×{PHAM_DMG_MULT['Trung']*CAP_DMG_MULT.get(cap,1.0):.3g}**\n"
                f"🔵 **Thượng** — ×{PHAM_DMG_MULT['Thượng']} × ×{CAP_DMG_MULT.get(cap,1.0)} = **×{PHAM_DMG_MULT['Thượng']*CAP_DMG_MULT.get(cap,1.0):.3g}**\n"
                f"🟣 **Cực** — ×{PHAM_DMG_MULT['Cực']} × ×{CAP_DMG_MULT.get(cap,1.0)} = **×{PHAM_DMG_MULT['Cực']*CAP_DMG_MULT.get(cap,1.0):.3g}**"
            ),
            color=CAP_COLOR.get(cap, 0xAAAAAA))
        try:
            await inter.edit_original_response(embed=embed, view=self)
        except Exception:
            await safe_followup(inter, embed=embed, view=self, ephemeral=True)

    # ── Chọn phẩm ────────────────────────────────────────────
    async def _on_pham(self, inter: discord.Interaction):
        try:

            await inter.response.defer(ephemeral=True)

        except Exception:
            log.exception("Lỗi cong_phap")
        cap, pham = inter.data["values"][0].split("|")
        self.ts = await _reload_ts(inter.user.id, self.ts)
        player_cg = self.ts.get("canh_gioi", 0)
        cp_list = [c for c in CONG_PHAP if c["cap"] == cap and c["pham"] == pham]
        owned   = set(self.ts.get("cong_phap_hoc", []))

        # Nếu không có công pháp nào trong hệ+phẩm này → báo lỗi, không tạo Select rỗng
        if not cp_list:
            await safe_followup(inter, 
                f"❌ Chưa có công pháp nào thuộc hệ **{cap} — {pham}**!",
                ephemeral=True)
            return

        self.clear_items()
        opts = []
        for cp in cp_list[:25]:
            locked = cp["cg_idx"] > player_cg
            tick   = "✅ " if cp["id"] in owned else ("🔒 " if locked else "")
            opts.append(discord.SelectOption(
                label=f"{tick}{cp['ten']} — {cp['canh_gioi']}",
                description=f"{cp['gia_mua']:,} LT" + (" [Chưa đủ CG]" if locked else ""),
                value=str(cp["id"])))
        sel = discord.ui.Select(
            placeholder=f"[{cap} {pham}] Chọn công pháp...", options=opts, row=0)
        sel.callback = self._on_cp_select
        btn_back = discord.ui.Button(label="Quay lại", style=discord.ButtonStyle.secondary, row=1)
        btn_back.callback = self._back_to_main
        self.add_item(sel)
        self.add_item(btn_back)

        lines = []
        for cp in cp_list:
            locked = cp["cg_idx"] > player_cg
            tick   = "✅" if cp["id"] in owned else ("🔒" if locked else "○")
            lines.append(f"{tick} **{cp['ten']}** — {cp['canh_gioi']} — {cp['gia_mua']:,} LT")
        embed = discord.Embed(
            title=f"{CP_CAP_EMOJI.get(cap,'')} {_cp_emoji(cap, pham)} {cap} {pham}",
            description="\n".join(lines),
            color=CAP_COLOR.get(cap, 0xAAAAAA))
        try:
            await inter.edit_original_response(embed=embed, view=self)
        except Exception:
            await safe_followup(inter, embed=embed, view=self, ephemeral=True)

    # ── Chi tiết công pháp ────────────────────────────────────
    async def _on_cp_select(self, inter: discord.Interaction):
        try:

            await inter.response.defer(ephemeral=True)

        except Exception:
            log.exception("Lỗi cong_phap")
        cp_id = int(inter.data["values"][0])
        cp = get_cp(cp_id)
        if not cp:
            return await safe_followup(inter, "❌ Không tìm thấy công pháp!", ephemeral=True)
        self.ts = await _reload_ts(inter.user.id, self.ts)
        owned    = set(self.ts.get("cong_phap_hoc", []))
        active_id = self.ts.get("cong_phap_active", -1)

        embed = discord.Embed(
            title=f"{_cp_emoji(cp['cap'], cp['pham'])} {cp['ten']}",
            description=(
                f"**Hệ:** {cp['cap']}  │  **Phẩm:** {cp['pham']}  │  **Cảnh giới:** {cp['canh_gioi']}\n"
                f"**Hệ số tấn công:** ×{PHAM_DMG_MULT[cp['pham']]} × ×{CAP_DMG_MULT.get(cp['cap'],1.0)} = **×{PHAM_DMG_MULT[cp['pham']]*CAP_DMG_MULT.get(cp['cap'],1.0):.2g}**\n"
                f"**Giá mua:** {cp['gia_mua']:,} {E_LINH_THACH}"
            ),
            color=CAP_COLOR.get(cp["cap"], 0xAAAAAA))
        embed.add_field(name="📊 Passive (khi học)", value=fmt_passive(cp), inline=False)
        for loai in LOAI_SK:
            s = cp["ky_nang"].get(loai)
            if s:
                embed.add_field(
                    name=f"{LOAI_SK_LABEL[loai]} — {s['ten']}  (CD {s['cd']}s · LL {s['ll']})",
                    value=s["mo_ta"], inline=False)

        self.clear_items()
        if cp_id not in owned:
            ok, reason = can_learn(self.ts, cp)
            btn_mua = discord.ui.Button(
                label=f"Mua {cp['gia_mua']:,} LT",
                emoji=discord.PartialEmoji(name="LinhThach", id=1481645991181553796),
                style=discord.ButtonStyle.success if ok else discord.ButtonStyle.secondary,
                disabled=not ok, row=0)
            async def _on_mua(i, _cp=cp):
                await i.response.defer(ephemeral=True)
                ts2 = await _reload_ts(i.user.id, self.ts)
                ok2, r2 = can_learn(ts2, _cp)
                if not ok2:
                    return await safe_followup(i, f"❌ {r2}", ephemeral=True)
                new_owned = list(ts2.get("cong_phap_hoc", [])) + [_cp["id"]]
                from utils.database import add_linh_thach as _alt_lt
                await _alt_lt(i.user.id, -_cp["gia_mua"])
                await _update_cp(i.user.id, cong_phap_hoc=new_owned)
                self.ts = await _reload_ts(i.user.id, ts2)
                e2 = discord.Embed(
                    title=f"✅ Đã học {_cp['ten']}!",
                    description=(
                        f"Tốn {_cp['gia_mua']:,} {E_LINH_THACH}\n"
                        f"Dùng **⚡ Đặt Active** để sử dụng trong chiến đấu."
                    ), color=0x2ECC71)
                await safe_followup(i, embed=e2, ephemeral=True)
            btn_mua.callback = _on_mua
            if not ok:
                embed.set_footer(text=f"⚠️ {reason}")
            self.add_item(btn_mua)
        else:
            is_active = (active_id == cp_id)
            btn_act = discord.ui.Button(
                label="✅ Đang active" if is_active else "⚡ Đặt làm active",
                style=discord.ButtonStyle.secondary if is_active else discord.ButtonStyle.primary,
                disabled=is_active, row=0)
            async def _on_set_active(i, _id=cp_id, _name=cp["ten"], _pham=cp["pham"]):
                await i.response.defer(ephemeral=True)
                await _update_cp(i.user.id, cong_phap_active=_id)
                self.ts = await _reload_ts(i.user.id, self.ts)
                await safe_followup(i, 
                    f"⚡ **{_name}** ({_pham} ×{PHAM_DMG_MULT[_pham]}) đã được đặt active!",
                    ephemeral=True)
            btn_act.callback = _on_set_active
            self.add_item(btn_act)
            # Nút Lãng Quên — chi phí 50% giá mua
            lang_quen_gia = max(500, int(cp["gia_mua"] * 0.5))
            btn_lq = discord.ui.Button(
                label=f"🗑️ Lãng Quên ({lang_quen_gia:,} LT)",
                style=discord.ButtonStyle.danger, row=0)
            async def _on_lang_quen(i, _id=cp_id, _name=cp["ten"], _gia=lang_quen_gia):
                await i.response.defer(ephemeral=True)
                ts3 = await _reload_ts(i.user.id, self.ts)
                if ts3.get("linh_thach", 0) < _gia:
                    return await safe_followup(i, 
                        f"❌ Cần **{_gia:,}** {E_LINH_THACH} để lãng quên!", ephemeral=True)
                new_owned = [x for x in ts3.get("cong_phap_hoc", []) if x != _id]
                new_active = ts3.get("cong_phap_active", -1)
                if new_active == _id:
                    new_active = new_owned[0] if new_owned else -1
                from utils.database import add_linh_thach as _alt_lt
                await _alt_lt(i.user.id, -_gia)
                await _update_cp(i.user.id, cong_phap_hoc=new_owned, cong_phap_active=new_active)
                self.ts = await _reload_ts(i.user.id, ts3)
                await safe_followup(i, 
                    f"🗑️ Đã lãng quên **{_name}**. Tốn **{_gia:,}** {E_LINH_THACH}.",
                    ephemeral=True)
            btn_lq.callback = _on_lang_quen
            self.add_item(btn_lq)

        btn_back = discord.ui.Button(label="Quay lại", style=discord.ButtonStyle.secondary, row=1)
        btn_back.callback = self._back_to_main
        self.add_item(btn_back)
        try:
            await inter.edit_original_response(embed=embed, view=self)
        except Exception:
            await safe_followup(inter, embed=embed, view=self, ephemeral=True)

    # ── Đặt active ───────────────────────────────────────────
    async def _on_chon_active(self, inter: discord.Interaction):
        try:

            await inter.response.defer(ephemeral=True)

        except Exception:
            log.exception("Lỗi cong_phap")
        self.ts = await _reload_ts(inter.user.id, self.ts)
        owned_cps = get_cps_owned(self.ts)
        if not owned_cps:
            return await safe_followup(inter, "❌ Bạn chưa học công pháp nào!", ephemeral=True)
        active_id = self.ts.get("cong_phap_active", -1)
        opts = []
        for cp in owned_cps[:25]:
            tag = "⚡ " if cp["id"] == active_id else ""
            opts.append(discord.SelectOption(
                label=f"{tag}{PHAM_EMOJI.get(cp['pham'],'')}{cp['ten']} — {cp['canh_gioi']}",
                description=f"Hệ {cp['cap']} {cp['pham']} — ×{PHAM_DMG_MULT[cp['pham']]}",
                value=str(cp["id"]),
                default=(cp["id"] == active_id)))
        view2 = discord.ui.View(timeout=300)
        sel = discord.ui.Select(placeholder="Chọn công pháp active...", options=opts)
        async def _sel_cb(i2):
            try:
                await i2.response.defer(ephemeral=True)
            except Exception:
                log.exception("Lỗi cong_phap")
            new_id = int(i2.data["values"][0])
            await _update_cp(i2.user.id, cong_phap_active=new_id)
            cp2 = get_cp(new_id)
            try:
                await safe_followup(i2, 
                    f"⚡ **{cp2['ten']}** ({cp2['pham']} ×{PHAM_DMG_MULT[cp2['pham']]}) đã active!\n"
                    f"Kỹ năng trong chiến đấu sẽ dùng: "
                    + " / ".join(cp2["ky_nang"][l]["ten"] for l in LOAI_SK if cp2["ky_nang"].get(l)),
                    ephemeral=True)
            except Exception:
                log.exception("Lỗi cong_phap")
        sel.callback = _sel_cb
        view2.add_item(sel)
        try:
            await safe_followup(inter, "⚡ Chọn công pháp active:", view=view2, ephemeral=True)
        except Exception:
            log.exception("Lỗi cong_phap")

    # ── Danh sách đã học ─────────────────────────────────────
    async def _on_ds_hoc(self, inter: discord.Interaction):
        try:
            await inter.response.defer(ephemeral=True)
        except Exception:
            log.exception("Lỗi cong_phap")
        self.ts = await _reload_ts(inter.user.id, self.ts)
        owned_cps = get_cps_owned(self.ts)
        if not owned_cps:
            return await safe_followup(inter, "📖 Chưa học công pháp nào.", ephemeral=True)
        active_id = self.ts.get("cong_phap_active", -1)
        player_cg = self.ts.get("canh_gioi", 0)
        cp_active = get_cp_active(self.ts)
        footer = (f"⚡ Active: {cp_active['ten']}  |  " if cp_active else "")
        footer += "Passive decay: cùng CG=100% | -1 CG=50% | -2 CG=20% | -3+ CG=5%"

        # Chia thành nhiều embed nếu quá dài (Discord limit 4096 chars/embed)
        embeds = []
        cur_lines = []
        cur_len   = 0
        LIMIT     = 3800  # buffer an toàn dưới 4096

        pham_colors = {"Hạ": "⚪", "Trung": "🟢", "Thượng": "🔵", "Cực": "🟣"}
        for cp in owned_cps:
            tag   = " ⚡" if cp["id"] == active_id else ""
            diff  = max(0, player_cg - cp.get("cg_idx", 0))
            mult  = _CP_PASSIVE_DECAY[min(diff, len(_CP_PASSIVE_DECAY) - 1)]
            decay_tag = "" if mult == 1.0 else f" *(passive ×{mult:.0%})*"
            p     = cp.get("passive", {})
            # Compact passive: chỉ hiện % stats quan trọng
            pstats = []
            if p.get("atk_pct"):  pstats.append(f"ATK +{p['atk_pct']}%")
            if p.get("def_pct"):  pstats.append(f"DEF +{p['def_pct']}%")
            if p.get("hp_pct"):   pstats.append(f"HP +{p['hp_pct']}%")
            if p.get("linh_luc"): pstats.append(f"LL +{p['linh_luc']}")
            if p.get("hoi_tam"):  pstats.append(f"HT +{p['hoi_tam']:,}đ")
            if p.get("ho_tam"):   pstats.append(f"HoT +{p['ho_tam']:,}đ")
            if p.get("bao_kich"): pstats.append(f"BK +{p['bao_kich']}%")
            if p.get("khang_bao"):pstats.append(f"KB +{p['khang_bao']}%")
            sk_names = " / ".join(cp["ky_nang"][l]["ten"] for l in LOAI_SK if cp["ky_nang"].get(l))
            pc = pham_colors.get(cp["pham"], "⚪")
            line = (
                f"{pc} **{cp['ten']}**{tag}"
                f" — {cp['cap']} {cp['pham']} {cp['canh_gioi']}{decay_tag}\n"
                f"  ↳ {sk_names}\n"
                f"  {' · '.join(pstats)}"
            )
            if cur_len + len(line) + 1 > LIMIT and cur_lines:
                embeds.append(discord.Embed(
                    title=f"📖 Công pháp đã học ({len(embeds)+1})",
                    description="\n".join(cur_lines),
                    color=0x5865F2))
                cur_lines = [line]
                cur_len   = len(line)
            else:
                cur_lines.append(line)
                cur_len += len(line) + 1

        if cur_lines:
            title = f"📖 Công pháp đã học" if len(embeds) == 0 else f"📖 Công pháp đã học ({len(embeds)+1})"
            embeds.append(discord.Embed(
                title=title,
                description="\n".join(cur_lines),
                color=0x5865F2))

        embeds[-1].set_footer(text=footer)

        # Dropdown lãng quên — chọn CP muốn xóa
        pham_emoji = {"Hạ": "⚪", "Trung": "🟢", "Thượng": "🔵", "Cực": "🟣"}
        forget_opts = [
            discord.SelectOption(
                label=f"{cp['ten']} — {cp['cap']} {cp['pham']} {cp['canh_gioi']}"[:100],
                value=str(cp["id"]),
                description=f"Lãng quên: {max(500, int(cp['gia_mua']*0.5)):,} LT",
                emoji=pham_emoji.get(cp["pham"], "⚪")
            )
            for cp in owned_cps
        ]
        view_forget = discord.ui.View(timeout=120)
        sel_forget = discord.ui.Select(
            placeholder="🗑️ Chọn công pháp muốn Lãng Quên...",
            options=forget_opts[:25],
            min_values=0, max_values=1,
            row=0)

        async def _on_forget_select(inter2: discord.Interaction):
            if not inter2.data.get("values"):
                return await inter2.response.defer()
            await inter2.response.defer(ephemeral=True)
            cp_id_f = int(inter2.data["values"][0])
            cp_f = get_cp(cp_id_f)
            if not cp_f:
                return await inter2.followup.send("❌ Không tìm thấy!", ephemeral=True)
            ts_f = await _reload_ts(inter2.user.id, self.ts)
            gia_f = max(500, int(cp_f["gia_mua"] * 0.5))
            if ts_f.get("linh_thach", 0) < gia_f:
                return await inter2.followup.send(
                    f"❌ Cần **{gia_f:,}** {E_LINH_THACH} để lãng quên!", ephemeral=True)
            new_owned = [x for x in ts_f.get("cong_phap_hoc", []) if x != cp_id_f]
            new_active = ts_f.get("cong_phap_active", -1)
            if new_active == cp_id_f:
                new_active = new_owned[0] if new_owned else -1
            from utils.database import add_linh_thach as _alt_lt
            await _alt_lt(inter2.user.id, -gia_f)
            await _update_cp(inter2.user.id, cong_phap_hoc=new_owned, cong_phap_active=new_active)
            self.ts = await _reload_ts(inter2.user.id, ts_f)
            await inter2.followup.send(
                f"🗑️ Đã lãng quên **{cp_f['ten']}**. Tốn **{gia_f:,}** {E_LINH_THACH}.",
                ephemeral=True)

        sel_forget.callback = _on_forget_select
        view_forget.add_item(sel_forget)

        # Gửi từng embed (tối đa 10 embeds/message theo Discord limit)
        await safe_followup(inter, embeds=embeds[:10], view=view_forget, ephemeral=True)

    async def _back_to_main(self, inter: discord.Interaction):
        try:

            await inter.response.defer(ephemeral=True)

        except Exception:
            log.exception("Lỗi cong_phap")
        self._build_main()
        embed = discord.Embed(
            title="📚 Công Pháp",
            description="Mua công pháp mới hoặc quản lý công pháp đã học.",
            color=0x5865F2)
        try:
            await inter.edit_original_response(embed=embed, view=self)
        except Exception:
            await safe_followup(inter, embed=embed, view=self, ephemeral=True)

    async def _on_back(self, inter: discord.Interaction):
        from cogs.views._common import _back_to_hoso
        await _back_to_hoso(inter, self.parent)


async def setup(bot):
    """discord.py cog setup — cong_phap.py chỉ là data/view module, không có Cog riêng."""
    pass
