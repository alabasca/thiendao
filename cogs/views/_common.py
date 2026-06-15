"""
Shared imports dùng chung cho tất cả views trong cogs/views/
"""
from __future__ import annotations

import discord
import asyncio
import random
import time
import logging
import os
from datetime import datetime, timezone, timedelta
from discord import app_commands
from typing import Optional

log = logging.getLogger("hoso")

from utils.config import (
    CANH_GIOI, LINH_CAN, LINH_CAN_BY_ID, LINH_CAN_CO_BAN, LINH_CAN_HIEM,
    LINH_QUA, LINH_QUA_BY_ID,
    LINH_QUA_DROP_CO_BAN,
    MANH_LINH_CAN_EMOJI, MANH_LINH_CAN_GIA,
    THE_CHAT, THE_CHAT_BY_ID, random_the_chat,
    TONG_MON, PHAP_BAO, PHAP_BAO_BY_ID, PHAP_BAO_BY_BASE, PHAP_BAO_SKILL,
    DAN_DUOC, DAN_TU_LUYEN, NGUYEN_LIEU, BI_CANH, BOSS_THE_GIOI,
    BOSS_SPAWN_HOURS_VN, boss_bar, BOSS_HP_BY_CG, emoji_hp_bar, BOSS_ANNOUNCE_CHANNEL_ID,
    DIEM_DANH_PHAN_THUONG, SU_KIEN_BI_CANH, BUFF_LABELS, DIEM_DANH_HE_SO,
    CD_TU_LUYEN, CD_DOT_PHA, CD_KHAI_HOANG, CD_DIEM_DANH,
    get_cg, get_cg_ten, bar, fmt, fmt_cd,
    exp_can_thiet, hp_max_cong_thuc, cong_cong_thuc, thu_cong_thuc,
    random_linh_can_co_ban,
)
from utils.embeds import e_loi, e_ok, e_warn, e_info, safe_followup, safe_defer
from utils.emoji_manager import get_stat_emoji
from utils.bot_emojis import (
    E_SINH_LUC, E_LINH_LUC, E_CONG_KICH, E_PHONG_NGU,
    E_LINH_THACH, E_TT_LINH_THACH, E_DAN_DUOC, E_TU_VI,
    E_HP_START, E_HP_MID, E_HP_END,
    E_HP_START_E, E_HP_MID_E, E_HP_END_E,
    E_LL_START, E_LL_MID, E_LL_END,
    E_LL_START_E, E_LL_MID_E, E_LL_END_E,
)
from cogs.cong_phap import CONG_PHAP, LOAI_CONG_PHAP, CongPhapView, calc_cp_bonus
from utils.database import (
    get_tu_si, create_tu_si, update_tu_si, add_linh_thach,
    get_bang_xep_hang,
    dang_ban, get_phien_cho, get_phien_cho_item, mua_phien_cho, cancel_phien_cho,
    has_nhan_thuong, mark_nhan_thuong,
    get_boss_state, upsert_boss, spawn_boss, add_boss_damage, get_boss_leaderboard,
    update_tu_si_wait,
    get_boss_message_id, save_boss_message_id, clear_boss_data, set_boss_end_time, set_boss_killer_atomic,
    get_the_luc, get_tran_the_luc, THE_LUC_MAX, THE_LUC_HOI, the_luc_toi_da,
    TRAN_THE_LUC_MAX, TRAN_THE_LUC_HOI,
    _enqueue,
    log_giao_dich,
    claim_first_hit_reward,
    transfer_dan_duoc_atomic,
    buy_phap_bao_atomic,
    get_quan_he, upsert_quan_he, set_quan_he_loai,
    get_tang_qua_hom_nay, add_tang_qua_log,
    get_boss_guild_messages, save_boss_guild_message, clear_boss_guild_messages,
)

# Import helpers từ hoso_utils và _session
from cogs.views._session import BiCanhSession, _bc_sessions
from cogs.hoso_utils import (
    _run_task,
    _back_to_hoso, _parse_emoji, _calc_stats, _calc_full_stats, _calc_linh_can_lop2,
    _gen_rooms, _apply_event,
    _send_hoso_embed, _embed_hoso, _embed_tu_luyen, _embed_hanh_dong,
    _build_inventory, _embed_kho_trang,
    _boss_current_window, _boss_is_active, _embed_the_gioi,
    VN_TZ, BOSS_LIFETIME, ITEMS_PER_PAGE,
)

