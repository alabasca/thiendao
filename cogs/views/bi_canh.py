from __future__ import annotations
from typing import Any

from utils.config import PHAP_BAO_SKILL, PHAP_BAO_BY_ID, LINH_QUA_BC_DROP, DOTPHA_TC_NGUYEN_LIEU, DOTPHA_TC_DROP_RATE, DOTPHA_TC_NL_BY_ID
from utils.config import SUNG_THU
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from cogs.hoso import HoSoView

def _dtc_kho(ts: dict[str, Any]) -> dict:
    """Parse dotpha_tc_nl từ DB (có thể là str JSON hoặc dict)."""
    raw = ts.get("dotpha_tc_nl", {})
    if isinstance(raw, dict): return raw
    try: return json.loads(raw) if raw else {}
    except Exception: return {}
from cogs.views._common import *
from utils.embeds import e_loi, e_ok, e_warn, e_info
import json
import re as _re
import logging
log = logging.getLogger("hoso")

BC_CHON_IMG = "images/chon_bi_canh.png"
from dataclasses import dataclass, field
from utils.bot_emojis import (
    E_SINH_LUC, E_LINH_LUC, E_CONG_KICH, E_PHONG_NGU,
    E_LINH_THACH, E_TT_LINH_THACH, E_TU_VI,
    E_HP_START, E_HP_MID, E_HP_END,
    E_HP_START_E, E_HP_MID_E, E_HP_END_E,
    E_LL_START, E_LL_MID, E_LL_END,
    E_LL_START_E, E_LL_MID_E, E_LL_END_E,
    E_HOI_TAM, E_HO_TAM, E_BAO_KICH, E_KHANG_BAO,
)

# BiCanhSession và _bc_sessions được import từ hoso_utils khi cần,
# nhưng vì bi_canh.py được import bởi hoso.py nên sẽ dùng trực tiếp
# Các hàm helper từ hoso_utils sẽ được inject khi import
from cogs.hoso_utils import (
    _cleanup_stale_sessions, _bc_sessions, BiCanhSession,
    _calc_stats, _calc_full_stats, SESSION_TIMEOUT_SECS,
    _scale_rooms_by_rebirth,
    _get_mount_level,
)

def _embed_bi_canh_chon(ts: dict[str, Any], user) -> discord.Embed:
    cg      = get_cg(ts["canh_gioi"])
    tl_hien  = get_the_luc(ts)
    tl_max   = the_luc_toi_da(ts.get("canh_gioi", 0))
    tran_hien = get_tran_the_luc(ts)
    if tl_hien < tl_max:
        hoi_tiep = THE_LUC_HOI - (int(time.time()) - ts.get("the_luc_cap_nhat", 0)) % THE_LUC_HOI
        tl_str  = f"{tl_hien}/{tl_max} ⚡  *(+1 sau {hoi_tiep}s)*"
    else:
        tl_str  = f"{tl_hien}/{tl_max} ⚡"
    # Tràn thể lực
    if tran_hien > 0 or tl_hien >= tl_max:
        if tran_hien < TRAN_THE_LUC_MAX:
            hoi_tran = TRAN_THE_LUC_HOI - (int(time.time()) - ts.get("tran_the_luc_cap_nhat", 0)) % TRAN_THE_LUC_HOI
            tl_str += f"\n🔋 Tràn: {tran_hien}/{TRAN_THE_LUC_MAX}  *(+1 sau {hoi_tran}s)*"
        else:
            tl_str += f"\n🔋 Tràn: {tran_hien}/{TRAN_THE_LUC_MAX} *(đầy)*"
    embed = discord.Embed(
        title="✦ KHÁM PHÁ BÍ CẢNH",
        description="Nơi chứa đựng vô vàn cơ duyên nhưng cũng đầy rẫy hiểm nguy.",
        color=cg["mau"])
    embed.add_field(name=f"Thể lực",            value=tl_str,    inline=False)
    embed.add_field(name="Cảnh giới hiện tại",  value=cg["ten"], inline=False)
    embed.set_footer(text="Vào bí cảnh tốn 10 ⚡  •  Hồi 1 ⚡/phút")
    if os.path.exists(BC_CHON_IMG):
        embed.set_image(url=f"attachment://{os.path.basename(BC_CHON_IMG)}")
    return embed



async def _send_bi_canh_embed(inter, embed, view, *, respond=True):
    """Gửi/edit embed bí cảnh kèm ảnh nếu có.
    respond=True  → dùng response.send_message (chưa respond)
    respond=False → dùng followup.send (đã defer trước đó)
    """
    if os.path.exists(BC_CHON_IMG):
        f = discord.File(BC_CHON_IMG, filename=os.path.basename(BC_CHON_IMG))
        if respond:
            await inter.response.send_message(embed=embed, file=f, view=view, ephemeral=True)
        else:
            await safe_followup(inter, embed=embed, file=f, view=view, ephemeral=True)
    else:
        if respond:
            await inter.response.send_message(embed=embed, view=view, ephemeral=True)
        else:
            await safe_followup(inter, embed=embed, view=view, ephemeral=True)


def _drop_linh_qua(s, la_boss: bool, linh_can_so_huu: list, drop_m: float = 1.0,
                   da_trung_sinh: bool = False):
    """Drop linh quả vào session tích lũy — scale theo bc_id.
    - Căn cơ bản: rate và count theo LINH_QUA_BC_DROP
    - Căn hiếm (loi/phong): rate × 0.4, chỉ drop từ BC5+ (Nguyên Anh) — bỏ giới hạn sau trùng sinh
    - Căn siêu hiếm (am/quang): rate × 0.15 (×2 khi boss), BC7+ — bỏ giới hạn sau trùng sinh
    - Chưa có căn → rate / 3
    - drop_m: hệ số drop từ thể chất/linh căn (lt_m)
    - da_trung_sinh: nếu True → rate × 1.5, bỏ giới hạn cảnh giới cho căn hiếm
    """
    bc_id   = s.bc_id if hasattr(s, "bc_id") else 0
    base_rate, count = LINH_QUA_BC_DROP.get(bc_id, (LINH_QUA_DROP_CO_BAN, 1))
    # Boss phòng cuối: rate × 1.5
    if la_boss:
        base_rate = min(1.0, base_rate * 1.5)
    # Nhân hệ số drop từ thể chất/linh căn, cap 1.0
    base_rate = min(1.0, base_rate * drop_m)
    # Sau trùng sinh: rate × 1.5
    if da_trung_sinh:
        base_rate = min(1.0, base_rate * 1.5)

    for lq in LINH_QUA:
        lq_id = lq["id"]
        loai  = lq["loai"]
        if loai == "co_ban":
            rate = base_rate
        elif lq_id in ("loi", "phong"):
            if not da_trung_sinh and bc_id < 5:   # chỉ drop từ BC5+ nếu chưa trùng sinh
                continue
            rate = base_rate * 0.4
        else:  # am, quang
            if not da_trung_sinh and bc_id < 7:   # chỉ drop từ BC7+ nếu chưa trùng sinh
                continue
            rate = base_rate * 0.15 * (2 if la_boss else 1)

        # User chưa có căn → giảm drop xuống 1/3
        if lq_id not in linh_can_so_huu:
            rate = rate / 3

        if random.random() < rate:
            qty = count if loai == "co_ban" else 1
            s.linh_qua_tich[lq_id] = s.linh_qua_tich.get(lq_id, 0) + qty



def _drop_manh_linh_can(s, la_boss: bool, drop_m: float = 1.0):
    """Drop mảnh linh căn — chỉ drop khi thắng boss bí cảnh.
    - Căn cơ bản (hoa/thuy/tho/moc/kim): 20% từ boss BC
    - Lôi/Phong: 8% từ boss BC5+, 2% phòng thường BC5+
    - Ám/Quang: 3% từ boss BC7+ (chỉ world boss trước đây, nay thêm BC7+)
    - drop_m: hệ số drop từ thể chất/linh căn (lt_m)
    """
    bc_id = s.bc_id if hasattr(s, "bc_id") else 0
    if not la_boss:
        # Phòng thường: chỉ Lôi/Phong từ BC5+
        if bc_id >= 5:
            for lq_id in ("loi", "phong"):
                if random.random() < min(1.0, 0.015 * drop_m):
                    s.manh_tich[lq_id] = s.manh_tich.get(lq_id, 0) + 1
        return
    # Boss bí cảnh
    for lq in LINH_QUA:
        lq_id = lq["id"]
        if lq_id in ("am", "quang"):
            if bc_id < 7:   # Ám/Quang chỉ từ BC7+ và world boss
                continue
            rate = min(1.0, 0.04 * drop_m)
        elif lq_id in ("loi", "phong"):
            if bc_id < 5:   # Lôi/Phong chỉ từ BC5+
                continue
            rate = min(1.0, 0.06 * drop_m)
        else:  # căn cơ bản
            rate = min(1.0, 0.15 * drop_m)
        if random.random() < rate:
            s.manh_tich[lq_id] = s.manh_tich.get(lq_id, 0) + 1


def _drop_dotpha_tc_nl(s: "BiCanhSession", la_boss: bool) -> None:
    """Drop tài nguyên đột phá thể chất 0.5% từ boss BC và phòng thường BC."""
    for nl in DOTPHA_TC_NGUYEN_LIEU:
        nguon = nl["nguon"]
        if la_boss and nguon in ("boss", "boss_bi_canh"):
            if random.random() < DOTPHA_TC_DROP_RATE:
                s.dotpha_tc_nl_tich[nl["id"]] = s.dotpha_tc_nl_tich.get(nl["id"], 0) + 1
        elif not la_boss and nguon in ("bi_canh", "boss_bi_canh"):
            if random.random() < DOTPHA_TC_DROP_RATE:
                s.dotpha_tc_nl_tich[nl["id"]] = s.dotpha_tc_nl_tich.get(nl["id"], 0) + 1


def _drop_sung_thu_bc(s: "BiCanhSession", la_boss: bool, drop_m: float = 1.0) -> None:
    """Drop sủng thú Tier 1 từ bí cảnh — 0.1% × drop_m mọi phòng."""
    import json as _j2
    raw = s.ts.get("sung_thu", {})
    owned = set(raw.keys()) if isinstance(raw, dict) else set(_j2.loads(raw).keys() if raw else [])
    pool  = [st for st in SUNG_THU if st["tier"] == 1 and str(st["id"]) not in owned]
    if not pool:
        return
    if random.random() < min(1.0, 0.001 * drop_m):  # 0.1% × drop_m
        s.sung_thu_drop.append(random.choice(pool))


class BiCanhChuanBiView(discord.ui.View):
    """View chuẩn bị thám hiểm — không có dropdown, chỉ nút hành động."""
    def __init__(self, chon_view: "BiCanhChonView", bc_id: int):
        super().__init__(timeout=300)  # auto-cleanup
        self.chon_view = chon_view
        self.bc_id     = bc_id
        self.parent    = chon_view.parent
        self.actor_id  = chon_view.actor_id

        btn_vao = discord.ui.Button(
            label="✖ KHIÊU CHIẾN", style=discord.ButtonStyle.danger, row=0)
        btn_cp  = discord.ui.Button(
            label="Công Pháp",
            emoji=discord.PartialEmoji(name="CongPhap", id=1481877198435778754),
            style=discord.ButtonStyle.primary, row=0)
        btn_guide = discord.ui.Button(
            label="Hướng Dẫn", emoji="❓",
            style=discord.ButtonStyle.secondary, row=1)
        btn_back  = discord.ui.Button(
            label="Quay Lại", emoji="◀️",
            style=discord.ButtonStyle.secondary, row=1)

        btn_vao.callback   = chon_view._make_enter_cb(bc_id)
        btn_cp.callback    = chon_view._on_cong_phap
        btn_guide.callback = chon_view._on_guide
        btn_back.callback  = self._on_back

        self.add_item(btn_vao)
        self.add_item(btn_cp)
        self.add_item(btn_guide)
        self.add_item(btn_back)

    async def _on_back(self, inter: discord.Interaction):
        if inter.user.id != self.actor_id:
            return await _back_to_hoso(inter, self.chon_view.parent)
        # Reset chon_view và quay về
        self.chon_view._selected_bc_id = None
        self.chon_view._select.disabled = False
        self.chon_view._btn_vao.label    = "Vào Bí Cảnh"
        self.chon_view._btn_vao.emoji    = discord.PartialEmoji(name="⚔️")
        self.chon_view._btn_vao.disabled = True
        self.chon_view._btn_vao.style    = discord.ButtonStyle.success
        self.chon_view.ts = await get_tu_si(self.actor_id)
        embed = _embed_bi_canh_chon(self.chon_view.ts, inter.user)
        await _send_bi_canh_embed(inter, embed, self.chon_view, respond=True)


