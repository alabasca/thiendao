"""
╔══════════════════════════════════════════════════════════╗
║  QCBH TU TIÊN BOT  —  /hoso  (refactored)               ║
╚══════════════════════════════════════════════════════════╝
"""
from __future__ import annotations
from typing import Any

import discord
from utils.embeds import e_loi, e_ok, e_warn
from cogs.bxh import _build_bxh_embed
import asyncio
import logging
import time
from discord import app_commands
from discord.ext import commands, tasks
import discord.ext.tasks
from datetime import datetime, timezone, timedelta

log = logging.getLogger("hoso")

# ── Utils & Helpers ────────────────────────────────────────
from cogs.thuoc_tinh import _build_embed_thuoc_tinh
from cogs.views._session import BiCanhSession, _bc_sessions, _cleanup_stale_sessions
from cogs.hoso_utils import (
    _run_task,
    _back_to_hoso, _parse_emoji, _calc_stats, _calc_full_stats,
    _gen_rooms, _apply_event,
    _send_hoso_embed, _embed_hoso, _embed_tu_luyen, _embed_hanh_dong,
    _build_inventory, _embed_kho_trang,
    _boss_current_window, _boss_is_active, _embed_the_gioi,
    VN_TZ, BOSS_LIFETIME, ITEMS_PER_PAGE,
    diem_danh_cd_con_lai, diem_danh_day_delta,
)

# ── Shared config/db imports ───────────────────────────────
from utils.config import (
    CANH_GIOI, TONG_MON, PHAP_BAO,
    DAN_DUOC, DAN_TU_LUYEN, NGUYEN_LIEU, BI_CANH, BOSS_THE_GIOI,
    BOSS_SPAWN_HOURS_VN, boss_bar, BOSS_HP_BY_CG, emoji_hp_bar,
    DIEM_DANH_PHAN_THUONG, BUFF_LABELS, DIEM_DANH_HE_SO,
    CD_TU_LUYEN, CD_DOT_PHA, CD_KHAI_HOANG,
    get_cg, get_cg_ten, bar, fmt, fmt_cd,
    exp_can_thiet, hp_max_cong_thuc, cong_cong_thuc, thu_cong_thuc,
    random_linh_can_co_ban, OWNER_IDS,
    LINH_CAN_BY_ID, LINH_CAN_DIEM_YEU_CAU,
    QUAN_HE_LOAI, get_quan_he_cap,
    BOSS_ANNOUNCE_CHANNEL_ID,
    DOTPHA_TC_NGUYEN_LIEU, DOTPHA_TC_DROP_RATE,
    VAN_DINH_TUVI_YEU_CAU,
    SHOP_CONTACT_ID,
)
from utils.emoji_manager import get_stat_emoji
from cogs.cong_phap import CONG_PHAP, LOAI_CONG_PHAP, CongPhapView, calc_cp_bonus
from utils.database import (
    get_tu_si, create_tu_si, update_tu_si, add_linh_thach,
    get_bang_xep_hang, get_bxh_tong_tu_vi, get_bxh_linh_thach, get_bxh_linh_can, get_bxh_chien_luc,
    dang_ban, get_phien_cho, get_phien_cho_item, mua_phien_cho,
    has_nhan_thuong, mark_nhan_thuong,
    get_boss_state, upsert_boss, spawn_boss, add_boss_damage, get_boss_leaderboard,
    get_the_luc, get_tran_the_luc, THE_LUC_HOI, the_luc_toi_da,
    TRAN_THE_LUC_MAX, TRAN_THE_LUC_HOI,
    get_quan_he,
    get_boss_channel, set_boss_channel,
    set_boss_end_time,
    save_boss_guild_message, get_boss_guild_messages, clear_boss_guild_messages,
    cleanup_old_boss_data,
    get_expired_phien_cho,
    _enqueue,
)

# ── Views ──────────────────────────────────────────────────
from cogs.views.tu_luyen  import TuLuyenView, DungDanView, DungDanModal
from cogs.views.tong_mon  import TongMonView
from cogs.views.dotpha_tc import DotPhaTCView, _embed_chon as _embed_dotpha_chon
from cogs.views.van_dinh  import VanDinhView
from cogs.views.sung_thu import SungThuView, _embed_sung_thu_list, _parse_sung_thu, _calc_sung_thu_buff
from cogs.views.kho_do    import (KhoDoView, BanLaiModal, TreoBanDTLModal,
                                   CuaHangView, MuaDanModal, PhuongThiView,
                                   MuaPhienModal, DangBanModal)
from cogs.shop import ShopView
from cogs.views.boss      import _build_ket_qua, LobbyBossView, BossView, _build_initial_boss_message
from cogs.views.profile   import DangKyModal, ChinhSuaModal, _DangKyTriggerView
from cogs.views.quan_he   import TangQuaView, _embed_quan_he
from cogs.views.pvp import start_pvp
from cogs.views.bi_canh   import (BiCanhChonView, BiCanhPhongView,
                                   _embed_bi_canh_chon, _send_bi_canh_embed,
                                   _bc_embed_phong, BC_CHON_IMG)

import re as _re
import random
import os
from utils.bot_emojis import (
    E_SINH_LUC, E_LINH_LUC, E_CONG_KICH, E_PHONG_NGU,
    E_LINH_THACH, E_TT_LINH_THACH,
    E_TIM_DO, E_TIM_NUA, E_TIM_DEN,
    E_TU_VI,
)
from utils.embeds import safe_followup, safe_defer

# ══════════════════════════════════════════════════════════════
#  MAIN HOSO VIEW
# ══════════════════════════════════════════════════════════════


class BiCanhLoaiView(discord.ui.View):
    def __init__(self, parent_view, ts, actor_id, guild_id, mount_lv):
        super().__init__(timeout=120)
        self._parent = parent_view
        self._ts = ts
        self._actor_id = actor_id
        self._guild_id = guild_id
        self._mount_lv = mount_lv

    @discord.ui.button(label="⚔️ Bị Cảnh Thường", style=discord.ButtonStyle.primary, row=0)
    async def btn_thuong(self, inter):
        if inter.user.id != self._actor_id:
            return await inter.response.send_message("❌", ephemeral=True)
        await inter.response.defer(ephemeral=True)
        embed2 = _embed_bi_canh_chon(self._ts, inter.user)
        view2 = BiCanhChonView(self._parent, self._ts, actor_id=self._actor_id, guild_id=self._guild_id)
        try:
            await inter.followup.send(embed=embed2, view=view2, ephemeral=True)
        except Exception:
            try:
                await inter.edit_original_response(embed=embed2, view=view2)
            except Exception:
                pass

    @discord.ui.button(label="🐉 Bị Cảnh Tọa Kỹ", style=discord.ButtonStyle.success, row=0)
    async def btn_toa_ky(self, inter):
        if inter.user.id != self._actor_id:
            return await inter.response.send_message("❌", ephemeral=True)
        if self._mount_lv < 1:
            return await inter.response.send_message("❌ Cần có tọa kỹ level ≥ 1!", ephemeral=True)
        await inter.response.defer(ephemeral=True)
        from cogs.views.toa_ky_bi_canh import ToaKyBiCanhView, _embed_toa_ky_bi_canh_chon
        embed3 = _embed_toa_ky_bi_canh_chon(self._ts, inter.user)
        view3 = ToaKyBiCanhView(self._parent, self._ts, actor_id=self._actor_id, guild_id=self._guild_id)
        try:
            await inter.followup.send(embed=embed3, view=view3, ephemeral=True)
        except Exception:
            try:
                await inter.edit_original_response(embed=embed3, view=view3)
            except Exception:
                pass