# Force export private helpers (needed for 'import *')
__all__ = [
    # discord + stdlib
    'discord', 'asyncio', 'random', 'time', 'logging', 'os',
    'datetime', 'timezone', 'timedelta', 'app_commands', 'Optional',
    # config
    'CANH_GIOI','LINH_CAN','LINH_CAN_BY_ID','LINH_CAN_CO_BAN','LINH_CAN_HIEM',
    'LINH_QUA','LINH_QUA_BY_ID',
    'LINH_QUA_DROP_CO_BAN',
    'MANH_LINH_CAN_EMOJI','MANH_LINH_CAN_GIA',
    'THE_CHAT','THE_CHAT_BY_ID','random_the_chat',
    'TONG_MON','PHAP_BAO','PHAP_BAO_BY_ID','PHAP_BAO_BY_BASE','PHAP_BAO_SKILL',
    'DAN_DUOC','DAN_TU_LUYEN','NGUYEN_LIEU','BI_CANH','BOSS_THE_GIOI',
    'BOSS_SPAWN_HOURS_VN','boss_bar','BOSS_HP_BY_CG','emoji_hp_bar','BOSS_ANNOUNCE_CHANNEL_ID',
    'DIEM_DANH_PHAN_THUONG','SU_KIEN_BI_CANH','BUFF_LABELS','DIEM_DANH_HE_SO',
    'CD_TU_LUYEN','CD_DOT_PHA','CD_KHAI_HOANG','CD_DIEM_DANH',
    'get_cg','get_cg_ten','bar','fmt','fmt_cd',
    'exp_can_thiet','hp_max_cong_thuc','cong_cong_thuc','thu_cong_thuc',
    'random_linh_can_co_ban',
    # embeds helpers
    'e_loi','e_ok','e_warn','e_info',
    # emoji
    'get_stat_emoji',
    'E_SINH_LUC','E_LINH_LUC','E_CONG_KICH','E_PHONG_NGU',
    'E_LINH_THACH','E_TT_LINH_THACH','E_DAN_DUOC','E_TU_VI',
    'E_HP_START','E_HP_MID','E_HP_END',
    'E_HP_START_E','E_HP_MID_E','E_HP_END_E',
    'E_LL_START','E_LL_MID','E_LL_END',
    'E_LL_START_E','E_LL_MID_E','E_LL_END_E',
    # cong_phap
    'CONG_PHAP','LOAI_CONG_PHAP','CongPhapView','calc_cp_bonus',
    # database
    'get_tu_si','create_tu_si','update_tu_si','add_linh_thach',
    'get_bang_xep_hang',
    'dang_ban','get_phien_cho','get_phien_cho_item','mua_phien_cho','cancel_phien_cho',
    'has_nhan_thuong','mark_nhan_thuong',
    'get_boss_state','upsert_boss','spawn_boss','add_boss_damage','get_boss_leaderboard',
    'update_tu_si_wait',
    'get_boss_message_id','save_boss_message_id','clear_boss_data','set_boss_end_time','set_boss_killer_atomic',
    'get_the_luc','get_tran_the_luc','THE_LUC_MAX','THE_LUC_HOI','the_luc_toi_da','TRAN_THE_LUC_MAX','TRAN_THE_LUC_HOI',
    '_enqueue',
    'log_giao_dich',
    'claim_first_hit_reward',
    'transfer_dan_duoc_atomic',
    'buy_phap_bao_atomic',
    'get_quan_he','upsert_quan_he','set_quan_he_loai',
    'get_tang_qua_hom_nay','add_tang_qua_log',
    'get_boss_guild_messages','save_boss_guild_message','clear_boss_guild_messages',
    # hoso_utils
    'BiCanhSession','_bc_sessions','_run_task',
    '_back_to_hoso','_parse_emoji','_calc_stats','_calc_full_stats','_calc_linh_can_lop2',
    '_gen_rooms','_apply_event',
    '_send_hoso_embed','_embed_hoso','_embed_tu_luyen','_embed_hanh_dong',
    '_build_inventory','_embed_kho_trang',
    '_boss_current_window','_boss_is_active','_embed_the_gioi',
    'VN_TZ','BOSS_LIFETIME','ITEMS_PER_PAGE',
    'safe_edit_message',
    'safe_followup',
    'safe_defer',
]


# ── SSL/network retry helper ──────────────────────────────────
import asyncio as _asyncio
import aiohttp as _aiohttp
import ssl as _ssl


async def safe_edit_message(inter, *, embed=None, view=None, content=None, retries=2):
    """edit_message với retry khi gặp SSL/network error thoáng qua.
    Bắt NotFound (10015 Unknown Webhook / 10062 Unknown Interaction) — interaction đã expire,
    không raise lên để tránh spam error log.
    """
    kwargs = {}
    if embed   is not None: kwargs["embed"]   = embed
    if view    is not None: kwargs["view"]    = view
    if content is not None: kwargs["content"] = content
    for attempt in range(retries + 1):
        try:
            if inter.response.is_done():
                await inter.edit_original_response(**kwargs)
            else:
                await inter.response.edit_message(**kwargs)
            return True
        except (_aiohttp.ClientOSError, _ssl.SSLError, OSError) as e:
            if attempt < retries:
                await _asyncio.sleep(0.5 * (attempt + 1))
                continue
            log.warning(f"safe_edit_message network error after {retries} retries: {e}")
            return False
        except discord.NotFound as e:
            # 10015 = Unknown Webhook (interaction token expired)
            # 10062 = Unknown Interaction (interaction too old)
            if e.code in (10015, 10062):
                log.debug(f"safe_edit_message: interaction expired ({e.code}), skipping")
                return False
            raise
        except discord.HTTPException as e:
            # 50027 = Invalid Webhook Token
            if e.status == 401 or getattr(e, "code", 0) == 50027:
                log.debug(f"safe_edit_message: webhook token invalid, skipping")
                return False
            raise
