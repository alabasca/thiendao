from __future__ import annotations
from typing import Any

from cogs.views._common import *
import json
from utils.config import DOTPHA_TC_NGUYEN_LIEU, DOTPHA_TC_DROP_RATE, DOTPHA_TC_NL_BY_ID
import re as _re
import logging
from typing import TYPE_CHECKING
from utils.bot_emojis import E_SINH_LUC, E_LINH_LUC, E_CONG_KICH, E_PHONG_NGU, E_LINH_THACH, E_TU_VI
from utils.database import get_boss_channel as _get_boss_channel_id
from utils.database import save_boss_guild_message, get_boss_guild_messages, clear_boss_guild_messages
from utils.config import SUNG_THU, SUNG_THU_BY_ID
log = logging.getLogger("hoso")

def _dtc_kho(ts: dict[str, Any]) -> dict:
    """Parse dotpha_tc_nl từ DB (str JSON hoặc dict)."""
    raw = ts.get("dotpha_tc_nl", {})
    if isinstance(raw, dict): return raw
    try: return json.loads(raw) if raw else {}
    except Exception: return {}

if TYPE_CHECKING:
    from cogs.hoso import HoSoView


# ══════════════════════════════════════════════════════════════
#  BOSS VIEW
# ══════════════════════════════════════════════════════════════
async def _build_ket_qua(inter_guild, boss_found, lb_found, state=None) -> tuple:
    """Tạo embed kết quả boss theo hình mẫu. Trả về (embed, file_or_None, boss_active)."""
    if state is None:
        state = await get_boss_state(boss_found["id"])
    boss_dead    = state and state.get("hp_hien", 1) <= 0
    boss_active  = _boss_is_active(state) if state else False
    total_raiders = len(lb_found)

    if boss_active:
        status_str = "⚔️ Boss đang bị tấn công — Bảng xếp hạng real-time."
        color = 0xDC143C
    elif boss_dead:
        status_str = "💀 Boss đã bị tiêu diệt."
        color = 0xFFD700
    else:
        status_str = "🌫️ Boss đã biến mất (hết thời gian)."
        color = 0x888888

    embed = discord.Embed(
        title=f"📊 KẾT QUẢ BOSS: {boss_found['ten']}",
        description=status_str,
        color=color)

    # Thời điểm kết thúc
    end_time = (state or {}).get("end_time", 0)
    if end_time:
        embed.description += f"\n⏰ Kết thúc: <t:{end_time}:R> (<t:{end_time}:T>)"
    elif boss_active:
        spawn_ts  = state.get("spawn_time", 0)
        deadline  = spawn_ts + BOSS_LIFETIME
        embed.description += f"\n⏰ Hết giờ: <t:{deadline}:R>"

    # Xếp hạng sát thương — chỉ hiện top 10
    # Batch load tên người chơi (tránh N+1 DB queries)
    medals = ["🥇","🥈","🥉","🏅","🏅","🏅","🏅","🏅","🏅","🏅"]
    top10  = lb_found[:10]
    lines  = []
    import asyncio as _asyncio
    ts_list = await _asyncio.gather(*(get_tu_si(e["user_id"]) for e in top10))
    for i, (e, ts_lb) in enumerate(zip(top10, ts_list)):
        name  = ts_lb["dao_hieu"] if ts_lb else str(e["user_id"])
        medal = medals[i]
        lines.append(f"{medal} **{i+1}.** {name} — {fmt(e['tong_damage'])} sát thương")
    embed.add_field(
        name=f"⚔️ Bảng Xếp Hạng (Top 10 / {total_raiders} tu sĩ tham chiến)",
        value="\n".join(lines) if lines else "—",
        inline=False)
    if total_raiders > 10:
        embed.add_field(
            name="\u200b",
            value=f"*...và {total_raiders - 10} tu sĩ khác tham chiến (không hiển thị)*",
            inline=False)

    # Milestone bonus hiển thị công khai
    if lb_found:
        cg_boss_lb   = (state or {}).get("canh_gioi", 3)
        from utils.config import BOSS_HP_BY_CG as _BHPBCG
        hp_max_lb    = _BHPBCG.get(cg_boss_lb, boss_found.get("hp_max", 1))
        total_dmg_lb = sum(e["tong_damage"] for e in lb_found)
        milestones_lb = min(10, int(total_dmg_lb / hp_max_lb * 10))
        if milestones_lb > 0:
            milestone_bonus_lb = round(1.0 + milestones_lb * 0.10, 2)
            embed.add_field(
                name=f"🔥 Bonus Phần Thưởng",
                value=(
                    f"Boss đã mất **{milestones_lb*10}%** máu\n"
                    f"→ Toàn bộ phần thưởng tăng **×{milestone_bonus_lb}**"
                ),
                inline=False)

    # Người kết liễu — chỉ hiện khi boss đã chết
    nguoi_tc  = (state or {}).get("nguoi_tan_cong", {})
    killer_id = nguoi_tc.get("_killer")
    if boss_dead and killer_id:
        ts_k = await get_tu_si(int(killer_id))
        embed.add_field(name="🏆 Người kết liễu",
            value=ts_k["dao_hieu"] if ts_k else str(killer_id), inline=False)
    elif boss_dead and lb_found:
        ts_k = await get_tu_si(lb_found[0]["user_id"])
        embed.add_field(name="🏆 Người kết liễu",
            value=ts_k["dao_hieu"] if ts_k else str(lb_found[0]["user_id"]), inline=False)
    elif boss_active:
        embed.add_field(name="🏆 Người kết liễu", value="*Boss chưa bị kết liễu*", inline=False)

    # Ảnh boss
    file_obj = None
    img_path = boss_found.get("image_file", "")
    if img_path and os.path.exists(img_path):
        fname    = os.path.basename(img_path)
        file_obj = discord.File(img_path, filename=fname)
        embed.set_image(url=f"attachment://{fname}")

    return embed, file_obj, boss_active


