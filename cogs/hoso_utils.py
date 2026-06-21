"""
hoso_utils.py — Shared helpers, embeds, constants cho hoso system
"""
from __future__ import annotations
from typing import Any

import discord
import asyncio
import random
import time
import logging
import os
import re as _re
from datetime import datetime, timezone, timedelta
from dataclasses import dataclass, field
from typing import Optional

log = logging.getLogger("hoso")

from utils.config import (
    CANH_GIOI, LINH_CAN_BY_ID, LINH_CAN_CO_BAN, LINH_CAN_HIEM, LINH_CAN_DIEM_YEU_CAU,
    LINH_QUA, LINH_QUA_BY_ID, LINH_QUA_DROP_CO_BAN,
    THE_CHAT, THE_CHAT_BY_ID,
    MANH_LINH_CAN_EMOJI, MANH_LINH_CAN_GIA,
    TONG_MON, PHAP_BAO, PHAP_BAO_BY_ID, PHAP_BAO_SKILL,
    DAN_DUOC, DAN_TU_LUYEN, NGUYEN_LIEU, BI_CANH, BOSS_THE_GIOI,
    DOTPHA_TC_NGUYEN_LIEU,
    BOSS_SPAWN_HOURS_VN, boss_bar, BOSS_HP_BY_CG, emoji_hp_bar,
    DIEM_DANH_PHAN_THUONG, SU_KIEN_BI_CANH, BUFF_LABELS, DIEM_DANH_HE_SO,
    CD_TU_LUYEN, CD_DOT_PHA, CD_KHAI_HOANG,
    get_cg, get_cg_ten, bar, fmt, fmt_cd,
    exp_can_thiet, hp_max_cong_thuc, cong_cong_thuc, thu_cong_thuc,
    random_linh_can_co_ban,
)
from utils.embeds import e_loi, e_ok, e_warn, e_info
from utils.emoji_manager import get_stat_emoji
from cogs.cong_phap import calc_cp_bonus
from utils.database import (
    get_tu_si, update_tu_si, get_the_luc, get_tran_the_luc, THE_LUC_HOI, the_luc_toi_da,
    TRAN_THE_LUC_MAX, TRAN_THE_LUC_HOI,
    _enqueue,
)

VN_TZ = timezone(timedelta(hours=7))
BOSS_LIFETIME = 3600


def diem_danh_cd_con_lai(last_claim_ts: int, now_ts: int | None = None) -> int:
    """Điểm danh theo ngày VN: đã nhận hôm nay thì chờ tới 00:00 hôm sau."""
    now_ts = int(now_ts if now_ts is not None else time.time())
    last_claim_ts = int(last_claim_ts or 0)
    if last_claim_ts <= 0:
        return 0

    now_vn = datetime.fromtimestamp(now_ts, VN_TZ)
    last_vn = datetime.fromtimestamp(last_claim_ts, VN_TZ)
    if now_vn.date() != last_vn.date():
        return 0

    next_midnight_vn = now_vn.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
    return max(0, int(next_midnight_vn.timestamp()) - now_ts)


def diem_danh_day_delta(last_claim_ts: int, now_ts: int | None = None) -> int:
    """Số ngày lệch theo múi giờ VN giữa lần điểm danh gần nhất và hiện tại."""
    now_ts = int(now_ts if now_ts is not None else time.time())
    last_claim_ts = int(last_claim_ts or 0)
    if last_claim_ts <= 0:
        return 10**9
    now_vn = datetime.fromtimestamp(now_ts, VN_TZ)
    last_vn = datetime.fromtimestamp(last_claim_ts, VN_TZ)
    return (now_vn.date() - last_vn.date()).days

# Cache cho lazy import sung_thu (tránh circular + overhead lặp lại)
_st_buff_fn = None
ITEMS_PER_PAGE = 5

from cogs.views._session import BiCanhSession, _bc_sessions, SESSION_TIMEOUT_SECS, _cleanup_stale_sessions

_bg_tasks: set = set()  # giữ reference để task không bị GC

def _run_task(coro) -> asyncio.Task:
    """Tạo background task và giữ reference tránh GC."""
    task = asyncio.create_task(coro)
    _bg_tasks.add(task)
    task.add_done_callback(_bg_tasks.discard)
    return task


async def _back_to_hoso(inter: discord.Interaction, parent) -> None:
    """Quay về main HoSoView — edit nếu là chủ, send hồ sơ bản thân nếu viewer."""
    is_own = (inter.user.id == parent.owner_id)
    if is_own:
        await parent._reload(inter.user.id)
        parent._rebuild()
        try:
            await inter.response.edit_message(
                embed=parent._current_embed(), view=parent, attachments=[])
        except discord.errors.InteractionResponded:
            await inter.edit_original_response(
                embed=parent._current_embed(), view=parent, attachments=[])
    else:
        # Viewer → gửi hồ sơ bản thân kèm view đầy đủ
        ts_caller = await get_tu_si(inter.user.id)
        if not ts_caller:
            try:
                await inter.response.send_message("❌ Bạn chưa có hồ sơ!", ephemeral=True)
            except discord.errors.InteractionResponded:
                await safe_followup(inter, "❌ Bạn chưa có hồ sơ!", ephemeral=True)
            return
        from cogs.hoso import HoSoView as _HoSoView
        view_self = _HoSoView(ts_caller, inter.user, inter.user.id)
        embed_self = _embed_hoso(ts_caller, inter.user, is_own=True)
        try:
            await inter.response.send_message(embed=embed_self, view=view_self, ephemeral=True)
        except discord.errors.InteractionResponded:
            await safe_followup(inter, embed=embed_self, view=view_self, ephemeral=True)

# ══════════════════════════════════════════════════════════════
#  COMBAT HELPERS
# ══════════════════════════════════════════════════════════════
import re as _re
from utils.bot_emojis import (
    E_SINH_LUC, E_CONG_KICH, E_PHONG_NGU, E_LINH_LUC,
    E_HOI_TAM, E_HO_TAM, E_BAO_KICH, E_KHANG_BAO,
    E_LINH_THACH, E_TT_LINH_THACH, E_TU_VI,
)
from utils.embeds import safe_followup
def _parse_emoji(s: str) -> discord.PartialEmoji | str:
    """Chuyển '<:name:id>f' thành discord.PartialEmoji, hoặc trả về string gốc nếu là unicode."""
    m = _re.match(r"<a?:(\w+):(\d+)>", s)
    if m:
        return discord.PartialEmoji(name=m.group(1), id=int(m.group(2)))
    return s

def _calc_linh_can_passive(ts: dict[str, Any]) -> dict[str, Any]:
    """Tính tổng passive lớp 1 từ tất cả linh căn đang sở hữu (mỗi loại tính 1 lần)."""
    result = {"at_flat": 0, "df_flat": 0, "hp_flat": 0,
              "at_pct": 0.0, "def_pct": 0.0, "hp_pct": 0.0,
              "hoi_tam": 0, "ho_tam": 0, "bao_kich": 0.0, "khang_bao": 0.0,
              "drop_rate": 0.0, "exp_pct": 0.0}
    # Deduplicate: mỗi loại chỉ tính 1 lần dù data cũ có thể có duplicate
    seen = set()
    for lc_id in ts.get("linh_can_so_huu", []):
        if lc_id in seen:
            continue
        seen.add(lc_id)
        lc = LINH_CAN_BY_ID.get(lc_id)
        if not lc:
            continue
        p = lc.get("passive", {})
        result["at_flat"]   += p.get("at_flat",   0)
        result["df_flat"]   += p.get("df_flat",   0)
        result["hp_flat"]   += p.get("hp_flat",   0)
        result["hoi_tam"]   += p.get("hoi_tam",   0)
        result["ho_tam"]    += p.get("ho_tam",    0)
        result["bao_kich"]  += p.get("bao_kich",  0.0)
        result["khang_bao"] += p.get("khang_bao", 0.0)
        result["drop_rate"] += p.get("drop_rate", 0.0)
        result["exp_pct"]   += p.get("exp_pct",   0.0)
        result["at_pct"]    += p.get("at_pct",    0.0)
        result["def_pct"]   += p.get("def_pct",   0.0)
        result["hp_pct"]    += p.get("hp_pct",    0.0)
    return result


