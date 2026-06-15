"""
boss_combat.py
══════════════════════════════════════════════════════
Auto-combat World Boss (10 hiệp) — thay thế flow spam skill cũ.

Flow:
  1. Người chơi bấm "⚔️ Tấn Công" trên message boss public
  2. Bot gửi ephemeral → chạy 10 hiệp auto combat (dùng CombatTaskCog)
  3. Sau 10 hiệp: cộng tổng damage vào boss DB, edit public message
  4. Cooldown 60s per user (lưu in-memory, reset khi bot restart)
  5. Không rớt nguyên liệu

Chỉ số boss = boss bí cảnh cùng cảnh giới × 15 (trừ HP, giữ nguyên từ BOSS_HP_BY_CG).
"""
from __future__ import annotations
from typing import Any

import asyncio
import random
import time
import logging

import discord

from cogs.views._common import (
    get_tu_si, update_tu_si, add_linh_thach,
    get_boss_state, upsert_boss, add_boss_damage, claim_first_hit_reward,
    set_boss_end_time, set_boss_killer_atomic,
    fmt, bar, get_cg,
    BOSS_THE_GIOI, BOSS_HP_BY_CG, BI_CANH,
    _boss_is_active, _calc_stats, _calc_full_stats,
    E_SINH_LUC, E_LINH_THACH, E_TU_VI,
    safe_followup, safe_defer,
)

log = logging.getLogger("boss_combat")

# ── Hệ số nhân chỉ số boss từ bí cảnh ─────────────────────────
BOSS_STAT_MULT = 3         # AT, DEF, HOI_TAM, BAO_KICH, HO_TAM, KHANG_BAO × 3
MAX_HIEP       = 10        # số hiệp tối đa mỗi lần đánh
COMBAT_CD_SECS = 60        # cooldown sau mỗi lần đánh (giây)
DELAY_PER_HIEP = 1.2       # giây delay giữa các hiệp khi animate

# ── In-memory CD: {user_id: last_attack_timestamp} ─────────────
_boss_atk_cd: dict[int, float] = {}
# NOTE: _boss_atk_cd là in-memory — reset về {} khi Railway redeploy.
# Hậu quả: user có thể đánh boss lần nữa ngay sau restart (1 lần, sau đó CD lại bình thường).
# Chấp nhận được ở scale hiện tại — không cần persist vào DB.
# ── CD timer tasks: {user_id: asyncio.Task} ─────────────────────
_boss_cd_tasks: dict[int, asyncio.Task] = {}

# ── Kỹ năng ────────────────────────────────────────────────────
SKILL_ORDER = ["than_thong", "tuyet_ky", "than_phap", "vo_ky"]
LOAI_CD     = {"vo_ky": 2, "than_phap": 3, "tuyet_ky": 4, "than_thong": 5}
LOAI_DMGM   = {"vo_ky": 1.0, "than_phap": 1.0, "tuyet_ky": 1.6, "than_thong": 2.5}
FALLBACK_SK  = {
    "vo_ky": "Quyền Cước", "than_phap": "Thân Pháp",
    "tuyet_ky": "Tuyệt Kỹ", "than_thong": "Thần Thông",
}


# ══════════════════════════════════════════════════════════════
#  LẤY STAT BOSS TỪ BÍ CẢNH
# ══════════════════════════════════════════════════════════════
def _get_boss_stat(canh_gioi: int) -> dict:
    """
    Lấy stat boss bí cảnh cùng cảnh giới (hoặc gần nhất) × BOSS_STAT_MULT.
    HP giữ nguyên từ BOSS_HP_BY_CG.
    """
    # BI_CANH[cg].boss nếu có, fallback về boss cuối cùng
    bc = None
    for b in reversed(BI_CANH):
        if b["id"] <= canh_gioi:
            bc = b
            break
    if bc is None:
        bc = BI_CANH[0]

    boss_bc = bc["boss"]
    m = BOSS_STAT_MULT

    return {
        "at":        int(boss_bc["at"]        * m),
        "df":        int(boss_bc.get("df", 0) * m),
        "hoi_tam":   int(boss_bc.get("hoi_tam", 0)   * m),
        "bao_kich":  boss_bc.get("bao_kich", 1.5),      # multiplier, không nhân
        "ho_tam":    int(boss_bc.get("ho_tam", 0)   * m),
        "khang_bao": min(0.90, boss_bc.get("khang_bao", 0) * m),
    }