# ══════════════════════════════════════════════════════════════
#  LOBBY BOSS VIEW — sảnh chờ, chỉ 3 nút
# ══════════════════════════════════════════════════════════════
class KetQuaBossView(discord.ui.View):
    """View embed kết quả boss — Nhận Thưởng + Quay Lại Sảnh."""

    def __init__(self, parent, boss_active: bool):
        super().__init__(timeout=300)
        self.parent = parent

        btn_nhan = discord.ui.Button(
            label="🎁 Nhận Thưởng",
            style=discord.ButtonStyle.success,
            disabled=boss_active,
            row=0,
        )
        btn_ql = discord.ui.Button(
            label="◀️ Quay Lại Sảnh",
            style=discord.ButtonStyle.secondary,
            row=0,
        )
        btn_nhan.callback = self._on_nhan
        btn_ql.callback   = self._on_back
        self.add_item(btn_nhan)
        self.add_item(btn_ql)

    async def _on_nhan(self, inter: discord.Interaction):
        if not await safe_defer(inter, ephemeral=True):
            return
        ok = await _process_nhan_thuong(inter, inter.user.id)
        if not ok:
            await safe_followup(inter,
                "❌ Không có boss nào đã kết thúc để nhận thưởng!", ephemeral=True)

    async def _on_back(self, inter: discord.Interaction):
        await _back_to_hoso(inter, self.parent)


class LobbyBossView(discord.ui.View):
    """View sảnh boss khi chưa có boss nào active — Xem Kết Quả / Hướng Dẫn / Quay Lại."""
    def __init__(self, parent: "HoSoView", ts: dict[str, Any], boss_states: list):
        super().__init__(timeout=120)
        self.parent      = parent
        self.ts          = ts
        self.boss_states = boss_states

        btn_kq    = discord.ui.Button(label="Xem Kết Quả", emoji="📊",
            style=discord.ButtonStyle.primary,   row=0)
        btn_guide = discord.ui.Button(label="Hướng Dẫn",   emoji="📋",
            style=discord.ButtonStyle.secondary, row=0)
        btn_back  = discord.ui.Button(label="Quay Lại",     emoji="◀️",
            style=discord.ButtonStyle.secondary, row=0)

        async def _ket_qua(inter: discord.Interaction):
            try:
                await inter.response.defer(ephemeral=True)
            except Exception:
                log.exception("Lỗi boss")
            boss_found = None
            lb_found   = []
            st_found   = None
            # Ưu tiên boss đang active, sau đó boss vừa chết gần nhất
            candidates = []
            for boss in BOSS_THE_GIOI:
                st = await get_boss_state(boss["id"])
                if not st: continue
                sp_time = st.get("spawn_time", 0)
                lb = await get_boss_leaderboard(boss["id"], sp_time)
                if lb:
                    is_active = _boss_is_active(st)
                    candidates.append((boss, st, lb, is_active, sp_time))
            if not candidates:
                return await safe_followup(inter, "❌ Chưa có dữ liệu xếp hạng!", ephemeral=True)
            # Ưu tiên active → mới nhất
            candidates.sort(key=lambda x: (not x[3], -x[4]))
            boss_found, st_found, lb_found, _, _ = candidates[0]
            embed, file_obj, _boss_active = await _build_ket_qua(inter.guild, boss_found, lb_found, st_found)
            nhan_view = KetQuaBossView(self.parent, _boss_active)
            if file_obj:
                await safe_followup(inter, embed=embed, file=file_obj, view=nhan_view, ephemeral=True)
            else:
                await safe_followup(inter, embed=embed, view=nhan_view, ephemeral=True)

        async def _guide(inter: discord.Interaction):
            embed = discord.Embed(
                title="🗺️ HƯỚNG DẪN BOSS THẾ GIỚI",
                description=(
                    "Phàm là tu sĩ trong thiên hạ, ai cũng có trách nhiệm trừ ma về đạo, "
                    "bảo vệ sự bình yên của Bát hoang."
                ),
                color=0xF0A500)
            embed.add_field(name="🕐  Thời gian & Phạm vi",
                value=(
                    "• Boss xuất hiện **00:00**, **06:00**, **12:00**, **18:00** (giờ VN).\n"
                    "• Tồn tại tối đa **60 phút** — nếu không bị tiêu diệt sẽ tự rút lui.\n"
                    "• Boss xuất hiện **đồng thời trên tất cả server** — tu sĩ các server cùng tham chiến!"
                ),
                inline=False)
            embed.add_field(name="⚔️  Kỹ năng tấn công",
                value=(
                    "• **Võ Kỹ:** CD 10s — sát thương cơ bản.\n"
                    "• **Thân Pháp:** CD 20s — sát thương cơ bản.\n"
                    "• **Tuyệt Kỹ:** CD 60s — sát thương lớn.\n"
                    "• **Thần Thông:** CD 90s — sát thương cực lớn.\n"
                    "• **⚔️ Pháp Bảo:** CD 30s — kích hoạt kỹ năng passive của pháp bảo đang trang bị."
                ), inline=False)
            embed.add_field(name="🎁  Phần thưởng",
                value=(
                    f"• **Tham gia lần đầu:** +1.000 {E_LINH_THACH} & +500 {E_TU_VI}\n"
                    f"• **Kết liễu boss:** Thêm +8.000 {E_LINH_THACH} & +800 {E_TU_VI}\n"
                    "• **Bảng xếp hạng** (tính theo tổng sát thương):\n"
                    f"  🥇 Top 1: +20.000 {E_LINH_THACH} & +2.000 {E_TU_VI}\n"
                    f"  🥈 Top 2: +15.000 {E_LINH_THACH} & +1.700 {E_TU_VI}\n"
                    f"  🥉 Top 3: +13.000 {E_LINH_THACH} & +1.500 {E_TU_VI}\n"
                    f"  🏅 Top 4: +11.000 {E_LINH_THACH} & +1.300 {E_TU_VI}\n"
                    f"  🏅 Top 5: +10.000 {E_LINH_THACH} & +1.100 {E_TU_VI}\n"
                    f"  🎖️ Top 6–10: +5.000 {E_LINH_THACH} & +500 {E_TU_VI}\n"
                    f"  *(Ngoài top 10: +500 {E_LINH_THACH} & +500 {E_TU_VI})*\n"
                    "  *(Tất cả nhân hệ số cảnh giới, tối đa ×2.0)*\n"
                    "• **Pháp bảo & Sủng thú huyền thoại:** 0.1% drop khi nhận thưởng."
                ), inline=False)
            embed.add_field(name="💡  Mẹo",
                value=(
                    "• Trang bị **Pháp Bảo** và dùng nút ⚔️ Pháp Bảo để tăng sát thương.\n"
                    "• **Thần Thông** có CD dài nhưng damage cao nhất — ưu tiên dùng sớm.\n"
                    "• Sát thương càng cao → thứ hạng càng tốt → phần thưởng càng lớn!"
                ), inline=False)
            await inter.response.send_message(embed=embed, ephemeral=True)

        btn_kq.callback    = _ket_qua
        btn_guide.callback = _guide
        async def _do_back_lobby(i): await _back_to_hoso(i, self.parent)
        btn_back.callback  = _do_back_lobby
        self.add_item(btn_kq)
        self.add_item(btn_guide)
        self.add_item(btn_back)