def _calc_linh_can_lop2(ts: dict[str, Any]) -> dict[str, Any]:
    """Tính tổng buff lớp 2 tích lũy từ cột linh_can_lop2 trong DB.
    Đây là các buff được cộng dồn mỗi lần đột phá đại cảnh thành công.
    Format DB: {"hoi_tam": 200, "ho_tam": 100, "bao_kich": 3.0, "drop_rate": 6.0, ...}
    """
    raw = ts.get("linh_can_lop2", {})
    if isinstance(raw, str):
        import json as _j
        try: raw = _j.loads(raw) if raw else {}
        except Exception: raw = {}
    if not isinstance(raw, dict):
        return {}
    return raw


def _calc_stats(ts: dict[str, Any]) -> dict[str, Any]:  # noqa: PLR0912
    # Pháp bảo: chỉ 1 pháp bảo active đóng góp stats
    _pb_active_id = ts.get("phap_bao_active", -1)
    _pb_active    = PHAP_BAO_BY_ID.get(_pb_active_id) if _pb_active_id >= 0 else None
    pb_at  = _pb_active["at"]  if _pb_active else 0
    pb_df  = _pb_active["df"]  if _pb_active else 0
    pb_pas = _pb_active.get("passive", {}) if _pb_active else {}
    tm    = TONG_MON[ts["tong_mon"]] if 0 <= ts["tong_mon"] < len(TONG_MON) else None
    pb_at_pct = pb_pas.get("at_pct", 0.0)
    pb_df_pct = pb_pas.get("df_pct", 0.0)
    pb_hp_pct = pb_pas.get("hp_pct", 0.0)
    at    = int((ts["cong"] + pb_at) * (1 + pb_at_pct / 100))
    df    = int((ts["thu"]  + pb_df) * (1 + pb_df_pct / 100))
    hp_e  = int(ts["hp_max"] * (1 + pb_hp_pct / 100))  # pháp bảo HP% áp vào base
    at    = int(at * (tm["buff_val"] if tm and tm["buff"] == "cong" else 1.0))
    hp_e  = int(hp_e * (tm["buff_val"] if tm and tm["buff"] == "hp" else 1.0))
    lt_m  = tm["buff_val"] if tm and tm["buff"] == "linh_thach" else 1.0
    exp_m = tm["buff_val"] if tm and tm["buff"] == "exp"        else 1.0
    # Hệ số EXP & LT từ cảnh giới (chỉ ảnh hưởng tu vi và linh thạch nhận được)
    cg_he_so = DIEM_DANH_HE_SO[min(ts.get("canh_gioi", 0), len(DIEM_DANH_HE_SO) - 1)]
    lt_m  = round(lt_m  * cg_he_so, 2)
    exp_m = round(exp_m * cg_he_so, 2)
    # Passive linh căn lớp 1
    lc_p = _calc_linh_can_passive(ts)
    # exp_pct linh căn → chỉ ảnh hưởng tu vi
    exp_m = round(exp_m * (1 + lc_p["exp_pct"] / 100), 2)
    # drop_rate linh căn → chỉ ảnh hưởng drop rate (drop_m), KHÔNG ảnh hưởng lt_m
    drop_m = round(1.0 * (1 + lc_p["drop_rate"] / 100), 2)
    # Cộng bonus từ công pháp đã học (stack tất cả)
    cp_b  = calc_cp_bonus(ts)
    # 1. Passive flat: pháp bảo + linh căn + công pháp
    at   += cp_b["at_flat"] + lc_p["at_flat"]
    df   += cp_b["df_flat"] + lc_p["df_flat"]
    hp_e += cp_b["hp_flat"] + lc_p["hp_flat"]
    # 2. % bonus từ công pháp + linh căn
    at    = int(at   * (1 + (cp_b["at_pct"]  + lc_p.get("at_pct",  0.0)) / 100))
    df    = int(df   * (1 + (cp_b["def_pct"] + lc_p.get("def_pct", 0.0)) / 100))
    hp_e  = int(hp_e * (1 + (cp_b["hp_pct"]  + lc_p.get("hp_pct",  0.0)) / 100))
    # Apply THE_CHAT buff
    from utils.config import THE_CHAT_BY_ID as _TC_BY_ID
    tc_data = _TC_BY_ID.get(ts.get("the_chat", ""))
    tc_hoi_tam = 0; tc_ho_tam = 0; tc_bao_kich = 0.0; tc_khang_bao = 0.0
    if tc_data:
        b = tc_data.get("buff", {})
        if b.get("at_pct"):  at   = int(at   * (1 + b["at_pct"]  / 100))
        if b.get("def_pct"): df   = int(df   * (1 + b["def_pct"] / 100))
        if b.get("hp_pct"):  hp_e = int(hp_e * (1 + b["hp_pct"]  / 100))
        if b.get("exp_m"):   exp_m  = round(exp_m  * b["exp_m"], 2)
        if b.get("lt_m"):    lt_m   = round(lt_m   * b["lt_m"],  2)
        # drop_rate thể chất → chỉ ảnh hưởng drop_m, KHÔNG ảnh hưởng lt_m
        if b.get("drop_rate"): drop_m = round(drop_m * (1 + b["drop_rate"] / 100), 2)
        if b.get("hoi_tam"):    tc_hoi_tam  = b["hoi_tam"]   # flat điểm → _calc_full_stats
        if b.get("ho_tam"):     tc_ho_tam   = b["ho_tam"]    # flat điểm → _calc_full_stats
        if b.get("bao_kich"):   tc_bao_kich = b["bao_kich"]  # flat % → _calc_full_stats
        if b.get("khang_bao"):  tc_khang_bao= b["khang_bao"] # flat % → _calc_full_stats
    # Sủng Thú buff (lazy import lần đầu, cache lại để tránh circular + overhead)
    global _st_buff_fn
    if _st_buff_fn is None:
        from cogs.views.sung_thu import _calc_sung_thu_buff as _f
        _st_buff_fn = _f
    st_b = _st_buff_fn(ts)
    if st_b.get("at_pct"):   at   = int(at   * (1 + st_b["at_pct"]  / 100))
    if st_b.get("def_pct"):  df   = int(df   * (1 + st_b["def_pct"] / 100))
    if st_b.get("hp_pct"):   hp_e = int(hp_e * (1 + st_b["hp_pct"]  / 100))
    if st_b.get("exp_pct"):  exp_m = round(exp_m * (1 + st_b["exp_pct"] / 100), 2)
    # drop_rate sủng thú → chỉ ảnh hưởng drop_m, KHÔNG ảnh hưởng lt_m
    if st_b.get("drop_rate"): drop_m = round(drop_m * (1 + st_b["drop_rate"] / 100), 2)

    vd_pct = float(ts.get("van_dinh_all_stat_pct", 0.0) or 0.0)
    if vd_pct > 0:
        vd_mult = 1 + vd_pct / 100
        at = int(at * vd_mult)
        df = int(df * vd_mult)
        hp_e = int(hp_e * vd_mult)

    # ── Buff lớp 2 từ linh căn (drop_rate, exp_pct) ──────────
    lc2 = _calc_linh_can_lop2(ts)
    if lc2.get("drop_rate"):
        drop_m = round(drop_m * (1 + lc2["drop_rate"] / 100), 2)
    if lc2.get("exp_pct"):
        exp_m = round(exp_m * (1 + lc2["exp_pct"] / 100), 2)

    # ── Ý Cảnh effects ────────────────────────────────────────
    from cogs.views.y_canh import _get_y_canh, _tinh_effect
    ycanh_eff = _tinh_effect(_get_y_canh(ts))
    if ycanh_eff.get("at_pct"):
        at = int(at * (1 + ycanh_eff["at_pct"] / 100))
    if ycanh_eff.get("def_pct"):
        df = int(df * (1 + ycanh_eff["def_pct"] / 100))
    if ycanh_eff.get("hp_pct"):
        hp_e = int(hp_e * (1 + ycanh_eff["hp_pct"] / 100))
    if ycanh_eff.get("exp_pct"):
        exp_m = round(exp_m * (1 + ycanh_eff["exp_pct"] / 100), 2)
    if ycanh_eff.get("drop_rate"):
        drop_m = round(drop_m * (1 + ycanh_eff["drop_rate"] / 100), 2)
    if ycanh_eff.get("lt_nhan"):
        lt_m = round(lt_m * (1 + ycanh_eff["lt_nhan"] / 100), 2)

    # ── Trận Đạo effects ──────────────────────────────────────
    from utils.config import TRAN_DAO_BY_ID
    tran_id = ts.get("tran_dao_active", "")
    tran_cfg = TRAN_DAO_BY_ID.get(tran_id)
    if tran_cfg:
        for k, v in tran_cfg["buff"].items():
            if k == "at_pct":
                at = int(at * (1 + v / 100))
            elif k == "def_pct":
                df = int(df * (1 + v / 100))
            elif k == "hp_pct":
                hp_e = int(hp_e * (1 + v / 100))
            elif k == "bao_kich":
                pass  # applied in _calc_full_stats
            elif k == "linh_luc_pct":
                pass  # applied in _calc_full_stats
            elif k == "cd_giam":
                pass  # applied in _calc_full_stats
        for k, v in tran_cfg["debuff"].items():
            if k == "at_pct":
                at = int(at * (1 + v / 100))
            elif k == "def_pct":
                df = int(df * (1 + v / 100))
            elif k == "hp_pct":
                hp_e = int(hp_e * (1 + v / 100))

    # Tách riêng drop_rate và lt_m từ thể chất để hiển thị trong thuộc tính
    tc_drop_rate = tc_data.get("buff", {}).get("drop_rate", 0.0) if tc_data else 0.0
    tc_lt_m      = tc_data.get("buff", {}).get("lt_m", 1.0)      if tc_data else 1.0

    return {"at": at, "df": df, "hp_eff": hp_e, "tm": tm, "lc_p": lc_p, "st_b": st_b,
            "pb_at": pb_at, "pb_df": pb_df, "lt_m": lt_m, "exp_m": exp_m, "drop_m": drop_m,
            "pb_at_pct": pb_at_pct, "pb_df_pct": pb_df_pct, "pb_hp_pct": pb_hp_pct,
            "cp_b": cp_b, "tc": tc_data, "tc_hoi_tam": tc_hoi_tam,
            "tc_ho_tam": tc_ho_tam, "tc_bao_kich": tc_bao_kich, "tc_khang_bao": tc_khang_bao,
            "cl": int(at * 10 + df * 8 + hp_e * 0.1),
            "cd_tl_pct":   tc_data.get("buff", {}).get("cd_tu_luyen_pct", 0.0) if tc_data else 0.0,
            "tc_drop_rate": tc_drop_rate,
            "tc_lt_m":      tc_lt_m,
            "van_dinh_all_stat_pct": vd_pct}