class BiCanhChonView(discord.ui.View):
    def __init__(self, parent: "HoSoView", ts: dict[str, Any], actor_id: int = None, guild_id: int = 0):
        super().__init__(timeout=300)  # auto-cleanup
        self.parent   = parent
        self.ts       = ts
        self.actor_id = actor_id or parent.owner_id  # người thực sự đang chơi
        self.guild_id = guild_id
        self._selected_bc_id: int | None = None

        # Dropdown chọn bí cảnh
        opts = []
        for bc in BI_CANH:
            ok      = ts["canh_gioi"] >= bc["cap_toi_thieu"]
            cg_yc   = get_cg(bc["cap_toi_thieu"])
            label   = f"{'✅' if ok else '🔒'} {bc['ten']}"
            desc    = f"Yêu cầu: {cg_yc['ten']}  |  3 phòng (2 quái + boss)"
            opts.append(discord.SelectOption(
                label=label[:100],
                value=str(bc["id"]),
                emoji=bc["emoji"],
                description=desc[:100]))
        mount_lv = _get_mount_level(ts)
        if mount_lv > 0:
            opts.append(discord.SelectOption(
                label="🐉 Bí Cảnh Tọa Kỹ",
                value="tk_0",
                emoji="🐉",
                description=f"Farm nguyên liệu nâng cấp tọa kỹ (Lv{mount_lv})"))
        select = discord.ui.Select(
            placeholder="Chọn Bí cảnh để khám phá...",
            options=opts,
            row=0)
        self._select = select
        select.callback = self._on_select
        self.add_item(select)

        # Buttons hàng dưới
        self._btn_vao = discord.ui.Button(
            label="Vào Bí Cảnh", emoji="⚔️",
            style=discord.ButtonStyle.success, row=1, disabled=True)
        self._btn_cong_phap = discord.ui.Button(
            label="Công Pháp", emoji=discord.PartialEmoji(name="CongPhap", id=1481877198435778754),
            style=discord.ButtonStyle.primary, row=1)

        btn_guide = discord.ui.Button(label="Hướng Dẫn", emoji="❓",
            style=discord.ButtonStyle.secondary, row=2)
        btn_back  = discord.ui.Button(label="Quay Lại",  emoji="◀️",
            style=discord.ButtonStyle.secondary, row=2)

        async def _noop(inter: discord.Interaction):
            try:
                await inter.response.defer()
            except Exception:
                log.exception("Lỗi bi_canh")

        self._btn_vao.callback       = _noop  # sẽ bị ghi đè khi chọn bí cảnh
        self._btn_cong_phap.callback = self._on_cong_phap
        btn_guide.callback = self._on_guide
        btn_back.callback  = self._on_back

        self.add_item(self._btn_vao)
        self.add_item(self._btn_cong_phap)
        self.add_item(btn_guide)
        self.add_item(btn_back)

    async def _on_select(self, inter: discord.Interaction):
        if inter.user.id != self.actor_id:
            return await inter.response.send_message("❌", ephemeral=True)
        # Refresh ts để thể lực hiển thị chính xác
        self.ts = await get_tu_si(self.actor_id)
        val = inter.data["values"][0]
        if val.startswith("tk_"):
            from cogs.views.toa_ky_bi_canh import ToaKyBiCanhView, _embed_toa_ky_bi_canh_chon
            embed3 = _embed_toa_ky_bi_canh_chon(self.ts, inter.user)
            view3 = ToaKyBiCanhView(self.parent, self.ts, actor_id=self.actor_id, guild_id=self.guild_id)
            await inter.response.send_message(embed=embed3, view=view3, ephemeral=True)
            return
        bc_id = int(val)
        if bc_id < 0 or bc_id >= len(BI_CANH):
            return await inter.response.send_message("❌ Bí cảnh không hợp lệ!", ephemeral=True)
        ok    = self.ts["canh_gioi"] >= bc["cap_toi_thieu"]

        if not ok:
            cg_yc = get_cg(bc["cap_toi_thieu"])
            return await inter.response.send_message(
                embed=e_loi("🔒 Chưa Đủ Cảnh Giới", f"Bí cảnh **{bc['ten']}** yêu cầu **{cg_yc['emoji']} {cg_yc['ten']}**."),
                ephemeral=True)

        self._selected_bc_id = bc_id

        # Lấy quái đại diện (phong_thuong[0]) để hiển thị thông tin yêu cầu
        quai     = bc["phong_thuong"][0]
        boss     = bc["boss"]
        cg       = get_cg(self.ts["canh_gioi"])
        tl_hien   = get_the_luc(self.ts)
        tran_hien = get_tran_the_luc(self.ts)
        tieu_phi = 10

        e_hp  = E_SINH_LUC
        e_at  = get_stat_emoji("cong_kich")
        e_df  = get_stat_emoji("phong_ngu")
        e_ht  = get_stat_emoji("hoi_tam")
        e_bk  = get_stat_emoji("bao_kich")
        e_hmt = get_stat_emoji("ho_tam")
        e_kb  = get_stat_emoji("khang_bao")

        embed = discord.Embed(
            title=f"☁️ CHUẨN BỊ THÁM HIỂM: {bc['ten']}",
            description=f"Vùng đất này đang bị **{boss['ten']}** trấn giữ!",
            color=cg["mau"])

        thong_tin = (
            f"{e_hp} HP: {fmt(quai['hp'])}\n"
            f"{e_at} Tấn công: {fmt(quai['at'])}\n"
            f"{e_df} Phòng ngự: {fmt(quai['df'])}\n"
            f"{e_ht} Hội tâm: {quai.get('hoi_tam', 0)}\n"
            f"{e_bk} Bạo kích: {int(quai.get('bao_kich', 1.5) * 100)}%\n"
            f"{e_hmt} Hộ tâm: {quai.get('ho_tam', 0)}\n"
            f"{e_kb} Kháng bạo: {int(quai.get('khang_bao', 0) * 100)}%"
        )
        embed.add_field(
            name=f"🐾 Quái tiêu biểu: {quai['ten']} (HP {fmt(bc['phong_thuong'][0]['hp']):}–{fmt(bc['phong_thuong'][-1]['hp'])})",
            value=thong_tin, inline=False)

        embed.add_field(
            name="\u200b",
            value=(f"⚡ Thể lực: **{tl_hien}/{the_luc_toi_da(self.ts.get('canh_gioi', 0))}** 🔋 Tràn: **{tran_hien}/{TRAN_THE_LUC_MAX}**\n"
                   f"⚠️ Tiêu phí: **{tieu_phi} ⚡**"),
            inline=False)

        embed.set_footer(text=f"3 phòng  |  Boss: {boss['ten']}")

        # Swap sang view chuẩn bị (không có dropdown)
        chuan_bi_view = BiCanhChuanBiView(self, bc_id)
        self._btn_back_tmp = True
        await safe_edit_message(inter, embed=embed, view=chuan_bi_view)

    def _make_enter_cb(self, bc_id: int):
        async def cb(inter: discord.Interaction):
            try:
                if inter.user.id != self.actor_id:
                    return await inter.response.send_message("❌", ephemeral=True)
                # Kiểm tra thể lực TRƯỚC khi respond
                ts_fresh  = await get_tu_si(inter.user.id)
                tl_hien   = get_the_luc(ts_fresh)
                tran_hien = get_tran_the_luc(ts_fresh)
                BC_PHI    = 10
                # Ưu tiên trừ thể lực chính; nếu chính = 0 thì dùng tràn
                if tl_hien >= BC_PHI:
                    new_tl   = tl_hien - BC_PHI
                    new_tran = tran_hien
                    dung_tran = False
                elif tran_hien >= BC_PHI:
                    new_tl   = tl_hien
                    new_tran = tran_hien - BC_PHI
                    dung_tran = True
                else:
                    # Cả hai không đủ
                    tl_max  = the_luc_toi_da(ts_fresh.get("canh_gioi", 0))
                    hoi_con = (BC_PHI - tl_hien) * THE_LUC_HOI if tl_hien < BC_PHI else 0
                    return await inter.response.send_message(
                        embed=e_warn("⚡ Thể Lực Không Đủ",
                            f"Cần **{BC_PHI} ⚡** để vào bí cảnh.\n"
                            f"Thể lực chính: **{tl_hien}/{tl_max}**\n"
                            f"Thể lực tràn: **{tran_hien}/{TRAN_THE_LUC_MAX}**\n"
                            + (f"Hồi đủ sau: **{fmt_cd(hoi_con)}**" if hoi_con else "")),
                        ephemeral=True)
                # Defer trước khi làm bất kỳ việc nặng nào
                try:
                    await inter.response.defer()
                except Exception:
                    log.exception("Lỗi defer bi_canh")
                    return
                # Cleanup sessions cũ
                _cleanup_stale_sessions()
                # Vào bí cảnh luôn với full HP
                full_st = _calc_stats(ts_fresh)
                hp_vao  = full_st["hp_eff"]
                await update_tu_si(inter.user.id,
                    the_luc=new_tl,
                    the_luc_cap_nhat=int(time.time()),
                    tran_the_luc=new_tran,
                    tran_the_luc_cap_nhat=int(time.time()),
                    bc_thua_lan_truoc=0,
                    hp=hp_vao)
                if bc_id < 0 or bc_id >= len(BI_CANH):
                    return await safe_followup(inter, "❌ Bí cảnh không hợp lệ!", ephemeral=True)
                bc    = BI_CANH[bc_id]
                rooms = _gen_rooms(bc)
                rooms = _scale_rooms_by_rebirth(rooms, ts_fresh.get("so_lan_trung_sinh", 0))
                # Sync toàn bộ chỉ số thuộc tính thực (pháp bảo, sủng thú, tông môn, linh căn)
                full  = _calc_full_stats(ts_fresh)
                ts_for_session = {
                    **ts_fresh,
                    "cong":      full["at"],
                    "thu":       full["df"],
                    "hp_max":    full["hp_eff"],
                    "linh_luc":  full["linh_luc"],
                    "hoi_tam":   full["hoi_tam"],
                    "ho_tam":    full["ho_tam"],
                    "bao_kich":  full["bao_kich"],
                    "khang_bao": full["khang_bao"],
                }
                s = BiCanhSession(
                    user_id=inter.user.id, bc_id=bc_id, ts=ts_for_session,
                    phong_list=rooms, hp_hien=hp_vao,
                    ll_hien=ts_for_session.get("linh_luc", 100),
                    created_at=int(time.time()))
                sess_key = (self.guild_id, inter.user.id)
                _bc_sessions[sess_key] = s
                view = BiCanhPhongView(self.parent, s, bc, bc_view=self)
                self._select.disabled = True
                view._compute_combat()
                view._prepare_combat_buttons()
                await safe_edit_message(inter,
                    embed=view._embed_combat(inter.user, 0), view=view)
                view._enqueue_combat(inter)
            except Exception:
                log.exception("Lỗi khiêu chiến bí cảnh")
                try:
                    if inter.response.is_done():
                        await safe_followup(inter,
                            embed=e_loi("❌ Lỗi", "Có lỗi xảy ra khi vào bí cảnh. Vui lòng thử lại."),
                            ephemeral=True)
                    else:
                        await inter.response.send_message(
                            embed=e_loi("❌ Lỗi", "Có lỗi xảy ra khi vào bí cảnh. Vui lòng thử lại."),
                            ephemeral=True)
                except Exception:
                    log.exception("Lỗi gửi thông báo khiêu chiến")
        return cb


    async def _on_cong_phap(self, inter: discord.Interaction):
        if inter.user.id != self.actor_id:
            return await inter.response.send_message("❌", ephemeral=True)
        try:
            await inter.response.defer(ephemeral=True)
        except discord.InteractionResponded:
            pass
        view = CongPhapView(self.parent, self.ts)
        embed = discord.Embed(
            title="📚 Công Pháp",
            description="Mua công pháp mới hoặc quản lý công pháp đã học.",
            color=0x5865F2)
        try:
            await safe_followup(inter, embed=embed, view=view, ephemeral=True)
        except Exception as e:
            log.error(f"_on_cong_phap user={inter.user.id}: {e}", exc_info=True)

    async def _on_guide(self, inter: discord.Interaction):
        embed = discord.Embed(
            title="📖 HƯỚNG DẪN BÍ CẢNH",
            description="Nắm vững các quy tắc sau để thượng lộ bình an!",
            color=0x4D96FF)

        embed.add_field(name="⚡ Thể Lực", value=(
            "• Mỗi lần khiêu chiến tốn **10 ⚡ thể lực**.\n"
            "• Thể lực chính hồi **1 điểm / 1 phút**, tối đa **250 + CG×20**.\n"
            "• 🔋 **Tràn thể lực** (tối đa 100): chỉ tích khi chính đầy, hồi **4 phút/điểm**.\n"
            "• Ưu tiên dùng thể lực **chính** trước; khi chính = 0 mới dùng **tràn**."
        ), inline=False)

        embed.add_field(name="⚔️ Chiến Đấu", value=(
            "• Chiến đấu diễn ra **tự động** theo công pháp đang trang bị.\n"
            "• Mỗi lượt hồi **5% Linh Lực** — kỹ năng mạnh tốn nhiều LL hơn.\n"
            "• Thứ tự ưu tiên kỹ năng: **Thần Thông → Tuyệt Kỹ → Thân Pháp → Võ Kỹ**\n"
            "• **Bạo kích** phụ thuộc Hội Tâm của ngươi và Hộ Tâm của quái.\n"
            "• **Pháp bảo** kích hoạt đòn passive mỗi 3–5 lượt tùy loại."
        ), inline=False)

        embed.add_field(name="🏃 Rút Lui — QUAN TRỌNG", value=(
            "• Rút lui **sau khi thắng phòng** → nhận **80% tu vi + linh thạch** tích lũy.\n"
            "• **Thua trận** → mất **toàn bộ tu vi + linh thạch** tích lũy.\n"
            "• 📦 Mọi vật phẩm khác **(đan, linh quả, sủng thú, nguyên liệu...)** luôn giữ nguyên.\n"
            "• ⚠️ Càng vào sâu rủi ro càng cao — hãy rút lui đúng lúc!"
        ), inline=False)

        embed.add_field(name="🎁 Phần Thưởng", value=(
            "• **Tu vi + Linh thạch** tích lũy qua từng phòng, nhận khi hoàn thành.\n"
            "• **Nguyên liệu, Đan, Linh Quả, Sủng Thú, Mảnh Linh Căn** → luôn giữ 100% dù rút lui hay thua.\n"
            "• **Đan Tu Luyện** drop từ quái — dùng để đột phá tiểu cảnh.\n"
            "• **Sủng Thú ⭐** ~1–5% từ quái thường, ~2.5–12% từ boss bí cảnh.\n"
            "• **Linh Quả / Mảnh Linh Căn** drop từ boss bí cảnh.\n"
            "• **Nguyên liệu Đột Phá Thể Chất** 0.7% từ mọi phòng."
        ), inline=False)

        embed.add_field(name="💡 Mẹo", value=(
            "• Trang bị **Pháp bảo** trước khi vào — passive tự kích hoạt mỗi vài lượt.\n"
            "• Chọn **Công pháp** cùng cảnh giới hoặc cao hơn để damage tốt hơn.\n"
            "• **Sủng Thú hệ Thổ** (DEF+8%) và **hệ Thủy** (giảm 5% dmg nhận) — rất hữu ích.\n"
            "• BC thấp (BC0–2) có tỉ lệ drop Sủng Thú cao hơn BC cao.\n"
            "• Nếu HP thấp sau phòng quái — **rút lui ngay** để giữ nguyên liệu!"
        ), inline=False)

        embed.set_footer(text="Đạo lộ vô biên — rút lui đúng lúc cũng là trí tuệ!")
        btn_back = discord.ui.Button(label="◀ Quay lại", style=discord.ButtonStyle.secondary)
        v = discord.ui.View(timeout=60)
        async def _back_guide(i):
            await i.response.defer()
        btn_back.callback = _back_guide
        v.add_item(btn_back)
        await inter.response.send_message(embed=embed, view=v, ephemeral=True)

    async def _on_back(self, inter: discord.Interaction):
        if getattr(self, "_btn_back_tmp", False):
            # Reset về màn hình chọn bí cảnh
            self._btn_back_tmp = False
            self._select.disabled = False
            self._btn_vao.disabled = True
            self._btn_vao.label = "Vào Bí Cảnh"
            self._btn_vao.emoji = discord.PartialEmoji(name="⚔️")
            self._btn_vao.style = discord.ButtonStyle.success
            async def _noop_vao(i): await i.response.defer()
            self._btn_vao.callback = _noop_vao
            # Fetch lại ts để thể lực hiển thị chính xác
            self.ts = await get_tu_si(self.actor_id)
            embed = _embed_bi_canh_chon(self.ts, inter.user)
            await _send_bi_canh_embed(inter, embed, self, respond=True)
        else:
            await _back_to_hoso(inter, self.parent)