# ── Helpers thông báo boss public ─────────────────────────────
# In-memory set để track ngay lập tức, tránh double-claim trước khi DB flush
# Per-(boss_id, uid) lock để tránh double-claim race condition
_nhan_locks: dict = {}  # {(boss_id, uid): asyncio.Lock}


async def _process_nhan_thuong(inter_or_i2, uid: int) -> bool:
    """Xử lý nhận thưởng boss spawn hiện tại.
    boss_tham_gia bị xóa khi spawn mới → chỉ nhận được thưởng trong cùng 1 lần spawn.
    Trả về True nếu đã gửi ít nhất 1 response.
    """
    from utils.database import get_unclaimed_boss_spawns
    any_found = False

    # Lấy danh sách (boss_id, spawn_time) chưa nhận trực tiếp từ boss_tham_gia
    unclaimed = await get_unclaimed_boss_spawns(uid)
    if not unclaimed:
        return False

    for entry in unclaimed:
        boss_id_e  = entry["boss_id"]
        sp_time    = entry["spawn_time"]

        # Tìm config boss
        boss = next((b for b in BOSS_THE_GIOI if b["id"] == boss_id_e), None)
        if not boss:
            continue

        # Kiểm tra boss đã kết thúc chưa — 3 cách:
        # 1. Đã hết thời gian (60 phút từ spawn_time)
        # 2. Đã được ghi vào boss_ended_spawns (set khi boss bị kill/expire)
        # 3. boss_state hiện tại có cùng spawn_time và hp=0
        from utils.database import is_boss_spawn_ended
        now_ts = int(time.time())
        boss_lifetime_ended = (now_ts - sp_time) >= BOSS_LIFETIME
        boss_in_log = await is_boss_spawn_ended(boss_id_e, sp_time)
        state = await get_boss_state(boss_id_e)
        boss_killed = state and state.get("hp_hien", 1) <= 0 and state.get("spawn_time", -1) == sp_time
        boss_ended  = boss_lifetime_ended or boss_in_log or boss_killed
        if not boss_ended:
            continue  # Boss này vẫn đang active, chưa nhận được

        # Lấy leaderboard dùng đúng spawn_time từ boss_tham_gia
        lb = await get_boss_leaderboard(boss_id_e, sp_time)
        if not lb:
            continue

        rank = next((i for i, e in enumerate(lb) if e["user_id"] == uid), None)
        if rank is None:
            continue

        # Lock per (boss_id, uid) tránh double-claim
        # dùng setdefault để tránh race condition tạo 2 lock khác nhau
        lock_key = (boss_id_e, uid)
        nhan_lock = _nhan_locks.setdefault(lock_key, asyncio.Lock())

        if nhan_lock.locked():
            await safe_followup(inter_or_i2, "⏳ Đang xử lý, vui lòng chờ...", ephemeral=True)
            return True

        async with nhan_lock:
            # Double-check sau lock — đọc lại DB sau khi đã giữ lock
            da_nhan = await has_nhan_thuong(boss_id_e, uid, sp_time)
            if da_nhan:
                continue

            # Lấy nguoi_tan_cong từ boss_state (nếu còn) để xác định killer
            nguoi_tc = {}
            if state and state.get("spawn_time", -1) == sp_time:
                nguoi_tc = state.get("nguoi_tan_cong", {})

            ts_r_cg   = await get_tu_si(uid)
            player_cg = ts_r_cg["canh_gioi"] if ts_r_cg else 0
            cg_bonus  = round(1.0 + player_cg * 0.10, 2)

            BASE_LT  = 15000;  BASE_EXP = 500  # Tăng base top10: 5000 → 15000
            RANK_LT  = [15000, 10000, 8000, 6000, 5000]
            RANK_EXP = [1500,  1200,  1000,  800,  600]
            KILL_LT  = 8000;  KILL_EXP = 800
            NGOAI_TOP_LT = 7000;  NGOAI_TOP_EXP = 500  # Tăng base ngoài top10: 500 → 7000

            if rank < len(RANK_LT):
                lt_r  = int((BASE_LT  + RANK_LT[rank])  * cg_bonus)
                exp_r = int((BASE_EXP + RANK_EXP[rank]) * cg_bonus)
            elif rank < 10:
                lt_r  = int(BASE_LT  * cg_bonus)
                exp_r = int(BASE_EXP * cg_bonus)
            else:
                lt_r  = int(NGOAI_TOP_LT  * cg_bonus)
                exp_r = int(NGOAI_TOP_EXP * cg_bonus)

            killer_uid = nguoi_tc.get("_killer")
            is_killer  = (killer_uid is not None and uid == killer_uid)
            if is_killer:
                lt_r  += int(KILL_LT  * cg_bonus)
                exp_r += int(KILL_EXP * cg_bonus)

            ts_r = ts_r_cg
            if not ts_r:
                await safe_followup(inter_or_i2, "❌ Không tìm thấy hồ sơ!", ephemeral=True)
                return True

            from cogs.hoso_utils import _calc_stats as _cs_boss
            _st_boss = _cs_boss(ts_r)
            player_drop_m = _st_boss.get("drop_m", 1.0)
            # Fix #2+3: áp dụng lt_m và exp_m của người chơi vào LT+TV boss, và first-hit × cg_bonus
            player_lt_m  = _st_boss.get("lt_m",  1.0)
            player_exp_m = _st_boss.get("exp_m", 1.0)
            lt_r  = int(lt_r  * player_lt_m)
            exp_r = int(exp_r * player_exp_m)

            # Fix #5: mỗi 10% máu boss bị đánh xuống → thưởng tăng thêm 10%
            # Tính tổng damage đã gây (= HP boss đã mất) từ leaderboard
            cg_boss_state = state.get("canh_gioi", 3) if state and state.get("spawn_time", -1) == sp_time else 3
            hp_max_boss_r = BOSS_HP_BY_CG.get(cg_boss_state, boss.get("hp_max", 1))
            total_dmg_all = sum(e["tong_damage"] for e in lb)
            milestones    = min(10, int(total_dmg_all / hp_max_boss_r * 10))  # 0–10 mốc
            milestone_bonus = round(1.0 + milestones * 0.10, 2)              # ×1.0 đến ×2.0
            lt_r  = int(lt_r  * milestone_bonus)
            exp_r = int(exp_r * milestone_bonus)

            pt   = boss["phan_thuong"]
            nl_r = ts_r["nguyen_lieu"].copy()

            in_top5 = rank < 5
            nl_drops = []; manh_drops = []; lq_drops = []

            # Fix #4: tỉ lệ mảnh + linh quả điều chỉnh
            if rank == 0 or is_killer:
                drop_rate_manh = 0.40
            elif in_top5:
                drop_rate_manh = 0.25
            elif rank < 10:
                drop_rate_manh = 0.15
            else:
                drop_rate_manh = 0.13  # tăng từ 0.08 → 0.13

            # Linh quả: tỉ lệ tương ứng (giữ factor 0.36/0.18/0.09)
            lq_rate_co_ban = min(1.0, drop_rate_manh * 0.36 * player_drop_m)
            lq_rate_hiem   = min(1.0, drop_rate_manh * 0.18 * player_drop_m)
            lq_rate_sieu   = min(1.0, drop_rate_manh * 0.09 * player_drop_m)

            # Fix #5: milestone bonus áp vào tỉ lệ drop mảnh + linh quả (không áp PB/ST)
            drop_rate_manh_m  = min(1.0, drop_rate_manh  * milestone_bonus)
            lq_rate_co_ban_m  = min(1.0, lq_rate_co_ban  * milestone_bonus)
            lq_rate_hiem_m    = min(1.0, lq_rate_hiem    * milestone_bonus)
            lq_rate_sieu_m    = min(1.0, lq_rate_sieu    * milestone_bonus)

            manh_new = ts_r.get("manh_linh_can", {}).copy()
            lq_new   = ts_r.get("linh_qua", {}).copy()

            for lq in LINH_QUA:
                lq_id = lq["id"]
                if random.random() < min(1.0, drop_rate_manh_m * player_drop_m):
                    cnt = random.randint(1, 3) if (rank == 0 or in_top5 or is_killer) else 1  # Fix #1: killer nhận 1-3
                    manh_new[lq_id] = manh_new.get(lq_id, 0) + cnt
                    manh_drops.append(f"{MANH_LINH_CAN_EMOJI.get(lq_id, lq['emoji'])}×{cnt}")
                if lq_id in ("am", "quang"):
                    lq_rate = lq_rate_sieu_m
                elif lq_id in ("loi", "phong"):
                    lq_rate = lq_rate_hiem_m
                else:
                    lq_rate = lq_rate_co_ban_m
                if random.random() < lq_rate:
                    lq_new[lq_id] = lq_new.get(lq_id, 0) + 1
                    lq_drops.append(f"{lq['emoji']}×1")

            # Fix #1: killer (dù ngoài top5) nhận NL như top5 (3-6 cái)
            # Fix #5: milestone_bonus tăng số lượng NL (làm tròn)
            if in_top5 or is_killer:
                for nl_id in pt["nl"]:
                    base_amt = random.randint(3, 6)
                    amt = max(1, round(base_amt * milestone_bonus))  # Fix #5: scale
                    nl_r[str(nl_id)] = nl_r.get(str(nl_id), 0) + amt
                    nl_drops.append(f"NL#{nl_id}×{amt}")

            # Thưởng đảm bảo: top6-10 → random 5 linh quả HOẶC 5 mảnh linh căn
            #                  ngoài top10 → random 2 linh quả HOẶC 2 mảnh linh căn
            if not in_top5 and not is_killer:
                if rank < 10:
                    guaranteed_count = 5
                else:
                    guaranteed_count = 2
                # 50/50: linh quả hoặc mảnh linh căn
                if random.random() < 0.5:
                    # Drop linh quả: chọn ngẫu nhiên, ưu tiên loại co_ban (80%) vs hiem (20%)
                    lq_pool_co_ban = [lq for lq in LINH_QUA if lq["loai"] == "co_ban"]
                    lq_pool_hiem   = [lq for lq in LINH_QUA if lq["loai"] == "hiem"]
                    for _ in range(guaranteed_count):
                        lq_pick = random.choice(lq_pool_co_ban if random.random() < 0.8 else lq_pool_hiem)
                        lq_new[lq_pick["id"]] = lq_new.get(lq_pick["id"], 0) + 1
                        lq_drops.append(f"{lq_pick['emoji']}×1")
                else:
                    # Drop mảnh linh căn: chọn ngẫu nhiên từ LINH_CAN
                    for _ in range(guaranteed_count):
                        lc_pick = random.choice(LINH_CAN)
                        lc_id = lc_pick["id"]
                        manh_new[lc_id] = manh_new.get(lc_id, 0) + 1
                        manh_drops.append(f"{MANH_LINH_CAN_EMOJI.get(lc_id, lc_pick['emoji'])}×1")

            # Sủng thú huyền thoại Tier 2: 0.1%
            st_drop_boss = None
            raw_st_b = ts_r.get("sung_thu", {})
            owned_st = set(raw_st_b.keys()) if isinstance(raw_st_b, dict) else set(__import__("json").loads(raw_st_b).keys() if raw_st_b else [])
            pool_tier2 = [st for st in SUNG_THU if st["tier"] == 2 and str(st["id"]) not in owned_st]
            if pool_tier2 and random.random() < min(1.0, 0.001 * player_drop_m):
                st_drop_boss = random.choice(pool_tier2)

            # Pháp bảo huyền thoại: 0.1%
            pb_drop_tag = ""
            pb_match_dropped = None
            if random.random() < min(1.0, 0.001 * player_drop_m):
                pb_pool = PHAP_BAO_BY_BASE.get(random.randint(0, 9), [])
                pb_match_dropped = next((pb for pb in pb_pool if pb["canh_gioi"] == player_cg),
                                pb_pool[-1] if pb_pool else None)
                if pb_match_dropped:
                    pb_owned = ts_r.get("phap_bao", []).copy()
                    pb_owned.append(pb_match_dropped["id"])
                    await update_tu_si_wait(uid, phap_bao=pb_owned)
                    pb_drop_tag = f"\n✨ **Pháp Bảo: {pb_match_dropped['emoji']} {pb_match_dropped['ten']}** (CG {pb_match_dropped['canh_gioi']}) — Rớt từ boss!"
                    _dao_hieu_w = ts_r["dao_hieu"] if ts_r else "Vô Danh"
                    _is_killed  = boss_killed
                    _pb_msg = (
                        f"⚔️ **{_dao_hieu_w}** đã nhanh tay cướp được pháp bảo trong lúc không ai để ý"
                        if _is_killed else
                        f"🏃 **{_dao_hieu_w}** đã nhanh tay cướp mất pháp bảo"
                    )
                    _pb_embed = discord.Embed(
                        title=f"✨ {pb_match_dropped['emoji']} {pb_match_dropped['ten']} XUẤT HIỆN!",
                        description=_pb_msg, color=0xFFD700)
                    _bot = inter_or_i2.client if hasattr(inter_or_i2, "client") else None
                    if _bot:
                        for _guild in _bot.guilds:
                            try:
                                _ch_id = await _get_boss_channel_id(_guild.id)
                                _ch = _guild.get_channel(_ch_id) if _ch_id else None
                                if _ch:
                                    await _ch.send(embed=_pb_embed)
                            except Exception:
                                log.exception("Lỗi boss")

            drop_tag = "  ".join(manh_drops + lq_drops)

            # Drop nguyên liệu đột phá thể chất (Fix #5: scale với milestone_bonus)
            dtc_new = _dtc_kho(ts_r).copy()
            dtc_drops = []
            for nl in DOTPHA_TC_NGUYEN_LIEU:
                if nl["nguon"] in ("boss", "boss_bi_canh"):
                    if random.random() < min(1.0, DOTPHA_TC_DROP_RATE * milestone_bonus):
                        dtc_new[nl["id"]] = dtc_new.get(nl["id"], 0) + 1
                        dtc_drops.append(f"{nl['emoji']} {nl['ten']}")
            dtc_drop_tag = ("\n" + "  ".join(dtc_drops)) if dtc_drops else ""

            try:
                raw_st2 = ts_r.get("sung_thu", {})
                st_kho_b = raw_st2 if isinstance(raw_st2, dict) else (__import__("json").loads(raw_st2) if raw_st2 else {})
                st_kho_b = st_kho_b.copy()
                if st_drop_boss and str(st_drop_boss["id"]) not in st_kho_b:
                    st_kho_b[str(st_drop_boss["id"])] = {"level": 1, "obtained_at": int(__import__("time").time())}
                # Mark đã nhận TRƯỚC khi phát thưởng
                # → tránh double-claim nếu exception xảy ra giữa chừng
                await mark_nhan_thuong(boss_id_e, uid, sp_time)
                await add_linh_thach(uid, lt_r)
                await update_tu_si_wait(uid,
                    exp=ts_r["exp"] + exp_r,
                    nguyen_lieu=nl_r,
                    linh_qua=lq_new, manh_linh_can=manh_new,
                    dotpha_tc_nl=dtc_new, sung_thu=st_kho_b)
            except Exception as e:
                await safe_followup(inter_or_i2, f"❌ Lỗi khi phát thưởng: {e}", ephemeral=True)
                return True

            medal = ["🥇","🥈","🥉","🏅","🏅"][min(rank,4)] if rank < 5 else "🎖️"
            st_tag = f" +{st_drop_boss['emoji']} {st_drop_boss['ten']}!" if st_drop_boss else ""
            milestone_tag = f"\n🔥 **Boss mất {milestones*10}% máu** — Thưởng tăng ×**{milestone_bonus}**" if milestones > 0 else ""
            desc = (
                f"{E_LINH_THACH} **+{fmt(lt_r)}** Linh Thạch\n"
                f"{E_TU_VI} **+{fmt(exp_r)}** Tu Vi"
                + milestone_tag
            )
            if drop_tag:
                desc += f"\n{drop_tag}"
            if st_tag:
                desc += f"\n🐾 {st_tag}"
            if is_killer:
                desc += "\n⚔️ **Thưởng kết liễu!**"
            desc += pb_drop_tag
            desc += dtc_drop_tag
            await safe_followup(inter_or_i2, 
                embed=discord.Embed(
                    title=f"{medal} Phần thưởng — {boss['ten']}",
                    description=desc,
                    color=0xFFD700),
                ephemeral=True)
            any_found = True

    return any_found