def _calc_full_stats(ts: dict[str, Any]) -> dict[str, Any]:
    """Tính toàn bộ chỉ số thuộc tính như hiển thị trong /thuoctính."""
    st        = _calc_stats(ts)
    cp_b      = st["cp_b"]
    lc_p      = st["lc_p"]
    lv        = ts["canh_gioi"] * 9 + ts["cap_nho"]
    # Base stats
    linh_luc  = int((200 + ts["canh_gioi"]**2 * 2300 + ts["cap_nho"] * 230) * 0.8 * 0.7)
    hoi_tam   = int(st["at"] * 0.08 + lv * 3)
    ho_tam    = int(st["df"] * 0.15 + lv * 2)
    bao_kich  = min(5 + ts["canh_gioi"] * 3 + ts["cap_nho"], 75)
    khang_bao = min(3 + ts["canh_gioi"] * 2 + ts["cap_nho"] // 2, 50)
    # Cộng bonus từ công pháp (điểm trực tiếp, không ×100)
    linh_luc  += cp_b.get("linh_luc", 0)
    hoi_tam   += cp_b.get("hoi_tam", 0)    # điểm trực tiếp
    ho_tam    += cp_b.get("ho_tam", 0)     # điểm trực tiếp
    bao_kich  += cp_b.get("bao_kich", 0)   # % flat
    khang_bao += cp_b.get("khang_bao", 0)  # % flat
    # Cộng passive lớp 1 từ linh căn
    hoi_tam   += lc_p.get("hoi_tam",   0)
    ho_tam    += lc_p.get("ho_tam",    0)
    # THE_CHAT flat bonus
    hoi_tam   += st.get("tc_hoi_tam",   0)
    ho_tam    += st.get("tc_ho_tam",    0)
    bao_kich  += st.get("tc_bao_kich",  0.0)
    khang_bao += st.get("tc_khang_bao", 0.0)
    bao_kich  += lc_p.get("bao_kich",  0.0)
    khang_bao += lc_p.get("khang_bao", 0.0)
    # Sung thu BK/KB/HT/HoT buff
    st_b = st.get("st_b", {})
    bao_kich  += st_b.get("bao_kich",  0.0)
    khang_bao += st_b.get("khang_bao", 0.0)
    hoi_tam   += st_b.get("hoi_tam",   0)
    ho_tam    += st_b.get("ho_tam",    0)
    # ── Buff lớp 2 từ linh căn (hoi_tam, ho_tam, bao_kich, khang_bao) ──
    lc2 = _calc_linh_can_lop2(ts)
    hoi_tam   += lc2.get("hoi_tam",   0)
    ho_tam    += lc2.get("ho_tam",    0)
    bao_kich  += lc2.get("bao_kich",  0.0)
    khang_bao += lc2.get("khang_bao", 0.0)

    vd_pct = float(ts.get("van_dinh_all_stat_pct", 0.0) or 0.0)
    if vd_pct > 0:
        vd_mult = 1 + vd_pct / 100
        linh_luc = int(linh_luc * vd_mult)
        hoi_tam = int(hoi_tam * vd_mult)
        ho_tam = int(ho_tam * vd_mult)
        bao_kich = bao_kich * vd_mult
        khang_bao = khang_bao * vd_mult

    # ── Ý Cảnh effects (full stats) ──────────────────────────
    from cogs.views.y_canh import _get_y_canh, _tinh_effect
    ycanh_eff = _tinh_effect(_get_y_canh(ts))
    if ycanh_eff.get("linh_luc_pct"):
        linh_luc = int(linh_luc * (1 + ycanh_eff["linh_luc_pct"] / 100))
    if ycanh_eff.get("hoi_tam"):
        hoi_tam += int(st["at"] * ycanh_eff["hoi_tam"] / 100)
    if ycanh_eff.get("ho_tam"):
        ho_tam += int(st["df"] * ycanh_eff["ho_tam"] / 100)
    if ycanh_eff.get("bao_kich"):
        bao_kich += ycanh_eff["bao_kich"]
    if ycanh_eff.get("khang_bao"):
        khang_bao += ycanh_eff["khang_bao"]
    if ycanh_eff.get("crit_dmg"):
        pass  # used in combat formula, not stored in stat

    # ── Trận Đạo effects (full stats) ────────────────────────
    from utils.config import TRAN_DAO_BY_ID
    tran_id = ts.get("tran_dao_active", "")
    tran_cfg = TRAN_DAO_BY_ID.get(tran_id)
    if tran_cfg:
        for k, v in tran_cfg["buff"].items():
            if k == "linh_luc_pct":
                linh_luc = int(linh_luc * (1 + v / 100))
            elif k == "bao_kich":
                bao_kich += v
            elif k == "cd_giam":
                pass  # used in combat, not stored
        for k, v in tran_cfg["debuff"].items():
            if k == "bao_kich":
                bao_kich += v  # negative value

    # Giới hạn — cap SAU khi cộng tất cả
    bao_kich  = min(bao_kich, 75)
    khang_bao = min(khang_bao, 60)
    # drop_m / exp_m đã bao gồm lop2 từ _calc_stats — dùng trực tiếp
    return {**st,
            "linh_luc": linh_luc, "hoi_tam": hoi_tam, "ho_tam": ho_tam,
            "bao_kich": bao_kich / 100, "khang_bao": khang_bao / 100,
            "drop_m": st["drop_m"], "exp_m": st["exp_m"],
            "lc2": lc2}



# ══════════════════════════════════════════════════════════════
#  BI CANH HELPERS
# ══════════════════════════════════════════════════════════════
def _gen_rooms(bc: dict) -> list[dict]:
    """Tạo đúng 3 phòng: 2 phòng quái khác loại + 1 phòng boss.
    Đảm bảo 2 quái không trùng nhau nếu có ≥2 loại trong config.
    """
    rooms  = []
    thuong = bc["phong_thuong"]

    if len(thuong) >= 2:
        # Chọn 2 quái khác loại
        idx0 = random.randrange(len(thuong))
        choices_2 = [i for i in range(len(thuong)) if i != idx0]
        idx1 = random.choice(choices_2)
        picked = [{**thuong[idx0]}, {**thuong[idx1]}]
    else:
        picked = [{**thuong[0]}, {**thuong[0]}]

    for q in picked:
        sk = random.choice(SU_KIEN_BI_CANH) if random.random() < 0.4 else None
        rooms.append({"loai": "quai", "data": q, "su_kien": sk})
    rooms.append({"loai": "boss", "data": bc["boss"], "su_kien": None})
    return rooms

def _scale_rooms_by_rebirth(rooms: list[dict], so_lan_ts: int) -> list[dict]:
    """Scale HP/ATK/DEF của quái theo số lần trùng sinh."""
    if so_lan_ts <= 0:
        return rooms
    from utils.config import monster_scale
    m = monster_scale(so_lan_ts)
    for room in rooms:
        d = room["data"]
        d["hp"] = int(d["hp"] * m)
        d["at"] = int(d["at"] * m)
        if "df" in d:
            d["df"] = int(d["df"] * m)
    return rooms

def _apply_event(s: BiCanhSession, sk: dict) -> str:
    """Áp dụng sự kiện ngẫu nhiên vào session sau khi thắng phòng quái.
    Trả về chuỗi mô tả hiệu ứng (rỗng nếu không xử lý được).
    """
    loai = sk["loai"]
    if loai == "reward":
        if sk.get("lt_bonus") and s.lt_tich > 0:
            b = int(s.lt_tich * sk["lt_bonus"]); s.lt_tich += b
            return f"{E_LINH_THACH} +{fmt(b)} LT *(+{int(sk['lt_bonus']*100)}%)*"
        if sk.get("hp_bonus"):
            h = int(s.ts["hp_max"] * sk["hp_bonus"])
            s.hp_hien = min(s.ts["hp_max"], s.hp_hien + h)
            return f"{E_SINH_LUC} +{h} HP"
        if sk.get("exp_bonus") and s.exp_tich > 0:
            b = int(s.exp_tich * sk["exp_bonus"]); s.exp_tich += b
            return f"{E_TU_VI} +{fmt(b)} Tu vi *(+{int(sk['exp_bonus']*100)}%)*"
    elif loai == "trap":
        parts = []
        if sk.get("hp_mat"):
            m = int(s.ts["hp_max"] * sk["hp_mat"])
            s.hp_hien = max(1, s.hp_hien - m)
            parts.append(f"{E_SINH_LUC} -{m} HP")
        if sk.get("lt_mat") and s.lt_tich > 0:
            m = int(s.lt_tich * sk["lt_mat"])
            s.lt_tich = max(0, s.lt_tich - m)
            parts.append(f"{E_LINH_THACH} -{fmt(m)} LT")
        return " | ".join(parts)
    elif loai == "combat_bonus":
        # Linh thú lang thang: thưởng nguyên liệu ngẫu nhiên
        import random as _r
        nl_id = str(_r.randint(0, 2))  # nguyên liệu thấp cấp (0-2)
        amt   = _r.randint(1, 3)
        s.nl_tich[nl_id] = s.nl_tich.get(nl_id, 0) + amt
        return f"📦 +{amt} nguyên liệu"
    return ""



# ══════════════════════════════════════════════════════════════
#  EMBED BUILDERS
# ══════════════════════════════════════════════════════════════
async def _send_hoso_embed(inter_or_msg, embed, view, ts, *, followup=False, edit=False):
    """Gửi/edit embed hồ sơ (không kèm banner — banner đã bị loại bỏ)."""
    if followup:
        return await safe_followup(inter_or_msg, embed=embed, view=view)
    elif edit:
        await inter_or_msg.response.defer()
        return await inter_or_msg.edit_original_response(embed=embed, attachments=[], view=view)
    else:
        return await inter_or_msg.response.send_message(embed=embed, view=view, ephemeral=True)

def _embed_hoso(ts: dict[str, Any], user: discord.User, is_own: bool = True) -> discord.Embed:
    cg  = get_cg(ts["canh_gioi"])
    st  = _calc_stats(ts)

    danh_hieu = ts.get("danh_hieu_hien", "") or "*(chưa có)*"
    gioi_tinh = ts.get("gioi_tinh", "") or "*(chưa điền)*"
    tuoi      = ts.get("tuoi", 0)
    so_thich  = ts.get("so_thich", "") or "*(chưa điền)*"
    tuoi_str  = f"{tuoi}" if tuoi else "*(chưa điền)*"

    # Thể chất
    the_chat_id  = ts.get("the_chat", "")
    tc_data      = THE_CHAT_BY_ID.get(the_chat_id) if the_chat_id else None
    the_chat_str = f"{tc_data['emoji']} **{tc_data['ten']}**" if tc_data else "*(chưa xác định)*"

    # Linh căn sở hữu — mỗi loại unique 1 lần
    lc_ids = ts.get("linh_can_so_huu", [])
    lc_ids_unique = list(dict.fromkeys(lc_ids))  # deduplicate phòng data cũ
    if lc_ids_unique:
        lc_str = "  ".join(
            f"{LINH_CAN_BY_ID[i]['emoji']} {LINH_CAN_BY_ID[i]['ten']}"
            for i in lc_ids_unique if i in LINH_CAN_BY_ID
        )
    else:
        lc_str = "*(chưa có)*"

    so_lan_trung_sinh = ts.get("so_lan_trung_sinh", 0)
    trung_sinh_str = f"🔄 **Đã trùng sinh:** {so_lan_trung_sinh} lần" if so_lan_trung_sinh > 0 else ""

    lines = [
        f"**Tên:** {ts['dao_hieu']}",
        f"**Cảnh giới:** {get_cg_ten(ts['canh_gioi'], ts['cap_nho'])}",
        f"**Thể chất:** {the_chat_str}",
        f"**Linh căn:** {lc_str}",
        f"**Danh hiệu:** {danh_hieu}",
        f"**Giới tính:** {gioi_tinh}",
        f"**Tuổi:** {tuoi_str}",
        f"**Sở thích:** {so_thich}",
        f"{E_TU_VI} **Tu vi:** {fmt(ts['exp'])}",
        f"**Linh thạch:** {fmt(ts['linh_thach'])} {E_TT_LINH_THACH}",
        f"**Hệ số phần thưởng:** x{st['lt_m']}",
    ]
    if trung_sinh_str:
        lines.insert(2, trung_sinh_str)

    title = "Hồ sơ của bạn" if is_own else f"Hồ sơ của {ts['dao_hieu']}"
    embed = discord.Embed(title=title, description="\n".join(lines), color=cg["mau"])
    embed.set_thumbnail(url=user.display_avatar.url)

    # ── Công pháp active + tổng passive từ tất cả CP đã học ──
    from cogs.cong_phap import get_cp_active, get_cps_owned, _cp_emoji, PHAM_DMG_MULT
    cp_active  = get_cp_active(ts)
    owned_cps  = get_cps_owned(ts)
    if owned_cps:
        cp_b = calc_cp_bonus(ts)
        active_line = (
            f"{_cp_emoji(cp_active['cap'], cp_active['pham'])} **{cp_active['ten']}**"
            f" ×{PHAM_DMG_MULT[cp_active['pham']]} ⚡"
            if cp_active else "*(chưa chọn active)*"
        )
        passive_parts = []
        if cp_b.get("at_pct"):  passive_parts.append(f"{E_CONG_KICH} ATK +{cp_b['at_pct']:.2g}%")
        if cp_b.get("def_pct"): passive_parts.append(f"{E_PHONG_NGU} DEF +{cp_b['def_pct']:.2g}%")
        if cp_b.get("hp_pct"):  passive_parts.append(f"{E_SINH_LUC} HP +{cp_b['hp_pct']:.2g}%")
        if cp_b.get("linh_luc"):passive_parts.append(f"{E_LINH_LUC} LL +{fmt(cp_b['linh_luc'])}")
        if cp_b.get("hoi_tam"): passive_parts.append(f"{E_HOI_TAM} HT +{fmt(cp_b['hoi_tam'])}đ")
        if cp_b.get("ho_tam"):  passive_parts.append(f"{E_HO_TAM} HoT +{fmt(cp_b['ho_tam'])}đ")
        if cp_b.get("bao_kich"):passive_parts.append(f"{E_BAO_KICH} BK +{cp_b['bao_kich']:.3g}%")
        if cp_b.get("khang_bao"):passive_parts.append(f"{E_KHANG_BAO} KB +{cp_b['khang_bao']:.3g}%")
        cp_field = (
            f"Active: {active_line}\n"
            f"Đã học: **{len(owned_cps)}** công pháp\n"
            + ("  ".join(passive_parts) if passive_parts else "*(chưa có passive)*")
        )
        embed.add_field(name="📚 Công Pháp", value=cp_field, inline=False)

    # ── Linh căn sở hữu + tổng passive ──────────────────────
    lc_ids_e = ts.get("linh_can_so_huu", [])
    lc_ids_unique_e = list(dict.fromkeys(lc_ids_e))  # deduplicate phòng data cũ
    if lc_ids_unique_e:
        lc_p = _calc_linh_can_passive(ts)
        lc_names = "  ".join(
            f"{LINH_CAN_BY_ID[i]['emoji']} **{LINH_CAN_BY_ID[i]['ten']}**"
            for i in lc_ids_unique_e if i in LINH_CAN_BY_ID
        )
        lc_passive_parts = []
        if lc_p.get("at_flat"):   lc_passive_parts.append(f"{E_CONG_KICH} ATK +{lc_p['at_flat']}")
        if lc_p.get("at_pct"):    lc_passive_parts.append(f"{E_CONG_KICH} ATK +{lc_p['at_pct']:.1f}%")
        if lc_p.get("df_flat"):   lc_passive_parts.append(f"{E_PHONG_NGU} DEF +{lc_p['df_flat']}")
        if lc_p.get("def_pct"):   lc_passive_parts.append(f"{E_PHONG_NGU} DEF +{lc_p['def_pct']:.1f}%")
        if lc_p.get("hp_flat"):   lc_passive_parts.append(f"{E_SINH_LUC} HP +{lc_p['hp_flat']}")
        if lc_p.get("hp_pct"):    lc_passive_parts.append(f"{E_SINH_LUC} HP +{lc_p['hp_pct']:.1f}%")
        if lc_p.get("hoi_tam"):   lc_passive_parts.append(f"{E_HOI_TAM} HT +{lc_p['hoi_tam']}đ")
        if lc_p.get("ho_tam"):    lc_passive_parts.append(f"{E_HO_TAM} HoT +{lc_p['ho_tam']}đ")
        if lc_p.get("bao_kich"):  lc_passive_parts.append(f"{E_BAO_KICH} BK +{lc_p['bao_kich']:.3g}%")
        if lc_p.get("khang_bao"): lc_passive_parts.append(f"{E_KHANG_BAO} KB +{lc_p['khang_bao']:.3g}%")
        if lc_p.get("drop_rate"): lc_passive_parts.append(f"🍀 Drop +{lc_p['drop_rate']:.3g}%")
        if lc_p.get("exp_pct"):   lc_passive_parts.append(f"{E_TU_VI} TV +{lc_p['exp_pct']:.3g}%")
        cur_cg   = ts.get("canh_gioi", 0)
        next_cg  = cur_cg + 1
        diem_yc  = LINH_CAN_DIEM_YEU_CAU.get(next_cg, 0)
        lc_diem  = ts.get("linh_can_diem", {})
        cg_names_lc = ["Luyện Khí","Trúc Cơ","Kết Tinh","Kim Đan","Cụ Linh",
                        "Nguyên Anh","Hóa Thần","Ngộ Đạo","Vũ Hóa","Đăng Tiên"]
        diem_parts = []
        if diem_yc > 0 and lc_ids_unique_e:
            for _id in lc_ids_unique_e:
                _lc2 = LINH_CAN_BY_ID.get(_id)
                if not _lc2: continue
                _d    = lc_diem.get(_id, 0)
                _ok   = _d >= diem_yc
                _mark = "✅" if _ok else f"**{_d}/{diem_yc}đ** ({min(99,int(_d/diem_yc*100))}%)"
                diem_parts.append(f"{_lc2['emoji']} {_mark}")
            next_cg_name = cg_names_lc[next_cg] if next_cg < len(cg_names_lc) else f"CG{next_cg}"
            diem_str = f"\n🔒 Đột phá → {next_cg_name}: {'  '.join(diem_parts)}"
        elif not diem_yc and lc_ids_unique_e:
            diem_str = "\n✅ Đã đạt cảnh giới tối đa"
        else:
            diem_str = ""
        lc_field_1 = (
            f"Sở hữu: **{len(lc_ids_unique_e)}** linh căn\n{lc_names}\n"
            + ("  ".join(lc_passive_parts) if lc_passive_parts else "*(chưa có passive)*")
        )
        if len(lc_field_1) > 1024:
            lc_field_1 = lc_field_1[:1020] + "..."
        embed.add_field(name="🌟 Linh Căn", value=lc_field_1, inline=False)
        if diem_str:
            diem_field = diem_str.lstrip("\n")
            if len(diem_field) > 1024:
                diem_field = diem_field[:1020] + "..."
            embed.add_field(name="🔒 Yêu Cầu Đột Phá", value=diem_field, inline=False)
        # Buff lớp 2 đã tích lũy
        _lop2 = _calc_linh_can_lop2(ts)
        if _lop2:
            _L2_LABEL = {
                "hoi_tam": f"{E_HOI_TAM} Hội Tâm", "ho_tam": f"{E_HO_TAM} Hộ Tâm",
                "bao_kich": f"{E_BAO_KICH} Bạo Kích", "khang_bao": f"{E_KHANG_BAO} Kháng Bạo",
                "drop_rate": "🍀 Drop", "exp_pct": f"{E_TU_VI} Tu Vi",
            }
            l2_parts = []
            for k, v in _lop2.items():
                if not v: continue
                lbl = _L2_LABEL.get(k, k)
                if "pct" in k or k in ("bao_kich", "khang_bao", "drop_rate"):
                    l2_parts.append(f"{lbl} **+{round(v,2)}%**")
                else:
                    l2_parts.append(f"{lbl} **+{int(v)}**")
            if l2_parts:
                embed.add_field(
                    name="✨ Buff Lớp 2 Tích Lũy",
                    value="  ".join(l2_parts),
                    inline=False)
            # Hiển thị note về linh căn có buff lớp 2 dạng base stat (ATK/DEF/HP)
            _BASE_LABEL = {"at_pct": "ATK", "def_pct": "DEF", "hp_pct": "HP"}
            _BASE_FIELDS = {"at_pct", "def_pct", "hp_pct"}
            _LOC2_FIELDS = {"hoi_tam","ho_tam","bao_kich","khang_bao","drop_rate","exp_pct"}
            base_note_parts = []
            for _lc_id2 in lc_ids_unique_e:
                _lc2 = LINH_CAN_BY_ID.get(_lc_id2)
                if not _lc2: continue
                _dpb = _lc2.get("dot_pha_buff", {})
                _base = {k:v for k,v in _dpb.items() if k in _BASE_FIELDS}
                _lop2 = {k:v for k,v in _dpb.items() if k in _LOC2_FIELDS}
                if _base:
                    _parts = [f"{_BASE_LABEL[k]}+{v}%" for k,v in _base.items()]
                    base_note_parts.append(f"{_lc2['emoji']} {_lc2['ten']}: {', '.join(_parts)}/lần ĐP")
            if base_note_parts:
                embed.add_field(
                    name="📊 Buff Lớp 2 Đã Cộng Vào Chỉ Số Cơ Bản",
                    value="\n".join(base_note_parts) + "\n**(Đã nằm trong ATK/DEF/HP — không hiện riêng)**",
                    inline=False)

    return embed


def _embed_tu_luyen(ts: dict[str, Any], user: discord.User) -> discord.Embed:
    """Embed tab Tu Luyện — Thức Hải phong cách"""
    cg  = get_cg(ts["canh_gioi"])
    st  = _calc_stats(ts)

    embed = discord.Embed(title="✨ THỨC HẢI TU LUYỆN", color=cg["mau"])
    embed.set_author(name=ts["dao_hieu"], icon_url=user.display_avatar.url)

    # Quote từ sở thích nếu có, không thì dùng câu mặc định
    quote = ts.get("so_thich") or "Tu luyện là con đường duy nhất dẫn đến đỉnh cao."
    embed.description = (
        f"*\"{quote}\"* {ts['dao_hieu']} khẽ nói.\n\n"
        "Đạo hữu tiến vào thức hải. Tiên tử hiện thân trong linh quang, "
        "dẫn dắt linh lực vận chuyển chu thiên"
    )

    # Cảnh giới + Tu vi
    ec = exp_can_thiet(ts["canh_gioi"], ts["cap_nho"])
    tong_tu_vi = ts.get("tong_tu_vi", 0) + ts["exp"]

    # Tính % tràn tu vi
    tran_pct_str = ""
    if ec > 0 and ts["exp"] > ec:
        tran_pct = int((ts["exp"] - ec) / ec * 100)
        tran_pct_str = f" *(tràn {tran_pct}%)*"

    embed.add_field(name="Cảnh Giới Hiện Tại", value=f"{cg['emoji']} {get_cg_ten(ts['canh_gioi'], ts['cap_nho'])}", inline=True)
    embed.add_field(name="📜 Tổng Tu Vi",       value=f"{fmt(tong_tu_vi)} Tu vi", inline=True)
    embed.add_field(name=f"{E_TU_VI} Tu Vi Hiện Có",       value=f"{fmt(ts['exp'])}{tran_pct_str}", inline=True)

    # Hệ số thưởng — st["lt_m"] đã = CG × thiên phú × tông môn
    cg_he_so = DIEM_DANH_HE_SO[min(ts["canh_gioi"], len(DIEM_DANH_HE_SO) - 1)]
    lc_he_so = 1.0  # Legacy: he_so đã được tích hợp vào cg_he_so
    he_so    = st["lt_m"]
    he_so_parts = [f"×{cg_he_so} cảnh giới"]
    tm_he_so = round(st["lt_m"] / cg_he_so, 2)
    if tm_he_so != 1.0: he_so_parts.append(f"×{tm_he_so} tông môn")
    embed.add_field(name="📊 Hệ Số Thưởng", value=f"**×{he_so}**\n_{' · '.join(he_so_parts)}_", inline=False)

    # Tiến độ đột phá
    next_cg_id  = ts["canh_gioi"] + 1
    next_cg_ten = CANH_GIOI[next_cg_id]["ten"] if next_cg_id < len(CANH_GIOI) else "Tối Đỉnh"
    pct = min(100, int(ts["exp"] / ec * 100)) if ec > 0 else 100

    # Tính tỉ lệ đột phá thành công
    fail_base  = min(0.10 + ts["canh_gioi"] * 0.10, 0.90)
    ty_le_base = 1.0 - fail_base
    tran_bonus = 0.0
    if ec > 0 and ts["exp"] > ec:
        so_lan_tran = int((ts["exp"] - ec) / (ec * 0.10))
        tran_bonus  = min(so_lan_tran * 0.02, 0.45)
    ty_le_hien = min(1.0, ty_le_base + tran_bonus)

    ty_le_str = f"**{int(ty_le_base*100)}%** cơ bản"
    if tran_bonus > 0:
        ty_le_str += f" + **{int(tran_bonus*100)}%** tràn = **{int(ty_le_hien*100)}%**"

    embed.add_field(
        name=f"Tiến Độ Đột Phá: {next_cg_ten}",
        value=(
            f"`{bar(ts['exp'], ec)}` {pct}%\n"
            f"*(Yêu cầu: {fmt(ec)} {E_TU_VI})*\n"
            f"⚡ Tỉ lệ thành công: {ty_le_str}"
        ),
        inline=False)

    # Nguyên liệu đột phá — đan tương ứng với cảnh giới + cấp nhỏ hiện tại
    def _dan_phu_hop(d):
        if d.get("cg_yeu_cau") != ts["canh_gioi"]:
            return False
        cap_nho_yc = d.get("cap_nho_yeu_cau", None)
        if cap_nho_yc is not None and cap_nho_yc != ts["cap_nho"]:
            return False
        # Đan thường (không có cap_nho_yeu_cau): chỉ hiện khi đang ở Hậu Kì (cap=max)
        if cap_nho_yc is None:
            max_cap = CANH_GIOI[ts["canh_gioi"]]["cap"]
            if ts["cap_nho"] != max_cap:
                return False
        return True

    dot_pha_dan = next((d for d in DAN_DUOC if _dan_phu_hop(d)), None)
    if dot_pha_dan:
        so_luong   = ts["dan_duoc"].get(str(dot_pha_dan["id"]), 0)
        trang_thai = "✅ Đã có" if so_luong > 0 else "❌ Chưa có"
        embed.add_field(
            name="Nguyên Liệu Yêu Cầu",
            value=f"{dot_pha_dan['emoji']} {dot_pha_dan['ten']}\nTrạng thái: {trang_thai}",
            inline=False)

    # Điểm linh căn — chỉ hiện khi Hậu Kì (sắp đột phá đại cảnh)
    max_cap   = CANH_GIOI[ts["canh_gioi"]]["cap"]
    la_hau_ki = (ts["cap_nho"] >= max_cap)
    lc_ids_tl = ts.get("linh_can_so_huu", [])
    if lc_ids_tl and la_hau_ki:
        next_cg_lc = ts["canh_gioi"] + 1
        diem_yc_lc = LINH_CAN_DIEM_YEU_CAU.get(next_cg_lc, 0)
        lc_diem_tl = ts.get("linh_can_diem", {})
        CG_NAMES_TL = ["Luyện Khí","Trúc Cơ","Kết Tinh","Kim Đan","Cụ Linh",
                       "Nguyên Anh","Hóa Thần","Ngộ Đạo","Vũ Hóa","Đăng Tiên"]
        if diem_yc_lc > 0:
            lc_lines = []
            all_ok   = True
            for _id in lc_ids_tl:
                _lc2 = LINH_CAN_BY_ID.get(_id)
                if not _lc2: continue
                _d  = lc_diem_tl.get(_id, 0)
                _ok = _d >= diem_yc_lc
                if not _ok: all_ok = False
                pct_str = "100%" if _ok else (str(min(99, int(_d / diem_yc_lc * 100))) + "%")
                mark = "✅" if _ok else ("**" + str(_d) + "/" + str(diem_yc_lc) + "đ** (" + pct_str + ")")
                lc_lines.append(_lc2["emoji"] + " " + mark)
            next_name = CG_NAMES_TL[next_cg_lc] if next_cg_lc < len(CG_NAMES_TL) else ("CG" + str(next_cg_lc))
            status_lc = "✅ Đủ điều kiện đột phá!" if all_ok else "❌ Chưa đủ điểm — không thể đột phá đại cảnh!"
            embed.add_field(
                name="🌟 Linh Căn — Đột Phá " + next_name + " (cần " + str(diem_yc_lc) + "đ/căn)",
                value="  ".join(lc_lines) + "\n" + status_lc,
                inline=False)

    embed.set_footer(text="⚡ Tu Luyện | " + ts["dao_hieu"])
    return embed

def _embed_hanh_dong(ts: dict[str, Any], user: discord.User) -> discord.Embed:
    now = int(time.time())
    embed = discord.Embed(title=f"{E_CONG_KICH}  HÀNH ĐỘNG", color=0xFF6B35)
    embed.set_author(name=ts["dao_hieu"], icon_url=user.display_avatar.url)
    tl_hien   = get_the_luc(ts)
    tran_hien = get_tran_the_luc(ts)
    cds = [
        ("⚡ Tu Luyện",   ts["cd_tu_luyen"]  + CD_TU_LUYEN   - now),
        ("💥 Đột Phá (CD thất bại)", ts["cd_dot_pha"] + CD_DOT_PHA - now),
        ("⛏️ Khai Hoang", ts["cd_khai_hoang"]+ CD_KHAI_HOANG - now),
        ("📅 Điểm Danh",  diem_danh_cd_con_lai(ts.get("cd_diem_danh", 0), now)),
    ]
    for name, cd in cds:
        embed.add_field(name=name, value="✅ Sẵn sàng!" if cd <= 0 else fmt_cd(cd), inline=True)
    embed.add_field(name="⚡ Thể Lực", value=f"{tl_hien}/{the_luc_toi_da(ts.get('canh_gioi', 0))} 🔋{tran_hien}/{TRAN_THE_LUC_MAX}", inline=True)
    embed.add_field(name="🔥 Chiến Lực", value=fmt(_calc_stats(ts)["cl"]), inline=True)
    embed.set_footer(text="⚔️ Tab Hành Động")
    return embed

def _build_inventory(ts: dict[str, Any]) -> list[dict]:
    """Gom tất cả vật phẩm đang sở hữu thành list có mô tả rõ ràng."""
    items = []

    # ── Đan dược đột phá (từ shop) ─────────────────────────────
    for k, v in ts["dan_duoc"].items():
        if k.startswith("dtl:"):
            parts = k[4:].split(":", 2)
            if len(parts) == 3 and v > 0:
                cg_id, cap_nho_sau, ten = int(parts[0]), int(parts[1]), parts[2]
                emoji = ""
                ki_names = {1: "Sơ Kì", 2: "Trung Kì", 3: "Hậu Kì"}
                cg_ten = CANH_GIOI[cg_id]["ten"] if 0 <= cg_id < len(CANH_GIOI) else "?"
                gia_dtl = 0
                if 0 <= cg_id < len(DAN_TU_LUYEN):
                    for d in DAN_TU_LUYEN[cg_id]:
                        if d["ten"] == ten and d["cap_nho_sau"] == cap_nho_sau:
                            emoji = d["emoji"]
                            gia_dtl = d.get("gia", 0)
                            break
                ki_yc  = ki_names.get(cap_nho_sau - 1, "?")
                ki_sau = ki_names.get(cap_nho_sau, "?")
                mo_ta = (
                    f"📍 Dùng khi đang ở **{cg_ten} {ki_yc}** → lên **{ki_sau}**\n"
                    f"{E_LINH_THACH} Giá thị trường: **{fmt(gia_dtl)} LT** — Bán shop: **{fmt(int(gia_dtl*0.6))} LT**"
                )
                items.append({"ten": ten, "emoji": emoji,
                              "so_luong": v, "mo_ta": mo_ta, "loai": "Đan Tu Luyện",
                              "_dtl_key": k, "_dtl_gia": gia_dtl})
            continue
        idx = int(k) if k.lstrip("-").isdigit() else -1
        if idx < 0 or idx >= len(DAN_DUOC) or v <= 0:
            continue
        d = DAN_DUOC[idx]
        cg_yc  = CANH_GIOI[d["cg_yeu_cau"]]["ten"] if d.get("cg_yeu_cau", -1) >= 0 else ""
        cg_sau = CANH_GIOI[d["cg_sau"]]["ten"]      if d.get("cg_sau", 99) < len(CANH_GIOI) else ""
        gia_dd = d.get("gia", 0)
        gia_ban_lai = int(gia_dd * 0.6)
        mo_ta  = (f"📍 Đột phá từ **{cg_yc}** lên **{cg_sau}**" if cg_yc and cg_sau else d.get("mo_ta", ""))
        if gia_dd > 0:
            mo_ta += "\n" + f"{E_LINH_THACH} Giá gốc: **{fmt(gia_dd)} LT** — Bán shop: **{fmt(gia_ban_lai)} LT**"
        items.append({"ten": d["ten"], "emoji": d["emoji"],
                      "so_luong": v, "mo_ta": mo_ta, "loai": "Đan Dược",
                      "_dd_id": idx, "_dd_gia": gia_dd})

    # ── Nguyên liệu ─────────────────────────────────────────────
    for k, v in ts["nguyen_lieu"].items():
        if not k.lstrip("-").isdigit():
            continue
        idx = int(k)
        if idx < len(NGUYEN_LIEU) and v > 0:
            n = NGUYEN_LIEU[idx]
            mo_ta = f"{E_LINH_THACH} Giá shop: **{fmt(n['gia'])} LT/cái** — Nguyên liệu craft & nâng cấp"
            items.append({"ten": n["ten"], "emoji": n["emoji"],
                          "so_luong": v, "mo_ta": mo_ta, "loai": "Nguyên Liệu",
                          "_nl_id": idx})

    # ── Pháp bảo ────────────────────────────────────────────────
    _pb_active_id_inv = ts.get("phap_bao_active", -1)
    for _pb_slot, pb_id in enumerate(ts.get("phap_bao", [])):
        p = PHAP_BAO_BY_ID.get(pb_id)
        if not p: continue
        pas = p.get("passive", {})
        pas_parts = []
        if pas.get("hp_pct"): pas_parts.append(f"HP +{pas['hp_pct']}%")
        if pas.get("at_pct"): pas_parts.append(f"ATK +{pas['at_pct']}%")
        if pas.get("df_pct"): pas_parts.append(f"DEF +{pas['df_pct']}%")
        cg_name = ["Luyện Khí","Trúc Cơ","Kết Tinh","Kim Đan","Cụ Linh",
                   "Nguyên Anh","Hóa Thần","Ngộ Đạo","Vũ Hóa"][p["canh_gioi"]]
        active_tag = " ⚡" if pb_id == _pb_active_id_inv else ""
        mo_ta = (
            f"{E_CONG_KICH} ATK +{p['at']}  {E_PHONG_NGU} DEF +{p['df']}\n"
            f"✨ Passive: {', '.join(pas_parts) if pas_parts else 'Không có'}\n"
            f"📍 Cảnh giới: **{cg_name}**"
        )
        items.append({"ten": p["ten"] + active_tag, "emoji": p["emoji"],
                      "so_luong": 1, "mo_ta": mo_ta, "loai": "Pháp Bảo",
                      "_pb_id": pb_id, "_pb_slot": _pb_slot,
                      "_active": pb_id == _pb_active_id_inv})

    # ── Linh quả ─────────────────────────────────────────────────
    for lq in LINH_QUA:
        lq_id = lq["id"]
        cnt   = ts.get("linh_qua", {}).get(lq_id, 0)
        if cnt <= 0: continue
        lc    = LINH_CAN_BY_ID.get(lq_id)
        diem_hien = ts.get("linh_can_diem", {}).get(lq_id, 0)
        # Tìm ngưỡng điểm lớp tiếp theo
        from utils.config import LINH_CAN_DIEM_YEU_CAU
        nguong_tiep = next((v for v in sorted(LINH_CAN_DIEM_YEU_CAU.values()) if v > diem_hien), None)
        can_dung = lq_id in ts.get("linh_can_so_huu", [])
        mo_ta = (
            f"🌿 Tăng **+{lq['diem']} điểm** {lc['ten'] if lc else lq_id} mỗi lần dùng\n"
            f"📊 Điểm hiện tại: **{diem_hien}đ**"
            + (f" / {nguong_tiep}đ (lớp tiếp)" if nguong_tiep else " *(tối đa)*")
            + ("\n⚠️ Chưa sở hữu linh căn này — không thể dùng" if not can_dung else "")
        )
        items.append({"ten": lq["ten"], "emoji": lq["emoji"],
                      "so_luong": cnt, "mo_ta": mo_ta,
                      "loai": "Linh Quả", "_lq_id": lq_id})

    # ── Mảnh linh căn ────────────────────────────────────────────
    manh = ts.get("manh_linh_can", {})
    for lq in LINH_QUA:
        lq_id = lq["id"]
        cnt   = manh.get(lq_id, 0)
        if cnt <= 0: continue
        lc       = LINH_CAN_BY_ID.get(lq_id)
        manh_emo = MANH_LINH_CAN_EMOJI.get(lq_id, lq["emoji"])
        ten      = f"Mảnh {lc['ten']}" if lc else f"Mảnh {lq_id}"
        ghep_duoc = cnt // 100
        con_lai   = cnt % 100
        mo_ta = (
            f"🔮 Tích lũy **100 mảnh** → ghép **{lc['ten'] if lc else lq_id}**\n"
            f"📊 Tiến độ: **{cnt}/100** mảnh"
            + (f" — có thể ghép **{ghep_duoc} lần** (còn {con_lai} mảnh)" if ghep_duoc > 0 else "")
            + f"\n{E_LINH_THACH} Bán shop: **{fmt(int(MANH_LINH_CAN_GIA.get(lq_id, 200) * 0.7))} LT/mảnh**"
        )
        items.append({"ten": ten, "emoji": manh_emo,
                      "so_luong": cnt, "mo_ta": mo_ta,
                      "loai": "Mảnh Linh Căn", "_lq_id": lq_id})

    # ── Tài nguyên đột phá thể chất ──────────────────────────────
    dtc_kho = ts.get("dotpha_tc_nl", {})
    if isinstance(dtc_kho, str):
        import json as _json
        try: dtc_kho = _json.loads(dtc_kho)
        except Exception: dtc_kho = {}
    for nl in DOTPHA_TC_NGUYEN_LIEU:
        cnt = dtc_kho.get(nl["id"], 0)
        if cnt <= 0: continue
        nguon_str = {"boss": "World Boss", "bi_canh": "Bí Cảnh",
                     "boss_bi_canh": "Boss & Bí Cảnh"}.get(nl["nguon"], nl["nguon"])
        mo_ta = f"🧬 Tài nguyên dùng để **đột phá thể chất**\n📍 Nguồn rơi: {nguon_str}"
        items.append({"ten": nl["ten"], "emoji": nl["emoji"],
                      "so_luong": cnt, "mo_ta": mo_ta,
                      "loai": "Nguyên Liệu ĐP TC", "_dtc_id": nl["id"]})
    return items


def _embed_kho_trang(ts: dict[str, Any], user: discord.User, items: list, trang: int,
                     tab_label: str = "📦 Tất Cả") -> discord.Embed:
    """Tạo embed túi đồ — hiện theo tab đang chọn, 5 item/trang."""
    embed = discord.Embed(color=0x2B2D31)
    embed.set_author(name=ts["dao_hieu"], icon_url=user.display_avatar.url)
    embed.description = f"**Linh thạch:** {fmt(ts['linh_thach'])} {E_TT_LINH_THACH}"

    if not items:
        embed.description += "\n\n*(Không có vật phẩm nào trong danh mục này)*"
        embed.set_footer(text=f"Tab: {tab_label}")
        return embed

    total      = len(items)
    total_page = max(1, (total + ITEMS_PER_PAGE - 1) // ITEMS_PER_PAGE)
    start      = trang * ITEMS_PER_PAGE
    page_items = items[start : start + ITEMS_PER_PAGE]

    embed.description += f"\n**{total}** vật phẩm trong danh mục này.\n\u200b"

    for item in page_items:
        mo_ta = item.get("mo_ta") or f"Phân loại: {item['loai']}"
        name  = f"{item['emoji']} {item['ten']} ×{item['so_luong']}"
        if item.get("_active"):
            name += " ⚡ **[Đang trang bị]**"
        embed.add_field(name=name, value=mo_ta, inline=False)

    embed.set_footer(text=f"Trang {trang + 1}/{total_page}  ·  Tab: {tab_label}  ·  {ts['dao_hieu']}")
    return embed


def _boss_current_window() -> tuple[int, int]:
    """Trả về (spawn_timestamp, next_spawn_timestamp) theo giờ VN."""
    now_vn = datetime.now(VN_TZ)
    today  = now_vn.replace(minute=0, second=0, microsecond=0)
    # Tìm giờ spawn gần nhất đã qua
    spawn_h = None
    for h in sorted(BOSS_SPAWN_HOURS_VN, reverse=True):
        if now_vn.hour >= h:
            spawn_h = h
            break
    if spawn_h is None:
        # Trước 00:00 → lấy spawn cuối hôm qua
        yesterday = today - timedelta(days=1)
        spawn_dt  = yesterday.replace(hour=BOSS_SPAWN_HOURS_VN[-1])
    else:
        spawn_dt  = today.replace(hour=spawn_h)

    # Next spawn
    next_h = None
    for h in sorted(BOSS_SPAWN_HOURS_VN):
        if h > now_vn.hour:
            next_h = h; break
    if next_h is None:
        next_dt = today.replace(hour=BOSS_SPAWN_HOURS_VN[0]) + timedelta(days=1)
    else:
        next_dt = today.replace(hour=next_h)

    return int(spawn_dt.timestamp()), int(next_dt.timestamp())


def _boss_is_active(state: dict | None) -> bool:
    """Boss còn sống trong vòng 1 tiếng kể từ spawn."""
    if not state or state.get("hp_hien", 0) <= 0:
        return False
    return (int(time.time()) - state["spawn_time"]) < BOSS_LIFETIME

def _embed_the_gioi(user: discord.User) -> discord.Embed:
    embed = discord.Embed(title="🌍  THẾ GIỚI", color=0xDC143C,
        description="Boss Raid • Phường Thị • Bảng Xếp Hạng")
    embed.set_author(name=user.display_name, icon_url=user.display_avatar.url)
    for boss in BOSS_THE_GIOI:
        embed.add_field(
            name=f"{boss['emoji']} {boss['ten']}",
            value=f"HP: **{fmt(boss['hp_max'])}**  |  Spawn: 00:00 · 06:00 · 12:00 · 18:00 (VN)",
            inline=False)
    embed.set_footer(text="🌍 Tab Thế Giới")
    return embed

# ══════════════════════════════════════════════════════════════
#  MAIN HOSO VIEW
# ══════════════════════════════════════════════════════════════