def _bc_embed_phong(s: BiCanhSession, bc: dict, user: discord.User) -> discord.Embed:
    idx     = s.phong_hien
    total   = len(s.phong_list)
    phong   = s.phong_list[idx]
    quai    = phong["data"]
    la_boss = phong["loai"] == "boss"
    prog    = "".join(
        "✅" if i < idx else ("🔴" if i == idx and la_boss else "⚔️" if i == idx else "🔒")
        for i in range(total))
    embed = discord.Embed(
        title=f"{bc['ten']}  —  Phòng {idx+1}/{total}" + (" — 💀 BOSS!" if la_boss else ""),
        description=prog,
        color=0xFF0000 if la_boss else 0xFF8C00)
    embed.set_author(name=user.display_name, icon_url=user.display_avatar.url)

    e_hp  = E_SINH_LUC
    e_at  = get_stat_emoji("cong_kich")
    e_df  = get_stat_emoji("phong_ngu")
    e_ht  = get_stat_emoji("hoi_tam")
    e_bk  = get_stat_emoji("bao_kich")
    e_hmt = get_stat_emoji("ho_tam")
    e_kb  = get_stat_emoji("khang_bao")

    stats = (
        f"{e_hp} **{fmt(quai['hp'])}**  {e_at} **{fmt(quai['at'])}**  {e_df} **{fmt(quai['df'])}**\n"
        f"{e_ht} {quai.get('hoi_tam',0)}  {e_bk} {int(quai.get('bao_kich',1.5)*100)}%  "
        f"{e_hmt} {quai.get('ho_tam',0)}  {e_kb} {int(quai.get('khang_bao',0)*100)}%"
    )
    if la_boss and quai.get("mo_ta"):
        stats += f"\n*{quai['mo_ta']}*"

    embed.add_field(
        name=f"{'💀 ' if la_boss else ''}{quai['ten']}",
        value=stats,
        inline=False)
    embed.add_field(name=f"{E_SINH_LUC} HP Bạn",
        value=f"`{bar(s.hp_hien, s.ts['hp_max'])}` {s.hp_hien}/{s.ts['hp_max']}", inline=True)
    embed.add_field(name=f"{E_LINH_THACH} Tích Lũy",
        value=f"{E_TU_VI}{fmt(s.exp_tich)} Tu vi  {E_LINH_THACH}{fmt(s.lt_tich)}", inline=True)
    if s.dan_tich:
        # Hiển thị đan drop: phân biệt tiểu cảnh và đại cảnh
        dan_lines = []
        for key, cnt in s.dan_tich.items():
            if key.startswith("__dd:"):
                # Đan đại cảnh
                dd_id = int(key[5:])
                dd = next((d for d in DAN_DUOC if d["id"] == dd_id), None)
                if dd:
                    dan_lines.append(f"{dd.get('emoji', '💊')} **{dd['ten']}** ×{cnt} *(đột phá đại cảnh)*")
            else:
                # Đan tiểu cảnh — key: "cg_id:cap_nho_sau:ten"
                parts = key.split(":", 2)
                if len(parts) == 3:
                    cg_id, cap_nho_sau, ten = int(parts[0]), int(parts[1]), parts[2]
                    emoji = ""
                    if 0 <= cg_id < len(DAN_TU_LUYEN):
                        for d in DAN_TU_LUYEN[cg_id]:
                            if d["ten"] == ten and d["cap_nho_sau"] == cap_nho_sau:
                                emoji = d["emoji"]; break
                    dan_lines.append(f"{emoji} **{ten}** ×{cnt}")
        if dan_lines:
            embed.add_field(name="Đan Dược", value="\n".join(dan_lines), inline=False)
    embed.set_footer(text="⚔️ Tiến lên  |  🏃 Rút lui → nhận 80% tu vi & linh thạch, giữ 100% vật phẩm")
    return embed