async def _announce_boss_killed(inter: discord.Interaction, boss_cfg: dict,
                                killer_id, killer_name: str):
    """Gửi thông báo public trong server khi boss bị tiêu diệt."""
    channel = None
    if inter.guild:
        ch_id = await _get_boss_channel_id(inter.guild.id)
        if not ch_id:
            ch_id = BOSS_ANNOUNCE_CHANNEL_ID
        if ch_id:
            channel = inter.guild.get_channel(ch_id) or inter.guild.get_thread(ch_id)
    if channel is None:
        return  # Boss channel chưa được set — không gửi ở channel khác
    embed = discord.Embed(
        title=f"💀 {boss_cfg['ten']} ĐÃ BỊ TIÊU DIỆT!",
        description=(
            f"⚔️ **{killer_name}** đã là người kết liễu!\n"
            f"Cảm ơn tất cả các tu sĩ đã tham chiến bảo vệ thiên hạ!"
        ),
        color=0xFFD700,
    )
    img_path = boss_cfg.get("image_file", "")
    if img_path and os.path.exists(img_path):
        fname = os.path.basename(img_path)
        f_img = discord.File(img_path, filename=fname)
        embed.set_thumbnail(url=f"attachment://{fname}")
        try:
            await channel.send(embed=embed, file=f_img)
        except Exception:
            await channel.send(embed=embed)
    else:
        try:
            await channel.send(embed=embed)
        except Exception:
            log.exception("Lỗi boss")