# ══════════════════════════════════════════════════════════════
#  TÍNH TOÁN 10 HIỆP AUTO COMBAT (synchronous, chạy trong executor)
# ══════════════════════════════════════════════════════════════
def _compute_boss_combat(ts: dict[str, Any], boss_stat: dict, hp_boss_max: int, hp_boss_hien: int) -> list[tuple]:
    """
    Tính trước toàn bộ log 10 hiệp.
    Trả về list[(hiep, dmg_player, crit, skill_name, hp_boss_sau, hp_player_sau, log_line)]
    """
    from cogs.cong_phap import get_cp_active, PHAM_DMG_MULT, CAP_DMG_MULT, LOAI_SK

    # ── Stat người chơi ────────────────────────────────────────
    full_st    = _calc_full_stats(ts)
    at_p       = full_st.get("at",  ts["cong"])
    df_p       = full_st.get("df",  full_st.get("def", ts["thu"]))
    hp_max_p   = full_st.get("hp_eff", ts["hp_max"])  # HP tổng sau buff
    hp_p       = hp_max_p   # Luôn bắt đầu với full HP — ts["hp"] có thể thấp sau bí cảnh
    p_ht       = int(full_st.get("hoi_tam", ts.get("hoi_tam", 0)))
    bao_kich_f = full_st.get("bao_kich", ts.get("bao_kich", 0) / 100)
    ho_tam_p   = int(full_st.get("ho_tam", ts.get("ho_tam", 0)))
    khang_bao_p = full_st.get("khang_bao", ts.get("khang_bao", (3 + ts.get("canh_gioi", 0) * 2) / 100))

    # Hệ số công pháp
    cp_active  = get_cp_active(ts)
    pham_mult  = 1.0
    skill_names = {}
    skill_ll    = {}
    if cp_active:
        pham_mult = (PHAM_DMG_MULT.get(cp_active["pham"], 1.0)
                     * CAP_DMG_MULT.get(cp_active["cap"], 1.0))
        for loai in LOAI_SK:
            sk = cp_active["ky_nang"].get(loai)
            if sk:
                skill_names[loai] = sk["ten"]
                skill_ll[loai]    = sk.get("ll", 0)

    # ── Stat boss ──────────────────────────────────────────────
    q_at  = boss_stat["at"]
    q_df  = boss_stat["df"]
    q_ht  = boss_stat["hoi_tam"]
    q_bk  = boss_stat["bao_kich"]
    q_hmt = boss_stat["ho_tam"]
    q_kb  = boss_stat["khang_bao"]

    # Crit rate người chơi
    crit_rate_p = max(0.10, min(0.75, p_ht / 1000 + bao_kich_f))
    # Crit rate boss
    crit_rate_q = max(0.10, min(0.75, q_ht / 1000 + (q_bk - 1.0)))

    ll_max = ts.get("linh_luc", 100)
    ll_hien = ll_max
    ll_hoi  = max(1, ll_max // 20)

    skill_cd = {k: 0 for k in LOAI_SK}

    logs = []

    hp_b = hp_boss_hien

    for hiep in range(1, MAX_HIEP + 1):
        if hp_b <= 0:
            break
        if hp_p <= 0:   # player đã chết hiệp trước → dừng ngay
            break

        # ── Hồi LL ────────────────────────────────────────────
        ll_hien = min(ll_max, ll_hien + ll_hoi)

        # ── Giảm CD skill ──────────────────────────────────────
        for k in skill_cd:
            if skill_cd[k] > 0:
                skill_cd[k] -= 1

        # ── Chọn skill tốt nhất ────────────────────────────────
        chosen = "vo_ky"
        for sk in SKILL_ORDER:
            if skill_cd.get(sk, 0) == 0 and (sk in skill_names or sk == "vo_ky"):
                ll_cost = skill_ll.get(sk, 0)
                if ll_hien >= ll_cost:
                    chosen = sk
                    break

        ll_cost_c = skill_ll.get(chosen, 0)
        ll_hien = max(0, ll_hien - ll_cost_c)
        skill_cd[chosen] = LOAI_CD.get(chosen, 2)
        skill_name = skill_names.get(chosen, FALLBACK_SK.get(chosen, "Tấn Công"))

        # ── Damage người chơi → boss ───────────────────────────
        mul = LOAI_DMGM.get(chosen, 1.0) * pham_mult
        d_raw = max(1, int(at_p * mul * random.uniform(0.85, 1.15)))
        # Giảm theo phòng thủ boss (không quá 70%)
        df_reduce = min(0.70, q_df / (q_df + at_p * 2 + 1))
        d = max(1, int(d_raw * (1 - df_reduce)))
        # Crit
        crit_p = random.random() < crit_rate_p
        if crit_p:
            d = int(d * 2)
        hp_b = max(0, hp_b - d)

        # ── Damage boss → người chơi ───────────────────────────
        d_boss_raw = max(1, int(q_at * random.uniform(0.85, 1.15)))
        # Giảm theo phòng thủ người chơi (không quá 60%)
        df_reduce_p = min(0.60, df_p / (df_p + q_at + 1))
        d_boss = max(1, int(d_boss_raw * (1 - df_reduce_p)))
        # Boss crit → hộ tâm người chơi giảm crit nhận vào
        crit_q = random.random() < max(0.05, crit_rate_q - ho_tam_p / 1500)
        if crit_q:
            # Khang bạo giảm thiệt hại crit
            kb_reduce = min(0.80, khang_bao_p)
            d_boss = int(d_boss * q_bk * (1 - kb_reduce))
        hp_p = max(0, hp_p - d_boss)

        crit_tag  = " ⚡**Bạo Kích!**" if crit_p else ""
        bcrit_tag = " 💢" if crit_q else ""
        line = (
            f"**Hiệp {hiep}** — *{skill_name}*: **+{fmt(d)}**{crit_tag} "
            f"| Boss phản: **-{fmt(d_boss)}**{bcrit_tag}"
        )
        logs.append((hiep, d, crit_p, skill_name, hp_b, hp_p, line))

        if hp_p <= 0:
            break

    return logs


# ══════════════════════════════════════════════════════════════
#  EMBED KẾT QUẢ TỪNG HIỆP
# ══════════════════════════════════════════════════════════════
def _embed_boss_combat(
    user: discord.User,
    ts: dict[str, Any],
    logs: list,
    n_show: int,
    boss_cfg: dict,
    boss_stat: dict,
    hp_boss_max: int,
    hp_boss_start: int,
) -> discord.Embed:
    """Build embed hiệp thứ n_show."""
    shown = logs[:n_show]
    last  = shown[-1] if shown else None

    hp_b_now = last[4] if last else hp_boss_start
    hp_p_now = last[5] if last else ts["hp_max"]  # trước khi combat bắt đầu = full HP
    total_dmg = sum(l[1] for l in shown)

    cg_boss = boss_cfg.get("_cg_boss", 3)
    cg_obj  = get_cg(cg_boss)

    embed = discord.Embed(
        title=f"⚔️ CÔNG KÍCH {boss_cfg['ten'].upper()}",
        description=f"Cảnh giới: **{cg_obj['emoji']} {cg_obj['ten']}**",
        color=0xDC143C,
    )

    # HP bars
    embed.add_field(
        name=f"👹 {boss_cfg['ten']}",
        value=f"`{bar(hp_b_now, hp_boss_max)}` {fmt(hp_b_now)}/{fmt(hp_boss_max)}",
        inline=False,
    )
    embed.add_field(
        name=f"{E_SINH_LUC} HP của bạn",
        value=f"`{bar(hp_p_now, ts['hp_max'])}` {hp_p_now}/{ts['hp_max']}",
        inline=True,
    )
    embed.add_field(
        name="⚔️ Tổng sát thương",
        value=f"**{fmt(total_dmg)}**",
        inline=True,
    )

    # Log chiến đấu
    log_lines = [l[6] for l in shown[-5:]]  # 5 hiệp gần nhất
    embed.add_field(
        name=f"📜 Nhật Ký Chiến Đấu ({n_show}/{len(logs)} hiệp)",
        value="\n".join(log_lines) if log_lines else "...",
        inline=False,
    )

    if hp_p_now <= 0:
        embed.set_footer(text="💀 Bạn đã ngã xuống! Boss vẫn còn sống.")
    elif hp_b_now <= 0:
        embed.set_footer(text="🏆 Boss đã bị tiêu diệt! (đóng góp của bạn)")
    elif n_show >= len(logs):
        embed.set_footer(text=f"✅ Hoàn thành {len(logs)} hiệp! Damage đã cập nhật lên Boss.")
    else:
        embed.set_footer(text=f"⚔️ Hiệp {n_show}/{MAX_HIEP}...")

    embed.set_author(name=user.display_name, icon_url=user.display_avatar.url)
    return embed


# ══════════════════════════════════════════════════════════════
#  VIEW KẾT QUẢ SAU COMBAT
# ══════════════════════════════════════════════════════════════
class BossCombatDoneView(discord.ui.View):
    """View sau combat — nút Đánh Tiếp (disabled khi CD) + nút Đóng."""
    def __init__(self, actor_id: int, boss_id: int):
        super().__init__(timeout=120)
        self.actor_id = actor_id
        self.boss_id  = boss_id

    @discord.ui.button(label="⚔️ Đánh Tiếp", style=discord.ButtonStyle.danger, disabled=True)
    async def atk_again_btn(self, inter: discord.Interaction, btn: discord.ui.Button):
        if inter.user.id != self.actor_id:
            return await inter.response.send_message("❌", ephemeral=True)
        # Đóng ephemeral này và kích hoạt combat mới
        try:
            await inter.response.defer()
            await inter.delete_original_response()
        except discord.NotFound:
            pass
        except Exception:
            log.exception("Lỗi boss_combat")
        await do_boss_auto_combat(inter, self.boss_id)

    @discord.ui.button(label="✖ Đóng", style=discord.ButtonStyle.secondary)
    async def close_btn(self, inter: discord.Interaction, btn: discord.ui.Button):
        if inter.user.id != self.actor_id:
            return await inter.response.send_message("❌", ephemeral=True)
        try:
            await inter.response.defer()
            await inter.delete_original_response()
        except discord.NotFound:
            pass
        except Exception:
            log.exception("Lỗi boss_combat")


async def _run_boss_cd_timer(uid: int, msg: discord.Message,
                              embed_done: discord.Embed, view: BossCombatDoneView,
                              cd_end: float, boss_dead: bool = False) -> None:
    """Task đếm ngược CD và cập nhật embed + enable nút Đánh Tiếp khi hết."""
    try:
        while True:
            remaining = cd_end - time.time()
            if remaining <= 0:
                break
            secs = int(remaining)
            mins, s = divmod(secs, 60)
            cd_str = f"{mins}p {s:02d}s" if mins else f"{s}s"

            e = embed_done.copy()
            e.set_footer(text=f"⏳ Có thể đánh lại sau: {cd_str}")
            try:
                await msg.edit(embed=e, view=view)
            except discord.NotFound:
                return
            except Exception:
                log.exception("Lỗi boss_combat")
                return
            await asyncio.sleep(5)

        # Hết CD
        e_ready = embed_done.copy()
        if boss_dead:
            e_ready.set_footer(text="✅ Cooldown xong! Boss đã bị tiêu diệt.")
        else:
            # Enable nút Đánh Tiếp
            for item in view.children:
                if hasattr(item, 'label') and '⚔️' in (item.label or ''):
                    item.disabled = False
            e_ready.set_footer(text="✅ Cooldown xong! Bấm ⚔️ Đánh Tiếp để tiếp tục.")
        try:
            await msg.edit(embed=e_ready, view=view)
        except discord.NotFound:
            return
        except Exception:
            log.exception("Lỗi boss_combat")
    except asyncio.CancelledError:
        pass
    finally:
        _boss_cd_tasks.pop(uid, None)


# ══════════════════════════════════════════════════════════════
#  HÀM CHÍNH — gọi từ BossSpawnView
# ══════════════════════════════════════════════════════════════
async def do_boss_auto_combat(inter: discord.Interaction, boss_id: int) -> None:
    """
    Entry point: người chơi bấm "⚔️ Tấn Công" trên message boss.
    Gửi ephemeral riêng cho user, chạy 10 hiệp auto combat, cập nhật DB.
    """
    uid = inter.user.id

    # ── 1. Kiểm tra cooldown ────────────────────────────────────
    now_ts = time.time()
    last_atk = _boss_atk_cd.get(uid, 0)
    remaining = COMBAT_CD_SECS - (now_ts - last_atk)
    if remaining > 0:
        secs = int(remaining)
        try:
            await inter.response.send_message(
                f"⏳ Bạn vừa tấn công! Cooldown còn **{secs}s**.", ephemeral=True)
        except Exception:
            await safe_followup(inter, 
                f"⏳ Cooldown còn **{secs}s**.", ephemeral=True)
        return

    # ── 2. Defer ephemeral ──────────────────────────────────────
    if not await safe_defer(inter, ephemeral=True, thinking=True):
        return

    # ── 3. Lấy dữ liệu ─────────────────────────────────────────
    ts = await get_tu_si(uid)
    if not ts:
        return await safe_followup(inter, 
            "❌ Bạn chưa có hồ sơ tu sĩ! Dùng /hoso để tạo.", ephemeral=True)

    if boss_id < 0 or boss_id >= len(BOSS_THE_GIOI):
        return await safe_followup(inter, "❌ Boss không hợp lệ!", ephemeral=True)

    boss_cfg = BOSS_THE_GIOI[boss_id]
    state    = await get_boss_state(boss_id)

    if not _boss_is_active(state):
        if state and state.get("hp_hien", 1) <= 0:
            return await safe_followup(inter, 
                f"💀 **{boss_cfg['ten']}** đã bị tiêu diệt!", ephemeral=True)
        return await safe_followup(inter, 
            f"🌫️ **{boss_cfg['ten']}** đã rút lui! Hãy chờ đến đợt spawn tiếp theo.", ephemeral=True)

    cg_boss      = state.get("canh_gioi", boss_cfg["canh_gioi_pool"][0])
    hp_boss_max  = BOSS_HP_BY_CG.get(cg_boss, boss_cfg["hp_max"])
    hp_boss_hien = min(state["hp_hien"], hp_boss_max)
    boss_cfg     = dict(boss_cfg)
    boss_cfg["_cg_boss"] = cg_boss

    if hp_boss_hien <= 0:
        return await safe_followup(inter, 
            f"💀 **{boss_cfg['ten']}** đã bị tiêu diệt!", ephemeral=True)

    # ── 4. Set cooldown ngay để tránh double-click ──────────────
    _boss_atk_cd[uid] = now_ts
    # Dọn entries cũ tránh memory leak
    if len(_boss_atk_cd) > 500:
        cutoff = now_ts - COMBAT_CD_SECS * 2
        for u in [x for x, t in list(_boss_atk_cd.items()) if t < cutoff]:
            _boss_atk_cd.pop(u, None)
            _boss_cd_tasks.pop(u, None)

    # ── 5. Tính full stats một lần duy nhất (tránh double-buff) ──
    full_sync = _calc_full_stats(ts)
    # ts_display: dùng cho embed — hp_max và hp hiển thị đúng với buffed HP
    # ts gốc được giữ nguyên để _compute_boss_combat tự gọi _calc_full_stats từ base stats
    ts_display = {
        **ts,
        "cong":      full_sync["at"],
        "thu":       full_sync["df"],
        "hp_max":    full_sync["hp_eff"],
        "hp":        full_sync["hp_eff"],   # HP đầu combat = full buffed HP
        "linh_luc":  full_sync["linh_luc"],
        "hoi_tam":   full_sync["hoi_tam"],
        "ho_tam":    full_sync["ho_tam"],
        "bao_kich":  full_sync["bao_kich"],
        "khang_bao": full_sync["khang_bao"],
    }

    # ── 6. Tính combat (blocking, chạy trong thread pool) ───────
    boss_stat = _get_boss_stat(cg_boss)
    loop = asyncio.get_event_loop()
    logs = await loop.run_in_executor(
        None, _compute_boss_combat, ts, boss_stat, hp_boss_max, hp_boss_hien)

    if not logs:
        return await safe_followup(inter, "❌ Không thể tính toán chiến đấu!", ephemeral=True)

    total_dmg = sum(l[1] for l in logs)

    # ── 6. Gửi embed đầu tiên → lấy message để edit ─────────────
    embed_0 = _embed_boss_combat(
        inter.user, ts_display, logs, 1, boss_cfg, boss_stat, hp_boss_max, hp_boss_hien)
    done_view = BossCombatDoneView(uid, boss_id)

    try:
        msg = await safe_followup(inter, embed=embed_0, view=done_view, ephemeral=True)
    except Exception as e:
        log.error(f"[BossCombat] send failed: {e}")
        return

    # ── 7. Animate từng hiệp ────────────────────────────────────
    for n in range(2, len(logs) + 1):
        await asyncio.sleep(DELAY_PER_HIEP)
        emb = _embed_boss_combat(
            inter.user, ts_display, logs, n, boss_cfg, boss_stat, hp_boss_max, hp_boss_hien)
        try:
            await msg.edit(embed=emb, view=done_view)
        except Exception:
            break

    # ── 8. Cập nhật DB (atomic) ──────────────────────────────────────────
    # set_boss_killer_atomic dùng FOR UPDATE lock để đảm bảo chỉ 1 người được tính kill
    # kể cả khi nhiều người tấn công đồng thời trong cùng window
    state_now = await get_boss_state(boss_id)
    if not state_now:
        return

    ten_player = ts.get("dao_hieu", inter.user.display_name)
    log_entry  = f"• **{ten_player}** — **{fmt(total_dmg)}** ({len(logs)} hiệp)"
    spawn_time = state_now["spawn_time"]

    # Atomic: cập nhật HP, set _killer (chỉ 1 lần), append log
    boss_dead = await set_boss_killer_atomic(
        boss_id, uid, total_dmg, spawn_time, log_entry
    )

    if boss_dead:
        await set_boss_end_time(boss_id, int(time.time()))

    # Ghi thêm damage vào bảng boss_tham_gia (cho leaderboard/thưởng)
    await add_boss_damage(boss_id, uid, total_dmg, spawn_time)

    # Thưởng first-hit (atomic — chỉ thành công 1 lần per user/boss/spawn)
    # Fix #3: first-hit cũng × cg_bonus + lt_m + exp_m
    _fh_cg_bonus = round(1.0 + ts.get("canh_gioi", 0) * 0.10, 2)
    _fh_lt  = int(1000 * _fh_cg_bonus * full_sync.get("lt_m",  1.0))
    _fh_exp = int(500  * _fh_cg_bonus * full_sync.get("exp_m", 1.0))
    await claim_first_hit_reward(boss_id, uid, spawn_time, lt=_fh_lt, exp=_fh_exp)

    # Lấy lại state_now để embed & refresh public message dùng giá trị mới nhất
    state_now = await get_boss_state(boss_id)
    if not state_now:
        state_now = {"hp_hien": 0, "spawn_time": spawn_time,
                     "nguoi_tan_cong": {}, "canh_gioi": cg_boss}
    nguoi_tc = state_now.get("nguoi_tan_cong", {})
    hp_b_new = state_now.get("hp_hien", 0)

    # Announce boss chết
    if boss_dead and inter.guild:
        try:
            from cogs.views.boss import _announce_boss_killed
            await _announce_boss_killed(inter, boss_cfg, uid, ten_player)
        except Exception as e:
            log.warning(f"[BossCombat] announce killed failed: {e}")

    # ── 9. Embed kết thúc ───────────────────────────────────────
    emb_done = _embed_boss_combat(
        inter.user, ts_display, logs, len(logs), boss_cfg, boss_stat, hp_boss_max, hp_boss_hien)

    # Kiểm tra player có chết trong combat không
    last_log    = logs[-1] if logs else None
    player_died = last_log is not None and last_log[5] <= 0  # last_log[5] = hp_p cuối

    cd_note = f"\n⏳ Cooldown: **{COMBAT_CD_SECS}s** trước lần đánh tiếp theo."
    if boss_dead:
        emb_done.color = 0xFFD700
        emb_done.description = f"💀 **{boss_cfg['ten']}** đã bị tiêu diệt bởi đòn cuối của bạn!"
    elif player_died:
        emb_done.color = 0x808080
        emb_done.description = (
            f"💀 Bạn đã ngã xuống sau **{len(logs)} hiệp** | Gây **{fmt(total_dmg)}** sát thương.{cd_note}"
        )
    else:
        emb_done.description = (
            f"✅ Hoàn thành **{len(logs)} hiệp** | Gây **{fmt(total_dmg)}** sát thương tổng.{cd_note}"
        )

    try:
        await msg.edit(embed=emb_done, view=done_view)
    except Exception:
        log.exception("Lỗi boss_combat")

    # ── 10. Khởi động CD timer (luôn chạy, kể cả boss dead) ────
    if msg is not None and isinstance(msg, discord.Message):
        old_task = _boss_cd_tasks.pop(uid, None)
        if old_task and not old_task.done():
            old_task.cancel()
        cd_end = now_ts + COMBAT_CD_SECS
        task = asyncio.create_task(
            _run_boss_cd_timer(uid, msg, emb_done, done_view, cd_end, boss_dead=boss_dead))
        _boss_cd_tasks[uid] = task

    # ── 11. Cập nhật public boss message (best-effort) ──────────
    if inter.guild:
        await _try_refresh_public_boss_msg(inter, boss_id, boss_cfg, cg_boss,
                                            hp_b_new, hp_boss_max, state_now, nguoi_tc, boss_dead)


async def _try_refresh_public_boss_msg(
    inter: discord.Interaction,
    boss_id: int,
    boss_cfg: dict,
    cg_boss: int,
    hp_b_new: int,
    hp_boss_max: int,
    state: dict,
    nguoi_tc: dict,
    boss_dead: bool,
) -> None:
    """Edit public boss message để cập nhật HP sau khi combat xong."""
    try:
        from cogs.views.boss import BossView, BossSpawnView
        from cogs.hoso_utils import BOSS_LIFETIME
        from utils.config import emoji_hp_bar

        guild_msg = BossView._get_guild_msg(boss_id, inter.guild.id)
        if not guild_msg:
            return

        pct       = max(0, hp_b_new / hp_boss_max * 100)
        spawn_ts  = state.get("spawn_time", 0)
        secs_left = max(0, BOSS_LIFETIME - (int(time.time()) - spawn_ts))
        h, m      = secs_left // 3600, (secs_left % 3600) // 60
        cg_obj    = get_cg(cg_boss)

        combat_logs = nguoi_tc.get("_log", [])
        tc_display  = {k: v for k, v in nguoi_tc.items() if k not in ("_log", "_killer")}

        embed = discord.Embed(
            title=f"⚠️ CẢNH BÁO: {boss_cfg['ten'].upper()} XUẤT HIỆN!",
            color=0xFFD700 if boss_dead else 0xDC143C,
        )
        embed.add_field(
            name="📋 Thông tin Boss",
            value=(
                f"• Tên: **{boss_cfg['ten']}**\n"
                f"• Cảnh giới: **{cg_obj['emoji']} {cg_obj['ten']}**\n"
                f"• Sinh lực: {emoji_hp_bar(hp_b_new, hp_boss_max)}\n"
                f"• Chi tiết: **{fmt(hp_b_new)} / {fmt(hp_boss_max)} ({pct:.1f}%)**"
            ),
            inline=False,
        )
        embed.add_field(
            name="⚔️ Nhật ký gần đây",
            value="\n".join(combat_logs) if combat_logs else "*Chưa có ai tấn công...*",
            inline=False,
        )
        if tc_display:
            sorted_tc = sorted(tc_display.items(), key=lambda x: x[1], reverse=True)[:10]
            tc_lines  = [f"**{i+1}.** <@{uid_k}>: {fmt(dmg_k)}"
                         for i, (uid_k, dmg_k) in enumerate(sorted_tc)]
            embed.add_field(
                name=f"⚔️ Tham chiến ({len(tc_display)} tu sĩ)",
                value="\n".join(tc_lines),
                inline=False,
            )
        embed.add_field(
            name="⏳ Thời gian còn lại",
            value=f"{h}h {m}m" if h else f"{m} phút",
            inline=False,
        )
        embed.set_footer(text="Bấm nút bên dưới để tấn công!")

        new_view = BossSpawnView(boss_id)
        img_path = boss_cfg.get("image_file", "")

        import os
        if img_path and os.path.exists(img_path):
            import discord as _d
            fname = os.path.basename(img_path)
            f_img = _d.File(img_path, filename=fname)
            embed.set_image(url=f"attachment://{fname}")
            await guild_msg.edit(embed=embed, view=new_view, attachments=[f_img])
        else:
            await guild_msg.edit(embed=embed, view=new_view, attachments=[])
    except Exception as e:
        log.warning(f"[BossCombat] refresh public msg failed: {e}")