class BiCanhPhongView(discord.ui.View):
    """View bí cảnh — combat auto-play qua CombatTaskCog."""

    def __init__(self, parent, s: BiCanhSession, bc: dict, bc_view=None):
        super().__init__(timeout=600)  # auto-cleanup
        self.parent        = parent
        self.s             = s
        self.bc            = bc
        self.bc_view       = bc_view
        self.actor_id      = bc_view.actor_id if bc_view else s.user_id
        # guild_id từ bc_view (đã được set từ inter.guild_id khi vào bí cảnh)
        # Fallback về user_id nếu không có bc_view, tránh conflict key (guild_id=0) đa server
        self.guild_id      = bc_view.guild_id if bc_view else s.user_id
        self._combat_logs  = []
        self._msg          = None  # cached discord.Message để dùng message.edit()
        self._won          = None
        self._hp_after     = s.hp_hien

        self._btn_skip = discord.ui.Button(
            label="⏩ Bỏ qua", style=discord.ButtonStyle.primary,
            row=0, disabled=True)
        self._btn_run = discord.ui.Button(
            label="✖ Rút lui", style=discord.ButtonStyle.danger, row=0)
        self._btn_tiep = discord.ui.Button(
            label="Tiếp tục thám hiểm", style=discord.ButtonStyle.success,
            row=1, disabled=True)
        self._btn_ve = discord.ui.Button(
            label="Về Hồ Sơ", style=discord.ButtonStyle.secondary,
            row=1, disabled=True)
        self._btn_lai = discord.ui.Button(
            label="⚔️ Khiêu Chiến Tiếp", style=discord.ButtonStyle.danger,
            row=1, disabled=True)

        self._btn_skip.callback = self._on_skip
        self._btn_run.callback  = self._on_run
        self._btn_tiep.callback = self._on_tiep_tuc
        self._btn_ve.callback   = self._on_ve
        self._btn_lai.callback  = self._on_lai

        self.add_item(self._btn_skip)
        self.add_item(self._btn_run)
        self.add_item(self._btn_tiep)
        self.add_item(self._btn_ve)
        self.add_item(self._btn_lai)

    # ── Lấy CombatTaskCog ─────────────────────────────────────
    def _get_task_cog(self, inter: discord.Interaction):
        return inter.client.cogs.get("CombatTaskCog")

    # ── Tính toàn bộ combat log ────────────────────────────────
    # Cooldown công pháp (lượt): đồng bộ với LOAI_CD trong cong_phap.py
    SKILL_CD_BC  = {"vo_ky": 2, "than_phap": 3, "tuyet_ky": 4, "than_thong": 5}
    # Damage multiplier: đồng bộ với LOAI_DMGM trong cong_phap.py (rebalanced v2)
    SKILL_DMG_BC = {"vo_ky": 1.0, "than_phap": 1.0, "tuyet_ky": 1.6, "than_thong": 2.5}

    def _compute_combat(self):
        s     = self.s
        phong = s.phong_list[s.phong_hien]
        quai  = phong["data"]
        at_p  = s.ts["cong"]; df_p = s.ts["thu"]; hp_p = s.hp_hien
        hp_q  = quai["hp"]
        q_at  = quai["at"]; q_df = quai.get("df", 0)
        q_ht  = quai.get("hoi_tam", 0)
        q_bk  = quai.get("bao_kich", 1.5)
        q_hmt = quai.get("ho_tam", 0)
        q_kb  = quai.get("khang_bao", 0)
        p_hot = s.ts.get("ho_tam", 0)   # hộ tâm người chơi để giảm crit nhận vào
        # khang_bao trong ts_for_session là phân số (0.xx) từ _calc_full_stats — dùng trực tiếp, không /100
        p_kb  = s.ts.get("khang_bao", (3 + s.ts.get("canh_gioi", 0) * 2) / 100)

        # Khởi tạo CD + tên skill từ công pháp active (hệ mới V3)
        from cogs.cong_phap import (
            get_cp_active, LOAI_SK, LOAI_CD, LOAI_DMGM, PHAM_DMG_MULT, CAP_DMG_MULT
        )
        if s.skill_cd is None:
            s.skill_cd = {k: 0 for k in LOAI_SK}
        if s.skill_names is None:
            cp_active = get_cp_active(s.ts)
            s.skill_names = {}
            s.skill_ll    = {}   # linh lực mỗi kỹ năng
            s.pham_mult   = 1.0
            if cp_active:
                for loai in LOAI_SK:
                    sk = cp_active["ky_nang"].get(loai)
                    if sk:
                        s.skill_names[loai] = sk["ten"]
                        s.skill_ll[loai]    = sk["ll"]
                # Hệ số tổng = phẩm × hệ (Hạ×1.5 × Hoàng×1.5 = ×2.25, Cực×4.0 × Thiên×4.5 = ×18)
                s.pham_mult = (PHAM_DMG_MULT.get(cp_active["pham"], 1.0)
                               * CAP_DMG_MULT.get(cp_active["cap"], 1.0))
        if not hasattr(s, "pham_mult") or s.pham_mult is None:
            s.pham_mult = 1.0
        if not hasattr(s, "skill_ll") or s.skill_ll is None:
            s.skill_ll = {}

        FALLBACK_NAME = {
            "vo_ky": "Quyền Cước", "than_phap": "Thân Pháp",
            "tuyet_ky": "Tuyệt Kỹ", "than_thong": "Thần Thông"
        }
        SKILL_ORDER = ["than_thong", "tuyet_ky", "than_phap", "vo_ky"]

        logs = []; won = True

        # ── Pháp bảo kỹ năng ───────────────────────────────────
        pb_active_id = s.ts.get("phap_bao_active", -1)
        _pb = PHAP_BAO_BY_ID.get(pb_active_id) if pb_active_id >= 0 else None
        pb_skill = PHAP_BAO_SKILL.get(_pb["id_base"]) if _pb else None
        pb_cd  = 0        # cooldown còn lại
        pb_buf = {}       # {"at_buff":lượt, "df_buff":lượt, "absorb":lượt, "invinc":lượt, "def_shred":lượt}
        hp_max_p = s.ts.get("hp_max", hp_p)
        # Kỹ năng battle_start kích hoạt ngay lượt đầu
        if pb_skill and pb_skill["trigger"] == "battle_start":
            buf = pb_skill.get("buff_pct", 0)
            pb_buf["at_buff"]  = pb_skill["duration"]
            pb_buf["df_buff"]  = pb_skill["duration"]
            logs.append((0, "pb_skill", 0, False, f"✨ {pb_skill['ten']}: AT & DEF +{int(buf*100)}% ({pb_skill['duration']} lượt)"))
            pb_cd = pb_skill["cd"]
        # Passive amplify không cần init
        pb_crit_mult_extra = (pb_skill.get("extra_mult", 0)
                              if pb_skill and pb_skill["effect"] == "crit_amplify" else 0)

        ll_max = s.ts.get("linh_luc", 100)
        ll_hoi_moi_luot = max(1, ll_max // 20)   # hồi 5% LL mỗi lượt

        for turn in range(1, 51):
            for k in s.skill_cd:
                if s.skill_cd[k] > 0:
                    s.skill_cd[k] -= 1
            # Hồi LL mỗi lượt
            s.ll_hien = min(ll_max, s.ll_hien + ll_hoi_moi_luot)
            # Chọn skill tốt nhất sẵn sàng VÀ đủ LL
            chosen = "vo_ky"
            for sk in SKILL_ORDER:
                if s.skill_cd.get(sk, 0) == 0 and (sk in s.skill_names or sk == "vo_ky"):
                    ll_cost = s.skill_ll.get(sk, 0)
                    if s.ll_hien >= ll_cost:
                        chosen = sk; break
            base_mul = LOAI_DMGM.get(chosen, 1.0)
            # Trừ LL khi dùng skill
            ll_cost_chosen = s.skill_ll.get(chosen, 0)
            s.ll_hien = max(0, s.ll_hien - ll_cost_chosen)
            # Lưu ll_hien vào logs để embed reconstruct đúng từng lượt
            logs.append((turn, "ll_tick", s.ll_hien, False, ""))
            # Hệ số = loại kỹ năng × phẩm công pháp
            mul = base_mul * s.pham_mult
            s.skill_cd[chosen] = LOAI_CD.get(chosen, 2)
            skill_name = s.skill_names.get(chosen, FALLBACK_NAME.get(chosen, "Tấn Công"))

            # ── Tick pháp bảo cooldown & buffs ──────────────────
            if pb_cd > 0: pb_cd -= 1
            for bk in list(pb_buf.keys()):
                if pb_buf[bk] > 0: pb_buf[bk] -= 1
            # Trigger every_n
            if pb_skill and pb_skill["trigger"] == "every_n" and pb_cd == 0:
                if turn % pb_skill["n"] == 0:
                    eff = pb_skill["effect"]
                    if eff == "heal":
                        heal_amt = int(hp_max_p * pb_skill["heal_pct"])
                        hp_p = min(hp_max_p, hp_p + heal_amt)
                        logs.append((turn, "pb_skill", heal_amt, False,
                                     f"✨ {pb_skill['ten']}: hồi +{heal_amt} HP"))
                    elif eff == "dmg_absorb":
                        pb_buf["absorb"] = pb_skill["duration"]
                        logs.append((turn, "pb_skill", 0, False,
                                     f"✨ {pb_skill['ten']}: hấp thụ dmg {pb_skill['absorb_pct']*100:.0f}% ({pb_skill['duration']} lượt)"))
                    elif eff == "extra_attack":
                        pass  # xử lý sau khi đánh
                    pb_cd = pb_skill["cd"]
            # Trigger hp_below AT buff
            if pb_skill and pb_skill["trigger"] == "hp_below" and pb_cd == 0:
                pct_now = hp_p / hp_max_p
                if pct_now <= pb_skill["threshold"]:
                    eff = pb_skill["effect"]
                    if eff == "at_buff":
                        pb_buf["at_buff"] = pb_skill["duration"]
                        logs.append((turn, "pb_skill", 0, False,
                                     f"✨ {pb_skill['ten']}: AT +{int(pb_skill['buff_pct']*100)}% ({pb_skill['duration']} lượt)"))
                    elif eff == "invincible":
                        pb_buf["invinc"] = pb_skill["duration"]
                        logs.append((turn, "pb_skill", 0, False,
                                     f"✨ {pb_skill['ten']}: miễn sát thương 1 lượt!"))
                    pb_cd = pb_skill["cd"]
            # Áp dụng AT buff vào at_p_eff
            at_p_eff = at_p
            if pb_buf.get("at_buff", 0) > 0 and pb_skill:
                at_p_eff = int(at_p * (1 + pb_skill.get("buff_pct", 0)))
            if pb_buf.get("df_buff", 0) > 0 and pb_skill:
                df_p = int(s.ts["thu"] * (1 + pb_skill.get("buff_pct", 0)))
            else:
                df_p = s.ts["thu"]  # restore về base khi không có buff

            # ── Công thức sát thương mới: % mitigation thay vì flat ─────────────
            # def_mit = q_df / (q_df + at*mul*0.4) → % giảm sát thương
            # Quái df=30, player at*mul=500 → 30/(30+200) = 13% giảm
            raw_dmg = at_p_eff * mul * random.uniform(0.85, 1.15)
            def_mit = q_df / (q_df + raw_dmg * 0.4)
            dmg_p   = max(1, int(raw_dmg * (1.0 - def_mit)))
            # Bạo kích: (hội_tâm người - hộ_tâm địch) / 300 + bk_flat - kb_quai
            # bao_kich và khang_bao trong ts_for_session là phân số từ _calc_full_stats — dùng trực tiếp
            # quai["khang_bao"] cũng là phân số trong config (e.g. 0.07)
            p_ht          = s.ts.get("hoi_tam", 0)
            q_ho_tam      = quai.get("ho_tam", 0)
            bao_kich_frac = s.ts.get("bao_kich", 0)
            khang_bao_q   = quai.get("khang_bao", 0)
            crit_rate = max(0.10, min(0.75,
                (p_ht - q_ho_tam) / 300 + bao_kich_frac - khang_bao_q))
            crit_p = random.random() < crit_rate
            if crit_p:
                crit_mul = 1.8 * (1 + pb_crit_mult_extra)
                dmg_p = int(dmg_p * crit_mul)
            # on_hit: def_shred
            if pb_skill and pb_skill["trigger"] == "on_hit" and pb_skill["effect"] == "def_shred" and pb_cd == 0:
                if random.random() < pb_skill["chance"]:
                    pb_buf["def_shred"] = pb_skill["duration"]
                    q_df_eff = int(quai["df"] * (1 - pb_skill["shred_pct"]))
                    logs.append((turn, "pb_skill", 0, False,
                                 f"✨ {pb_skill['ten']}: phá giáp! DEF quái -{int(pb_skill['shred_pct']*100)}% ({pb_skill['duration']} lượt)"))
                    pb_cd = pb_skill["cd"]
            # Áp dụng def_shred vào q_df (dùng cho % mitigation)
            q_df_use = int(quai["df"] * (1 - pb_skill.get("shred_pct",0))) if pb_buf.get("def_shred",0) > 0 and pb_skill else q_df
            # extra_attack (Cổ Cầm) sau đòn chính — dùng % mitigation nhất quán
            if pb_skill and pb_skill["trigger"] == "every_n" and pb_skill["effect"] == "extra_attack":
                if turn % pb_skill["n"] == 0:
                    _extra_raw = at_p_eff * pb_skill["extra_pct"] * random.uniform(0.85,1.15)
                    _extra_mit = q_df_use / (q_df_use + _extra_raw * 0.4)
                    extra_dmg = max(1, int(_extra_raw * (1.0 - _extra_mit)))
                    dmg_p += extra_dmg
                    logs.append((turn, "pb_skill", extra_dmg, False,
                                 f"✨ {pb_skill['ten']}: đòn phụ +{extra_dmg}"))
            # ── Đòn pháp bảo (mỗi 5 lượt) ──────────────────────
            pb_bonus_dmg = 0
            pb_bonus_name = ""
            if _pb and turn % 5 == 0:
                _pb_at  = _pb.get("at", 0)
                _pb_def = _pb.get("df", 0)
                _pb_base = _pb.get("id_base", 0)
                _rnd = random.uniform(0.85, 1.15)
                _pb_sk_ten = PHAP_BAO_SKILL.get(_pb_base, {}).get("ten", _pb.get("ten","Pháp Bảo"))
                # Công thức theo id_base
                if _pb_base == 0:
                    raw = _pb_at * 18.0 * _rnd; _hits = 1
                elif _pb_base == 1:
                    raw = _pb_def * 12.0 * _rnd; _hits = 1   # xuyên giáp: không trừ q_df
                elif _pb_base == 2:
                    raw = (_pb_at*8.0 + _pb_def*5.0) * _rnd; _hits = 2
                elif _pb_base == 3:
                    raw = (_pb_def*8.0 + _pb_at*5.0) * _rnd; _hits = 1  # xuyên giáp
                elif _pb_base == 4:
                    raw = _pb_at * 13.0 * random.uniform(0.70, 1.30); _hits = 1
                elif _pb_base == 5:
                    raw = (_pb_at + _pb_def) * 9.0 * _rnd; _hits = 1
                elif _pb_base == 6:
                    raw = (_pb_at + _pb_def) * 13.0 * _rnd; _hits = 1
                elif _pb_base == 7:
                    raw = (_pb_at*5.0 + _pb_def*5.0) * _rnd; _hits = 3
                elif _pb_base == 8:
                    raw = (_pb_at + _pb_def) * 9.0 * _rnd; _hits = 1
                elif _pb_base == 9:
                    raw = _pb_at * 4.5 * _rnd; _hits = 4
                else:
                    raw = _pb_at * 10.0 * _rnd; _hits = 1
                # Xuyên giáp (id_base 1, 3): không bị DEF giảm
                # Các đòn khác: dùng % mitigation nhất quán với công thức chính
                _pierce = _pb_base in (1, 3)
                if _pierce:
                    pb_bonus_dmg = max(1, int(raw * _hits))
                else:
                    _pb_total_raw = raw * _hits
                    _pb_mit = q_df * 0.3 / (_pb_total_raw + 0.001)  # tương đương ~15-25% với pb damage
                    pb_bonus_dmg = max(1, int(_pb_total_raw * (1.0 - min(0.35, _pb_mit))))
                # Huyết Diện (4): crit rate +20%; Thiết Bích (8): guaranteed crit
                _pb_crit = crit_p
                if _pb_base == 4 and random.random() < min(0.95, crit_rate + 0.20):
                    pb_bonus_dmg = int(pb_bonus_dmg * 1.8); _pb_crit = True
                elif _pb_base == 8:
                    pb_bonus_dmg = int(pb_bonus_dmg * 1.8); _pb_crit = True
                # Ngưng Châu (6): hồi 5% HP sau đòn
                if _pb_base == 6:
                    _heal = int(hp_max_p * 0.05)
                    hp_p = min(hp_max_p, hp_p + _heal)
                pb_bonus_name = _pb_sk_ten
                hp_q = max(0, hp_q - pb_bonus_dmg)
                logs.append((turn, "pb_atk", pb_bonus_dmg, _pb_crit, pb_bonus_name))
                if hp_q <= 0: won = True; break

            hp_q -= dmg_p
            logs.append((turn, "player", dmg_p, crit_p, skill_name))
            if hp_q <= 0: won = True; break
            # Quái tấn công: % mitigation từ DEF người chơi
            raw_dmg_q = q_at * random.uniform(0.85, 1.15)
            p_def_mit  = df_p / (df_p + raw_dmg_q * 0.4)
            dmg_q  = max(1, int(raw_dmg_q * (1.0 - p_def_mit)))
            # Quái bạo kích: driven bởi bao_kich multiplier của quái
            # (q_bk - 1.0) × 25 → BC0 quái 1.5 = 12.5%, BC9 boss 3.42 = 60%
            # Player hộ tâm giảm crit nhận vào: -p_hot/500 (p_hot đã define ở đầu hàm)
            crit_q = random.random() < max(0.10, min(0.65, (q_bk - 1.0) * 25 / 100 - p_hot / 500))
            if crit_q: dmg_q = int(dmg_q * q_bk * (1 - p_kb))
            # on_recv: full_block
            if pb_skill and pb_skill["trigger"] == "on_recv" and pb_skill["effect"] == "full_block" and pb_cd == 0:
                if random.random() < pb_skill["chance"]:
                    logs.append((turn, "pb_skill", dmg_q, False,
                                 f"✨ {pb_skill['ten']}: BLOCK! chặn {dmg_q} sát thương"))
                    dmg_q = 0; pb_cd = pb_skill["cd"]
            # invincible (Bạch Bào)
            if pb_buf.get("invinc", 0) > 0:
                logs.append((turn, "pb_skill", dmg_q, False,
                             f"✨ Bạch Bào Thiết Phòng: miễn sát thương ({dmg_q})"))
                dmg_q = 0
            # absorb (Hoàng Cực)
            elif pb_buf.get("absorb", 0) > 0 and pb_skill:
                absorbed = int(dmg_q * pb_skill.get("absorb_pct", 0))
                dmg_q = max(1, dmg_q - absorbed)
                logs.append((turn, "pb_skill", absorbed, False,
                             f"✨ {pb_skill['ten']}: hấp thụ {absorbed} sát thương"))
            # on_crit_recv: counter (Huyền Chung)
            if crit_q and pb_skill and pb_skill["trigger"] == "on_crit_recv" and pb_cd == 0:
                counter_dmg = max(1, int(q_at * pb_skill["counter_pct"]))
                hp_q = max(0, hp_q - counter_dmg)
                logs.append((turn, "pb_skill", counter_dmg, False,
                             f"✨ {pb_skill['ten']}: phản sát {counter_dmg}!"))
                pb_cd = pb_skill["cd"]
            hp_p -= dmg_q
            logs.append((turn, "quai", dmg_q, crit_q, quai["ten"]))
            if hp_p <= 0: won = False; break
        else:
            won = True
        self._combat_logs = logs
        self._won         = won
        self._hp_after    = max(1, hp_p)

    # ── Embed đang chiến đấu ───────────────────────────────────
    def _embed_combat(self, user, n_show: int) -> discord.Embed:
        s       = self.s
        phong   = s.phong_list[s.phong_hien]
        quai    = phong["data"]
        la_boss = phong["loai"] == "boss"
        q_name  = quai["ten"]
        phong_idx   = s.phong_hien + 1
        phong_total = len(s.phong_list)

        hp_q = quai["hp"]; hp_p = s.hp_hien
        for log_hp in self._combat_logs[:n_show]:
            _, side, dmg = log_hp[0], log_hp[1], log_hp[2]
            if side in ("player", "pb_atk"): hp_q -= dmg
            elif side == "quai":             hp_p -= dmg
        hp_q = max(0, hp_q); hp_p = max(0, hp_p)

        pct_q = hp_q / quai["hp"]     if quai["hp"] > 0     else 0

        if la_boss:
            color = 0x992D22 if pct_q > 0.5 else (0xE74C3C if pct_q > 0.2 else 0xFF6B6B)
        else:
            color = 0xA84300 if pct_q > 0.5 else (0xE67E22 if pct_q > 0.2 else 0xFFA94D)

        title_icon = "⚔️" if not la_boss else ("💥" if pct_q < 0.3 else "☠️")
        embed = discord.Embed(
            title="{} {} — Phòng {}/{}".format(title_icon, q_name, phong_idx, phong_total),
            color=color)
        embed.set_author(
            name="⚔️  {} vs {}".format(s.ts.get("dao_hieu", user.display_name), q_name),
            icon_url=user.display_avatar.url)

        ll_p_max = s.ts.get("linh_luc", 100)
        # Tính ll_p_cur tại lượt n_show từ logs (ll_tick lưu giá trị sau mỗi lượt)
        ll_p_cur = ll_p_max  # mặc định đầy khi chưa có lượt nào
        for log_ll in self._combat_logs[:n_show]:
            if log_ll[1] == "ll_tick":
                ll_p_cur = log_ll[2]
        ll_q_max = quai.get("linh_luc", 100)

        e_sl = E_SINH_LUC
        e_ll = E_LINH_LUC

        # ── Emoji ID thanh HP / LL ──────────────────────────────
        HP_F = [E_HP_START, E_HP_MID, E_HP_END]
        HP_E = [E_HP_START_E, E_HP_MID_E, E_HP_END_E]
        LL_F = [E_LL_START, E_LL_MID, E_LL_END]
        LL_E = [E_LL_START_E, E_LL_MID_E, E_LL_END_E]

        def imgbar(val, mx, full_list, empty_list):
            # full_list/empty_list: [start, mid, end]
            filled = round(min(val / mx, 1.0) * 8) if mx > 0 else 8
            parts  = [full_list[0] if filled > 0 else empty_list[0]]
            for i in range(6):
                parts.append(full_list[1] if i < filled - 1 else empty_list[1])
            parts.append(full_list[2] if filled >= 8 else empty_list[2])
            return "".join(parts)



        embed.add_field(
            name="Bạn:",
            value="{} {} {:,}/{:,}\n{} {} {:,}/{:,}".format(
                imgbar(hp_p,     s.ts["hp_max"], HP_F, HP_E), e_sl, hp_p,     s.ts["hp_max"],
                imgbar(ll_p_cur, ll_p_max,       LL_F, LL_E), e_ll, ll_p_cur, ll_p_max),
            inline=False)

        embed.add_field(
            name="{}{}:".format("💀 " if la_boss else "", q_name),
            value="{} {} {:,}/{:,}\n{} {} {:,}/{:,}".format(
                imgbar(hp_q,     quai["hp"],  HP_F, HP_E), e_sl, hp_q,     quai["hp"],
                imgbar(ll_q_max, ll_q_max,    LL_F, LL_E), e_ll, ll_q_max, ll_q_max),
            inline=False)

        lines = []
        if n_show == 0:
            lines.append("⚡ **Bắt đầu trận đấu với {}!**".format(q_name))
            lines.append("*Đang chờ lượt 1...*")
        else:
            # Lọc bỏ ll_tick trước khi hiển thị (chỉ dùng để tính LL bar)
            shown_visible = [e for e in self._combat_logs[:n_show] if e[1] != "ll_tick"]
            recent = shown_visible[-4:]  # chỉ hiện 4 entry gần nhất (không kể ll_tick)
            hidden_count = len(shown_visible) - 4
            if hidden_count > 0:
                lines.append("*— {} hiệp trước —*".format(hidden_count))
            for log_item in recent:
                turn, side, dmg, crit = log_item[0], log_item[1], log_item[2], log_item[3]
                skill_nm = log_item[4] if len(log_item) > 4 else ""
                if side == "player":
                    icon = "🌟" if crit else "🔷"
                    crit_txt = "  ✨ **BẠO KÍCH!**" if crit else ""
                    skill_txt = f" dùng *{skill_nm}*" if skill_nm else ""
                    lines.append("{} **Hiệp {}** ›{} gây **{:,}** sát thương{}".format(
                        icon, turn, skill_txt, dmg, crit_txt))
                elif side == "pb_atk":
                    icon = "✨" if crit else "⚔️"
                    crit_txt = "  🌟 **BẠO KÍCH!**" if crit else ""
                    lines.append("{} **Hiệp {}** › *{}* gây **{:,}** sát thương{}".format(
                        icon, turn, skill_nm, dmg, crit_txt))
                elif side == "pb_skill":
                    lines.append("✨ **Hiệp {}** › {}".format(turn, skill_nm))
                elif side == "quai":
                    icon = "💥" if crit else "🔶"
                    crit_txt = "  ⚡ **BẠO KÍCH!**" if crit else ""
                    lines.append("{} **Hiệp {}** › {} gây **{:,}** sát thương{}".format(
                        icon, turn, q_name, dmg, crit_txt))
                # ll_tick đã bị lọc trước — không bao giờ vào đây
            if n_show < len(self._combat_logs):
                # Tìm turn tiếp theo từ entry không phải ll_tick
                next_turn = None
                for _ne in self._combat_logs[n_show:]:
                    if _ne[1] != "ll_tick":
                        next_turn = _ne[0]; break
                if next_turn is None:
                    next_turn = self._combat_logs[n_show][0]
                lines.append("")
                lines.append("*⏳ Hiệp {} đang diễn ra...*".format(next_turn))

        embed.add_field(name="\u200b", value="\n".join(lines) if lines else "\u200b", inline=False)
        embed.set_footer(text="⚔️ Bí Cảnh")
        return embed

    # ── Embed kết quả ──────────────────────────────────────────
    def _embed_result(self, user, won: bool) -> discord.Embed:
        s       = self.s
        # phong_hien đã +1 sau khi thắng → clamp về phòng vừa đánh
        idx     = min(s.phong_hien, len(s.phong_list) - 1)
        phong   = s.phong_list[idx]
        quai    = phong["data"]
        q_name  = quai["ten"]
        bc_name = self.bc["ten"]
        bc_emoji = self.bc.get("emoji", "⚔️")

        color = 0x2ECC71 if won else 0xC0392B
        title = "✅ CHIẾN THẮNG — {}".format(bc_name) if won else "💀 THẤT BẠI — {}".format(bc_name)
        embed = discord.Embed(title=title, color=color)
        embed.set_author(
            name="{} đối đầu với {}".format(s.ts.get("dao_hieu", user.display_name), q_name),
            icon_url=user.display_avatar.url)

        lines = ["⚡ **Bắt đầu trận đấu với {}!**".format(q_name), ""]
        for log_item in self._combat_logs:
            turn, side, dmg, crit = log_item[0], log_item[1], log_item[2], log_item[3]
            skill_nm = log_item[4] if len(log_item) > 4 else ""
            if side == "ll_tick":
                continue  # bỏ qua — chỉ dùng để tính LL bar
            elif side == "player":
                icon = "🌟" if crit else "🔷"
                crit_txt = "  ✨ **BẠO KÍCH!**" if crit else ""
                skill_txt = f" dùng *{skill_nm}*" if skill_nm else ""
                lines.append("{} **Hiệp {}** ›{} gây **{:,}** sát thương{}".format(
                    icon, turn, skill_txt, dmg, crit_txt))
            elif side == "pb_atk":
                icon = "✨" if crit else "⚔️"
                crit_txt = "  🌟 **BẠO KÍCH!**" if crit else ""
                lines.append("{} **Hiệp {}** › *{}* gây **{:,}** sát thương{}".format(
                    icon, turn, skill_nm, dmg, crit_txt))
            elif side == "pb_skill" and skill_nm:
                lines.append("✨ **Hiệp {}** › {}".format(turn, skill_nm))
            elif side == "quai":
                icon = "💥" if crit else "🔶"
                crit_txt = "  ⚡ **BẠO KÍCH!**" if crit else ""
                lines.append("{} **Hiệp {}** › {} gây **{:,}** sát thương{}".format(
                    icon, turn, q_name, dmg, crit_txt))
        lines.append("")
        lines.append("🏆 **Bạn đã chiến thắng {}!**".format(q_name) if won
                     else "💔 **Bạn đã bại trận trước {}...**".format(q_name))

        # Tính số hiệp visible (bỏ ll_tick)
        visible_count = sum(1 for e in lines if e)  # dùng len(lines) đã loại ll_tick
        display = lines[-12:] if len(lines) > 12 else lines
        if len(lines) > 12:
            display = ["*— {} hiệp trước —*".format(len(lines) - 12), ""] + display

        embed.add_field(name="\u200b", value="\n".join(display), inline=False)

        if won:
            _exp_m_str = getattr(s, "exp_m_display", s.he_so)
            _lt_m_str  = getattr(s, "lt_m_display",  s.he_so)
            embed.add_field(
                name="🎁  Phần Thưởng",
                value=(
                    f"{E_TU_VI} **+{fmt(s.last_exp)}** Tu vi _(×{_exp_m_str})_\n"
                    f"{E_LINH_THACH} **+{fmt(s.last_lt)}** Linh thạch _(×{_lt_m_str})_"
                ),
                inline=True)
            # Hiển thị sự kiện bí cảnh nếu có
            if s.logs:
                embed.add_field(
                    name="✨  Sự Kiện",
                    value="\n".join(s.logs[-3:]),
                    inline=False)
                s.logs.clear()  # reset để phòng tiếp theo có log sạch
            embed.add_field(
                name="📊  Tích Lũy",
                value=f"{E_TU_VI} **{s.exp_tich:,}** Tu vi\n{E_TT_LINH_THACH} **{s.lt_tich:,}** LT",
                inline=True)
            # Hiện HP còn lại để user quyết định đi tiếp hay rút
            hp_pct = int(s.hp_hien / s.ts["hp_max"] * 100) if s.ts["hp_max"] > 0 else 0
            hp_icon = E_SINH_LUC
            embed.add_field(
                name=f"{E_SINH_LUC}  HP Còn Lại",
                value=f"**{fmt(s.hp_hien)} / {fmt(s.ts['hp_max'])}** ({hp_pct}%)",
                inline=False)
            # ── Thanh Tu Vi sau boss — chỉ hiện khi vừa đánh xong boss ──
            _la_boss_now = (idx < len(s.phong_list) and s.phong_list[idx]["loai"] == "boss") or                            (s.phong_hien >= len(s.phong_list) and len(s.phong_list) > 0 and
                            s.phong_list[-1]["loai"] == "boss")
            if _la_boss_now:
                _cg    = s.ts["canh_gioi"]
                _cap   = s.ts["cap_nho"]
                _exp_hien = s.ts.get("exp", 0)       # exp trước khi nhận thưởng
                _exp_sau  = _exp_hien + s.exp_tich    # exp sau khi nhận thưởng (tích lũy)
                _exp_yc   = exp_can_thiet(_cg, _cap)  # ngưỡng đột phá kế tiếp
                _max_cap  = CANH_GIOI[_cg]["cap"] if 0 <= _cg < len(CANH_GIOI) else 3
                _la_max   = (_cg >= len(CANH_GIOI) - 1) and (_cap >= _max_cap)
                if not _la_max and _exp_yc > 0:
                    _pct_hien = min(1.0, _exp_hien / _exp_yc)
                    _pct_sau  = min(1.0, _exp_sau  / _exp_yc)
                    _bar_hien = bar(_exp_hien, _exp_yc)
                    _bar_sau  = bar(_exp_sau,  _exp_yc)
                    _ten_muc  = get_cg_ten(_cg, _cap)
                    _du_dp    = _exp_sau >= _exp_yc
                    _du_icon  = "✅" if _du_dp else "⏳"
                    _thieu_txt = f"Còn thiếu **{fmt(_exp_yc - _exp_sau)}** tu vi"
                    _du_txt    = "**Đủ tu vi để đột phá!**"
                    _tv_val = (
                        f"`{_bar_sau}` **{fmt(_exp_sau)} / {fmt(_exp_yc)}**\n"
                        f"*Sau khi nhận thưởng: {int(_pct_sau*100)}% ngưỡng {_ten_muc}*\n"
                        f"{_du_icon} {_du_txt if _du_dp else _thieu_txt}"
                    )
                    embed.add_field(
                        name=f"{E_TU_VI}  Tu Vi Đột Phá",
                        value=_tv_val,
                        inline=False)
            # Hiện đan dược đã rớt từ đầu bí cảnh tới phòng này
            if s.dan_tich:
                dan_lines = []
                for key, cnt in s.dan_tich.items():
                    if key.startswith("__dd:"):
                        dd_id = int(key[5:])
                        dd = next((d for d in DAN_DUOC if d["id"] == dd_id), None)
                        if dd:
                            dan_lines.append(f"{dd.get('emoji', E_DAN_DUOC)} **{dd['ten']}** ×{cnt} *(đại cảnh)*")
                    else:
                        parts = key.split(":", 2)
                        ten = parts[2] if len(parts) == 3 else key
                        emoji = E_DAN_DUOC
                        try:
                            cg_idx = int(parts[0])
                            if 0 <= cg_idx < len(DAN_TU_LUYEN):
                                found = next((d for d in DAN_TU_LUYEN[cg_idx] if d["ten"] == ten), None)
                                if found:
                                    emoji = found["emoji"]
                        except (ValueError, IndexError):
                            pass
                        dan_lines.append(f"{emoji} **{ten}** ×{cnt}")
                embed.add_field(
                    name=f"{E_DAN_DUOC}  Đan Dược Rớt",
                    value="\n".join(dan_lines),
                    inline=False)
            # Linh quả rớt
            if s.linh_qua_tich:
                lq_lines = [
                    f"{LINH_QUA_BY_ID[k]['emoji']} **{LINH_QUA_BY_ID[k]['ten']}** ×{v}"
                    for k, v in s.linh_qua_tich.items() if k in LINH_QUA_BY_ID
                ]
                if lq_lines:
                    embed.add_field(name="Linh Quả Rớt", value="\n".join(lq_lines), inline=False)
            # Mảnh linh căn rớt
            if s.manh_tich:
                manh_lines = [
                    f"{MANH_LINH_CAN_EMOJI.get(k,'❓')} **Mảnh {LINH_CAN_BY_ID[k]['ten'] if k in LINH_CAN_BY_ID else k}** ×{v}"
                    for k, v in s.manh_tich.items()
                ]
                if manh_lines:
                    embed.add_field(name="Mảnh Linh Căn Rớt", value="\n".join(manh_lines), inline=False)
            # Sủng thú drop
            if s.sung_thu_drop:
                embed.add_field(name="🐾 Sủng Thú Rớt!",
                    value="\n".join(f"{d['emoji']} **{d['ten']}** ⭐ Tier 1" for d in s.sung_thu_drop),
                    inline=False)
        else:
            embed.add_field(
                name="⚠️  Hậu Quả",
                value="Bạn bị thương nặng và thất bại!\nHP còn lại: **20%**\n✅ Vật phẩm (đan, linh quả, nguyên liệu, sủng thú) **giữ nguyên**.\n⚠️ Tu vi & linh thạch tích lũy **mất hoàn toàn**.",
                inline=False)

        # ── Hiện stats phòng tiếp theo (khi còn phòng và chưa xong) ──
        if won and s.phong_hien < len(s.phong_list):
            next_phong = s.phong_list[s.phong_hien]
            nq = next_phong["data"]
            la_boss_next = next_phong["loai"] == "boss"
            boss_tag = " 💀 **BOSS**" if la_boss_next else ""
            next_val = (
                f"{nq.get('emoji','')} **{nq['ten']}**{boss_tag}\n"
                f"{E_SINH_LUC} HP: **{fmt(nq['hp'])}**  "
                f"{E_CONG_KICH} ATK: **{fmt(nq['at'])}**  "
                f"{E_PHONG_NGU} DEF: **{fmt(nq['df'])}**\n"
                f"{E_HOI_TAM} Hội Tâm: **{nq.get('hoi_tam', 0):,}đ**  "
                f"{E_HO_TAM} Hộ Tâm: **{nq.get('ho_tam', 0):,}đ**\n"
                f"{E_BAO_KICH} Bạo Kích: **{int(nq.get('bao_kich', 0) * 100)}%**  "
                f"{E_KHANG_BAO} Kháng Bạo: **{int(nq.get('khang_bao', 0) * 100)}%**"
            )
            embed.add_field(
                name=f"⚔️  Phòng {s.phong_hien + 1}/{len(s.phong_list)} — Tiếp Theo",
                value=next_val,
                inline=False)

        # Lấy turn số từ entry cuối không phải ll_tick
        total_turns = 0
        for _le in reversed(self._combat_logs):
            if _le[1] != "ll_tick":
                total_turns = _le[0]; break
        embed.set_footer(text="{} {}  •  Kết thúc sau {} hiệp".format(
            bc_emoji, bc_name, total_turns))
        return embed

    # ── Đẩy job vào CombatTaskCog ─────────────────────────────
    async def _edit_msg(self, inter: discord.Interaction, embed, view):
        """Edit message an toàn — dùng message.edit() nếu có, fallback inter."""
        if self._msg is not None:
            try:
                await self._msg.edit(embed=embed, view=view)
                return
            except Exception:
                self._msg = None
        try:
            await safe_edit_message(inter, embed=embed, view=view)
        except Exception as e:
            log.warning(f"_edit_msg fallback failed: {e}")

    def _prepare_combat_buttons(self):
        """Chuẩn bị trạng thái nút trước khi gửi message combat — phải gọi TRƯỚC safe_edit_message."""
        self._btn_skip.disabled = False
        self._btn_run.disabled  = True
        self._btn_tiep.disabled = True
        self._btn_ve.disabled   = True
        self._btn_lai.disabled  = True

    def _enqueue_combat(self, inter: discord.Interaction):
        from cogs.combat_task import CombatJob
        view_ref = self
        async def on_finish():
            await view_ref._finish_after_auto(inter)
        job = CombatJob(
            inter     = inter,
            logs      = self._combat_logs,
            embed_fn  = lambda n: self._embed_combat(inter.user, n),
            view      = self,
            on_finish = on_finish,
            delay     = 1.2,
        )
        # Cache message để dùng message.edit() tránh token expiry
        async def _fetch_and_cache():
            try:
                job._message = await inter.original_response()
                self._msg    = job._message
            except Exception:
                log.exception("Lỗi bi_canh")
        import asyncio as _asyncio
        _asyncio.ensure_future(_fetch_and_cache())
        cog = self._get_task_cog(inter)
        if cog:
            cog.enqueue(job)
        else:
            log.error(f"CombatTaskCog not found for user={inter.user.id}")

    # ── Skip button ────────────────────────────────────────────
    async def _on_skip(self, inter: discord.Interaction):
        if inter.user.id != self.actor_id:
            return await inter.response.send_message("❌", ephemeral=True)
        try:
            await inter.response.defer()
        except discord.NotFound:
            pass  # Interaction đã expired — vẫn thực hiện skip
        cog = self._get_task_cog(inter)
        if cog:
            cog.skip_current(self.actor_id)

    # ── Xử lý sau khi combat xong ─────────────────────────────
    async def _finish_after_auto(self, inter: discord.Interaction):
        try:
            await self._finish_after_auto_inner(inter)
        except Exception as e:
            log.error(f"_finish_after_auto user={inter.user.id} bc={self.bc.get('id')} phong={self.s.phong_hien}: {e}", exc_info=True)
            try:
                embed = e_loi("❌ Lỗi Combat", f"```{type(e).__name__}: {e}```")
                await self._edit_msg(inter, embed, None)
            except Exception as e2:
                log.error(f"_finish_after_auto fallback edit failed: {e2}")

    async def _finish_after_auto_inner(self, inter: discord.Interaction):
        s       = self.s; bc = self.bc
        phong   = s.phong_list[s.phong_hien]
        quai    = phong["data"]
        la_boss = phong["loai"] == "boss"
        won     = self._won

        s.hp_hien = self._hp_after
        self._btn_skip.disabled = True
        self._btn_run.disabled  = True

        if not won:
            s.ket_thuc = True
            _bc_sessions.pop((self.guild_id, self.actor_id), None)
            # Lưu 100% vật phẩm đã tích, chỉ mất tu vi & linh thạch
            ts_thua = await get_tu_si(self.actor_id)
            nl_t  = ts_thua.get("nguyen_lieu", {}).copy()
            dd_t  = ts_thua.get("dan_duoc", {}).copy()
            manh_t = ts_thua.get("manh_linh_can", {}).copy()
            lq_t  = ts_thua.get("linh_qua", {}).copy()
            dtc_t = _dtc_kho(ts_thua).copy()
            for k, v in s.nl_tich.items():
                nl_t[k] = nl_t.get(k, 0) + v
            for key, cnt in s.dan_tich.items():
                dd_key = key[5:] if key.startswith("__dd:") else f"dtl:{key}"
                dd_t[dd_key] = dd_t.get(dd_key, 0) + cnt
            for lq_id, cnt in s.manh_tich.items():
                manh_t[lq_id] = manh_t.get(lq_id, 0) + cnt
            for lq_id, cnt in s.linh_qua_tich.items():
                lq_t[lq_id] = lq_t.get(lq_id, 0) + cnt
            for k, v in s.dotpha_tc_nl_tich.items():
                dtc_t[k] = dtc_t.get(k, 0) + v
            _st_kho_t  = ts_thua.get("sung_thu") or {}
            if isinstance(_st_kho_t, str):
                import json as _jt; _st_kho_t = _jt.loads(_st_kho_t) if _st_kho_t else {}
            for _d in s.sung_thu_drop:
                _sid = str(_d["id"])
                if _sid not in _st_kho_t:
                    _st_kho_t[_sid] = {"level": 1, "obtained_at": int(__import__("time").time())}
            await update_tu_si(self.actor_id,
                hp=max(1, int(s.ts["hp_max"] * 0.2)),
                nguyen_lieu=nl_t, dan_duoc=dd_t,
                manh_linh_can=manh_t, linh_qua=lq_t,
                dotpha_tc_nl=dtc_t, sung_thu=_st_kho_t,
                bc_thua_lan_truoc=1)
            self._btn_ve.label    = "Về Hồ Sơ"
            self._btn_ve.disabled = False
            self._btn_run.disabled = True
            await self._edit_msg(inter, self._embed_result(inter.user, won=False), self)
            return

        # Tính thưởng: random trong range × hệ số cảnh giới (exp_m/lt_m từ _calc_stats)
        ts_now   = await get_tu_si(self.actor_id)
        st_now   = _calc_stats(ts_now)
        he_so    = round(DIEM_DANH_HE_SO[min(ts_now["canh_gioi"], len(DIEM_DANH_HE_SO) - 1)], 2)

        lt_raw  = random.randint(quai.get("lt_min", quai.get("lt", 0)),
                                 quai.get("lt_max", quai.get("lt", 0)))
        exp_raw = random.randint(quai.get("exp_min", quai.get("exp", 0)),
                                 quai.get("exp_max", quai.get("exp", 0)))

        # Giảm thưởng theo cảnh giới cao để cân bằng progression
        _cg_now = ts_now.get("canh_gioi", 0)
        if _cg_now >= 7:
            _bc_reward_mult = 0.80   # CG7+ (Ngộ Đạo+): giảm 20%
        elif _cg_now >= 4:
            _bc_reward_mult = 0.85   # CG4+ (Cụ Linh+): giảm 15%
        else:
            _bc_reward_mult = 1.0

        s.last_lt  = int(lt_raw  * st_now["lt_m"]  * _bc_reward_mult)
        s.last_exp = int(exp_raw * st_now["exp_m"] * _bc_reward_mult)
        s.he_so    = he_so
        s.exp_m_display = round(st_now["exp_m"] * _bc_reward_mult, 2)
        s.lt_m_display  = round(st_now["lt_m"]  * _bc_reward_mult, 2)
        s.exp_tich += s.last_exp
        s.lt_tich  += s.last_lt
        for nl_id in quai.get("nl_drop", []):
            if random.random() < 0.5:
                s.nl_tich[str(nl_id)] = s.nl_tich.get(str(nl_id), 0) + random.randint(1, 2)

        # Drop đan tu luyện theo cảnh giới NGƯỜI CHƠI
        cg_player = ts_now.get("canh_gioi", 0)
        drop_m = st_now.get("drop_m", 1.0)  # hệ số drop từ thể chất/linh căn/sủng thú
        _da_trung_sinh = ts_now.get("so_lan_trung_sinh", 0) > 0
        if not la_boss:
            # Phòng thường: drop đan TIỂU CẢNH (Sơ→Trung, Trung→Hậu) tỉ lệ thấp
            if 0 <= cg_player < len(DAN_TU_LUYEN):
                dtl_list = DAN_TU_LUYEN[cg_player]
                nhom_trung = [d for d in dtl_list if d["cap_nho_sau"] == 2]
                nhom_hau   = [d for d in dtl_list if d["cap_nho_sau"] == 3]
                for nhom in [nhom_trung, nhom_hau]:
                    if not nhom:
                        continue
                    dan_chon = random.choice(nhom)
                    if random.random() < min(1.0, 0.03 * drop_m):  # 3% × drop_m
                        key = f"{cg_player}:{dan_chon['cap_nho_sau']}:{dan_chon['ten']}"
                        s.dan_tich[key] = s.dan_tich.get(key, 0) + 1
        else:
            # Boss cuối: drop đan ĐẠI CẢNH (đột phá lên CG mới) 15%
            dan_dai = next(
                (d for d in DAN_DUOC
                 if d.get("dot_pha") and d.get("cg_yeu_cau") == cg_player
                 and d.get("cap_nho_yeu_cau") is None),
                None)
            _rate_dai = min(1.0, 0.01 * drop_m * (1.5 if _da_trung_sinh else 1.0))
            if dan_dai and random.random() < _rate_dai:  # 1%×drop_m (×1.5 sau trùng sinh)
                dd_key = str(dan_dai["id"])
                s.dan_tich[f"__dd:{dd_key}"] = s.dan_tich.get(f"__dd:{dd_key}", 0) + 1
        # Drop linh quả theo tỉ lệ — nhân hệ số drop từ thể chất/linh căn/sủng thú
        _drop_linh_qua(s, la_boss, ts_now.get("linh_can_so_huu", []), drop_m=drop_m, da_trung_sinh=_da_trung_sinh)
        _drop_manh_linh_can(s, la_boss, drop_m=drop_m)
        _drop_dotpha_tc_nl(s, la_boss)

        # Sủng thú: 0.1% × drop_m
        _drop_sung_thu_bc(s, la_boss, drop_m=drop_m)

        # Drop Ý Cảnh items: Đá Ngộ Đạo (2% boss, 0.5% quái, yêu cầu trùng sinh)
        from utils.config import DA_NGO_DAO_ID, DA_RESET_SKILL_TREE_ID
        _bc_id = s.bc_id
        if _da_trung_sinh:
            if la_boss:
                if _bc_id >= 6 and random.random() < 0.02 * drop_m:
                    s.nl_tich[DA_NGO_DAO_ID] = s.nl_tich.get(DA_NGO_DAO_ID, 0) + 1
                    s.logs.append(f"💎 Nhận **1 Đá Ngộ Đạo**!")
                if _bc_id >= 7 and random.random() < 0.02 * drop_m:
                    s.nl_tich[DA_RESET_SKILL_TREE_ID] = s.nl_tich.get(DA_RESET_SKILL_TREE_ID, 0) + 1
                    s.logs.append(f"🔄 Nhận **1 Đá Reset Skill Tree**!")
            elif _bc_id >= 6 and random.random() < 0.005 * drop_m:
                s.nl_tich[DA_NGO_DAO_ID] = s.nl_tich.get(DA_NGO_DAO_ID, 0) + 1
                s.logs.append(f"💎 Nhận **1 Đá Ngộ Đạo**!")

        # ── Sự kiện ngẫu nhiên (40%) — áp dụng SAU khi tính thưởng ──
        _sk = phong.get("su_kien")
        if _sk and _sk.get("loai") in ("reward", "trap"):
            _sk_msg = _apply_event(s, _sk)
            if _sk_msg:
                s.logs.append(f"{_sk['emoji']} **{_sk['ten']}** — {_sk_msg}")

        s.phong_hien += 1
        la_cuoi = s.phong_hien >= len(s.phong_list)

        if la_cuoi:
            s.ket_thuc = True
            _bc_sessions.pop((self.guild_id, self.actor_id), None)
            ts_fresh = await get_tu_si(self.actor_id)
            if not ts_fresh:
                log.error(f"_finish_after_auto: ts_fresh None uid={self.actor_id}")
                return
            nl_new = ts_fresh["nguyen_lieu"].copy()
            for k, v in s.nl_tich.items(): nl_new[k] = nl_new.get(k, 0) + v
            dd_new = ts_fresh["dan_duoc"].copy()
            for key, cnt in s.dan_tich.items():
                if key.startswith("__dd:"):
                    # Đan đại cảnh — lưu trực tiếp bằng id số
                    dd_key = key[5:]  # bỏ prefix __dd:
                else:
                    dd_key = f"dtl:{key}"
                dd_new[dd_key] = dd_new.get(dd_key, 0) + cnt
            # Cộng dồn mảnh linh quả vào DB
            manh_new = ts_fresh.get("manh_linh_can", {}).copy()
            for lq_id, cnt in s.manh_tich.items():
                manh_new[lq_id] = manh_new.get(lq_id, 0) + cnt
            lq_new = ts_fresh.get("linh_qua", {}).copy()
            for lq_id, cnt in s.linh_qua_tich.items():
                lq_new[lq_id] = lq_new.get(lq_id, 0) + cnt
            dtc_new  = _dtc_kho(ts_fresh).copy()
            for k, v in s.dotpha_tc_nl_tich.items():
                dtc_new[k] = dtc_new.get(k, 0) + v
            import json as _jsn
            _st_kho_win = ts_fresh.get("sung_thu") or {}
            if isinstance(_st_kho_win, str):
                _st_kho_win = _jsn.loads(_st_kho_win) if _st_kho_win else {}
            else:
                _st_kho_win = dict(_st_kho_win)
            import time as _t_win
            for _dw in s.sung_thu_drop:
                _sid = str(_dw["id"])
                if _sid not in _st_kho_win:
                    _st_kho_win[_sid] = {"level": 1, "obtained_at": int(_t_win.time())}
            await add_linh_thach(self.actor_id, s.lt_tich)
            await update_tu_si(self.actor_id,
                exp=ts_fresh["exp"] + s.exp_tich,
                hp=ts_fresh["hp_max"], nguyen_lieu=nl_new,
                dan_duoc=dd_new, manh_linh_can=manh_new, linh_qua=lq_new,
                dotpha_tc_nl=dtc_new, sung_thu=_st_kho_win)
            s.hp_hien = s.ts["hp_max"]  # heal full để embed hiển thị đúng
            self._btn_ve.label    = "✅ Hoàn Thành"
            self._btn_ve.disabled = False
            self._btn_tiep.disabled = True
            self._btn_run.disabled  = True
            self._btn_lai.disabled  = False
            self._btn_lai.label     = f"⚔️ Khiêu Chiến Tiếp ({self.bc.get('ten','')})"
        else:
            # Giữa chừng: chỉ hiện Tiếp tục + Rút lui (đỏ), ẩn btn_ve
            self._btn_tiep.disabled = False
            self._btn_run.disabled  = False
            self._btn_ve.disabled   = True

        await self._edit_msg(inter, self._embed_result(inter.user, won=True), self)

    # ── Tiếp tục phòng boss ────────────────────────────────────
    async def _on_tiep_tuc(self, inter: discord.Interaction):
        if inter.user.id != self.actor_id:
            return await inter.response.send_message("❌", ephemeral=True)
        try:
            await inter.response.defer()
        except Exception:
            log.exception("Lỗi bi_canh")
        nv = BiCanhPhongView(self.parent, self.s, self.bc, bc_view=self.bc_view)
        nv._msg = self._msg  # kế thừa cached message
        nv._compute_combat()
        nv._prepare_combat_buttons()
        await safe_edit_message(inter,
            embed=nv._embed_combat(inter.user, 0), view=nv)
        nv._enqueue_combat(inter)

    # ── Rút lui trước khi đánh ────────────────────────────────
    # ── Rút lui sau khi thắng phòng ───────────────────────────
    async def _on_run(self, inter: discord.Interaction):
        if inter.user.id != self.actor_id:
            return await inter.response.send_message("❌", ephemeral=True)
        try:
            await inter.response.defer()
        except Exception:
            log.exception("Lỗi bi_canh")
        s = self.s
        s.ket_thuc = True
        _bc_sessions.pop((self.guild_id, self.actor_id), None)

        ts_fresh = await get_tu_si(self.actor_id)
        exp_nhan = int(s.exp_tich * 0.8)
        lt_nhan  = int(s.lt_tich  * 0.8)

        # Luôn giữ 100% vật phẩm — chỉ mất tu vi & linh thạch khi rút lui
        nl_new   = ts_fresh.get("nguyen_lieu", {}).copy()
        dd_new   = ts_fresh.get("dan_duoc", {}).copy()
        manh_new = ts_fresh.get("manh_linh_can", {}).copy()
        lq_new   = ts_fresh.get("linh_qua", {}).copy()
        for k, v in s.nl_tich.items():
            nl_new[k] = nl_new.get(k, 0) + v
        for key, cnt in s.dan_tich.items():
            if key.startswith("__dd:"):
                dd_key = key[5:]
            else:
                dd_key = f"dtl:{key}"
            dd_new[dd_key] = dd_new.get(dd_key, 0) + cnt
        for lq_id, cnt in s.manh_tich.items():
            manh_new[lq_id] = manh_new.get(lq_id, 0) + cnt
        for lq_id, cnt in s.linh_qua_tich.items():
            lq_new[lq_id] = lq_new.get(lq_id, 0) + cnt

        dtc_new_r  = _dtc_kho(ts_fresh).copy()
        for k, v in s.dotpha_tc_nl_tich.items():
            dtc_new_r[k] = dtc_new_r.get(k, 0) + v
        import json as _j_rut
        _st_kho_rut  = ts_fresh.get("sung_thu") or {}
        if isinstance(_st_kho_rut, str):
            _st_kho_rut = _j_rut.loads(_st_kho_rut) if _st_kho_rut else {}
        else:
            _st_kho_rut = dict(_st_kho_rut)
        for _d in s.sung_thu_drop:
            _sid = str(_d["id"])
            if _sid not in _st_kho_rut:
                _st_kho_rut[_sid] = {"level": 1, "obtained_at": int(__import__("time").time())}
        await add_linh_thach(self.actor_id, lt_nhan)
        await update_tu_si(self.actor_id,
            exp=ts_fresh["exp"] + exp_nhan,
            hp=s.hp_hien,
            nguyen_lieu=nl_new, dan_duoc=dd_new,
            manh_linh_can=manh_new, linh_qua=lq_new,
            dotpha_tc_nl=dtc_new_r,
            sung_thu=_st_kho_rut,
            bc_thua_lan_truoc=1)

        embed = discord.Embed(
            title="🏃 Rút Lui",
            description=(
                f"Rút lui sau khi thắng **{s.phong_hien}** phòng.\n"
                "✅ Mọi vật phẩm (nguyên liệu, đan, linh quả, sủng thú...) **giữ 100%**.\n"
                "⚠️ Tu vi & linh thạch chỉ nhận **80%** tích lũy."
            ),
            color=0xFEE75C)
        embed.add_field(name=f"{E_TU_VI} Tu Vi",           value=f"+{fmt(exp_nhan)}", inline=True)
        embed.add_field(name=f"{E_LINH_THACH} Linh Thạch", value=f"+{fmt(lt_nhan)}", inline=True)
        if s.nl_tich:
            nl_lines = []
            for k, v in s.nl_tich.items():
                try:
                    nl_lines.append(f"{NGUYEN_LIEU[int(k)]['emoji']} ×{v}")
                except Exception:
                    log.exception("Lỗi bi_canh")
            if nl_lines:
                embed.add_field(name="📦 Nguyên liệu giữ lại", value="  ".join(nl_lines), inline=False)
        if s.linh_qua_tich or s.manh_tich:
            lq_lines = [f"{LINH_QUA_BY_ID[k]['emoji']} {LINH_QUA_BY_ID[k]['ten']} ×{v}"
                        for k, v in s.linh_qua_tich.items() if k in LINH_QUA_BY_ID]
            manh_lines = [f"{MANH_LINH_CAN_EMOJI.get(k, '❓')} Mảnh {LINH_CAN_BY_ID[k]['ten'] if k in LINH_CAN_BY_ID else k} ×{v}"
                          for k, v in s.manh_tich.items()]
            all_lines = lq_lines + manh_lines
            if all_lines:
                embed.add_field(name="Linh quả & mảnh giữ lại", value="\n".join(all_lines), inline=False)
        embed.set_footer(text="20% tu vi & linh thạch còn lại bị mất do rút lui.")

        if self.bc_view is not None:
            self.bc_view.ts = await get_tu_si(self.actor_id)
            self.bc_view._select.disabled  = False
            self.bc_view._selected_bc_id   = None
            self.bc_view._btn_back_tmp = False  # về thẳng hồ sơ khi bấm Quay Lại
            await safe_edit_message(inter, embed=embed, view=self.bc_view)
        else:
            await _back_to_hoso(inter, self.parent)

    async def _on_lai(self, inter: discord.Interaction):
        """Khiêu chiến lại tầng bí cảnh vừa hoàn thành — phần thưởng tầng trước đã nhận đủ 100%."""
        if inter.user.id != self.actor_id:
            return await inter.response.send_message("❌", ephemeral=True)
        try:
            await inter.response.defer()
        except Exception:
            log.exception("Lỗi bi_canh")
        ts_fresh   = await get_tu_si(self.actor_id)
        tl_hien    = get_the_luc(ts_fresh)
        tran_hien2 = get_tran_the_luc(ts_fresh)
        BC_PHI     = 10
        if tl_hien >= BC_PHI:
            new_tl2   = tl_hien - BC_PHI
            new_tran2 = tran_hien2
        elif tran_hien2 >= BC_PHI:
            new_tl2   = tl_hien
            new_tran2 = tran_hien2 - BC_PHI
        else:
            tl_max2 = the_luc_toi_da(ts_fresh.get("canh_gioi", 0))
            return await safe_followup(inter, 
                embed=e_warn("⚡ Thể Lực Không Đủ",
                    f"Cần **{BC_PHI} ⚡** để vào bí cảnh.\n"
                    f"Thể lực chính: **{tl_hien}/{tl_max2}**  "
                    f"Tràn: **{tran_hien2}/{TRAN_THE_LUC_MAX}**"),
                ephemeral=True)
        await update_tu_si(self.actor_id,
            the_luc=new_tl2,
            the_luc_cap_nhat=int(time.time()),
            tran_the_luc=new_tran2,
            tran_the_luc_cap_nhat=int(time.time()),
            bc_thua_lan_truoc=0)
        # Tạo session mới trên cùng bc_id
        bc_id = self.bc.get("id", 0)
        bc    = BI_CANH[bc_id]
        rooms = _gen_rooms(bc)
        rooms = _scale_rooms_by_rebirth(rooms, ts_fresh.get("so_lan_trung_sinh", 0))
        from cogs.hoso_utils import _calc_full_stats
        full  = _calc_full_stats(ts_fresh)
        ts_for_session = {
            **ts_fresh,
            "cong":      full["at"],
            "thu":       full["df"],
            "hp_max":    full["hp_eff"],
            "linh_luc":  full["linh_luc"],
            "hoi_tam":   full["hoi_tam"],
            "ho_tam":    full["ho_tam"],
            "bao_kich":  full["bao_kich"],
            "khang_bao": full["khang_bao"],
        }
        s_new = BiCanhSession(
            user_id=self.actor_id, bc_id=bc_id, ts=ts_for_session,
            phong_list=rooms, hp_hien=full["hp_eff"],
            ll_hien=ts_for_session.get("linh_luc", 100),
            created_at=int(time.time()))
        _bc_sessions[(self.guild_id, self.actor_id)] = s_new
        new_view = BiCanhPhongView(self.parent, s_new, bc, bc_view=self.bc_view)
        new_view._msg = self._msg
        new_view._compute_combat()
        new_view._prepare_combat_buttons()
        await safe_edit_message(inter,
            embed=new_view._embed_combat(inter.user, 0), view=new_view)
        new_view._enqueue_combat(inter)

    async def _on_ve(self, inter: discord.Interaction):
        if inter.user.id != self.actor_id:
            return await inter.response.send_message("❌", ephemeral=True)
        try:
            await inter.response.defer()
        except Exception:
            log.exception("Lỗi bi_canh")
        self.s.ket_thuc = True
        _bc_sessions.pop((self.guild_id, self.actor_id), None)

        # Lưu TẤT CẢ vật phẩm tích lũy vào DB (fix: trước chỉ lưu dan_tich)
        s = self.s
        has_items = (s.dan_tich or s.nl_tich or s.linh_qua_tich
                     or s.manh_tich or s.dotpha_tc_nl_tich or s.sung_thu_drop)
        if has_items:
            ts_fresh = await get_tu_si(self.actor_id)

            # Đan dược
            dd_new = ts_fresh["dan_duoc"].copy()
            for key, cnt in s.dan_tich.items():
                dd_key = key[5:] if key.startswith("__dd:") else f"dtl:{key}"
                dd_new[dd_key] = dd_new.get(dd_key, 0) + cnt

            # Nguyên liệu
            nl_new = ts_fresh.get("nguyen_lieu", {}).copy()
            for k, v in s.nl_tich.items():
                nl_new[k] = nl_new.get(k, 0) + v

            # Linh quả
            lq_new = ts_fresh.get("linh_qua", {}).copy()
            for lq_id, cnt in s.linh_qua_tich.items():
                lq_new[lq_id] = lq_new.get(lq_id, 0) + cnt

            # Mảnh linh căn
            manh_new = ts_fresh.get("manh_linh_can", {}).copy()
            for lq_id, cnt in s.manh_tich.items():
                manh_new[lq_id] = manh_new.get(lq_id, 0) + cnt

            # Nguyên liệu đột phá thể chất
            dtc_new = _dtc_kho(ts_fresh).copy()
            for k, v in s.dotpha_tc_nl_tich.items():
                dtc_new[k] = dtc_new.get(k, 0) + v

            # Sủng thú
            import json as _j_timeout
            _st_kho = ts_fresh.get("sung_thu") or {}
            if isinstance(_st_kho, str):
                _st_kho = _j_timeout.loads(_st_kho) if _st_kho else {}
            else:
                _st_kho = dict(_st_kho)
            for _d in s.sung_thu_drop:
                _sid = str(_d["id"])
                if _sid not in _st_kho:
                    _st_kho[_sid] = {"level": 1, "obtained_at": int(__import__("time").time())}

            await update_tu_si(self.actor_id,
                dan_duoc=dd_new, nguyen_lieu=nl_new,
                linh_qua=lq_new, manh_linh_can=manh_new,
                dotpha_tc_nl=dtc_new, sung_thu=_st_kho)

        if self.bc_view is not None:
            self.bc_view.ts = await get_tu_si(self.actor_id)
            self.bc_view._select.disabled  = False
            self.bc_view._selected_bc_id   = None
            self.bc_view._btn_back_tmp = False  # về thẳng hồ sơ khi bấm Quay Lại
            embed = _embed_bi_canh_chon(self.bc_view.ts, inter.user)
            await safe_edit_message(inter, embed=embed, view=self.bc_view)
        else:
            await _back_to_hoso(inter, self.parent)

# ══════════════════════════════════════════════════════════════
#  CÔNG PHÁP VIEW
# ══════════════════════════════════════════════════════════════