async def _announce_boss_expired(inter: discord.Interaction, boss_cfg: dict):
    """Gửi thông báo public khi boss hết giờ biến mất."""
    channel = None
    if inter.guild:
        ch_id = await _get_boss_channel_id(inter.guild.id)
        if not ch_id:
            ch_id = BOSS_ANNOUNCE_CHANNEL_ID
        if ch_id:
            channel = inter.guild.get_channel(ch_id) or inter.guild.get_thread(ch_id)
    if channel is None:
        return  # Boss channel chưa được set — không gửi ở channel khác
    embed = discord.Embed(
        title=f"🌫️ {boss_cfg['ten']} ĐÃ BIẾN MẤT!",
        description=(
            f"**{boss_cfg['ten']}** đã rút lui khỏi thiên hạ sau khi hết thời gian.\n"
            f"Hãy chuẩn bị cho lần xuất hiện tiếp theo!"
        ),
        color=0x555555,
    )
    try:
        await channel.send(embed=embed)
    except Exception:
        log.exception("Lỗi boss")


class BossSpawnView(discord.ui.View):
    """Persistent view cho message boss spawn — 1 nút Tấn Công + 1 nút Nhận Thưởng."""

    def __init__(self, boss_id: int):
        super().__init__(timeout=None)
        self.boss_id = boss_id

        # ── Nút Tấn Công (auto combat 10 hiệp) ─────────────────
        atk_btn = discord.ui.Button(
            label="⚔️ Tấn Công",
            style=discord.ButtonStyle.danger,
            row=0,
            custom_id=f"boss_atk:{boss_id}",
        )
        async def _atk_cb(inter: discord.Interaction):
            from cogs.views.boss_combat import do_boss_auto_combat
            await do_boss_auto_combat(inter, boss_id)
        atk_btn.callback = _atk_cb
        self.add_item(atk_btn)

        # ── Nút Nhận Thưởng ─────────────────────────────────────
        nhan_btn = discord.ui.Button(
            label="🎁 Nhận Thưởng",
            style=discord.ButtonStyle.success,
            row=0,
            custom_id=f"boss_nhan:{boss_id}",
        )
        async def _nhan_cb(inter: discord.Interaction):
            if not await safe_defer(inter, ephemeral=True):
                return
            ok = await _process_nhan_thuong(inter, inter.user.id)
            if not ok:
                await safe_followup(inter, 
                    "❌ Bạn chưa tham gia boss nào hoặc đã nhận thưởng rồi!", ephemeral=True)
        nhan_btn.callback = _nhan_cb
        self.add_item(nhan_btn)