class HoSoView(discord.ui.View):
    """
    Row 0 : tab buttons  [📋 Hồ Sơ] [⚔️ Hành Động] [🎒 Kho Đồ] [🌍 Thế Giới]
    Row 1-2: sub-buttons thay đổi theo tab
    """
    def __init__(self, ts: dict[str, Any], user: discord.User, owner_id: int, viewer_id: int = None):
        super().__init__(timeout=300)  # 5 phút — tránh memory leak
        self.ts        = ts
        self.user      = user
        self.owner_id  = owner_id
        self.viewer_id = viewer_id or owner_id  # người đang xem
        self._message  = None  # lưu message ref để edit sau
        self._rebuild()

    # ── guard: chỉ block bot, cho phép mọi user tương tác với ts của chính họ
    async def _guard(self, inter: discord.Interaction) -> bool:
        if inter.user.bot:
            try:
                await inter.response.defer()
            except Exception:
                log.exception("Lỗi hoso")
            return False
        # Nếu interaction đã expired (>3s hoặc sau restart) → bỏ qua
        try:
            _ = inter.id  # check interaction còn hợp lệ không
        except Exception:
            return False
        # Nếu bấm vào hồ sơ người khác → kiểm tra người bấm đã có hồ sơ chưa
        if inter.user.id != self.owner_id:
            ts_caller = await get_tu_si(inter.user.id)
            if not ts_caller:
                try:
                    await inter.response.send_message(
                        "❌ Bạn chưa có hồ sơ! Dùng `/hoso` để đăng ký.",
                        ephemeral=True)
                except Exception:
                    log.exception("Lỗi hoso")
                return False
        return True

    # ── reload: load ts của người đang tương tác ─────────────────
    async def _reload(self, user_id: int = None):
        uid   = user_id or self.owner_id
        fresh = await get_tu_si(uid)
        if fresh and uid == self.owner_id:
            self.ts = fresh
        return fresh

    # ── current embed ─────────────────────────────────────────
    def _current_embed(self) -> discord.Embed:
        return _embed_hoso(self.ts, self.user, is_own=True)

    # ── rebuild all buttons ───────────────────────────────────
    def _rebuild(self):
        self.clear_items()
        is_own = (self.viewer_id == self.owner_id)

        if is_own:
            # ── Row 0: Hồ sơ ──────────────────────────────────────────
            self._add(0, "✏️ Chỉnh sửa",   discord.ButtonStyle.primary,   self._cb_chinh_sua)
            self._add(0, "📅 Điểm danh",   discord.ButtonStyle.success,   self._cb_diem_danh)
            self._add(0, "📊 Thuộc tính",  discord.ButtonStyle.secondary, self._cb_chi_tiet)
            self._add(0, "🌸 Tông môn",    discord.ButtonStyle.secondary, self._cb_tong_mon)
            # ── Row 1: Tu luyện ───────────────────────────────────────
            self._add(1, "⚡ Tu luyện",    discord.ButtonStyle.primary,   self._cb_tu_luyen)
            self._add(1, "💝 Donate",   discord.ButtonStyle.success,   self._cb_donate)
            self._add(1, "🎒 Túi đồ",     discord.ButtonStyle.secondary, self._cb_kho_do)
            self._add(1, "🌐 Hệ Thống CG", discord.ButtonStyle.secondary, self._cb_he_thong_cg)
            # ── Row 2: Thế giới ───────────────────────────────────────
            self._add(2, "🗺️ Bí cảnh",   discord.ButtonStyle.primary,   self._cb_bi_canh_menu)
            self._add(2, "👿 Boss TG",     discord.ButtonStyle.danger,    self._cb_boss_menu)
            self._add(2, "🏪 Phường thị", discord.ButtonStyle.secondary, self._cb_phuong_thi)
            self._add(2, "🧬 Đột Phá TC",  discord.ButtonStyle.primary,   self._cb_dotpha_tc)
            # Nút Vấn Đỉnh hiện khi Đăng Tiên Hậu Kỳ + tu vi hiện có >= 999,999,999
            _cg_now  = self.ts.get("canh_gioi", 0)
            _cap_now = self.ts.get("cap_nho", 1)
            _tv_now  = self.ts.get("exp", 0)
            if _cg_now == 9 and _cap_now == 3 and _tv_now >= VAN_DINH_TUVI_YEU_CAU:
                self._add(3, "✨ Vấn Đỉnh", discord.ButtonStyle.danger, self._cb_van_dinh)
            # ── Row 3: Xã hội + Ý Cảnh (sau trùng sinh) ──────────────
            _so_lan_ts = self.ts.get("so_lan_trung_sinh", 0)
            self._add(3, "🐾 Sủng Thú",  discord.ButtonStyle.primary,   self._cb_sung_thu)
            self._add(3, "🐉 Tọa Kỵ",  discord.ButtonStyle.primary,   self._cb_toa_ky)
            self._add(3, "❤️ Quan hệ", discord.ButtonStyle.danger, self._cb_quan_he_owner)
            self._add(3, "🏆 Bảng XH",  discord.ButtonStyle.secondary, self._cb_bxh)
            if _so_lan_ts >= 1:
                self._add(4, "🧠 Ý Cảnh", discord.ButtonStyle.primary, self._cb_y_canh)
                self._add(4, "⚔️ Trận Đạo", discord.ButtonStyle.secondary, self._cb_tran_dao)
                self._add(4, "🛒 Cửa Hàng Ý Cảnh", discord.ButtonStyle.success, self._cb_cua_hang_y_canh)
        else:
            # ── Xem hồ sơ người khác: chỉ hiện Tặng Quà + Quan Hệ ───
            self._add(0, "🎁 Tặng Quà",   discord.ButtonStyle.success,   self._cb_tang_qua)
            self._add(0, "❤️ Quan Hệ",    discord.ButtonStyle.primary,   self._cb_quan_he)
            self._add(0, "⚔️ Thách Đấu",  discord.ButtonStyle.danger,    self._cb_pvp)

    def _add(self, row: int, label: str, style, callback):
        btn = discord.ui.Button(label=label, style=style, row=row)
        btn.callback = callback
        self.add_item(btn)

    def _add_disabled(self, row: int, label: str,
                      style=discord.ButtonStyle.secondary):
        btn = discord.ui.Button(label=label, style=style, row=row, disabled=True)
        self.add_item(btn)

    # helper: về main view — nếu chủ hồ sơ thì edit, ngược lại send ephemeral
    async def _back(self, inter: discord.Interaction):
        await _back_to_hoso(inter, self)

    # helper: refresh message gốc — chỉ khi là chủ hồ sơ
    async def _safe_refresh_main(self, inter: discord.Interaction):
        if inter.user.id == self.owner_id:
            await self._reload(inter.user.id)
            self._rebuild()
            try:
                await inter.edit_original_response(embed=self._current_embed(), view=self)
            except Exception:
                try:
                    if inter.message:
                        await inter.message.edit(embed=self._current_embed(), view=self)
                except Exception as e:
                    log.warning(f"_safe_refresh_main: message edit failed: {e}")


    async def _cb_refresh(self, inter: discord.Interaction):
        if not await self._guard(inter): return
        await self._back(inter)

    async def _cb_kho_do(self, inter: discord.Interaction):
        if not await self._guard(inter): return
        if not await safe_defer(inter, ephemeral=True):
            return
        try:
            ts = await get_tu_si(inter.user.id)
            if not ts:
                return await safe_followup(inter,
                    "❌ Không tìm thấy hồ sơ! Dùng `/hoso` để tạo nhân vật.",
                    ephemeral=True)
            items = _build_inventory(ts)
            embed = _embed_kho_trang(ts, inter.user, items, 0)
            view  = KhoDoView(self, inter.user, ts, items, actor_id=inter.user.id)
            msg = await safe_followup(inter, embed=embed, view=view, ephemeral=True)
            if msg:
                view._original_msg = msg
        except Exception:
            log.exception(f"_cb_kho_do crash user={inter.user.id}")
            await safe_followup(inter, "❌ Lỗi khi mở túi đồ — vui lòng thử lại!", ephemeral=True)

    async def _cb_chinh_sua(self, inter: discord.Interaction):
        if not await self._guard(inter): return
        if inter.user.id != self.owner_id:
            return await inter.response.send_message(
                "❌ Bạn chỉ có thể chỉnh sửa hồ sơ của chính mình!", ephemeral=True)
        # Dùng self.ts đã cache — tránh DB call trước send_modal
        # (DB call chậm có thể làm interaction token expire trước khi respond)
        try:
            await inter.response.send_modal(ChinhSuaModal(self, self.ts))
        except (discord.errors.InteractionResponded, discord.errors.NotFound):
            pass
        except Exception as e:
            log.warning(f"_cb_chinh_sua send_modal error user={inter.user.id}: {e}")

    async def _cb_bxh(self, inter: discord.Interaction):
        try:
            await inter.response.defer(ephemeral=True)
        except discord.NotFound:
            return
        try:
            embed, view = await _build_bxh_embed("canh_gioi")
            await safe_followup(inter, embed=embed, view=view, ephemeral=True)
        except Exception as e:
            log.error(f"_cb_bxh user={inter.user.id}: {e}", exc_info=True)
            await safe_followup(inter, f"❌ Lỗi: {e}", ephemeral=True)

    async def _cb_y_canh(self, inter: discord.Interaction):
        if not await self._guard(inter): return
        if not await safe_defer(inter, ephemeral=True):
            return
        ts = await get_tu_si(inter.user.id)
        if not ts:
            return await safe_followup(inter, "❌ Không tìm thấy hồ sơ!", ephemeral=True)
        if ts.get("so_lan_trung_sinh", 0) < 1:
            return await safe_followup(inter,
                "❌ Ý Cảnh chỉ mở sau khi **trùng sinh** lần đầu!", ephemeral=True)
        try:
            from cogs.views.y_canh import YCanhView, _embed_y_canh
            embed = _embed_y_canh(ts)
            view = YCanhView(self, ts, actor_id=inter.user.id)
            await safe_followup(inter, embed=embed, view=view, ephemeral=True)
        except Exception as e:
            log.error(f"_cb_y_canh user={inter.user.id}: {e}", exc_info=True)
            await safe_followup(inter, f"❌ Lỗi: {e}", ephemeral=True)

    async def _cb_tran_dao(self, inter: discord.Interaction):
        if not await self._guard(inter): return
        if not await safe_defer(inter, ephemeral=True):
            return
        ts = await get_tu_si(inter.user.id)
        if not ts:
            return await safe_followup(inter, "❌ Không tìm thấy hồ sơ!", ephemeral=True)
        if ts.get("so_lan_trung_sinh", 0) < 1:
            return await safe_followup(inter,
                "❌ Trận Đạo chỉ mở sau khi **trùng sinh** lần đầu!", ephemeral=True)
        try:
            from cogs.views.tran_dao import TranDaoView, _embed_tran_dao
            embed = _embed_tran_dao(ts)
            view = TranDaoView(self, ts, actor_id=inter.user.id)
            await safe_followup(inter, embed=embed, view=view, ephemeral=True)
        except Exception as e:
            log.error(f"_cb_tran_dao user={inter.user.id}: {e}", exc_info=True)
            await safe_followup(inter, f"❌ Lỗi: {e}", ephemeral=True)

    async def _cb_cua_hang_y_canh(self, inter: discord.Interaction):
        if not await self._guard(inter): return
        if not await safe_defer(inter, ephemeral=True):
            return
        ts = await get_tu_si(inter.user.id)
        if not ts:
            return await safe_followup(inter, "❌ Không tìm thấy hồ sơ!", ephemeral=True)
        if ts.get("so_lan_trung_sinh", 0) < 1:
            return await safe_followup(inter,
                "❌ Cửa Hàng Ý Cảnh chỉ mở sau khi **trùng sinh** lần đầu!", ephemeral=True)
        try:
            from cogs.views.cua_hang_y_canh import CuaHangYCanhView, _embed_shop
            embed = _embed_shop(ts)
            view = CuaHangYCanhView(self, ts, actor_id=inter.user.id)
            await safe_followup(inter, embed=embed, view=view, ephemeral=True)
        except Exception as e:
            log.error(f"_cb_cua_hang_y_canh user={inter.user.id}: {e}", exc_info=True)
            await safe_followup(inter, f"❌ Lỗi: {e}", ephemeral=True)

    async def _cb_pvp(self, inter: discord.Interaction):
        """Thách đấu chủ hồ sơ đang xem."""
        # self.user = target (owner of profile), inter.user = viewer (challenger)
        if inter.user.id == self.owner_id:
            return await inter.response.send_message(
                embed=e_loi("❌ Không thể tự thách mình", "Hãy xem hồ sơ người khác!"),
                ephemeral=True)
        await start_pvp(inter, self.user)

    async def _cb_tong_mon(self, inter: discord.Interaction):
        if not await self._guard(inter): return
        try:
            ts = await get_tu_si(inter.user.id)
            from cogs.views.tong_mon import PHI_ROI_TONG
            embed = discord.Embed(title="🌸 CHỌN TÔNG MÔN", color=0xC77DFF,
                description=(
                    f"Gia nhập tông môn để nhận buff thường trực.\n"
                    f"⚠️ Rời tông cũ tốn **{fmt(PHI_ROI_TONG)} {E_LINH_THACH}** — cần xác nhận."
                ))
            for tm in TONG_MON:
                active = " ← *đang theo*" if tm["id"] == ts["tong_mon"] else ""
                embed.add_field(
                    name=f"{tm['emoji']} {tm['ten']}{active}",
                    value=f"**{BUFF_LABELS[tm['buff']]}** ×{tm['buff_val']}\n*{tm.get('mo_ta', '')}*",
                    inline=False)
            await inter.response.send_message(embed=embed, view=TongMonView(self, ts, actor_id=inter.user.id), ephemeral=True)
        except Exception as e:
            log.error(f"_cb_tong_mon user={inter.user.id}: {e}", exc_info=True)
            try:
                await inter.response.send_message(f"❌ Lỗi: {e}", ephemeral=True)
            except Exception:
                log.exception("Lỗi hoso")

    async def _cb_he_thong_cg(self, inter: discord.Interaction):
        if not await self._guard(inter): return
        await inter.response.defer(ephemeral=True)

        from utils.config import LINH_CAN, THE_CHAT, _EXP_TABLE, LINH_CAN_DIEM_YEU_CAU

        # ── Helper compact number ──────────────────────────────────────────────
        def _fmts(n):
            if n >= 1_000_000: return f"{n/1_000_000:.1f}M"
            if n >= 1_000:     return f"{n//1_000}K"
            return str(n)

        # ── Helper format passive linh căn (đầy đủ mọi key) ──────────────────
        def _fmt_lc_passive(p):
            parts = []
            if p.get("at_flat"):    parts.append(f"AT+{p['at_flat']}")
            if p.get("at_pct"):     parts.append(f"AT+{p['at_pct']:.1f}%")
            if p.get("df_flat"):    parts.append(f"DEF+{p['df_flat']}")
            if p.get("def_pct"):    parts.append(f"DEF+{p['def_pct']:.1f}%")
            if p.get("hp_flat"):    parts.append(f"HP+{_fmts(p['hp_flat'])}")
            if p.get("hp_pct"):     parts.append(f"HP+{p['hp_pct']:.1f}%")
            if p.get("bao_kich"):   parts.append(f"BK+{p['bao_kich']:.1f}%")
            if p.get("hoi_tam"):    parts.append(f"HT+{p['hoi_tam']}đ")
            if p.get("ho_tam"):     parts.append(f"HTâm+{p['ho_tam']}đ")
            if p.get("khang_bao"):  parts.append(f"KB+{p['khang_bao']:.1f}%")
            if p.get("drop_rate"):  parts.append(f"Drop+{p['drop_rate']:.0f}%")
            if p.get("exp_pct"):    parts.append(f"TV+{p['exp_pct']:.0f}%")
            return " · ".join(parts) or "—"

        def _fmt_lc_dotpha(db):
            parts = []
            for k, v in db.items():
                if k == "at_pct":      parts.append(f"AT+{v}%")
                elif k == "def_pct":   parts.append(f"DEF+{v}%")
                elif k == "hp_pct":    parts.append(f"HP+{v}%")
                elif k == "bao_kich":  parts.append(f"BK+{v}%")
                elif k == "khang_bao": parts.append(f"KB+{v}%")
                elif k == "drop_rate": parts.append(f"Drop+{v}%")
                elif k == "exp_pct":   parts.append(f"TV+{v}%")
                elif k == "hoi_tam":   parts.append(f"HT+{v}đ")
                elif k == "ho_tam":    parts.append(f"HTâm+{v}đ")
            return " · ".join(parts) or "—"

        def _fmt_tc_buff(b):
            parts = []
            if b.get("at_pct"):          parts.append(f"AT{b['at_pct']:+.0f}%")
            if b.get("def_pct"):         parts.append(f"DEF{b['def_pct']:+.0f}%")
            if b.get("hp_pct"):          parts.append(f"HP{b['hp_pct']:+.0f}%")
            if b.get("bao_kich"):        parts.append(f"BK{b['bao_kich']:+.0f}%")
            if b.get("hoi_tam"):         parts.append(f"HT+{b['hoi_tam']}đ")
            if b.get("ho_tam"):          parts.append(f"HTâm+{b['ho_tam']}đ")
            if b.get("khang_bao"):       parts.append(f"KB{b['khang_bao']:+.0f}%")
            if b.get("exp_m") and b["exp_m"] != 1:       parts.append(f"TV×{b['exp_m']}")
            if b.get("lt_m") and b["lt_m"] != 1:         parts.append(f"LT×{b['lt_m']}")
            if b.get("drop_rate"):       parts.append(f"Drop+{b['drop_rate']:.0f}%")
            if b.get("cd_tu_luyen_pct"): parts.append(f"CD{b['cd_tu_luyen_pct']:+.0f}%")
            return " · ".join(parts) or "—"

        # ══════════════════════════════════════════════════════════
        #  EMBED 1 — Bảng cảnh giới + EXP + quy tắc đột phá
        # ══════════════════════════════════════════════════════════
        embed1 = discord.Embed(
            title="🌐 HỆ THỐNG CẢNH GIỚI  (1/3)",
            description=(
                "Thiên đạo vô tận, đường tu tiên trải dài **10 cảnh giới** lớn.\n"
                "Mỗi cảnh giới gồm **3 tiểu cảnh**: Sơ Kì → Trung Kì → Hậu Kì.\n"
                f"*Chỉ số bên dưới tính tại **Hậu Kì** (cap 3) của từng cảnh giới.*"
            ),
            color=0xF0A500)

        # ── Bảng CG với EXP Hậu Kì ────────────────────────────────────────────
        def _cg_line(i, cg):
            cap_max = CANH_GIOI[i]["cap"]  # = 3
            fail    = min(0.10 + i * 0.10, 0.90)
            tc_pct  = int((1.0 - fail) * 100)
            hp_hk   = hp_max_cong_thuc(i, cap_max)
            at_hk   = cong_cong_thuc(i, cap_max)
            df_hk   = thu_cong_thuc(i, cap_max)
            ll_hk   = int((200 + i**2 * 2300 + cap_max * 230) * 0.8 * 0.7)
            exp_hk  = _EXP_TABLE[i][cap_max - 1] if i < len(_EXP_TABLE) else 0
            dp_str  = f"ĐP:{tc_pct}%" if i < len(CANH_GIOI) - 1 else "MAX"
            lc_diem = LINH_CAN_DIEM_YEU_CAU.get(i + 1, 0)
            lc_str  = f"·LC:{lc_diem}đ" if lc_diem else ""
            # Dùng text thuần (không emoji custom) để tránh vượt 1024 ký tự
            return (
                f"{cg['emoji']} **{cg['ten']}** {dp_str}{lc_str} | TV:{_fmts(exp_hk)}\n"
                f"`HP:{_fmts(hp_hk)} AT:{_fmts(at_hk)} DEF:{_fmts(df_hk)} LL:{_fmts(ll_hk)}`"
            )

        lines_a = [_cg_line(i, cg) for i, cg in enumerate(CANH_GIOI[:5])]
        lines_b = [_cg_line(i, cg) for i, cg in enumerate(CANH_GIOI[5:], start=5)]
        embed1.add_field(
            name=f"📋 Cảnh Giới 1–5  *(ĐP = tỉ lệ đột phá đại cảnh, LC = điểm linh căn yêu cầu)*",
            value="\n".join(lines_a), inline=False)
        embed1.add_field(
            name="📋 Cảnh Giới 6–10",
            value="\n".join(lines_b), inline=False)

        # ── Quy tắc đột phá ───────────────────────────────────────────────────
        embed1.add_field(
            name="⚡ Quy Tắc Đột Phá",
            value=(
                "**Tiểu cảnh** *(Sơ → Trung → Hậu Kì)*\n"
                "┣ Dùng **Đan Tu Luyện** (rớt từ bí cảnh) để đột phá\n"
                "┣ Luôn **thành công**, không thất bại, không cooldown\n"
                f"┗ Chỉ tăng: {E_SINH_LUC} Sinh Lực + {E_LINH_LUC} Linh Lực\n\n"
                "**Đại cảnh** *(Hậu Kì → Cảnh Giới mới)*\n"
                "┣ Dùng **Đan Đột Phá** hoặc nút **⚡ Đột Phá** trong Tu Luyện\n"
                "┣ Có tỉ lệ thành công/thất bại theo bảng trên\n"
                "┣ Thất bại: mất **tu vi tràn + 15%** tu vi còn lại, CD **2 tiếng**\n"
                "┗ Thành công: tăng **toàn bộ** chỉ số + áp dụng buff linh căn lớp 2"
            ),
            inline=False)

        embed1.add_field(
            name=f"{E_TU_VI} Bonus Tràn Tu Vi *(đại cảnh)*",
            value=(
                "Mỗi **10%** tu vi vượt ngưỡng → **+2%** tỉ lệ thành công\n"
                "Tối đa **+45%** (tương đương 23 lần tràn 10%)"
            ),
            inline=False)

        embed1.add_field(
            name="🎁 Phúc Lợi Cảnh Giới Cao",
            value=(
                f"• {E_SINH_LUC}{E_CONG_KICH}{E_PHONG_NGU}{E_LINH_LUC} tăng cấp số nhân — gap rất lớn\n"
                "• Mở khóa Công Pháp cấp cao hơn\n"
                "• Bí cảnh cấp cao → phần thưởng lớn hơn\n"
                "• Sát thương Boss Thế Giới nhân theo cảnh giới\n"
                f"• Hệ số {E_LINH_THACH} Linh Thạch điểm danh tăng theo CG"
            ),
            inline=False)

        # ── Tông Môn (tự động từ config) ─────────────────────────────────────
        tm_lines = []
        for tm in TONG_MON:
            tm_lines.append(
                f"{tm['emoji']} **{tm['ten']}** — {BUFF_LABELS[tm['buff']]} ×{tm['buff_val']}\n"
                f"*{tm.get('mo_ta', '')}*"
            )
        embed1.add_field(
            name="🌸 Tông Môn (3 tông — rời tông tốn 10.000 LT)",
            value="\n".join(tm_lines),
            inline=False)

        embed1.set_footer(text="Trang 1/3 — Xem thêm: Linh Căn (2/3) · Thể Chất (3/3)")

        # ══════════════════════════════════════════════════════════
        #  EMBED 2 — Linh Căn
        # ══════════════════════════════════════════════════════════
        embed2 = discord.Embed(
            title="🌿 LINH CĂN NGUYÊN TỐ  (2/3)",
            description=(
                "Linh căn quyết định **passive lớp 1** (luôn active) "
                "và **buff lớp 2** (cộng dồn mỗi lần đột phá đại cảnh).\n\n"
                "⚗️ **Yêu cầu điểm linh căn để đột phá đại cảnh:**"
            ),
            color=0x208040)

        # Bảng điểm yêu cầu tự động từ config
        lc_req_lines = []
        for cg_id, diem in sorted(LINH_CAN_DIEM_YEU_CAU.items()):
            cg_ten = CANH_GIOI[cg_id]["ten"] if cg_id < len(CANH_GIOI) else f"CG{cg_id}"
            cg_emo = CANH_GIOI[cg_id]["emoji"] if cg_id < len(CANH_GIOI) else ""
            lc_req_lines.append(f"{cg_emo} Lên **{cg_ten}** → **{diem}đ** / căn")
        embed2.add_field(
            name="📊 Điểm Linh Căn Yêu Cầu",
            value="\n".join(lc_req_lines),
            inline=False)
        embed2.add_field(
            name="ℹ️ Lưu ý",
            value=(
                "• Nhiều căn → cần nhiều điểm hơn, nhưng **buff lớp 2 cộng dồn nhiều hơn**\n"
                "• Dùng **Linh Quả** để tăng điểm từng linh căn\n"
                "• Căn **Hiếm** chỉ kiếm qua mảnh drop trong game"
            ),
            inline=False)

        LOAI_LABEL = {"co_ban": "", "hiem": " 〔Hiếm〕", "sieu_hiem": " 〔Siêu Hiếm〕"}
        # Căn cơ bản
        lc_co_ban = [lc for lc in LINH_CAN if lc["loai"] == "co_ban"]
        lc_hiem   = [lc for lc in LINH_CAN if lc["loai"] != "co_ban"]

        cb_lines = []
        for lc in lc_co_ban:
            p  = lc.get("passive", {})
            db = lc.get("dot_pha_buff", {})
            cb_lines.append(
                f"{lc['emoji']} **{lc['ten']}**\n"
                f"┣ Passive: {_fmt_lc_passive(p)}\n"
                f"┗ Buff ĐP: {_fmt_lc_dotpha(db)}"
            )
        embed2.add_field(
            name=f"🌱 Linh Căn Cơ Bản ({len(lc_co_ban)} loại — random khi tạo hồ sơ)",
            value="\n".join(cb_lines),
            inline=False)

        hiem_lines = []
        for lc in lc_hiem:
            p  = lc.get("passive", {})
            db = lc.get("dot_pha_buff", {})
            tag = LOAI_LABEL.get(lc["loai"], "")
            hiem_lines.append(
                f"{lc['emoji']} **{lc['ten']}**{tag}\n"
                f"┣ Passive: {_fmt_lc_passive(p)}\n"
                f"┗ Buff ĐP: {_fmt_lc_dotpha(db)}"
            )
        embed2.add_field(
            name=f"💎 Linh Căn Hiếm ({len(lc_hiem)} loại — kiếm qua mảnh drop)",
            value="\n".join(hiem_lines),
            inline=False)

        embed2.set_footer(text="Trang 2/3 — Tiếp theo: Thể Chất Tu Luyện")

        # ══════════════════════════════════════════════════════════
        #  EMBED 3 — Thể Chất
        # ══════════════════════════════════════════════════════════
        embed3 = discord.Embed(
            title="🧬 THỂ CHẤT TU LUYỆN  (3/3)",
            description=(
                "Thể chất được random **1 lần khi tạo hồ sơ**, không thể đổi.\n"
                "Tỉ lệ trong ngoặc `[x%]` là xác suất random được thể chất đó."
            ),
            color=0xC77DFF)

        # Phân loại thể chất theo rate
        tc_than_cap  = [tc for tc in THE_CHAT if tc["rate"] < 1.0]
        tc_cao_cap   = [tc for tc in THE_CHAT if 1.0 <= tc["rate"] < 5.0]
        tc_thuong    = [tc for tc in THE_CHAT if tc["rate"] >= 5.0]

        def _tc_line(tc):
            mo_ta = tc.get("mo_ta", "")
            mo_ta_str = f" — *{mo_ta}*" if mo_ta else ""
            return (
                f"{tc['emoji']} **{tc['ten']}** `[{tc['rate']}%]`{mo_ta_str}\n"
                f"┗ {_fmt_tc_buff(tc['buff'])}"
            )

        if tc_than_cap:
            embed3.add_field(
                name=f"✨ Thần Cấp ({len(tc_than_cap)} loại)",
                value="\n".join(_tc_line(tc) for tc in tc_than_cap),
                inline=False)
        if tc_cao_cap:
            embed3.add_field(
                name=f"🔥 Cao Cấp ({len(tc_cao_cap)} loại)",
                value="\n".join(_tc_line(tc) for tc in tc_cao_cap),
                inline=False)
        if tc_thuong:
            # Chia đôi nếu quá dài
            mid = (len(tc_thuong) + 1) // 2
            embed3.add_field(
                name=f"⚪ Thường ({len(tc_thuong)} loại)",
                value="\n".join(_tc_line(tc) for tc in tc_thuong[:mid]),
                inline=False)
            if tc_thuong[mid:]:
                embed3.add_field(
                    name="\u200b",
                    value="\n".join(_tc_line(tc) for tc in tc_thuong[mid:]),
                    inline=False)

        embed3.set_footer(text="Đạo lộ vô tận — cảnh giới càng cao, thách thức càng lớn!")

        # ── View chọn trang ───────────────────────────────────────────────────
        embeds_map = {
            "cg": ("🌐 Cảnh Giới",  embed1),
            "lc": ("🌿 Linh Căn",   embed2),
            "tc": ("🧬 Thể Chất",   embed3),
        }

        class CGTabView(discord.ui.View):
            def __init__(self, current: str = "cg"):
                super().__init__(timeout=120)
                self.current = current
                self._rebuild()

            def _rebuild(self):
                self.clear_items()
                styles = {
                    "cg": discord.ButtonStyle.primary   if self.current == "cg" else discord.ButtonStyle.secondary,
                    "lc": discord.ButtonStyle.primary   if self.current == "lc" else discord.ButtonStyle.secondary,
                    "tc": discord.ButtonStyle.primary   if self.current == "tc" else discord.ButtonStyle.secondary,
                }
                for key, (label, _) in embeds_map.items():
                    btn = discord.ui.Button(label=label, style=styles[key], row=0)
                    btn.callback = self._make_cb(key)
                    self.add_item(btn)

            def _make_cb(self, key: str):
                async def _cb(inter2: discord.Interaction):
                    self.current = key
                    self._rebuild()
                    await inter2.response.edit_message(
                        embed=embeds_map[key][1], view=self)
                return _cb

            async def on_timeout(self):
                pass

        view = CGTabView(current="cg")
        await safe_followup(inter, embed=embed1, view=view, ephemeral=True)

    async def _cb_diem_danh(self, inter: discord.Interaction):
        if not await self._guard(inter): return
        await inter.response.defer(ephemeral=True)
        ts  = await get_tu_si(inter.user.id)
        now = int(time.time())
        cd  = diem_danh_cd_con_lai(ts.get("cd_diem_danh", 0), now)
        if cd > 0:
            embed = e_warn("📅 Đã Điểm Danh", f"Quay lại sau: **{fmt_cd(cd)}**\nChuỗi hiện tại: **{ts['chuoi_diem_danh']}** ngày")
            return await safe_followup(inter, embed=embed, ephemeral=True)

        # Tính chuỗi theo ngày VN: qua 00:00 là có thể điểm danh tiếp
        day_delta = diem_danh_day_delta(ts.get("cd_diem_danh", 0), now)
        if day_delta > 1:
            chuoi = 1
        else:
            chuoi = (ts["chuoi_diem_danh"] % 7) + 1

        # st["lt_m"] = tông môn LT × cg_he_so × the_chat lt_m (từ _calc_stats)
        # st["exp_m"] = tông môn EXP × cg_he_so × linh căn exp% × the_chat exp_m
        # st["drop_m"] = linh căn drop% × the_chat drop% × sủng thú drop% (KHÔNG ảnh hưởng lt/exp)
        st       = _calc_stats(ts)
        cg_he_so = DIEM_DANH_HE_SO[min(ts["canh_gioi"], len(DIEM_DANH_HE_SO) - 1)]
        tm_he_so = round(st["lt_m"] / cg_he_so, 2)
        lt_m     = st["lt_m"]
        exp_m    = st["exp_m"]

        pt      = DIEM_DANH_PHAN_THUONG[chuoi - 1]
        lt_nhan = int(pt["lt"]  * lt_m)
        tv_nhan = int(pt["exp"] * exp_m)

        await add_linh_thach(inter.user.id, lt_nhan)
        await update_tu_si(inter.user.id,
            exp=ts["exp"] + tv_nhan,
            cd_diem_danh=now, chuoi_diem_danh=chuoi)

        color = 0xFFD700 if chuoi == 7 else 0x57F287

        he_so_str = f"×{cg_he_so} (cảnh giới)"
        if tm_he_so != 1.0:
            he_so_str += f" × ×{tm_he_so} (tông môn)"
        # Bonus EXP từ linh căn Mộc/Quang
        lc_exp_bonus = st["lc_p"].get("exp_pct", 0.0)
        if lc_exp_bonus:
            he_so_str += f" + {lc_exp_bonus:.0f}% (linh căn)"

        embed = discord.Embed(
            title="📅 ĐIỂM DANH THÀNH CÔNG!" + (" 🎉" if chuoi == 7 else ""),
            description=(
                f"**+{fmt(lt_nhan)}** {E_LINH_THACH}  •  **+{fmt(tv_nhan)}** {E_TU_VI}"
            ),
            color=color)
        embed.add_field(name="🗓️ Chuỗi", value=f"**{chuoi}/7** ngày", inline=True)
        embed.add_field(name="📊 Hệ số", value=he_so_str, inline=True)
        embed.add_field(name="📦 Base", value=f"{fmt(pt['lt'])} {E_LINH_THACH}  •  {fmt(pt['exp'])} {E_TU_VI}", inline=True)
        if chuoi == 7:
            embed.set_footer(text="🎊 Chuỗi 7 ngày hoàn thành! Bonus x3 thưởng!")
        else:
            embed.set_footer(text=f"Còn {7 - chuoi} ngày nữa để nhận thưởng chuỗi 7!")
        await safe_followup(inter, embed=embed, ephemeral=True)
        await self._safe_refresh_main(inter)

    # ══════════════════════════════════════════════════════════
    #  SUB-CALLBACKS — HÀNH ĐỘNG TAB
    # ══════════════════════════════════════════════════════════
    async def _cb_tu_luyen(self, inter: discord.Interaction):
        if not await self._guard(inter): return
        actor_id = inter.user.id
        ts       = await get_tu_si(actor_id)
        embed    = _embed_tu_luyen(ts, inter.user)
        view     = TuLuyenView(self, inter.user, ts, actor_id=actor_id)
        await inter.response.send_message(embed=embed, view=view, ephemeral=True)

    async def _cb_dot_pha(self, inter: discord.Interaction):
        if not await self._guard(inter): return
        actor_id = inter.user.id
        ts  = await get_tu_si(actor_id)
        now = int(time.time())
        # Xác định tiểu/đại cảnh trước để defer đúng kiểu
        max_cap_pre = CANH_GIOI[ts["canh_gioi"]]["cap"]
        la_dai_pre  = ts["cap_nho"] >= max_cap_pre
        await inter.response.defer(ephemeral=not la_dai_pre)
        # Chỉ check CD khi đột phá thất bại (không CD khi thành công)
        cd  = ts["cd_dot_pha"] + CD_DOT_PHA - now
        if cd > 0:
            return await safe_followup(inter, embed=e_warn("⏳ Cooldown Đột Phá", f"Căn cơ chưa ổn định sau lần thất bại trước.\n**Chờ thêm:** {fmt_cd(cd)}"), ephemeral=True)

        ec = exp_can_thiet(ts["canh_gioi"], ts["cap_nho"])
        if ts["exp"] < ec:
            return await safe_followup(inter, embed=e_warn(f"{E_TU_VI} Tu Vi Chưa Đủ", f"`{bar(ts['exp'], ec)}`  {fmt(ts['exp'])}/{fmt(ec)}"), ephemeral=True)

        # ── Chặn đột phá thường ở Đăng Tiên Hậu Kỳ → chỉ có thể dùng Vấn Đỉnh
        if ts["canh_gioi"] >= len(CANH_GIOI) - 2 and ts["cap_nho"] >= CANH_GIOI[ts["canh_gioi"]]["cap"]:
            tong_tv_hien = ts.get("exp", 0)
            if tong_tv_hien >= VAN_DINH_TUVI_YEU_CAU:
                return await safe_followup(inter,
                    embed=e_warn("✨ Vấn Đỉnh Tiên Tôn",
                        "Đạo hữu đã đạt **Đăng Tiên Hậu Kỳ** và tích đủ tu vi!\\n"
                        "Hãy dùng nút **✨ Vấn Đỉnh** trong hồ sơ để thử vượt thiên đạo!"),
                    ephemeral=True)
            else:
                con_thieu = VAN_DINH_TUVI_YEU_CAU - tong_tv_hien
                return await safe_followup(inter,
                    embed=e_warn("🌌 Đỉnh Cao Tu Tiên",
                        f"Đạo hữu đã đạt cảnh giới **Đăng Tiên Hậu Kỳ** — đỉnh của con đường thường!\\n"
                        f"Còn thiếu **{fmt(con_thieu)}** tu vi để mở **✨ Vấn Đỉnh Tiên Tôn**."),
                    ephemeral=True)

        # lc_p đã được tính trong _calc_stats
        max_cap = CANH_GIOI[ts["canh_gioi"]]["cap"]

        # ── Phân loại: tiểu cảnh (Sơ→Trung→Hậu Kì) vs đại cảnh (lên CG mới)
        la_dai_canh = (ts["cap_nho"] >= max_cap)

        # ── Check điểm linh căn TRƯỚC khi cho đột phá đại cảnh ──────────
        if la_dai_canh:
            _next_cg    = ts["canh_gioi"] + 1
            _diem_yc    = LINH_CAN_DIEM_YEU_CAU.get(_next_cg, 0)
            _lc_so_huu  = ts.get("linh_can_so_huu", [])
            _lc_diem    = ts.get("linh_can_diem", {})
            # Nếu có linh căn và điểm chưa đủ → block đột phá
            if _lc_so_huu and _diem_yc > 0:
                _thieu = []
                for _id in _lc_so_huu:
                    _lc_c = LINH_CAN_BY_ID.get(_id)
                    if not _lc_c: continue
                    _d = _lc_diem.get(_id, 0)
                    if _d < _diem_yc:
                        _thieu.append(
                            f"{_lc_c['emoji']} **{_lc_c['ten']}**: {_d}/{_diem_yc}đ "
                            f"({min(99,int(_d/_diem_yc*100))}%)")
                if _thieu:
                    desc = (
                        "❌ **Đạo hữu chưa thông tuệ cảnh giới này, không thể đột phá!**\n\n"
                        "Linh căn chưa đủ điểm:\n" + "\n".join(_thieu) +
                        f"\n\n*Cần **{_diem_yc}đ** mỗi linh căn — dùng linh quả để tích điểm.*"
                    )
                    return await safe_followup(inter, 
                        embed=e_warn("🔒 Linh Căn Chưa Đủ Điểm", desc), ephemeral=True)

        if la_dai_canh:
            # Đại cảnh: có tỉ lệ thành/thất bại
            fail_rate_base = min(0.10 + ts["canh_gioi"] * 0.10, 0.90)
            ty_le_co_ban   = 1.0 - fail_rate_base
            tran_bonus = 0.0
            if ec > 0 and ts["exp"] > ec:
                so_lan_tran = int((ts["exp"] - ec) / (ec * 0.10))
                tran_bonus  = min(so_lan_tran * 0.02, 0.45)
            
            ty_le = min(1.0, ty_le_co_ban + tran_bonus)
            
            ok = random.random() < ty_le
        else:
            # Tiểu cảnh: luôn thành công, không thất bại, không CD
            ok = True

        # Tìm đan đột phá cần dùng (cho cả thành công lẫn thất bại)
        dan_dot_pha = None
        for d in DAN_DUOC:
            if not d.get("dot_pha"): continue
            if d.get("cg_yeu_cau") != ts["canh_gioi"]: continue
            if d.get("cap_nho_yeu_cau") is not None: continue
            dan_dot_pha = d; break

        # Đại cảnh bắt buộc phải có đan đột phá tương ứng
        if la_dai_canh:
            if not dan_dot_pha:
                return await safe_followup(inter,
                    embed=e_warn("🔒 Thiếu Đan Đột Phá",
                        "Cảnh giới này chưa có đan đột phá hợp lệ. Vui lòng báo quản trị để cập nhật cấu hình."),
                    ephemeral=True)
            so_dan_dp = ts.get("dan_duoc", {}).get(str(dan_dot_pha["id"]), 0)
            if so_dan_dp < 1:
                return await safe_followup(inter,
                    embed=e_warn("🔒 Thiếu Đan Đột Phá",
                        f"Cần **1× {dan_dot_pha['emoji']} {dan_dot_pha['ten']}** để đột phá đại cảnh.\n"
                        f"Trong kho hiện có: **{so_dan_dp}**"),
                    ephemeral=True)

        if ok:
            new_cap = ts["cap_nho"] + 1
            new_cg  = ts["canh_gioi"]
            if new_cap > max_cap:
                # Kiểm tra đã đạt cảnh giới tối đa thường (Đăng Tiên Hậu Kỳ)
                # Vấn Đỉnh Tiên Tôn (id=10) là cảnh giới đặc biệt, không đột phá bình thường
                if ts["canh_gioi"] >= len(CANH_GIOI) - 2:  # id=9 là Đăng Tiên, id=10 là Vấn Đỉnh
                    return await safe_followup(inter,
                        embed=e_warn("🌌 Đỉnh Cao Tu Tiên",
                            "Đạo hữu đã đạt cảnh giới **Đăng Tiên Hậu Kỳ** — đỉnh của con đường thường!\n"
                            "Hãy tích đủ **999,999,999** tu vi rồi thử **✨ Vấn Đỉnh Tiên Tôn**!"),
                        ephemeral=True)
                new_cap = 1
                new_cg  = ts["canh_gioi"] + 1
            new_hp  = hp_max_cong_thuc(new_cg, new_cap)
            new_at  = cong_cong_thuc(new_cg, new_cap)
            new_def = thu_cong_thuc(new_cg, new_cap)
            cg_new  = get_cg(new_cg)

            tong_tu_vi_moi = ts.get("tong_tu_vi", 0) + ts["exp"]
            if new_cg > ts["canh_gioi"]:
                new_exp = 0; tong_moi = tong_tu_vi_moi
            else:
                new_exp = ts["exp"]; tong_moi = ts.get("tong_tu_vi", 0)

            if la_dai_canh:
                # Trừ đan đột phá khi thành công
                dd_new = ts["dan_duoc"].copy()
                if dan_dot_pha:
                    key_d = str(dan_dot_pha["id"])
                    if dd_new.get(key_d, 0) > 0:
                        dd_new[key_d] -= 1
                        if dd_new[key_d] <= 0:
                            del dd_new[key_d]

                # Đại cảnh — tăng toàn bộ chỉ số
                lv_db     = new_cg * 9 + new_cap
                ll_db     = int((200 + new_cg**2 * 2300 + new_cap * 230) * 0.8 * 0.7)
                ht_db     = int(new_at * 0.08 + lv_db * 3)
                ho_db     = int(new_def * 0.15 + lv_db * 2)
                bk_db     = min(5 + new_cg * 3 + new_cap, 75)
                kb_db     = min(3 + new_cg * 2 + new_cap // 2, 50)
                # Apply buff lớp 2 từ tất cả linh căn đang sở hữu (đã pass check điểm)
                # Hướng 1: tích lũy vào cột linh_can_lop2 (JSON) — được đọc bởi _calc_full_stats
                lc_so_huu_dp  = ts.get("linh_can_so_huu", [])
                lc_buff_lines = []
                # Đọc lop2 hiện tại rồi cộng dồn thêm lần đột phá này
                _lop2_cur = ts.get("linh_can_lop2", {}) or {}
                if isinstance(_lop2_cur, str):
                    import json as _jlop2
                    try: _lop2_cur = _jlop2.loads(_lop2_cur) if _lop2_cur else {}
                    except Exception: _lop2_cur = {}
                _lop2_new = dict(_lop2_cur)
                for _lc_id in lc_so_huu_dp:
                    _lc = LINH_CAN_BY_ID.get(_lc_id)
                    if not _lc: continue
                    _b = _lc.get("dot_pha_buff", {})
                    if not _b: continue
                    # at_pct/def_pct/hp_pct: áp trực tiếp vào base stat (lưu vào cong/thu/hp_max)
                    if _b.get("at_pct"):   new_at  = int(new_at  * (1 + _b["at_pct"]  / 100))
                    if _b.get("def_pct"):  new_def = int(new_def * (1 + _b["def_pct"] / 100))
                    if _b.get("hp_pct"):   new_hp  = int(new_hp  * (1 + _b["hp_pct"]  / 100))
                    # hoi_tam/ho_tam/bao_kich/khang_bao/drop_rate/exp_pct: lưu vào linh_can_lop2
                    for _fk in ("hoi_tam", "ho_tam", "bao_kich", "khang_bao", "drop_rate", "exp_pct"):
                        if _b.get(_fk): _lop2_new[_fk] = round(_lop2_new.get(_fk, 0) + _b[_fk], 4)
                    lc_buff_lines.append(f"✨ {_lc['emoji']} {_lc['ten']}: buff lớp 2 kích hoạt!")
                import time as _t
                await update_tu_si(actor_id,
                    canh_gioi=new_cg, cap_nho=new_cap, exp=new_exp,
                    hp=new_hp, hp_max=new_hp, cong=new_at, thu=new_def,
                    linh_luc=ll_db, hoi_tam=ht_db, ho_tam=ho_db,
                    bao_kich=bk_db, khang_bao=kb_db,
                    linh_can_lop2=_lop2_new,
                    dan_duoc=dd_new,
                    tong_tu_vi=tong_moi)
            else:
                # Tiểu cảnh — chỉ tăng HP và Linh Lực, AT/DF/các chỉ số khác giữ nguyên
                lv_db2 = new_cg * 9 + new_cap
                ll_db2 = int((200 + new_cg**2 * 2300 + new_cap * 230) * 0.8 * 0.7)
                await update_tu_si(actor_id,
                    cap_nho=new_cap, exp=new_exp,
                    hp=new_hp, hp_max=new_hp,
                    linh_luc=ll_db2,
                    tong_tu_vi=tong_moi)

            if la_dai_canh:
                # Đại cảnh thành công — public, full stats, đạo hiệu
                ts_new    = await get_tu_si(actor_id)
                dao_hieu  = ts_new.get("dao_hieu", inter.user.display_name)
                linh_luc  = int((200 + new_cg**2 * 2300 + new_cap * 230) * 0.8 * 0.7)
                hoi_tam   = int(new_at * 0.08 + lv_db * 3)
                ho_tam    = int(new_def * 0.15 + lv_db * 2)
                bao_kich  = min(5 + new_cg * 3 + new_cap, 75)
                khang_bao = min(3 + new_cg * 2 + new_cap // 2, 50)
                embed = e_ok("🌟 ĐỘT PHÁ THÀNH CÔNG!", f"**{dao_hieu}** đã phá vỡ rào cản, tiến nhập vào cảnh giới **{cg_new['ten']}**!")
                embed.set_author(name=dao_hieu, icon_url=inter.user.display_avatar.url)
                embed.add_field(
                    name="Cảnh giới mới",
                    value=f"{cg_new['emoji']} **{get_cg_ten(new_cg, new_cap)}**",
                    inline=False)
                _e = get_stat_emoji
                embed.add_field(name=f"{_e('sinh_luc')} Sinh Lực",  value=fmt(new_hp),       inline=True)
                embed.add_field(name=f"{_e('cong_kich')} Tấn Công", value=fmt(new_at),       inline=True)
                embed.add_field(name=f"{_e('phong_ngu')} Phòng Ngự",value=fmt(new_def),      inline=True)
                embed.add_field(name=f"{_e('linh_luc')} Linh Lực",  value=fmt(linh_luc),     inline=True)
                embed.add_field(name=f"{_e('hoi_tam')} Hội Tâm",   value=str(hoi_tam),      inline=True)
                embed.add_field(name=f"{_e('ho_tam')} Hộ Tâm",     value=str(ho_tam),       inline=True)
                embed.add_field(name=f"{_e('bao_kich')} Bạo Kích",  value=f"{bao_kich}%",   inline=True)
                embed.add_field(name=f"{_e('khang_bao')} Kháng Bạo",value=f"{khang_bao}%",  inline=True)
                if lc_buff_lines:
                    embed.add_field(name="🌟 Linh Căn Lớp 2",
                        value="\n".join(lc_buff_lines), inline=False)
                embed.set_image(url="attachment://thanhcong.gif")
                embed.set_footer(text="Căn cơ đã ổn định, tiếp tục tu luyện!")
                gif_path = "images/thanhcong.gif"
                if os.path.exists(gif_path):
                    file = discord.File(gif_path, filename="thanhcong.gif")
                    await safe_followup(inter, embed=embed, file=file)
                else:
                    await safe_followup(inter, embed=embed)
            else:
                # Tiểu cảnh thành công — thông báo nhỏ gọn, ephemeral
                ki_names = {1: "Sơ Kì", 2: "Trung Kì", 3: "Hậu Kì"}
                ts_new2   = await get_tu_si(actor_id)
                dao_hieu2 = ts_new2.get("dao_hieu", inter.user.display_name)
                linh_luc2 = int((200 + new_cg**2 * 2300 + new_cap * 230) * 0.8 * 0.7)
                embed = e_ok("✨ THĂNG TIẾN THÀNH CÔNG!", f"**{dao_hieu2}** đã bước vào **{cg_new['emoji']} {get_cg_ten(new_cg, new_cap)}**!")
                embed.add_field(name=f"{get_stat_emoji('sinh_luc')} Sinh Lực", value=fmt(new_hp),    inline=True)
                embed.add_field(name=f"{get_stat_emoji('linh_luc')} Linh Lực",  value=fmt(linh_luc2), inline=True)
                await safe_followup(inter, embed=embed, ephemeral=True)
        else:
            # Đại cảnh thất bại — trừ đan + CD + EXP
            tran         = max(0, ts["exp"] - ec)
            exp_sau_tran = ts["exp"] - tran
            exp_mat      = int(exp_sau_tran * 0.15)
            exp_con      = exp_sau_tran - exp_mat
            tong_mat     = tran + exp_mat
            dd_fail = ts["dan_duoc"].copy()
            if dan_dot_pha:
                key_f = str(dan_dot_pha["id"])
                if dd_fail.get(key_f, 0) > 0:
                    dd_fail[key_f] -= 1
                    if dd_fail[key_f] <= 0:
                        del dd_fail[key_f]
            await update_tu_si(actor_id, exp=exp_con, cd_dot_pha=now, dan_duoc=dd_fail)

            thua_str = f"-{fmt(tong_mat)} {E_TU_VI}"
            if tran > 0:
                thua_str += f"\n*(Tràn: -{fmt(tran)} + 15% còn lại: -{fmt(exp_mat)})*"
            embed = e_loi("💀 ĐỘT PHÁ THẤT BẠI", "Tâm ma trỗi dậy, linh lực nghịch chuyển. Đạo hữu đã đột phá thất bại!")
            _dao_hieu_fail = ts.get("dao_hieu", inter.user.display_name)
            embed.set_author(name=_dao_hieu_fail, icon_url=inter.user.display_avatar.url)
            embed.add_field(name=f"⚠️ Tổn hao {E_TU_VI}", value=thua_str, inline=False)
            embed.add_field(name="⏳ Hồi phục", value="Cần **2 tiếng** để ổn định căn cơ.", inline=False)
            embed.set_image(url="attachment://thatbai.gif")
            embed.set_footer(text="Kiên trì luyện tập, thử lại sau!")
            gif_path = "images/thatbai.gif"
            if os.path.exists(gif_path):
                file = discord.File(gif_path, filename="thatbai.gif")
                await safe_followup(inter, embed=embed, file=file)
            else:
                await safe_followup(inter, embed=embed)

        await self._safe_refresh_main(inter)

    async def _cb_khai_hoang(self, inter: discord.Interaction):
        if not await self._guard(inter): return
        await inter.response.defer(ephemeral=True)
        ts  = await get_tu_si(inter.user.id)
        now = int(time.time())
        cd  = ts["cd_khai_hoang"] + CD_KHAI_HOANG - now
        if cd > 0:
            return await safe_followup(inter, embed=discord.Embed(
                title="⏳", description=fmt_cd(cd), color=0xFEE75C), ephemeral=True)

        st     = _calc_stats(ts)
        events = [
            ("💎 Phát Hiện Bảo Vật!", 2.0), ("🌿 Gặp Linh Thú!",   1.5),
            ("⛏️ Bình Thường",        1.0), ("⛏️ Bình Thường",      1.0),
            ("🌧️ Trời Xấu…",          0.6),
        ]
        ev_txt, ev_mul = random.choice(events)
        lt_base  = random.randint(50*(ts["canh_gioi"]+1), 200*(ts["canh_gioi"]+1))
        lt_nhan  = int(lt_base * st["lt_m"] * ev_mul)
        nl_idx   = random.randint(0, min(ts["canh_gioi"], len(NGUYEN_LIEU) - 1))
        nl_so    = random.randint(1, 3)
        nl = ts["nguyen_lieu"].copy()
        nl[str(nl_idx)] = nl.get(str(nl_idx), 0) + nl_so
        await add_linh_thach(inter.user.id, lt_nhan)
        await update_tu_si(inter.user.id,
            nguyen_lieu=nl, cd_khai_hoang=now)

        embed = discord.Embed(title=f"⛏️ Khai Hoang — {ev_txt}", color=0xFFD700)
        embed.add_field(name=f"{E_LINH_THACH} LT", value=f"+{fmt(lt_nhan)}", inline=True)
        embed.add_field(name="🧪 NL",
            value=f"+{nl_so}× {NGUYEN_LIEU[nl_idx]['emoji']} {NGUYEN_LIEU[nl_idx]['ten']}", inline=True)
        await safe_followup(inter, embed=embed, ephemeral=True)
        await self._safe_refresh_main(inter)

    async def _cb_bi_canh_menu(self, inter: discord.Interaction):
        if not await self._guard(inter): return
        # Defer ngay để tránh 10062 — các DB call bên dưới có thể mất > 3 giây
        try:
            await inter.response.defer(ephemeral=True)
        except discord.NotFound:
            return  # Interaction expired (10062)
        try:
            # Dùng data của người bấm (viewer hoặc owner)
            actor_id  = inter.user.id
            guild_id  = inter.guild_id or 0
            sess_key  = (guild_id, actor_id)
            ts        = await get_tu_si(actor_id)
            tl_hien   = get_the_luc(ts)
            tran_hien = get_tran_the_luc(ts)
            now       = int(time.time())

            if sess_key in _bc_sessions:
                s_old = _bc_sessions[sess_key]
                # Timeout 5 phút — tự cleanup nếu session treo
                session_age = int(time.time()) - s_old.created_at
                if not s_old.ket_thuc and session_age < 300:
                    return await safe_followup(inter,
                        embed=e_loi("❌ Đang trong bí cảnh!", "Đạo hữu đang trong bí cảnh. Hoàn thành hoặc rút lui trước."),
                        ephemeral=True)
                else:
                    # Session hết hạn hoặc đã kết thúc — cleanup
                    _bc_sessions.pop(sess_key, None)

            embed = _embed_bi_canh_chon(ts, inter.user)
            view = BiCanhChonView(self, ts, actor_id=actor_id, guild_id=guild_id)
            try:
                await inter.edit_original_response(embed=embed, view=view)
            except Exception:
                await safe_followup(inter, embed=embed, view=view, ephemeral=True)
        except Exception as e:
            log.error(f"_cb_bi_canh_menu user={inter.user.id}: {e}", exc_info=True)
            try:
                if inter.response.is_done():
                    await safe_followup(inter, f"❌ Lỗi: {e}", ephemeral=True)
                else:
                    await inter.response.send_message(f"❌ Lỗi: {e}", ephemeral=True)
            except Exception:
                log.exception("Lỗi hoso")

    async def _cb_chi_tiet(self, inter: discord.Interaction):
        if not await self._guard(inter): return
        try:
            await inter.response.defer(ephemeral=True)
        except (discord.errors.NotFound, discord.errors.InteractionResponded):
            return
        try:
            ts = await get_tu_si(inter.user.id)
            embed = _build_embed_thuoc_tinh(ts, inter.user)
            await safe_followup(inter, embed=embed, ephemeral=True)
        except Exception as e:
            log.error(f"_cb_chi_tiet error user={inter.user.id}: {e}", exc_info=True)
            try:
                await safe_followup(inter, f"❌ Lỗi hiển thị thuộc tính: `{e}`", ephemeral=True)
            except Exception:
                log.exception("Lỗi hoso")


    # ══════════════════════════════════════════════════════════
    #  SUB-CALLBACKS — KHO ĐỒ TAB
    # ══════════════════════════════════════════════════════════
    async def _cb_donate(self, inter: discord.Interaction):
        if not await self._guard(inter): return
        contact = f"<@{SHOP_CONTACT_ID}>"
        embed = discord.Embed(
            title="💝 Thiên Đế Donate",
            description=(
                "**HƯỚNG DẪN DONATE:**\n"
                "1️⃣ Nhấn nút **💝 Donate** bên dưới\n"
                "2️⃣ Chuyển khoản đúng số tiền vào 1 trong 2 QR\n"
                "3️⃣ Gửi bill xác nhận cho " + contact + "\n"
                "4️⃣ Nhận code → dùng `/redeem <CODE>` để nhận thưởng!"
            ),
            color=0x57F287,
        )
        await inter.response.send_message(embed=embed, view=ShopView(), ephemeral=True)

    async def _cb_phuong_thi(self, inter: discord.Interaction):
        if not await self._guard(inter): return
        try:
            items = await get_phien_cho(da_ban=False)
            embed, f_pt = await _build_phuong_thi_embed(items, page=0)
            view = PhuongThiView(self, items=items, page=0, actor_id=inter.user.id)
            if f_pt:
                await inter.response.send_message(embed=embed, file=f_pt, view=view, ephemeral=True)
            else:
                await inter.response.send_message(embed=embed, view=view, ephemeral=True)
        except Exception as e:
            log.error(f"_cb_phuong_thi user={inter.user.id}: {e}", exc_info=True)
            try:
                await inter.response.send_message(f"❌ Lỗi: {e}", ephemeral=True)
            except Exception:
                log.exception("Lỗi hoso")

    async def _cb_sung_thu(self, inter: discord.Interaction):
        if not await self._guard(inter): return
        ts = await get_tu_si(inter.user.id)
        view = SungThuView(self, ts, inter.user, actor_id=inter.user.id)
        await inter.response.send_message(
            embed=_embed_sung_thu_list(ts, inter.user), view=view, ephemeral=True)

    async def _cb_toa_ky(self, inter: discord.Interaction):
        if not await self._guard(inter): return
        try:
            ts = await get_tu_si(inter.user.id)
            if not ts:
                return await inter.response.send_message("❌ Chưa có hồ sơ!", ephemeral=True)
            from cogs.views.toa_ky import ToaKyView, _embed_toa_ky_list
            embed = _embed_toa_ky_list(ts, inter.user)
            view = ToaKyView(self, ts, inter.user, actor_id=inter.user.id)
            await inter.response.send_message(embed=embed, view=view, ephemeral=True)
        except Exception as e:
            log.error(f"_cb_toa_ky user={inter.user.id}: {e}", exc_info=True)
            try:
                await inter.response.send_message(f"❌ Lỗi: {e}", ephemeral=True)
            except Exception:
                log.exception("Lỗi hoso")

    async def _cb_dotpha_tc(self, inter: discord.Interaction):
        if not await self._guard(inter): return
        try:
            ts = await get_tu_si(inter.user.id)
            if not ts:
                return await inter.response.send_message("❌ Chưa có hồ sơ!", ephemeral=True)
            view  = DotPhaTCView(self, ts, actor_id=inter.user.id)
            embed = _embed_dotpha_chon(ts)
            await inter.response.send_message(embed=embed, view=view, ephemeral=True)
        except Exception as e:
            log.error(f"_cb_dotpha_tc user={inter.user.id}: {e}", exc_info=True)
            try:
                await inter.response.send_message(f"❌ Lỗi: {e}", ephemeral=True)
            except Exception:
                log.exception("Lỗi hoso")

    async def _cb_van_dinh(self, inter: discord.Interaction):
        if not await self._guard(inter): return
        if inter.user.id != self.owner_id:
            return await inter.response.send_message("❌ Chỉ chủ nhân mới dùng được!", ephemeral=True)
        try:
            ts = await get_tu_si(inter.user.id)
            if not ts:
                return await inter.response.send_message("❌ Chưa có hồ sơ!", ephemeral=True)
            from cogs.views.van_dinh import VanDinhView, _embed_chuan_bi
            embed, du_tuvi = _embed_chuan_bi(ts)
            view = VanDinhView(self, ts, actor_id=inter.user.id)
            await inter.response.send_message(embed=embed, view=view, ephemeral=True)
        except Exception as e:
            log.error(f"_cb_van_dinh user={inter.user.id}: {e}", exc_info=True)
            try:
                await inter.response.send_message(f"❌ Lỗi: {e}", ephemeral=True)
            except Exception:
                log.exception("Lỗi hoso")

    async def _cb_boss_menu(self, inter: discord.Interaction):
        if not await self._guard(inter): return
        try:
            await inter.response.defer(ephemeral=True)
        except discord.NotFound:
            return  # Interaction expired (10062)
        try:
            ts   = await get_tu_si(inter.user.id)
            _, next_spawn = _boss_current_window()
            next_vn = datetime.fromtimestamp(next_spawn, tz=VN_TZ)

            boss_states = []
            any_active  = False
            for boss in BOSS_THE_GIOI:
                state  = await get_boss_state(boss["id"])
                active = _boss_is_active(state)
                if active: any_active = True
                boss_states.append((boss, state, active))

            GIF_PATH = "images/sanh boss the gioi.gif"

            if not any_active:
                embed = discord.Embed(
                    title="😈 SẢNH BOSS THẾ GIỚI",
                    description=(
                        "⚠️ **Yêu ma chưa xuất hiện!** Đạo hữu hãy tranh thủ thời gian này để "
                        "tu luyện và chuẩn bị trang bị.\n\n"
                        f"🕐 Boss sẽ xuất hiện vào lúc **00:00**, **06:00**, **12:00** và **18:00** hằng ngày.\n"
                        f"⏳ Boss tiếp theo dự kiến: **{next_vn.strftime('%H:%M')}**"
                    ),
                    color=0x2B2D31)
                embed.set_footer(text="Sẵn sàng trừ ma về đạo!")
                view = LobbyBossView(self, ts, boss_states)
                if os.path.exists(GIF_PATH):
                    gif_file = discord.File(GIF_PATH, filename=os.path.basename(GIF_PATH))
                    embed.set_image(url=f"attachment://{os.path.basename(GIF_PATH)}")
                    return await safe_followup(inter, embed=embed, file=gif_file, view=view, ephemeral=True)
                return await safe_followup(inter, embed=embed, view=view, ephemeral=True)

            # Có boss active — hiện thông tin boss đang sống
            active_boss, active_state = next(
                ((b, s) for b, s, a in boss_states if a), (BOSS_THE_GIOI[0], None))
            cg_boss  = active_state.get("canh_gioi", active_boss["canh_gioi_pool"][0]) if active_state else 0
            cg_obj   = get_cg(cg_boss)
            hp_max_b = BOSS_HP_BY_CG.get(cg_boss, active_boss["hp_max"])
            hp_hien  = active_state["hp_hien"] if active_state else hp_max_b
            pct      = max(0, hp_hien / hp_max_b * 100)
            raiders  = len(active_state["nguoi_tan_cong"]) if active_state else 0

            embed = discord.Embed(
                title=f"⚠️ CẢNH BÁO: {active_boss['ten'].upper()} XUẤT HIỆN!",
                color=0xDC143C)
            embed.add_field(
                name="📋  Thông tin Boss",
                value=(
                    f"• Tên: **{active_boss['ten']}**\n"
                    f"• Cảnh giới: **{cg_obj['emoji']} {cg_obj['ten']}**\n"
                    f"• Sinh lực: {emoji_hp_bar(hp_hien, hp_max_b)}\n"
                    f"• Chi tiết: **{fmt(hp_hien)} / {fmt(hp_max_b)} ({pct:.1f}%)**\n"
                    + (lambda m, b: f"• 🔥 Thưởng tăng **×{b}** (boss mất {m*10}%)\n" if m > 0 else "")(
                        min(10, int((hp_max_b - hp_hien) / hp_max_b * 10)),
                        round(1.0 + min(10, int((hp_max_b - hp_hien) / hp_max_b * 10)) * 0.10, 2)) +
                    f"• Đang có **{raiders}** tu sĩ tham chiến"
                ),
                inline=False)
            embed.set_footer(text="Nhấn nút bên dưới để tham chiến!")
            view = BossView(self, ts, boss_states)
            img_path = active_boss.get("image_file", "")
            if img_path and os.path.exists(img_path):
                fname = os.path.basename(img_path)
                img_f = discord.File(img_path, filename=fname)
                embed.set_image(url=f"attachment://{fname}")
                await safe_followup(inter, embed=embed, file=img_f, view=view, ephemeral=True)
            elif os.path.exists(GIF_PATH):
                gif_file = discord.File(GIF_PATH, filename=os.path.basename(GIF_PATH))
                embed.set_image(url=f"attachment://{os.path.basename(GIF_PATH)}")
                await safe_followup(inter, embed=embed, file=gif_file, view=view, ephemeral=True)
            else:
                await safe_followup(inter, embed=embed, view=view, ephemeral=True)
        except Exception as e:
            log.error(f"_cb_boss_menu user={inter.user.id}: {e}", exc_info=True)
            await safe_followup(inter, f"❌ Lỗi: {e}", ephemeral=True)

    async def _cb_tang_qua(self, inter: discord.Interaction):
        if not await self._guard(inter): return
        viewer_id = inter.user.id
        target_id = self.owner_id
        if viewer_id == target_id:
            return await inter.response.send_message("❌ Không thể tặng quà cho chính mình!", ephemeral=True)
        ts_viewer = await get_tu_si(viewer_id)
        ts_target = await get_tu_si(target_id)
        if not ts_viewer:
            return await inter.response.send_message("❌ Bạn chưa có hồ sơ!", ephemeral=True)
        qh    = await get_quan_he(viewer_id, target_id)
        view  = TangQuaView(self, ts_viewer, ts_target, inter.user, self.user, qh)
        embed = _embed_quan_he(ts_viewer, ts_target, inter.user, self.user, qh)
        msg = await inter.response.send_message(embed=embed, view=view, ephemeral=True)
        view._message = await inter.original_message() if hasattr(inter, "original_message") else None
        try:
            view._message = await inter.original_response()
        except Exception:
            log.exception("Lỗi hoso")

    async def _cb_quan_he(self, inter: discord.Interaction):
        if not await self._guard(inter): return
        viewer_id = inter.user.id
        target_id = self.owner_id
        ts_viewer = await get_tu_si(viewer_id)
        ts_target = await get_tu_si(target_id)
        if not ts_viewer:
            return await inter.response.send_message("❌ Bạn chưa có hồ sơ!", ephemeral=True)
        qh    = await get_quan_he(viewer_id, target_id)
        view  = TangQuaView(self, ts_viewer, ts_target, inter.user, self.user, qh)
        embed = _embed_quan_he(ts_viewer, ts_target, inter.user, self.user, qh)
        await inter.response.send_message(embed=embed, view=view, ephemeral=True)
        try:
            view._message = await inter.original_response()
        except Exception:
            log.exception("Lỗi hoso")

    async def _cb_quan_he_owner(self, inter: discord.Interaction):
        """Xem danh sách quan hệ của chính mình."""
        if not await self._guard(inter): return
        if inter.user.id != self.owner_id:
            return await inter.response.send_message("❌", ephemeral=True)
        await inter.response.defer(ephemeral=True)
        from utils.database import get_danh_sach_quan_he
        danh_sach = await get_danh_sach_quan_he(inter.user.id)

        embed = discord.Embed(
            title="❤️ DANH SÁCH QUAN HỆ",
            color=0xE91E8C,
        )
        # Quote + intro
        embed.description = (
            "🌸 *\"Nhân duyên do trời định, nhưng gặp gỡ là do lòng người.\"*\n\n"
            f"Tiên tử **Phong Linh Lan** mỉm cười chào bạn. "
        )

        if not danh_sach:
            embed.description += (
                "Có vẻ như đạo hữu vẫn chưa kết giao "
                "nhân duyên với ai trong chốn này."
            )
        else:
            embed.description += f"Đạo hữu đang có **{len(danh_sach)}** mối quan hệ."
            for qh in danh_sach[:10]:
                other_id = qh["user_b"] if qh["user_a"] == inter.user.id else qh["user_a"]
                ts_other = await get_tu_si(other_id)
                dao_hieu = ts_other["dao_hieu"] if ts_other else f"<@{other_id}>"
                cap   = get_quan_he_cap(qh["diem"])
                loai  = QUAN_HE_LOAI.get(qh.get("loai", ""), None)
                loai_str = f" · {loai['emoji']} {loai['ten']}" if loai else ""
                diem  = qh["diem"]
                # Tính tim: mỗi 100 điểm = nửa tim → mỗi 200 = 1 tim đỏ
                # Chỉ áp dụng quan hệ dương
                tim_str = ""
                if diem > 0:
                    tims_total = diem // 100  # số nửa tim
                    full  = tims_total // 2   # tim đỏ đầy
                    half  = tims_total % 2    # nửa tim
                    empty = max(0, 5 - full - half)  # tim đen (tổng 5 tim = 1000đ)
                    tim_str = (E_TIM_DO * full) + (E_TIM_NUA * half) + (E_TIM_DEN * empty)
                # Điểm: diem/1000 — tên cap
                diem_max = 1000
                embed.add_field(
                    name=f"{dao_hieu}",
                    value=f"{tim_str}\n**{diem}/{diem_max}** điểm — *{cap['ten']}*{loai_str}",
                    inline=False,
                )

        # Ảnh Phong Linh Lan
        PLl_IMG = "images/phonglinhlan.png"
        embed.set_image(url=f"attachment://{os.path.basename(PLl_IMG)}")
        embed.set_footer(text="Phong Linh Lan quản lý nhân duyên")

        if os.path.exists(PLl_IMG):
            f_img = discord.File(PLl_IMG, filename=os.path.basename(PLl_IMG))
            await safe_followup(inter, embed=embed, file=f_img, ephemeral=True)
        else:
            await safe_followup(inter, embed=embed, ephemeral=True)

    async def on_timeout(self):
        pass


# ══════════════════════════════════════════════════════════════
#  TÔNG MÔN VIEW
# ══════════════════════════════════════════════════════════════


def _phien_expire_str(thoi_gian: int, expire_secs: int = 172800) -> str:
    """Trả về chuỗi thông báo thời hạn còn lại của phiên chợ (2 ngày)."""
    import time as _t
    remaining = (thoi_gian + expire_secs) - int(_t.time())
    if remaining <= 0:
        return "\n⏰ *Hết hạn — đang chờ hoàn trả*"
    h = remaining // 3600
    m = (remaining % 3600) // 60
    if h >= 24:
        d = h // 24
        return f"\n⏰ Hết hạn sau: **{d} ngày {h%24}h**"
    return f"\n⏰ Hết hạn sau: **{h}h {m}p**"


async def _build_phuong_thi_embed(items: list, page: int = 0):
    """Build embed phường thị cho trang page (8 items/trang). Trả về (embed, file_or_None)."""
    from cogs.views.kho_do import _resolve_phien_name
    PT_PER_PAGE = 8
    total       = len(items)
    total_pages = max(1, (total + PT_PER_PAGE - 1) // PT_PER_PAGE)
    page        = max(0, min(page, total_pages - 1))
    page_items  = items[page * PT_PER_PAGE : (page + 1) * PT_PER_PAGE]

    embed = discord.Embed(
        title="🏛️ PHƯỜNG THỊ TRUNG TÂM",
        description="Nơi giao lưu, buôn bán vật phẩm giữa các đạo hữu.\n\nHãy chọn vật phẩm muốn mua qua menu phía dưới.",
        color=0xC47A2B)
    PT_IMG = "images/phuong_thi.png"
    if os.path.exists(PT_IMG):
        embed.set_image(url="attachment://phuong_thi.png")

    if page_items:
        for idx_pt, ph in enumerate(page_items):
            loai = ph["loai"]; iid = ph["item_id"]; ikey = ph.get("item_key", "")
            if loai == "dan_duoc" and iid < len(DAN_DUOC):
                item_name = f"{DAN_DUOC[iid]['emoji']} {DAN_DUOC[iid]['ten']} ×{ph['so_luong']}"
            elif loai == "nguyen_lieu" and iid < len(NGUYEN_LIEU):
                item_name = f"{NGUYEN_LIEU[iid]['emoji']} {NGUYEN_LIEU[iid]['ten']} ×{ph['so_luong']}"
            elif loai == "dtl" and ikey:
                parts = ikey[4:].split(":", 2) if ikey.startswith("dtl:") else []
                if len(parts) == 3:
                    cg_i, cap_i, ten_i = int(parts[0]), int(parts[1]), parts[2]
                    emoji_i = next(
                        (d["emoji"] for d in DAN_TU_LUYEN[cg_i]
                         if d["ten"] == ten_i and d["cap_nho_sau"] == cap_i),
                        "") if 0 <= cg_i < len(DAN_TU_LUYEN) else ""
                    item_name = f"{emoji_i} {ten_i} ×{ph['so_luong']}"
                else:
                    item_name = f"Đan Tu Luyện ×{ph['so_luong']}"
            elif loai in ("lq", "manh") and ikey:
                emo, name = _resolve_phien_name(loai, iid, ikey)
                item_name = f"{emo} {name} ×{ph['so_luong']}"
            else:
                item_name = f"Item {iid} ×{ph['so_luong']}"

            ts_seller   = await get_tu_si(ph["nguoi_ban"])
            seller_name = ts_seller["dao_hieu"] if ts_seller else "Ẩn danh"
            mo_ta_pt    = ""
            if loai == "dan_duoc" and iid < len(DAN_DUOC):
                mo_ta_pt = DAN_DUOC[iid].get("mo_ta", "")
            elif loai == "dtl" and ikey and len(ikey[4:].split(":", 2)) == 3:
                p3    = ikey[4:].split(":", 2)
                cg_n  = CANH_GIOI[int(p3[0])]["ten"] if 0 <= int(p3[0]) < len(CANH_GIOI) else "?"
                ki_names = {1: "Sơ Kì", 2: "Trung Kì", 3: "Hậu Kì"}
                mo_ta_pt = f"Đan cần để đột phá {ki_names.get(int(p3[1])-1,'?')} {cg_n} → {ki_names.get(int(p3[1]),'?')}."
            global_idx = page * PT_PER_PAGE + idx_pt + 1
            embed.add_field(
                name=f"{global_idx}. {item_name}",
                value=(
                    f"{E_LINH_THACH} Giá: **{fmt(ph['gia'])}** / cái\n"
                    f"👤 Người bán: **{seller_name}**\n"
                    + (f"{mo_ta_pt}\n" if mo_ta_pt else "")
                    + f"*(Mã: #{ph['id']})*"
                    + _phien_expire_str(ph["thoi_gian"])
                ),
                inline=False)
        embed.set_footer(text=f"Trang {page+1}/{total_pages}  •  Tổng {total} vật phẩm")
    else:
        embed.description = "*(Chưa có hàng nào)*"

    f_pt = discord.File(PT_IMG, filename="phuong_thi.png") if os.path.exists(PT_IMG) else None
    return embed, f_pt


class HoSoCog(commands.Cog, name="Hồ Sơ"):
    def __init__(self, bot):
        self.bot = bot
        self._spawn_lock = asyncio.Lock()
        # Đăng ký BossSpawnView persistent cho mỗi boss — để buttons hoạt động sau restart
        from cogs.views.boss import BossSpawnView
        for _b in BOSS_THE_GIOI:
            try:
                bot.add_view(BossSpawnView(_b["id"]))
            except Exception:
                log.exception("Lỗi hoso")
        self._boss_spawn_task.start()
        self._boss_expire_task.start()
        self._boss_refresh_task.start()
        self._session_cleanup_task.start()
        self._boss_data_cleanup_task.start()
        self._phien_cho_expire_task.start()

    def cog_unload(self):
        self._boss_spawn_task.cancel()
        self._boss_expire_task.cancel()
        self._boss_refresh_task.cancel()
        self._session_cleanup_task.cancel()
        self._boss_data_cleanup_task.cancel()
        self._phien_cho_expire_task.cancel()

    async def _get_announce_channel(self, guild_id: int = None):
        """Trả về channel boss spawn đã setup — None nếu chưa set."""
        if not guild_id:
            return None
        ch_id = await get_boss_channel(guild_id)
        if not ch_id:
            return None
        for guild in self.bot.guilds:
            if guild.id != guild_id:
                continue
            # Thử cache trước, fallback fetch nếu không có (thread, chưa cache)
            ch = guild.get_channel(ch_id) or guild.get_thread(ch_id)
            if ch:
                return ch
            try:
                ch = await guild.fetch_channel(ch_id)
                return ch
            except discord.NotFound:
                return None  # kênh đã bị xóa
            except Exception:
                log.exception("Lỗi hoso")
                return None
        return None

    @discord.ext.tasks.loop(minutes=1)
    async def _boss_expire_task(self):
        """Kiểm tra boss hết giờ và gửi thông báo public."""
        now_ts = int(datetime.now(timezone.utc).timestamp())
        for boss in BOSS_THE_GIOI:
            state = await get_boss_state(boss["id"])
            if not state or state.get("hp_hien", 0) <= 0:
                continue
            elapsed = now_ts - state.get("spawn_time", 0)
            # Gửi thông báo đúng trong vòng 60s sau khi hết BOSS_LIFETIME
            if BOSS_LIFETIME <= elapsed < BOSS_LIFETIME + 60:
                embed = discord.Embed(
                    title=f"🌫️ {boss['ten']} ĐÃ BIẾN MẤT!",
                    description=(
                        f"**{boss['ten']}** đã rút lui sau khi hết thời gian.\n"
                        f"Hãy chuẩn bị cho lần xuất hiện tiếp theo!"
                    ),
                    color=0x555555,
                )
                img_path = boss.get("image_file", "")
                # Broadcast tất cả guild
                for _guild in self.bot.guilds:
                    _channel = await self._get_announce_channel(_guild.id)
                    if not _channel:
                        continue
                    try:
                        if img_path and os.path.exists(img_path):
                            fname = os.path.basename(img_path)
                            f_img = discord.File(img_path, filename=fname)
                            embed.set_thumbnail(url=f"attachment://{fname}")
                            await _channel.send(embed=embed, file=f_img)
                        else:
                            await _channel.send(embed=embed)
                    except Exception:
                        log.exception("Lỗi hoso")
                log.info(f"[BossExpire] {boss['ten']} hết giờ, đã thông báo")
                await set_boss_end_time(boss["id"], now_ts)

    @_boss_expire_task.error
    async def __boss_expire_task_error(self, error: Exception):
        log.error(f"[Task] _boss_expire_task crashed: {error}", exc_info=True)
        await asyncio.sleep(60)
        if not self._boss_expire_task.is_running():
            self._boss_expire_task.start()
            log.info("[Task] _boss_expire_task restarted after crash")

    @_boss_expire_task.before_loop
    async def _before_boss_expire(self):
        await self.bot.wait_until_ready()

    @discord.ext.tasks.loop(minutes=30)
    async def _boss_refresh_task(self):
        """Refresh message boss mỗi 30 phút để Discord không expire buttons."""
        from cogs.views.boss import BossView, _build_initial_boss_message, BossSpawnView
        now_ts = int(datetime.now(timezone.utc).timestamp())
        for boss in BOSS_THE_GIOI:
            state = await get_boss_state(boss["id"])
            if not _boss_is_active(state):
                continue
            # Build embed mới để renew buttons (tránh expire token)
            cg_boss  = state.get("canh_gioi", boss["canh_gioi_pool"][0])
            hp_hien  = state["hp_hien"]
            hp_max_b = BOSS_HP_BY_CG.get(cg_boss, boss["hp_max"])
            pct      = max(0, hp_hien / hp_max_b * 100)
            secs_left = max(0, BOSS_LIFETIME - (now_ts - state.get("spawn_time", 0)))
            h, m = secs_left // 3600, (secs_left % 3600) // 60
            nguoi_tc    = state.get("nguoi_tan_cong", {})
            combat_logs = nguoi_tc.get("_log", []) if isinstance(nguoi_tc.get("_log"), list) else []
            tc_display  = {k: v for k, v in nguoi_tc.items() if k not in ("_log", "_killer")}
            cg_obj = get_cg(cg_boss)
            embed = discord.Embed(
                title=f"⚠️ CẢNH BÁO: {boss['ten'].upper()} XUẤT HIỆN!",
                color=0xDC143C)
            embed.add_field(
                name="📋  Thông tin Boss",
                value=(
                    f"• Tên: **{boss['ten']}**\n"
                    f"• Cảnh giới: **{cg_obj['emoji']} {cg_obj['ten']}**\n"
                    f"• Sinh lực: {emoji_hp_bar(hp_hien, hp_max_b)}\n"
                    f"• Chi tiết: **{fmt(hp_hien)} / {fmt(hp_max_b)} ({pct:.1f}%)**"
                    + ((lambda m, b: f"\n• 🔥 Thưởng tăng **×{b}** (boss mất {m*10}%)")(
                        min(10, int((hp_max_b - hp_hien) / hp_max_b * 10)),
                        round(1.0 + min(10, int((hp_max_b - hp_hien) / hp_max_b * 10)) * 0.10, 2))
                        if hp_max_b > 0 and hp_hien < hp_max_b else "")
                ), inline=False)
            embed.add_field(
                name="⚔️  Nhật ký chiến đấu",
                value="\n".join(combat_logs) if combat_logs else "*Chưa có ai tấn công...*",
                inline=False)
            if tc_display:
                sorted_tc = sorted(tc_display.items(), key=lambda x: x[1], reverse=True)[:10]
                tc_lines  = [f"**{i+1}.** <@{uid_k}>: {fmt(dmg_k)}"
                             for i, (uid_k, dmg_k) in enumerate(sorted_tc)]
                embed.add_field(
                    name=f"⚔️  Tham chiến ({len(tc_display)} tu sĩ)",
                    value="\n".join(tc_lines), inline=False)
            embed.add_field(
                name="⏳  Thời gian còn lại",
                value=f"{h}h {m}m" if h else f"{m} phút", inline=False)
            embed.set_footer(text="Chọn kỹ năng bên dưới để tấn công!")
            new_view = BossSpawnView(boss["id"])
            img_path = boss.get("image_file", "")

            # Loop tất cả guild — edit hoặc tạo mới nếu chưa có
            for _guild in self.bot.guilds:
                guild_msg = BossView._get_guild_msg(boss["id"], _guild.id)
                if guild_msg:
                    try:
                        embed_c = embed.copy()
                        if img_path and os.path.exists(img_path):
                            fname = os.path.basename(img_path)
                            f_img = discord.File(img_path, filename=fname)
                            embed_c.set_image(url=f"attachment://{fname}")
                            await guild_msg.edit(embed=embed_c, view=new_view, attachments=[f_img])
                        else:
                            await guild_msg.edit(embed=embed_c, view=new_view, attachments=[])
                        log.info(f"[BossRefresh] Guild {_guild.id}: refreshed {boss['ten']}")
                        await asyncio.sleep(1.5)  # tránh rate limit khi nhiều guild
                    except discord.errors.NotFound:
                        # Message bị xóa → clear memory + DB rồi tạo lại
                        BossView._boss_msg.get(boss["id"], {}).pop(_guild.id, None)
                        try:
                            await save_boss_guild_message(boss["id"], _guild.id, 0, 0)
                        except Exception:
                            log.exception("Lỗi hoso")
                        guild_msg = None
                        log.warning(f"[BossRefresh] Guild {_guild.id}: message bị xóa, tạo lại")
                    except Exception as e:
                        log.warning(f"[BossRefresh] Guild {_guild.id}: {e}")
                        continue
                if not guild_msg:
                    # Thử restore từ DB trước khi tạo mới
                    try:
                        guild_db_msgs = await get_boss_guild_messages(boss["id"])
                        for _gid, _mid, _cid in guild_db_msgs:
                            if _gid == _guild.id and _mid and _cid:
                                try:
                                    _ch_db = _guild.get_channel(_cid) or _guild.get_thread(_cid)
                                    if not _ch_db:
                                        _ch_db = await _guild.fetch_channel(_cid)
                                    if _ch_db:
                                        guild_msg = await _ch_db.fetch_message(_mid)
                                        BossView._set_guild_msg(boss["id"], _guild.id, guild_msg)
                                        log.info(f"[BossRefresh] Restored from DB guild={_guild.id}")
                                except discord.NotFound:
                                    pass  # kênh / message đã bị xóa
                                except Exception:
                                    log.exception("Lỗi hoso")
                                break
                    except Exception:
                        log.exception("Lỗi hoso")
                if not guild_msg:
                    # Thực sự chưa có → tạo mới
                    _ch = await self._get_announce_channel(_guild.id)
                    if _ch:
                        try:
                            spawn_ts_r = state.get("spawn_time", 0)
                            await _build_initial_boss_message(
                                self.bot, _ch, boss, cg_boss, hp_hien, spawn_ts_r,
                                is_new_spawn=False)
                        except Exception as e:
                            log.warning(f"[BossRefresh] Guild {_guild.id} tạo mới: {e}")

    @_boss_refresh_task.error
    async def __boss_refresh_task_error(self, error: Exception):
        log.error(f"[Task] _boss_refresh_task crashed: {error}", exc_info=True)

    @_boss_refresh_task.before_loop
    async def _before_boss_refresh(self):
        await self.bot.wait_until_ready()

    @discord.ext.tasks.loop(hours=24)
    async def _boss_data_cleanup_task(self):
        """Xóa boss_tham_gia cũ hơn 2 ngày — dọn dẹp định kỳ, data đã được reset khi spawn mới."""
        try:
            await cleanup_old_boss_data(days=2)
        except Exception as e:
            log.warning(f"[BossDataCleanup] Lỗi: {e}")

    @_boss_data_cleanup_task.error
    async def __boss_data_cleanup_task_error(self, error: Exception):
        log.error(f"[Task] _boss_data_cleanup_task crashed: {error}", exc_info=True)

    @_boss_data_cleanup_task.before_loop
    async def _before_boss_data_cleanup(self):
        await self.bot.wait_until_ready()

    # ── Phiên chợ hết hạn: hoàn trả item sau 2 ngày ──────────────
    @discord.ext.tasks.loop(hours=1)
    async def _phien_cho_expire_task(self):
        """Mỗi giờ kiểm tra phiên chợ quá 2 ngày → cancel + hoàn trả item cho người bán."""
        try:
            from utils.database import get_expired_phien_cho, cancel_phien_cho, get_tu_si, update_tu_si
            from cogs.views.kho_do import _resolve_phien_name
            expired = await get_expired_phien_cho(expire_secs=172800)  # 2 ngày
            if not expired:
                return
            log.info(f"[PhienChoExpire] {len(expired)} phiên hết hạn, tiến hành hoàn trả...")
            for ph in expired:
                pid  = ph["id"]
                uid  = ph["nguoi_ban"]
                loai = ph["loai"]
                iid  = ph["item_id"]
                ikey = ph.get("item_key", "")
                sl   = ph["so_luong"]
                try:
                    # Cancel phiên (đánh dấu da_ban=1) — nếu đã bị mua/cancel trước thì skip
                    ok = await cancel_phien_cho(pid, uid)
                    if not ok:
                        continue  # Đã được xử lý bởi luồng khác
                    # Hoàn trả item về túi người bán
                    ts = await get_tu_si(uid)
                    if not ts:
                        continue
                    if loai == "dan_duoc":
                        dd = ts["dan_duoc"].copy()
                        dd[str(iid)] = dd.get(str(iid), 0) + sl
                        await update_tu_si(uid, dan_duoc=dd)
                    elif loai == "dtl" and ikey:
                        dd = ts["dan_duoc"].copy()
                        dd[ikey] = dd.get(ikey, 0) + sl
                        await update_tu_si(uid, dan_duoc=dd)
                    elif loai == "lq" and ikey:
                        lq = ts.get("linh_qua", {}).copy()
                        lq[ikey] = lq.get(ikey, 0) + sl
                        await update_tu_si(uid, linh_qua=lq)
                    elif loai == "manh" and ikey:
                        manh = ts.get("manh_linh_can", {}).copy()
                        manh[ikey] = manh.get(ikey, 0) + sl
                        await update_tu_si(uid, manh_linh_can=manh)
                    else:
                        nl = ts["nguyen_lieu"].copy()
                        nl[str(iid)] = nl.get(str(iid), 0) + sl
                        await update_tu_si(uid, nguyen_lieu=nl)
                    # Gửi DM thông báo cho người bán
                    try:
                        emoji, ten = _resolve_phien_name(loai, iid, ikey)
                        user = self.bot.get_user(uid) or await self.bot.fetch_user(uid)
                        if user:
                            embed = discord.Embed(
                                title="📦 Phiên Chợ Hết Hạn",
                                description=(
                                    f"**{emoji} {ten} ×{sl}** đã được hoàn trả về túi đồ của bạn.\n"
                                    f"*(Phiên đăng bán quá **2 ngày** không có người mua)*"
                                ),
                                color=0xFEE75C
                            )
                            await user.send(embed=embed)
                    except discord.HTTPException:
                        pass  # DM thất bại (user tắt DM) — vẫn hoàn trả item
                    log.info(f"[PhienChoExpire] Hoàn trả pid={pid} → uid={uid} {loai} ×{sl}")
                except Exception as e:
                    log.error(f"[PhienChoExpire] Lỗi pid={pid}: {e}", exc_info=True)
        except Exception as e:
            log.error(f"[PhienChoExpire] Task lỗi: {e}", exc_info=True)

    @_phien_cho_expire_task.error
    async def __phien_cho_expire_task_error(self, error: Exception):
        log.error(f"[Task] _phien_cho_expire_task crashed: {error}", exc_info=True)

    @_phien_cho_expire_task.before_loop
    async def _before_phien_cho_expire(self):
        await self.bot.wait_until_ready()

    @discord.ext.tasks.loop(minutes=1)
    async def _boss_spawn_task(self):
        """Spawn boss theo window 6h — không phụ thuộc vào phút chính xác.
        Mỗi lần task chạy (mỗi phút), kiểm tra xem window spawn hiện tại đã có boss chưa.
        Nếu chưa (hoặc boss cũ đã hết), spawn mới. Tránh lỗi miss spawn khi bot restart lệch giây.
        """
        now_vn   = datetime.now(VN_TZ)
        # Tính timestamp bắt đầu window spawn hiện tại (giờ VN gần nhất trong BOSS_SPAWN_HOURS_VN)
        current_window_h = None
        for h in sorted(BOSS_SPAWN_HOURS_VN, reverse=True):
            if now_vn.hour >= h:
                current_window_h = h
                break
        if current_window_h is None:
            yesterday = now_vn.replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(seconds=1)
            current_window_h = BOSS_SPAWN_HOURS_VN[-1]
            window_start_vn  = yesterday.replace(hour=current_window_h, minute=0, second=0, microsecond=0)
        else:
            window_start_vn = now_vn.replace(hour=current_window_h, minute=0, second=0, microsecond=0)
        window_start_ts = int(window_start_vn.timestamp())

        secs_into_window = int(datetime.now(timezone.utc).timestamp()) - window_start_ts
        if secs_into_window < 0 or secs_into_window > 600:
            return

        from utils.database import get_boss_state as _gbs
        for _b in BOSS_THE_GIOI:
            _st = await _gbs(_b["id"])
            if _st and _st.get("spawn_time", 0) >= window_start_ts:
                return

        if self._spawn_lock.locked():
            log.info("[BossSpawn] Skip — spawn đang được xử lý")
            return
        async with self._spawn_lock:
            for _b2 in BOSS_THE_GIOI:
                _st2 = await get_boss_state(_b2["id"])
                if _st2 and _st2.get("spawn_time", 0) >= window_start_ts:
                    log.info("[BossSpawn] Double-check: đã spawn trong window này")
                    return
            spawn_ts  = int(datetime.now(timezone.utc).timestamp())
            boss_pick = random.choice(BOSS_THE_GIOI)
            cg_rand   = random.choice(boss_pick["canh_gioi_pool"])
            hp_b      = BOSS_HP_BY_CG.get(cg_rand, boss_pick["hp_max"])
            from utils.database import clear_boss_data, get_boss_guild_messages, clear_boss_guild_messages
            for _b in BOSS_THE_GIOI:
                try:
                    guild_msgs = await get_boss_guild_messages(_b["id"])
                    for _gid, _mid, _cid in guild_msgs:
                        if _mid and _cid:
                            try:
                                _ch = self.bot.get_channel(_cid) or await self.bot.fetch_channel(_cid)
                                if _ch:
                                    _m = await _ch.fetch_message(_mid)
                                    await _m.delete()
                            except discord.NotFound:
                                pass  # kênh / message đã bị xóa — bỏ qua
                            except Exception:
                                log.exception("Lỗi hoso")
                except Exception:
                    log.exception("Lỗi hoso")
                await clear_boss_data(_b["id"], purge_rewards=True)
                log.info(f"[BossSpawn] Reset boss_id={_b['id']} (xóa toàn bộ data cũ)")
            await spawn_boss(boss_pick["id"], hp_b, spawn_ts, {}, canh_gioi=cg_rand)
            log.info(f"[BossSpawn] {boss_pick['ten']} xuất hiện CG={cg_rand} HP={hp_b:,} lúc {now_vn.strftime('%H:%M')} VN")

            for _guild in self.bot.guilds:
                _channel = await self._get_announce_channel(_guild.id)
                if _channel:
                    try:
                        await _build_initial_boss_message(
                            self.bot, _channel, boss_pick, cg_rand, hp_b, spawn_ts,
                            is_new_spawn=False)
                    except Exception as e:
                        log.warning(f"[BossSpawn] Không gửi được tới guild {_guild.id}: {e}")

    @_boss_spawn_task.error
    async def __boss_spawn_task_error(self, error: Exception):
        log.error(f"[Task] _boss_spawn_task crashed: {error}", exc_info=True)
        await asyncio.sleep(60)
        if not self._boss_spawn_task.is_running():
            self._boss_spawn_task.start()
            log.info("[Task] _boss_spawn_task restarted after crash")

    @_boss_spawn_task.before_loop
    async def _before_boss_spawn(self):
        await self.bot.wait_until_ready()
        await self._restore_boss_messages()


    @discord.ext.tasks.loop(minutes=10)
    async def _session_cleanup_task(self):
        """Dọn session bí cảnh timeout mỗi 10 phút — tránh RAM leak."""
        cleaned = _cleanup_stale_sessions()
        if cleaned:
            log.info(f"[SessionCleanup] Đã dọn {cleaned} session hết hạn")

    @_session_cleanup_task.error
    async def __session_cleanup_task_error(self, error: Exception):
        log.error(f"[Task] _session_cleanup_task crashed: {error}", exc_info=True)

    @_session_cleanup_task.before_loop
    async def _before_session_cleanup(self):
        await self.bot.wait_until_ready()

    @app_commands.command(name="setbosschannel",
        description="Set channel/thread để bot spawn World Boss (cần quyền Manage Guild)")
    @app_commands.describe(channel_id="ID của channel hoặc thread muốn dùng cho Boss TG")
    async def setbosschannel(self, inter: discord.Interaction, channel_id: str):
        if not inter.guild:
            return await inter.response.send_message("❌ Chỉ dùng trong server!", ephemeral=True)
        if not (inter.user.guild_permissions.administrator
                or inter.user.id == inter.guild.owner_id
                or inter.user.id in OWNER_IDS):
            return await inter.response.send_message("❌ Cần quyền Administrator!", ephemeral=True)
        await inter.response.defer(ephemeral=True)
        try:
            ch_id = int(channel_id)
        except ValueError:
            return await safe_followup(inter, "❌ ID không hợp lệ!", ephemeral=True)
        # Thử lấy channel hoặc thread
        ch = inter.guild.get_channel(ch_id) or inter.guild.get_thread(ch_id)
        if ch is None:
            # Thử fetch thread nếu chưa cache
            try:
                ch = await inter.guild.fetch_channel(ch_id)
            except Exception:
                return await safe_followup(inter, 
                    "❌ Không tìm thấy channel/thread với ID đó!", ephemeral=True)
        await set_boss_channel(inter.guild.id, ch_id)
        await safe_followup(inter, 
            f"✅ Đã set **{ch.mention}** (`{ch_id}`) làm channel spawn World Boss!\n"
            f"Bot sẽ gửi thông báo và tạo bảng chiến đấu tại đây.",
            ephemeral=True)
        log.info(f"[BossChannel] Guild={inter.guild.id} → channel={ch_id} ({ch.name})")


    @app_commands.command(name="killboss", description="[Owner] Force kill boss đang active")
    @app_commands.describe(boss_id="0=Hình Thiên 1=Trường Thừa 2=Đào Ngột 3=Kế Mông (-1=tất cả)")
    async def killboss(self, inter: discord.Interaction, boss_id: int = -1):
        if inter.user.id not in OWNER_IDS:
            return await inter.response.send_message("❌ Chỉ owner mới dùng được!", ephemeral=True)
        if not inter.guild:
            return await inter.response.send_message("❌ Chỉ dùng trong server!", ephemeral=True)
        await inter.response.defer(ephemeral=True)

        targets = BOSS_THE_GIOI if boss_id < 0 else ([BOSS_THE_GIOI[boss_id]] if 0 <= boss_id < len(BOSS_THE_GIOI) else [])
        if not targets:
            return await safe_followup(inter, "❌ boss_id không hợp lệ!", ephemeral=True)

        from cogs.views.boss import BossView
        from utils.database import get_boss_message_id, save_boss_message_id
        killed = []
        for boss in targets:
            state = await get_boss_state(boss["id"])
            if not state or not _boss_is_active(state):
                continue
            now_ts = int(__import__("time").time())
            nguoi_tc = state.get("nguoi_tan_cong", {})
            await upsert_boss(boss["id"], 0, state["spawn_time"], nguoi_tc, canh_gioi=state.get("canh_gioi", 0))
            await set_boss_end_time(boss["id"], now_ts)

            # Xóa message trên tất cả guild (in-memory)
            for _msg in list(BossView._boss_msg.get(boss["id"], {}).values()):
                try:
                    await _msg.delete()
                except Exception:
                    log.exception("Lỗi hoso")
            BossView._pop_boss_msg(boss["id"])

            # Xóa message từ DB (guild khác có thể lưu riêng)
            old_msg_id, old_ch_id = await get_boss_message_id(boss["id"])
            if old_msg_id and old_ch_id:
                try:
                    _ch = self.bot.get_channel(old_ch_id) or await self.bot.fetch_channel(old_ch_id)
                    _m  = await _ch.fetch_message(old_msg_id)
                    await _m.delete()
                except Exception:
                    log.exception("Lỗi hoso")
                await save_boss_message_id(boss["id"], 0, 0)

            # Thông báo boss biến mất trên tất cả guild
            expire_embed = discord.Embed(
                title=f"🌫️ {boss['ten']} ĐÃ BIẾN MẤT!",
                description="**" + boss["ten"] + "** đã bị xua đuổi khỏi thiên hạ.\nHãy chuẩn bị cho lần xuất hiện tiếp theo!",
                color=0x555555)
            for _guild in self.bot.guilds:
                _ch = await self._get_announce_channel(_guild.id)
                if _ch:
                    try:
                        await _ch.send(embed=expire_embed)
                    except Exception:
                        log.exception("Lỗi hoso")

            killed.append(boss["ten"])
            log.info(f"[KillBoss] {boss['ten']} bị force kill bởi {inter.user}")

        if not killed:
            return await safe_followup(inter, "❌ Không có boss nào đang active!", ephemeral=True)
        await safe_followup(inter, f"✅ Đã kill toàn server: **{', '.join(killed)}**", ephemeral=True)

    @app_commands.command(name="broadcast", description="[Owner] Gửi thông báo quan trọng tới tất cả server")
    @app_commands.describe(
        tieu_de="Tiêu đề thông báo",
        noi_dung="Nội dung thông báo (hỗ trợ markdown Discord)",
        mau="Màu embed: green/red/yellow/blue/purple (mặc định: blue)",
    )
    async def broadcast(self, inter: discord.Interaction,
                        tieu_de: str, noi_dung: str,
                        mau: str = "blue"):
        if inter.user.id not in OWNER_IDS:
            return await inter.response.send_message("❌ Chỉ owner mới dùng được!", ephemeral=True)
        await inter.response.defer(ephemeral=True)

        COLOR_MAP = {
            "green":  0x57F287, "red":    0xED4245,
            "yellow": 0xFEE75C, "blue":   0x5865F2,
            "purple": 0xC77DFF, "gold":   0xFFD700,
            "orange": 0xFF6B35,
        }
        color = COLOR_MAP.get(mau.lower(), 0x5865F2)

        # Cho phép dùng \n để xuống dòng trong nội dung
        noi_dung = noi_dung.replace('\\n', '\n')

        embed = discord.Embed(title=f"📢 {tieu_de}", description=noi_dung, color=color)
        embed.set_footer(text="— Thông báo từ Ban Quản Trị")
        embed.timestamp = discord.utils.utcnow()

        sent = 0; failed = 0; skipped = 0
        for guild in self.bot.guilds:
            # Ưu tiên: boss channel đã set → fallback system channel → channel đầu tiên có quyền gửi
            ch = await self._get_announce_channel(guild.id)
            if not ch:
                ch = guild.system_channel
            if not ch:
                # Tìm channel text đầu tiên bot có quyền gửi
                for channel in guild.text_channels:
                    perms = channel.permissions_for(guild.me)
                    if perms.send_messages and perms.embed_links:
                        ch = channel
                        break
            if not ch:
                skipped += 1
                continue
            try:
                await ch.send(embed=embed)
                sent += 1
                log.info(f"[Broadcast] Gửi tới guild={guild.id} ({guild.name}) → #{ch.name}")
            except Exception as e:
                failed += 1
                log.warning(f"[Broadcast] Thất bại guild={guild.id}: {e}")

        result_embed = e_ok(
            "📢 Broadcast Hoàn Tất",
            f"**Tiêu đề:** {tieu_de}\n\n"
            f"✅ Gửi thành công: **{sent}** server\n"
            f"❌ Thất bại: **{failed}** server\n"
            f"⏭️ Bỏ qua (không tìm được channel): **{skipped}** server\n"
            f"📊 Tổng: **{len(self.bot.guilds)}** server"
        )
        await safe_followup(inter, embed=result_embed, ephemeral=True)

    @app_commands.command(name="thoat_bicanh", description="Thoát khẩn cấp khỏi bí cảnh (không nhận thưởng)")
    async def thoat_bicanh(self, inter: discord.Interaction):
        uid      = inter.user.id
        guild_id = inter.guild_id or 0
        sess_key = (guild_id, uid)
        if sess_key in _bc_sessions:
            s = _bc_sessions.pop(sess_key)
            s.ket_thuc = True
            await inter.response.send_message(
                embed=e_warn("🚪 Thoát Bí Cảnh", "Đã thoát khẩn cấp khỏi bí cảnh.\n⚠️ Toàn bộ tiến trình và phần thưởng **không được lưu**."),
                ephemeral=True)
        else:
            await inter.response.send_message(
                "✅ Bạn không đang trong bí cảnh nào.", ephemeral=True)

    async def _restore_boss_messages(self):
        """Sau restart: restore message boss từ DB, edit với view mới (persistent buttons).
        BossSpawnView dùng custom_id nên không cần xóa/tạo lại sau restart.
        """
        from cogs.views.boss import BossView, BossSpawnView, _build_initial_boss_message
        for boss in BOSS_THE_GIOI:
            state = await get_boss_state(boss["id"])
            if not _boss_is_active(state):
                continue
            cg_boss  = state.get("canh_gioi", boss["canh_gioi_pool"][0])
            hp_hien  = state["hp_hien"]
            spawn_ts = state.get("spawn_time", 0)

            # Đăng ký lại BossSpawnView với custom_id → Discord tự route callbacks
            try:
                self.bot.add_view(BossSpawnView(boss["id"]))
            except Exception:
                log.exception("Lỗi hoso")

            # Edit các message đang tồn tại trong DB — không xóa, không tạo mới nếu còn
            for _guild in self.bot.guilds:
                _ch = await self._get_announce_channel(_guild.id)
                if _ch:
                    try:
                        await _build_initial_boss_message(
                            self.bot, _ch, boss, cg_boss, hp_hien, spawn_ts,
                            is_new_spawn=False)
                        await asyncio.sleep(1.0)  # tránh rate limit
                        log.info(f"[BossRestore] Restored {boss['ten']} tới guild {_guild.id}")
                    except Exception as e:
                        log.warning(f"[BossRestore] Guild {_guild.id}: {e}")

    @app_commands.command(name="pvp",
        description="Thách đấu tu sĩ khác — tùy chọn cược Linh Thạch")
    @app_commands.describe(target="Tu sĩ muốn thách đấu")
    async def pvp(self, inter: discord.Interaction, target: discord.User):
        await start_pvp(inter, target)

    @app_commands.command(name="hoso",
        description="Xem hồ sơ tu sĩ — toàn bộ gameplay từ đây")
    @app_commands.describe(user="@tag hoặc User ID để xem hồ sơ của họ (chỉ đọc)")
    async def hoso(self, inter: discord.Interaction, user: discord.User = None):
        target = user or inter.user
        is_own = (target.id == inter.user.id)

        # Defer ngay trước DB query — tránh 404 Unknown interaction khi DB chậm >3s.
        # Nếu là new user cần modal → sau defer không dùng send_modal được
        # → dùng _DangKyTriggerView (nút bấm ephemeral mở modal từ interaction mới).
        try:
            await inter.response.defer()
        except discord.NotFound:
            return  # interaction đã hết hạn trước khi bot xử lý — bỏ qua

        ts = await get_tu_si(target.id)

        if not ts:
            if not is_own:
                return await inter.followup.send(
                    embed=e_loi("❌ Chưa Tu Tiên", f"**{target.display_name}** chưa đăng ký!"),
                    ephemeral=True)
            # Kiểm tra tuổi tài khoản Discord — chống clone/alt
            import datetime as _dt
            acc_age_days = (_dt.datetime.now(_dt.timezone.utc) - inter.user.created_at).days
            if acc_age_days < 30:
                return await inter.followup.send(
                    embed=e_loi(
                        "❌ Tài Khoản Quá Mới",
                        f"Tài khoản Discord của bạn chỉ mới **{acc_age_days} ngày**.\n"
                        f"Cần tối thiểu **30 ngày** để tham gia tu tiên.\n"
                        f"*(Biện pháp chống tài khoản phụ)*"
                    ),
                    ephemeral=True)
            return await inter.followup.send(
                embed=discord.Embed(
                    title="✦ Nhập Môn Tu Tiên ✦",
                    description="Bạn chưa có hồ sơ tu tiên.\nNhấn nút bên dưới để đăng ký!",
                    color=0x5865F2,
                ),
                view=_DangKyTriggerView(inter.user.id),
                ephemeral=True,
            )

        try:
            view = HoSoView(ts, target, target.id, viewer_id=inter.user.id)
            embed_hoso = _embed_hoso(ts, target, is_own=is_own)
            msg = await safe_followup(inter, embed=embed_hoso, view=view)
            view._message = msg
        except Exception as e:
            log.exception("Lỗi hoso")
            await safe_followup(inter, embed=e_loi("Lỗi", str(e)), ephemeral=True)


async def setup(bot):
    await bot.add_cog(HoSoCog(bot))