async def _build_initial_boss_message(bot, channel, boss_cfg: dict,
                                      cg_rand: int, hp_b: int, spawn_ts: int,
                                      is_new_spawn: bool = False):
    """Tạo/restore message boss public, hiển thị đúng state hiện tại từ DB."""
    from cogs.views.boss import BossView  # local import tránh circular
    import time as _time
    boss_id  = boss_cfg["id"]
    cg_obj   = get_cg(cg_rand)
    hp_max_b = BOSS_HP_BY_CG.get(cg_rand, boss_cfg["hp_max"])
    pct      = hp_b / hp_max_b * 100 if hp_max_b else 100

    # Đọc state hiện tại để hiển thị đúng (không reset về blank slate)
    state        = await get_boss_state(boss_id)
    nguoi_tc     = state["nguoi_tan_cong"] if state else {}
    combat_logs  = nguoi_tc.get("_log", []) if isinstance(nguoi_tc.get("_log"), list) else []
    tc_display   = {k: v for k, v in nguoi_tc.items() if k not in ("_log", "_killer")}

    secs_left = max(0, BOSS_LIFETIME - (int(_time.time()) - spawn_ts))
    h, m = secs_left // 3600, (secs_left % 3600) // 60

    embed = discord.Embed(
        title=f"⚠️ CẢNH BÁO: {boss_cfg['ten'].upper()} XUẤT HIỆN!",
        color=0xDC143C,
    )
    embed.add_field(
        name="📋  Thông tin Boss",
        value=(
            f"• Tên: **{boss_cfg['ten']}**\n"
            f"• Cảnh giới: **{cg_obj['emoji']} {cg_obj['ten']}**\n"
            f"• Sinh lực: {emoji_hp_bar(hp_b, hp_max_b)}\n"
            f"• Chi tiết: **{fmt(hp_b)} / {fmt(hp_max_b)} ({pct:.1f}%)**"
        ),
        inline=False)
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
        value=f"{h}h {m}m" if h else f"{m} phút",
        inline=False)
    embed.set_footer(text="Chọn kỹ năng bên dưới để tấn công!")

    # Build attack view persistent — dùng custom_id để bot tự restore sau restart
    atk_view = BossSpawnView(boss_id)

    # Reset boss — CHỈ khi spawn mới (is_new_spawn=True từ admin force /spawnboss)
    # Automatic spawn task dùng clear_boss_data với purge_rewards=True (xóa hết data cũ khi spawn mới)
    if is_new_spawn:
        await clear_boss_data(boss_id, purge_rewards=True)  # Admin force: xóa hết
        to_remove = [k for k in list(_nhan_locks.keys()) if k[0] == boss_id]
        for k in to_remove: _nhan_locks.pop(k, None)
        # Xóa message cũ tất cả guild — từ in-memory dict
        for _guild_id, _old_msg in list(BossView._boss_msg.get(boss_id, {}).items()):
            try:
                await _old_msg.delete()
                log.info(f"[BossSpawn] Xóa message cũ guild={_guild_id}")
            except Exception as e:
                log.debug(f"[BossSpawn] Không xóa message guild={_guild_id}: {e}")
        BossView._pop_boss_msg(boss_id)
        # Cũng xóa message được lưu trong DB (guild cũ hoặc sau restart)
        old_msg_id, old_ch_id = await get_boss_message_id(boss_id)
        if old_msg_id and old_ch_id:
            try:
                old_ch = bot.get_channel(old_ch_id) or await bot.fetch_channel(old_ch_id)
                if old_ch:
                    old_msg_obj = await old_ch.fetch_message(old_msg_id)
                    await old_msg_obj.delete()
            except Exception as e:
                log.debug(f"[BossSpawn] Không xóa được message DB cũ: {e}")
        await save_boss_message_id(boss_id, 0, 0)

    img_path = boss_cfg.get("image_file", "")
    guild_id_save = channel.guild.id if hasattr(channel, "guild") and channel.guild else 0

    # Kiểm tra quyền trước khi làm gì
    if guild_id_save:
        me = channel.guild.me
        if me:
            perms = channel.permissions_for(me)
            if not perms.send_messages or not perms.view_channel:
                log.warning(f"[BossSpawn] Bot thiếu quyền tại #{channel.name} (guild={guild_id_save}) — bỏ qua")
                return

    # LUÔN check DB trước — tránh tạo duplicate sau restart
    if guild_id_save:
        try:
            guild_msgs = await get_boss_guild_messages(boss_id)
            for _gid, _mid, _cid in guild_msgs:
                if _gid == guild_id_save and _mid and _cid:
                    try:
                        _ch = (channel.guild.get_channel(_cid)
                               or channel.guild.get_thread(_cid))
                        if not _ch:
                            try:
                                _ch = await channel.guild.fetch_channel(_cid)
                            except Exception:
                                _ch = None
                        if _ch:
                            existing = await _ch.fetch_message(_mid)
                            # Message cũ còn tồn tại → edit thay vì tạo mới
                            if img_path and os.path.exists(img_path):
                                fname = os.path.basename(img_path)
                                embed.set_image(url=f"attachment://{fname}")
                                f_img = discord.File(img_path, filename=fname)
                                await existing.edit(embed=embed, view=atk_view, attachments=[f_img])
                            else:
                                await existing.edit(embed=embed, view=atk_view, attachments=[])
                            BossView._set_guild_msg(boss_id, guild_id_save, existing)
                            log.info(f"[BossSpawn] Edited existing message guild={guild_id_save} msg={_mid}")
                            return
                    except discord.NotFound:
                        # Message bị xóa → xóa record DB rồi tạo mới bên dưới
                        await save_boss_guild_message(boss_id, guild_id_save, 0, 0)
                    except Exception:
                        log.exception("Lỗi boss")
                    break
        except Exception:
            log.exception("Lỗi boss")

    # Tạo message mới (chỉ khi thực sự chưa có)
    try:
        if img_path and os.path.exists(img_path):
            fname = os.path.basename(img_path)
            f_img = discord.File(img_path, filename=fname)
            embed.set_image(url=f"attachment://{fname}")
            msg = await channel.send(embed=embed, file=f_img, view=atk_view)
        else:
            msg = await channel.send(embed=embed, view=atk_view)
        BossView._set_guild_msg(boss_id, guild_id_save, msg)
        if guild_id_save:
            await save_boss_guild_message(boss_id, guild_id_save, msg.id, channel.id)
        log.info(f"[BossSpawn] Tạo message mới #{channel.name} (guild={guild_id_save}) msg={msg.id}")
    except discord.Forbidden:
        log.warning(f"[BossSpawn] 403 tại #{channel.name} (guild={guild_id_save}) — bỏ qua")
    except Exception as e:
        log.warning(f"[BossSpawn] Lỗi tại #{channel.name} (guild={guild_id_save}): {e}")


async def _send_or_edit_direct(boss_id: int, embed, view, img_path: str, guild):
    """Thực hiện edit message boss — gọi từ debounce flush task."""
    if not guild:
        return
    guild_id_d   = guild.id
    existing_msg = BossView._get_guild_msg(boss_id, guild_id_d)
    if img_path and os.path.exists(img_path):
        embed.set_image(url=f"attachment://{os.path.basename(img_path)}")

    # Nếu không có trong memory → fetch từ DB trước khi tạo mới
    if not existing_msg:
        try:
            guild_msgs = await get_boss_guild_messages(boss_id)
            for _gid, _mid, _cid in guild_msgs:
                if _gid == guild_id_d and _mid and _cid:
                    try:
                        _ch = guild.get_channel(_cid) or guild.get_thread(_cid)
                        if not _ch:
                            try:
                                _ch = await guild.fetch_channel(_cid)
                            except Exception:
                                _ch = None
                        if _ch:
                            existing_msg = await _ch.fetch_message(_mid)
                            BossView._set_guild_msg(boss_id, guild_id_d, existing_msg)
                            log.debug(f"[BossMsg] Restored from DB guild={guild_id_d} msg={_mid}")
                    except discord.NotFound:
                        # Message không còn — xóa record DB
                        await save_boss_guild_message(boss_id, guild_id_d, 0, 0)
                    except Exception:
                        log.exception("Lỗi boss")
                    break
        except Exception:
            log.exception("Lỗi boss")

    if existing_msg:
        try:
            if img_path and os.path.exists(img_path):
                f_att = discord.File(img_path, filename=os.path.basename(img_path))
                await existing_msg.edit(embed=embed, view=view, attachments=[f_att])
            else:
                await existing_msg.edit(embed=embed, view=view, attachments=[])
            return
        except discord.HTTPException as e:
            if e.status == 429:
                retry_after = getattr(e, 'retry_after', 2.0)
                await asyncio.sleep(retry_after)
                try:
                    await existing_msg.edit(embed=embed, view=view, attachments=[])
                    return
                except Exception:
                    log.exception("Lỗi boss")
        except Exception:
            # Message không còn tồn tại — xóa khỏi memory và DB
            BossView._boss_msg.get(boss_id, {}).pop(guild_id_d, None)
            try:
                await clear_boss_guild_messages(boss_id)
            except Exception:
                log.exception("Lỗi boss")
            existing_msg = None

    # Fallback: gửi message mới (chỉ khi thực sự chưa có)
    ch_id = await _get_boss_channel_id(guild.id) or BOSS_ANNOUNCE_CHANNEL_ID
    if not ch_id:
        return
    boss_channel = guild.get_channel(ch_id) or guild.get_thread(ch_id)
    if not boss_channel:
        return
    # Kiểm tra quyền trước khi gửi
    me = guild.me
    if me:
        perms = boss_channel.permissions_for(me)
        if not perms.send_messages or not perms.view_channel:
            log.debug(f"[BossMsg] Thiếu quyền tại #{boss_channel.name} guild={guild_id_d}")
            return
    try:
        if img_path and os.path.exists(img_path):
            f_att = discord.File(img_path, filename=os.path.basename(img_path))
            new_msg = await boss_channel.send(embed=embed, file=f_att, view=view)
        else:
            new_msg = await boss_channel.send(embed=embed, view=view)
        BossView._set_guild_msg(boss_id, guild_id_d, new_msg)
        # Lưu vào DB để các lần sau fetch được
        await save_boss_guild_message(boss_id, guild_id_d, new_msg.id, boss_channel.id)
        log.debug(f"[BossMsg] Tạo message mới guild={guild_id_d} msg={new_msg.id}")
    except discord.Forbidden:
        log.debug(f"[BossMsg] 403 tại #{boss_channel.name} guild={guild_id_d} — bỏ qua")
    except Exception as e:
        log.debug(f"[BossMsg] Lỗi gửi: {e}")



class BossView(discord.ui.View):
    def __init__(self, parent: "HoSoView", ts: dict[str, Any], boss_states: list):
        super().__init__(timeout=120)
        self.parent      = parent
        self.ts          = ts
        self.boss_states = boss_states

        # Chỉ hiện Xếp hạng / Hướng dẫn / Quay Lại
        # Nút kỹ năng nằm trên message boss public trong channel setup sẵn
        btn_ket_qua = discord.ui.Button(label="Xếp hạng",  emoji="📊",
            style=discord.ButtonStyle.secondary, row=0)
        btn_guide   = discord.ui.Button(label="Hướng dẫn", emoji="📋",
            style=discord.ButtonStyle.secondary, row=0)
        btn_back    = discord.ui.Button(label="Quay Lại",   emoji="◀️",
            style=discord.ButtonStyle.secondary, row=0)

        async def _ket_qua(inter: discord.Interaction):
            if not await safe_defer(inter, ephemeral=True):
                return
            boss_found = None
            lb_found   = []
            st_found   = None
            # Ưu tiên boss đang active, sau đó boss vừa chết gần nhất
            candidates = []
            for boss in BOSS_THE_GIOI:
                st = await get_boss_state(boss["id"])
                if not st: continue
                sp_time = st.get("spawn_time", 0)
                lb = await get_boss_leaderboard(boss["id"], sp_time)
                if lb:
                    is_active = _boss_is_active(st)
                    candidates.append((boss, st, lb, is_active, sp_time))
            if not candidates:
                return await safe_followup(inter, "❌ Chưa có dữ liệu xếp hạng!", ephemeral=True)
            # Ưu tiên active → mới nhất
            candidates.sort(key=lambda x: (not x[3], -x[4]))
            boss_found, st_found, lb_found, _, _ = candidates[0]
            embed, file_obj, _boss_active = await _build_ket_qua(inter.guild, boss_found, lb_found, st_found)
            nhan_view = KetQuaBossView(self.parent, _boss_active)
            if file_obj:
                await safe_followup(inter, embed=embed, file=file_obj, view=nhan_view, ephemeral=True)
            else:
                await safe_followup(inter, embed=embed, view=nhan_view, ephemeral=True)

        async def _nhan_thuong(inter: discord.Interaction):
            if not await safe_defer(inter, ephemeral=True):
                return
            ok = await _process_nhan_thuong(inter, inter.user.id)
            if not ok:
                await safe_followup(inter, 
                    "❌ Không có boss nào đã kết thúc để nhận thưởng!", ephemeral=True)

        async def _guide(inter: discord.Interaction):
            embed = discord.Embed(
                title="🗺️ HƯỚNG DẪN BOSS THẾ GIỚI",
                description=(
                    "Phàm là tu sĩ trong thiên hạ, ai cũng có trách nhiệm trừ ma về đạo, "
                    "bảo vệ sự bình yên của Bát hoang."
                ),
                color=0xF0A500)
            embed.add_field(name="🕐  Thời gian & Phạm vi",
                value=(
                    "• Boss xuất hiện **00:00**, **06:00**, **12:00**, **18:00** (giờ VN).\n"
                    "• Tồn tại tối đa **60 phút** — nếu không bị tiêu diệt sẽ tự rút lui.\n"
                    "• Boss xuất hiện **đồng thời trên tất cả server** — tu sĩ các server cùng tham chiến!"
                ),
                inline=False)
            embed.add_field(name="⚔️  Cách tấn công",
                value=(
                    "• Bấm **⚔️ Tấn Công** trên message boss để vào chiến đấu tự động.\n"
                    "• Bot sẽ tự đánh **10 hiệp**, dùng công pháp và kỹ năng tốt nhất.\n"
                    "• Cooldown **60 giây** sau mỗi lần đánh — có thể đánh nhiều lần.\n"
                    "• Chỉ số boss = boss bí cảnh cùng cảnh giới × 15."
                ),
                inline=False)
            embed.add_field(name="🎁  Phần thưởng",
                value=(
                    f"• **Tham gia lần đầu:** +1.000 {E_LINH_THACH} & +500 {E_TU_VI}\n"
                    f"• **Kết liễu boss:** Thêm +8.000 {E_LINH_THACH} & +800 {E_TU_VI}\n"
                    "• **Bảng xếp hạng** (tính theo tổng sát thương):\n"
                    f"  🥇 Top 1: +20.000 {E_LINH_THACH} & +2.000 {E_TU_VI}\n"
                    f"  🥈 Top 2: +15.000 {E_LINH_THACH} & +1.700 {E_TU_VI}\n"
                    f"  🥉 Top 3: +13.000 {E_LINH_THACH} & +1.500 {E_TU_VI}\n"
                    f"  🏅 Top 4: +11.000 {E_LINH_THACH} & +1.300 {E_TU_VI}\n"
                    f"  🏅 Top 5: +10.000 {E_LINH_THACH} & +1.100 {E_TU_VI}\n"
                    f"  🎖️ Top 6–10: +5.000 {E_LINH_THACH} & +500 {E_TU_VI}\n"
                    f"  *(Ngoài top 10: +500 {E_LINH_THACH} & +500 {E_TU_VI})*\n"
                    "  *(Tất cả nhân hệ số cảnh giới, tối đa ×2.0)*\n"
                    "• **Pháp bảo & Sủng thú huyền thoại:** 0.1% drop khi nhận thưởng."
                ),
                inline=False)
            embed.add_field(name="💡  Mẹo",
                value=(
                    "• Nâng cao **Công Kích** và trang bị **Công Pháp** tốt để gây thêm sát thương.\n"
                    "• Đánh càng nhiều lần → tổng damage càng cao → thứ hạng càng tốt.\n"
                    "• **Bạo Kích** và **Hồi Tâm** ảnh hưởng trực tiếp đến damage mỗi hiệp!"
                ),
                inline=False)
            await inter.response.send_message(embed=embed, ephemeral=True)

        btn_ket_qua.callback = _ket_qua
        btn_guide.callback   = _guide
        async def _do_back_boss(i): await _back_to_hoso(i, self.parent)
        btn_back.callback    = _do_back_boss
        self.add_item(btn_ket_qua)
        self.add_item(btn_guide)
        self.add_item(btn_back)

    # 1 message per boss: {boss_id: {guild_id: Message}}
    _boss_msg:  dict = {}
    # Lock per boss để serialize edit
    _boss_lock: dict = {}

    @classmethod
    def _get_lock(cls, boss_id: int) -> asyncio.Lock:
        if boss_id not in cls._boss_lock:
            cls._boss_lock[boss_id] = asyncio.Lock()
        return cls._boss_lock[boss_id]

    @classmethod
    def _get_guild_msg(cls, boss_id: int, guild_id: int):
        val = cls._boss_msg.get(boss_id)
        if val is None:
            return None
        if not isinstance(val, dict):
            return val
        return val.get(guild_id)

    @classmethod
    def _set_guild_msg(cls, boss_id: int, guild_id: int, msg):
        existing = cls._boss_msg.get(boss_id)
        if existing is not None and not isinstance(existing, dict):
            cls._boss_msg[boss_id] = {}
        cls._boss_msg.setdefault(boss_id, {})[guild_id] = msg

    @classmethod
    def _pop_boss_msg(cls, boss_id: int):
        cls._boss_msg.pop(boss_id, None)


# ══════════════════════════════════════════════════════════════
#  ĐĂNG KÝ MODAL
# ══════════════════════════════════════════════════════════════
